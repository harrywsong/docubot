"""
Unit tests for ResourceMonitor class.

Tests memory monitoring, health checks, and query metrics logging.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from backend.resource_monitor import ResourceMonitor
from backend.config import Config
from backend.models import MemoryStats, HealthStatus


class TestResourceMonitor:
    """Test suite for ResourceMonitor class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        return config
    
    @pytest.fixture
    def resource_monitor(self, mock_config):
        """Create ResourceMonitor instance."""
        return ResourceMonitor(mock_config)
    
    def test_init(self, resource_monitor, mock_config):
        """Test ResourceMonitor initialization."""
        assert resource_monitor.config == mock_config
        assert resource_monitor.model_loaded is False
        assert resource_monitor.vector_store_loaded is False
        assert resource_monitor.total_chunks == 0
        assert resource_monitor.last_query_time is None
        assert resource_monitor._memory_threshold == 90.0
    
    @patch('psutil.virtual_memory')
    def test_get_memory_usage(self, mock_virtual_memory, resource_monitor):
        """Test getting memory usage statistics."""
        # Mock psutil memory data
        mock_memory = Mock()
        mock_memory.used = 2 * 1024 ** 3  # 2GB
        mock_memory.available = 2 * 1024 ** 3  # 2GB
        mock_memory.total = 4 * 1024 ** 3  # 4GB
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        result = resource_monitor.get_memory_usage()
        
        assert isinstance(result, MemoryStats)
        assert result.used_mb == pytest.approx(2048.0, rel=0.1)
        assert result.available_mb == pytest.approx(2048.0, rel=0.1)
        assert result.total_mb == pytest.approx(4096.0, rel=0.1)
        assert result.percent == 50.0
    
    @patch('psutil.virtual_memory')
    def test_get_system_health_healthy(self, mock_virtual_memory, resource_monitor):
        """Test system health when memory usage is normal."""
        # Mock psutil memory data (50% usage)
        mock_memory = Mock()
        mock_memory.used = 2 * 1024 ** 3
        mock_memory.available = 2 * 1024 ** 3
        mock_memory.total = 4 * 1024 ** 3
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        # Set some status
        resource_monitor.set_model_loaded(True)
        resource_monitor.set_vector_store_loaded(True, 100)
        resource_monitor.last_query_time = 1.5
        
        result = resource_monitor.get_system_health()
        
        assert isinstance(result, HealthStatus)
        assert result.status == "healthy"
        assert result.memory_usage_percent == 50.0
        assert result.memory_available_mb == pytest.approx(2048.0, rel=0.1)
        assert result.model_loaded is True
        assert result.vector_store_loaded is True
        assert result.total_chunks == 100
        assert result.last_query_time == 1.5
    
    @patch('psutil.virtual_memory')
    def test_get_system_health_warning(self, mock_virtual_memory, resource_monitor):
        """Test system health when memory usage is at warning level."""
        # Mock psutil memory data (92% usage)
        mock_memory = Mock()
        mock_memory.used = 3.68 * 1024 ** 3
        mock_memory.available = 0.32 * 1024 ** 3
        mock_memory.total = 4 * 1024 ** 3
        mock_memory.percent = 92.0
        mock_virtual_memory.return_value = mock_memory
        
        result = resource_monitor.get_system_health()
        
        assert result.status == "warning"
        assert result.memory_usage_percent == 92.0
    
    @patch('psutil.virtual_memory')
    def test_get_system_health_critical(self, mock_virtual_memory, resource_monitor):
        """Test system health when memory usage is critical."""
        # Mock psutil memory data (96% usage)
        mock_memory = Mock()
        mock_memory.used = 3.84 * 1024 ** 3
        mock_memory.available = 0.16 * 1024 ** 3
        mock_memory.total = 4 * 1024 ** 3
        mock_memory.percent = 96.0
        mock_virtual_memory.return_value = mock_memory
        
        result = resource_monitor.get_system_health()
        
        assert result.status == "critical"
        assert result.memory_usage_percent == 96.0
    
    def test_log_query_metrics(self, resource_monitor, caplog):
        """Test logging query metrics."""
        import logging
        caplog.set_level(logging.INFO)
        
        query_time = 2.5
        memory_delta = 10 * 1024 * 1024  # 10MB
        
        resource_monitor.log_query_metrics(query_time, memory_delta)
        
        assert resource_monitor.last_query_time == 2.5
        assert "Query processed in 2.50s" in caplog.text
        assert "memory delta: 10.00MB" in caplog.text
    
    @patch('psutil.virtual_memory')
    def test_check_memory_threshold_normal(self, mock_virtual_memory, resource_monitor):
        """Test memory threshold check when usage is normal."""
        # Mock psutil memory data (50% usage)
        mock_memory = Mock()
        mock_memory.used = 2 * 1024 ** 3
        mock_memory.available = 2 * 1024 ** 3
        mock_memory.total = 4 * 1024 ** 3
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        result = resource_monitor.check_memory_threshold()
        
        assert result is False
    
    @patch('psutil.virtual_memory')
    def test_check_memory_threshold_exceeded(self, mock_virtual_memory, resource_monitor, caplog):
        """Test memory threshold check when usage exceeds 90%."""
        import logging
        caplog.set_level(logging.WARNING)
        
        # Mock psutil memory data (92% usage)
        mock_memory = Mock()
        mock_memory.used = 3.68 * 1024 ** 3
        mock_memory.available = 0.32 * 1024 ** 3
        mock_memory.total = 4 * 1024 ** 3
        mock_memory.percent = 92.0
        mock_virtual_memory.return_value = mock_memory
        
        result = resource_monitor.check_memory_threshold()
        
        assert result is True
        assert "Memory usage critical: 92.0%" in caplog.text
    
    def test_set_model_loaded(self, resource_monitor):
        """Test setting model loaded status."""
        assert resource_monitor.model_loaded is False
        
        resource_monitor.set_model_loaded(True)
        assert resource_monitor.model_loaded is True
        
        resource_monitor.set_model_loaded(False)
        assert resource_monitor.model_loaded is False
    
    def test_set_vector_store_loaded(self, resource_monitor):
        """Test setting vector store loaded status."""
        assert resource_monitor.vector_store_loaded is False
        assert resource_monitor.total_chunks == 0
        
        resource_monitor.set_vector_store_loaded(True, 250)
        assert resource_monitor.vector_store_loaded is True
        assert resource_monitor.total_chunks == 250
        
        resource_monitor.set_vector_store_loaded(False, 0)
        assert resource_monitor.vector_store_loaded is False
        assert resource_monitor.total_chunks == 0
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    async def test_log_memory_periodically(self, mock_virtual_memory, resource_monitor, caplog):
        """Test periodic memory logging."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Mock psutil memory data
        mock_memory = Mock()
        mock_memory.used = 2 * 1024 ** 3
        mock_memory.available = 2 * 1024 ** 3
        mock_memory.total = 4 * 1024 ** 3
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        # Start monitoring
        resource_monitor.start_monitoring()
        
        # Wait a bit for the first log
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        resource_monitor.stop_monitoring()
        
        # Wait for task to complete
        await asyncio.sleep(0.1)
        
        # Check that memory was logged
        assert "Memory usage: 50.0%" in caplog.text
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, resource_monitor):
        """Test starting memory monitoring."""
        assert resource_monitor._monitoring_task is None
        
        resource_monitor.start_monitoring()
        
        assert resource_monitor._monitoring_task is not None
        assert not resource_monitor._monitoring_task.done()
        
        # Clean up
        resource_monitor.stop_monitoring()
        await asyncio.sleep(0.1)
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, resource_monitor):
        """Test stopping memory monitoring."""
        resource_monitor.start_monitoring()
        assert resource_monitor._monitoring_task is not None
        
        resource_monitor.stop_monitoring()
        
        # Wait for cancellation
        await asyncio.sleep(0.1)
        
        # Task should be cancelled
        assert resource_monitor._monitoring_task.cancelled() or resource_monitor._monitoring_task.done()
    
    def test_stop_monitoring_when_not_started(self, resource_monitor):
        """Test stopping monitoring when it was never started."""
        # Should not raise an error
        resource_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    async def test_monitoring_continues_on_error(self, mock_virtual_memory, resource_monitor, caplog):
        """Test that monitoring continues even if an error occurs."""
        import logging
        caplog.set_level(logging.ERROR)
        
        # Mock psutil to raise an error first, then work
        mock_virtual_memory.side_effect = [
            Exception("Test error"),
            Mock(used=2*1024**3, available=2*1024**3, total=4*1024**3, percent=50.0)
        ]
        
        # Start monitoring
        resource_monitor.start_monitoring()
        
        # Wait for error to occur
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        resource_monitor.stop_monitoring()
        
        # Check that error was logged
        assert "Error in memory monitoring" in caplog.text


class TestResourceMonitorIntegration:
    """Integration tests for ResourceMonitor."""
    
    @pytest.fixture
    def config(self):
        """Create real configuration."""
        return Config()
    
    @pytest.fixture
    def resource_monitor(self, config):
        """Create ResourceMonitor with real config."""
        return ResourceMonitor(config)
    
    def test_real_memory_usage(self, resource_monitor):
        """Test getting real memory usage from system."""
        result = resource_monitor.get_memory_usage()
        
        assert isinstance(result, MemoryStats)
        assert result.used_mb > 0
        assert result.available_mb > 0
        assert result.total_mb > 0
        assert 0 <= result.percent <= 100
        assert result.validate()
    
    def test_real_system_health(self, resource_monitor):
        """Test getting real system health."""
        result = resource_monitor.get_system_health()
        
        assert isinstance(result, HealthStatus)
        assert result.status in ("healthy", "warning", "critical")
        assert 0 <= result.memory_usage_percent <= 100
        assert result.memory_available_mb > 0
        assert result.validate()

"""
Resource monitoring for Pi server.

Monitors memory usage, system health, and query metrics.

Enhanced with:
- Error logging with timestamps and context
"""

import logging
import psutil
import time
import asyncio
from typing import Optional
from datetime import datetime
from backend.config import Config
from backend.models import MemoryStats, HealthStatus


logger = logging.getLogger(__name__)


class ResourceMonitor:
    """
    Monitors Pi resource usage and system health.
    
    Features:
    - Memory usage monitoring every 60 seconds
    - System health status tracking
    - Query metrics logging
    - Error logging with timestamps and context
    
    Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 14.4
    """
    
    def __init__(self, config: Config):
        """
        Initialize resource monitor.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.model_loaded = False
        self.vector_store_loaded = False
        self.total_chunks = 0
        self.last_query_time: Optional[float] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._memory_threshold = 90.0  # 90% warning threshold
        self._log_with_context("ResourceMonitor initialized")
    
    def _log_with_context(self, message: str, level: str = "info", error: Optional[Exception] = None):
        """
        Log message with timestamp and context.
        
        Args:
            message: Log message
            level: Log level (info, warning, error, critical)
            error: Optional exception for error context
        
        Requirements: 14.4
        """
        timestamp = datetime.now().isoformat()
        context = f"[{timestamp}] [ResourceMonitor]"
        
        log_func = getattr(logger, level.lower(), logger.info)
        
        if error:
            log_func(f"{context} {message}: {str(error)}", exc_info=True)
        else:
            log_func(f"{context} {message}")
        
    def get_memory_usage(self) -> MemoryStats:
        """
        Get current memory usage statistics.
        
        Returns:
            MemoryStats with used, available, total, and percentage
        """
        memory = psutil.virtual_memory()
        
        return MemoryStats(
            used_mb=memory.used / (1024 * 1024),
            available_mb=memory.available / (1024 * 1024),
            total_mb=memory.total / (1024 * 1024),
            percent=memory.percent
        )
    
    def get_system_health(self) -> HealthStatus:
        """
        Get overall system health status.
        
        Returns:
            HealthStatus with memory, model, and vector store status
        """
        memory_stats = self.get_memory_usage()
        
        # Determine health status based on memory usage
        if memory_stats.percent >= 95.0:
            status = "critical"
        elif memory_stats.percent >= self._memory_threshold:
            status = "warning"
        else:
            status = "healthy"
        
        return HealthStatus(
            status=status,
            memory_usage_percent=memory_stats.percent,
            memory_available_mb=memory_stats.available_mb,
            model_loaded=self.model_loaded,
            vector_store_loaded=self.vector_store_loaded,
            total_chunks=self.total_chunks,
            last_query_time=self.last_query_time
        )
    
    def log_query_metrics(self, query_time: float, memory_delta: int):
        """
        Log metrics for a query with timestamp and context.
        
        Args:
            query_time: Time taken to process query (seconds)
            memory_delta: Change in memory usage (bytes)
        
        Requirements: 13.3, 14.4
        """
        self.last_query_time = query_time
        
        self._log_with_context(
            f"Query processed in {query_time:.2f}s, "
            f"memory delta: {memory_delta / (1024 * 1024):.2f}MB"
        )
    
    def check_memory_threshold(self) -> bool:
        """
        Check if memory usage exceeds warning threshold (90%).
        
        Returns:
            True if memory usage is critical (>= 90%)
        
        Requirements: 13.2
        """
        memory_stats = self.get_memory_usage()
        
        if memory_stats.percent >= self._memory_threshold:
            self._log_with_context(
                f"Memory usage critical: {memory_stats.percent:.1f}% "
                f"({memory_stats.used_mb:.1f}MB used, "
                f"{memory_stats.available_mb:.1f}MB available)",
                level="warning"
            )
            return True
        
        return False
    
    async def _log_memory_periodically(self):
        """
        Background task to log memory usage every 60 seconds.
        
        Requirements: 13.1
        """
        while True:
            try:
                memory_stats = self.get_memory_usage()
                self._log_with_context(
                    f"Memory usage: {memory_stats.percent:.1f}% "
                    f"({memory_stats.used_mb:.1f}MB used, "
                    f"{memory_stats.available_mb:.1f}MB available)"
                )
                
                # Check threshold and log warning if exceeded
                self.check_memory_threshold()
                
                await asyncio.sleep(60)  # Log every 60 seconds
                
            except asyncio.CancelledError:
                self._log_with_context("Memory monitoring task cancelled")
                break
            except Exception as e:
                self._log_with_context("Error in memory monitoring", level="error", error=e)
                await asyncio.sleep(60)  # Continue monitoring even on error
    
    def start_monitoring(self):
        """Start background task for logging memory every 60 seconds."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._log_memory_periodically())
            self._log_with_context("Started memory monitoring (60s interval)")
    
    def stop_monitoring(self):
        """Stop background memory monitoring task."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            self._log_with_context("Stopped memory monitoring")
    
    def set_model_loaded(self, loaded: bool):
        """
        Set model loaded status.
        
        Args:
            loaded: True if model is loaded
        """
        self.model_loaded = loaded
    
    def set_vector_store_loaded(self, loaded: bool, total_chunks: int = 0):
        """
        Set vector store loaded status.
        
        Args:
            loaded: True if vector store is loaded
            total_chunks: Total number of chunks in vector store
        """
        self.vector_store_loaded = loaded
        self.total_chunks = total_chunks

"""
End-to-End Integration Tests for Desktop-Pi RAG Pipeline

Tests complete workflows:
1. Desktop workflow: process → validate → export
2. Pi workflow: load → query → respond
3. Transfer workflow: export → transfer → load → query
4. Incremental workflow: process new → export incremental → merge → query
5. Model compatibility validation
6. Resource monitoring under load

Requirements: All requirements (1-15)
"""

import pytest
import tempfile
import shutil
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

from backend.config import Config
from backend.vector_store import VectorStore
from backend.database import DatabaseManager
from backend.export_manager import ExportManager
from backend.data_loader import DataLoader
from backend.incremental_merger import IncrementalMerger
from backend.processing_validator import ProcessingValidator
from backend.resource_monitor import ResourceMonitor
from backend.document_processor import DocumentProcessor
from backend.embedding_engine import EmbeddingEngine
from backend.models import DocumentChunk


@pytest.fixture
def temp_dir():
    """Create temporary directory for test data."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def desktop_config(temp_dir):
    """Create desktop configuration for testing."""
    config = Config()
    config.CHROMADB_PATH = str(Path(temp_dir) / "desktop" / "chromadb")
    config.SQLITE_PATH = str(Path(temp_dir) / "desktop" / "app.db")
    config.ENABLE_DOCUMENT_PROCESSING = True
    config.EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    config.CONVERSATIONAL_MODEL = "qwen2.5:3b"
    config.OLLAMA_MODEL = "qwen2.5vl:7b"
    
    # Create directories
    Path(config.CHROMADB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(config.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    return config


@pytest.fixture
def pi_config(temp_dir):
    """Create Pi configuration for testing."""
    config = Config()
    config.CHROMADB_PATH = str(Path(temp_dir) / "pi" / "data" / "chromadb")
    config.SQLITE_PATH = str(Path(temp_dir) / "pi" / "data" / "app.db")
    config.MANIFEST_PATH = str(Path(temp_dir) / "pi" / "data" / "manifest.json")
    config.ENABLE_DOCUMENT_PROCESSING = False
    config.EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    config.CONVERSATIONAL_MODEL = "qwen2.5:3b"
    
    # Create directories
    Path(config.CHROMADB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(config.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    return config


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        {
            "content": "Python is a high-level programming language known for its simplicity and readability.",
            "metadata": {"filename": "python.txt", "folder_path": "/docs", "file_type": "text"}
        },
        {
            "content": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
            "metadata": {"filename": "ml.txt", "folder_path": "/docs", "file_type": "text"}
        },
        {
            "content": "The Raspberry Pi is a small, affordable computer used for education and embedded systems.",
            "metadata": {"filename": "raspberry_pi.txt", "folder_path": "/docs", "file_type": "text"}
        }
    ]


class TestDesktopWorkflow:
    """Test complete desktop workflow: process → validate → export."""
    
    def test_desktop_workflow_full_cycle(self, desktop_config, sample_documents, temp_dir):
        """
        Test complete desktop workflow from document processing to export.
        
        Workflow:
        1. Initialize components
        2. Process documents (add chunks with embeddings)
        3. Validate processing
        4. Create export package
        5. Validate export package
        
        Requirements: 1.1-1.5, 2.1-2.4, 3.1-3.5, 15.1-15.5
        """
        # Step 1: Initialize components
        vector_store = VectorStore(persist_directory=desktop_config.CHROMADB_PATH)
        vector_store.initialize()
        
        db_manager = DatabaseManager(db_path=desktop_config.SQLITE_PATH)
        
        # Mock embedding engine to avoid actual model loading
        with patch('backend.embedding_engine.EmbeddingEngine') as MockEmbedding:
            mock_embedding_engine = Mock()
            mock_embedding_engine.generate_embeddings.return_value = [[0.1] * 384 for _ in sample_documents]
            mock_embedding_engine.get_embedding_dimension.return_value = 384
            MockEmbedding.return_value = mock_embedding_engine
            
            # Step 2: Process documents (simulate document processing)
            chunks = []
            for doc in sample_documents:
                chunk = DocumentChunk(
                    content=doc["content"],
                    metadata=doc["metadata"],
                    embedding=[0.1] * 384  # Mock embedding
                )
                chunks.append(chunk)
            
            # Add chunks to vector store
            vector_store.add_chunks(chunks)
            
            # Add to database
            with db_manager.transaction() as conn:
                # First insert folder
                conn.execute("INSERT OR IGNORE INTO folders (id, path) VALUES (?, ?)", (1, "/docs"))
                
                for doc in sample_documents:
                    conn.execute("""
                        INSERT INTO processed_files (file_path, folder_id, file_hash, modified_at, processed_at, file_type)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        f"{doc['metadata']['folder_path']}/{doc['metadata']['filename']}",
                        1,
                        "test_hash",
                        datetime.now(),
                        datetime.now(),
                        doc['metadata']['file_type']
                    ))
            
            # Step 3: Validate processing
            validator = ProcessingValidator(vector_store, db_manager)
            report = validator.validate_processing()
            
            assert report.validation_passed, "Processing validation should pass"
            assert report.total_documents == len(sample_documents)
            assert report.total_chunks == len(sample_documents)
            assert report.total_embeddings == len(sample_documents)
            assert len(report.missing_embeddings) == 0
            assert len(report.incomplete_metadata) == 0
            
            # Step 4: Create export package
            export_manager = ExportManager(desktop_config, vector_store, db_manager)
            export_dir = Path(temp_dir) / "export"
            
            result = export_manager.create_export_package(output_dir=str(export_dir))
            
            assert result.success, f"Export should succeed: {result.errors}"
            assert Path(result.package_path).exists()
            assert Path(result.archive_path).exists()
            assert result.size_bytes > 0
            assert result.statistics['total_documents'] == len(sample_documents)
            assert result.statistics['total_chunks'] == len(sample_documents)
            
            # Step 5: Validate export package
            validation = export_manager.validate_export_package(result.package_path)
            
            assert validation.valid, f"Export package should be valid: {validation.errors}"
            assert len(validation.errors) == 0
    
    def test_desktop_workflow_with_validation_failure(self, desktop_config, temp_dir):
        """
        Test desktop workflow when validation fails (missing embeddings).
        
        Requirements: 15.5
        """
        # Initialize components
        vector_store = VectorStore(persist_directory=desktop_config.CHROMADB_PATH)
        vector_store.initialize()
        
        db_manager = DatabaseManager(db_path=desktop_config.SQLITE_PATH)
        
        # Don't add any chunks - empty vector store
        
        # Try to export
        export_manager = ExportManager(desktop_config, vector_store, db_manager)
        export_dir = Path(temp_dir) / "export"
        
        result = export_manager.create_export_package(output_dir=str(export_dir))
        
        # Export should fail due to empty vector store
        assert not result.success
        assert len(result.errors) > 0
        assert any("nothing to export" in error.lower() for error in result.errors)


class TestPiWorkflow:
    """Test complete Pi workflow: load → query → respond."""
    
    def test_pi_workflow_full_cycle(self, pi_config, desktop_config, sample_documents, temp_dir):
        """
        Test complete Pi workflow from data loading to query processing.
        
        Workflow:
        1. Create export package on desktop
        2. Transfer to Pi location
        3. Load data on Pi
        4. Validate manifest
        5. Process query
        6. Monitor resources
        
        Requirements: 4.1-4.5, 6.1-6.5, 7.1-7.5, 13.1-13.5
        """
        # Step 1: Create export package on desktop
        vector_store = VectorStore(persist_directory=desktop_config.CHROMADB_PATH)
        vector_store.initialize()
        
        db_manager = DatabaseManager(db_path=desktop_config.SQLITE_PATH)
        
        # Add sample data
        chunks = []
        for doc in sample_documents:
            chunk = DocumentChunk(
                content=doc["content"],
                metadata=doc["metadata"],
                embedding=[0.1] * 384
            )
            chunks.append(chunk)
        
        vector_store.add_chunks(chunks)
        
        with db_manager.transaction() as conn:
            # First insert folder
            conn.execute("INSERT OR IGNORE INTO folders (id, path) VALUES (?, ?)", (1, "/docs"))
            
            for doc in sample_documents:
                conn.execute("""
                    INSERT INTO processed_files (file_path, folder_id, file_hash, modified_at, processed_at, file_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"{doc['metadata']['folder_path']}/{doc['metadata']['filename']}",
                    1,
                    "test_hash",
                    datetime.now(),
                    datetime.now(),
                    doc['metadata']['file_type']
                ))
        
        export_manager = ExportManager(desktop_config, vector_store, db_manager)
        export_dir = Path(temp_dir) / "export"
        
        with patch('backend.embedding_engine.EmbeddingEngine') as MockEmbedding:
            mock_embedding_engine = Mock()
            mock_embedding_engine.get_embedding_dimension.return_value = 384
            MockEmbedding.return_value = mock_embedding_engine
            
            result = export_manager.create_export_package(output_dir=str(export_dir))
            assert result.success
        
        # Step 2: Transfer to Pi location (simulate by copying)
        pi_data_dir = Path(pi_config.CHROMADB_PATH).parent
        shutil.copytree(Path(result.package_path) / "chromadb", pi_data_dir / "chromadb")
        shutil.copy(Path(result.package_path) / "app.db", pi_data_dir / "app.db")
        shutil.copy(Path(result.package_path) / "manifest.json", pi_data_dir / "manifest.json")
        
        # Step 3: Load data on Pi
        data_loader = DataLoader(pi_config)
        
        with patch('backend.embedding_engine.EmbeddingEngine') as MockEmbedding:
            mock_embedding_engine = Mock()
            mock_embedding_engine.get_embedding_dimension.return_value = 384
            MockEmbedding.return_value = mock_embedding_engine
            
            pi_vector_store = data_loader.load_vector_store()
            pi_db_manager = data_loader.load_database()
            
            # Verify data loaded correctly
            assert pi_vector_store is not None
            assert pi_db_manager is not None
            
            stats = pi_vector_store.get_stats()
            assert stats['total_chunks'] == len(sample_documents)
            
            # Step 4: Validate manifest
            manifest_validation = data_loader.validate_manifest()
            
            assert manifest_validation.valid or len(manifest_validation.errors) == 0
            
            # Step 5: Process query (mock query engine)
            query = "What is Python?"
            
            # Mock query processing
            results = pi_vector_store.query(query_embedding=[0.1] * 384, top_k=3)
            
            assert len(results) > 0
            assert any("Python" in result.content for result in results)
            
            # Step 6: Monitor resources
            resource_monitor = ResourceMonitor(pi_config)
            
            # Set vector store loaded status
            resource_monitor.set_vector_store_loaded(True, total_chunks=len(sample_documents))
            
            memory_stats = resource_monitor.get_memory_usage()
            assert memory_stats.used_mb > 0
            assert memory_stats.available_mb > 0
            assert 0 <= memory_stats.percent <= 100
            
            health_status = resource_monitor.get_system_health()
            assert health_status.status in ["healthy", "warning", "critical"]
            assert health_status.vector_store_loaded is True


class TestTransferWorkflow:
    """Test complete transfer workflow: export → transfer → load → query."""
    
    def test_transfer_workflow_full_cycle(self, desktop_config, pi_config, sample_documents, temp_dir):
        """
        Test complete transfer workflow from desktop export to Pi query.
        
        Workflow:
        1. Process documents on desktop
        2. Export package
        3. Transfer package (simulate)
        4. Load on Pi
        5. Query on Pi
        6. Verify results match original data
        
        Requirements: 3.1-3.5, 4.1-4.5, 9.1-9.5, 12.1-12.5
        """
        # Step 1 & 2: Process and export on desktop
        desktop_vs = VectorStore(persist_directory=desktop_config.CHROMADB_PATH)
        desktop_vs.initialize()
        
        desktop_db = DatabaseManager(db_path=desktop_config.SQLITE_PATH)
        
        chunks = []
        for doc in sample_documents:
            chunk = DocumentChunk(
                content=doc["content"],
                metadata=doc["metadata"],
                embedding=[0.1] * 384
            )
            chunks.append(chunk)
        
        desktop_vs.add_chunks(chunks)
        
        with desktop_db.transaction() as conn:
            # First insert folder
            conn.execute("INSERT OR IGNORE INTO folders (id, path) VALUES (?, ?)", (1, "/docs"))
            
            for doc in sample_documents:
                conn.execute("""
                    INSERT INTO processed_files (file_path, folder_id, file_hash, modified_at, processed_at, file_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"{doc['metadata']['folder_path']}/{doc['metadata']['filename']}",
                    1,
                    "test_hash",
                    datetime.now(),
                    datetime.now(),
                    doc['metadata']['file_type']
                ))
        
        export_manager = ExportManager(desktop_config, desktop_vs, desktop_db)
        export_dir = Path(temp_dir) / "export"
        
        with patch('backend.embedding_engine.EmbeddingEngine') as MockEmbedding:
            mock_embedding_engine = Mock()
            mock_embedding_engine.get_embedding_dimension.return_value = 384
            MockEmbedding.return_value = mock_embedding_engine
            
            result = export_manager.create_export_package(output_dir=str(export_dir))
            assert result.success
            
            # Verify deployment instructions generated
            instructions = export_manager.generate_deployment_instructions(result.package_path)
            assert "Transfer Instructions" in instructions
            assert "Installation Instructions" in instructions
            assert "scp" in instructions or "rsync" in instructions
            assert pi_config.CONVERSATIONAL_MODEL in instructions
        
        # Step 3: Transfer (simulate by copying)
        pi_data_dir = Path(pi_config.CHROMADB_PATH).parent
        shutil.copytree(Path(result.package_path) / "chromadb", pi_data_dir / "chromadb")
        shutil.copy(Path(result.package_path) / "app.db", pi_data_dir / "app.db")
        shutil.copy(Path(result.package_path) / "manifest.json", pi_data_dir / "manifest.json")
        
        # Step 4: Load on Pi
        data_loader = DataLoader(pi_config)
        
        with patch('backend.embedding_engine.EmbeddingEngine') as MockEmbedding:
            mock_embedding_engine = Mock()
            mock_embedding_engine.get_embedding_dimension.return_value = 384
            MockEmbedding.return_value = mock_embedding_engine
            
            pi_vs = data_loader.load_vector_store()
            pi_db = data_loader.load_database()
            
            # Step 5: Query on Pi
            query_results = pi_vs.query(query_embedding=[0.1] * 384, top_k=3)
            
            # Step 6: Verify results match original data
            assert len(query_results) == len(sample_documents)
            
            # Verify content matches
            desktop_results = desktop_vs.query(query_embedding=[0.1] * 384, top_k=3)
            
            assert len(query_results) == len(desktop_results)
            
            for pi_result, desktop_result in zip(query_results, desktop_results):
                assert pi_result.content == desktop_result.content
                assert pi_result.metadata == desktop_result.metadata


class TestIncrementalWorkflow:
    """Test complete incremental workflow: process new → export incremental → merge → query."""
    
    def test_incremental_workflow_full_cycle(self, desktop_config, pi_config, sample_documents, temp_dir):
        """
        Test complete incremental update workflow.
        
        Workflow:
        1. Create initial export
        2. Transfer and load on Pi
        3. Add new documents on desktop
        4. Create incremental export
        5. Transfer incremental package
        6. Merge on Pi
        7. Query updated data
        
        Requirements: 11.1-11.5
        """
        # Step 1: Create initial export
        desktop_vs = VectorStore(persist_directory=desktop_config.CHROMADB_PATH)
        desktop_vs.initialize()
        
        desktop_db = DatabaseManager(db_path=desktop_config.SQLITE_PATH)
        
        # Add initial documents
        initial_docs = sample_documents[:2]  # First 2 documents
        chunks = []
        for doc in initial_docs:
            chunk = DocumentChunk(
                content=doc["content"],
                metadata=doc["metadata"],
                embedding=[0.1] * 384
            )
            chunks.append(chunk)
        
        desktop_vs.add_chunks(chunks)
        
        base_timestamp = datetime.now()
        
        with desktop_db.transaction() as conn:
            # First insert folder
            conn.execute("INSERT OR IGNORE INTO folders (id, path) VALUES (?, ?)", (1, "/docs"))
            
            for doc in initial_docs:
                conn.execute("""
                    INSERT INTO processed_files (file_path, folder_id, file_hash, modified_at, processed_at, file_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"{doc['metadata']['folder_path']}/{doc['metadata']['filename']}",
                    1,
                    "test_hash",
                    base_timestamp,
                    base_timestamp,
                    doc['metadata']['file_type']
                ))
        
        export_manager = ExportManager(desktop_config, desktop_vs, desktop_db)
        export_dir = Path(temp_dir) / "export_initial"
        
        with patch('backend.embedding_engine.EmbeddingEngine') as MockEmbedding:
            mock_embedding_engine = Mock()
            mock_embedding_engine.get_embedding_dimension.return_value = 384
            MockEmbedding.return_value = mock_embedding_engine
            
            result = export_manager.create_export_package(output_dir=str(export_dir))
            assert result.success
        
        # Step 2: Transfer and load on Pi
        pi_data_dir = Path(pi_config.CHROMADB_PATH).parent
        shutil.copytree(Path(result.package_path) / "chromadb", pi_data_dir / "chromadb")
        shutil.copy(Path(result.package_path) / "app.db", pi_data_dir / "app.db")
        shutil.copy(Path(result.package_path) / "manifest.json", pi_data_dir / "manifest.json")
        
        data_loader = DataLoader(pi_config)
        
        with patch('backend.embedding_engine.EmbeddingEngine') as MockEmbedding:
            mock_embedding_engine = Mock()
            mock_embedding_engine.get_embedding_dimension.return_value = 384
            MockEmbedding.return_value = mock_embedding_engine
            
            pi_vs = data_loader.load_vector_store()
            pi_db = data_loader.load_database()
            
            # Verify initial data
            stats = pi_vs.get_stats()
            assert stats['total_chunks'] == len(initial_docs)
        
        # Step 3: Add new documents on desktop
        time.sleep(0.1)  # Ensure timestamp difference
        new_timestamp = datetime.now()
        
        new_docs = sample_documents[2:]  # Last document
        new_chunks = []
        for doc in new_docs:
            chunk = DocumentChunk(
                content=doc["content"],
                metadata=doc["metadata"],
                embedding=[0.2] * 384  # Different embedding
            )
            new_chunks.append(chunk)
        
        desktop_vs.add_chunks(new_chunks)
        
        with desktop_db.transaction() as conn:
            for doc in new_docs:
                conn.execute("""
                    INSERT INTO processed_files (file_path, folder_id, file_hash, modified_at, processed_at, file_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"{doc['metadata']['folder_path']}/{doc['metadata']['filename']}",
                    1,
                    "test_hash_new",
                    new_timestamp,
                    new_timestamp,
                    doc['metadata']['file_type']
                ))
        
        # Step 4: Create incremental export
        export_dir_inc = Path(temp_dir) / "export_incremental"
        
        with patch('backend.embedding_engine.EmbeddingEngine') as MockEmbedding:
            mock_embedding_engine = Mock()
            mock_embedding_engine.get_embedding_dimension.return_value = 384
            MockEmbedding.return_value = mock_embedding_engine
            
            result_inc = export_manager.create_export_package(
                output_dir=str(export_dir_inc),
                incremental=True,
                since_timestamp=base_timestamp
            )
            assert result_inc.success
            
            # Verify incremental export contains only new data
            assert result_inc.statistics.get('new_chunks', 0) == len(new_docs)
        
        # Step 5: Transfer incremental package
        inc_package_dir = Path(temp_dir) / "pi_incremental"
        shutil.copytree(Path(result_inc.package_path), inc_package_dir)
        
        # Step 6: Merge on Pi
        # Need to disable read-only mode for merging
        pi_vs_merge = VectorStore(persist_directory=pi_config.CHROMADB_PATH, read_only=False)
        pi_vs_merge.initialize()
        
        merger = IncrementalMerger(pi_vs_merge, pi_db)
        
        merge_result = merger.merge_incremental_package(str(inc_package_dir))
        
        assert merge_result.success, f"Merge should succeed: {merge_result.errors}"
        assert merge_result.merged_chunks == len(new_docs)
        
        # Step 7: Query updated data
        updated_stats = pi_vs_merge.get_stats()
        assert updated_stats['total_chunks'] == len(sample_documents)
        
        # Verify all documents are queryable
        query_results = pi_vs_merge.query(query_embedding=[0.1] * 384, top_k=5)
        assert len(query_results) >= len(sample_documents)


class TestModelCompatibility:
    """Test model compatibility validation."""
    
    def test_embedding_dimension_compatibility(self, desktop_config, pi_config, temp_dir):
        """
        Test that embedding dimension mismatch is detected.
        
        Requirements: 12.2, 12.3
        """
        # Create export with 384-dim embeddings
        desktop_vs = VectorStore(persist_directory=desktop_config.CHROMADB_PATH)
        desktop_vs.initialize()
        
        desktop_db = DatabaseManager(db_path=desktop_config.SQLITE_PATH)
        
        chunk = DocumentChunk(
            content="Test content",
            metadata={"filename": "test.txt", "folder_path": "/docs", "file_type": "text"},
            embedding=[0.1] * 384
        )
        desktop_vs.add_chunks([chunk])
        
        with desktop_db.transaction() as conn:
            conn.execute("INSERT OR IGNORE INTO folders (id, path) VALUES (?, ?)", (1, "/docs"))
            conn.execute("""
                INSERT INTO processed_files (file_path, folder_id, file_hash, modified_at, processed_at, file_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("/docs/test.txt", 1, "hash", datetime.now(), datetime.now(), "text"))
        
        export_manager = ExportManager(desktop_config, desktop_vs, desktop_db)
        export_dir = Path(temp_dir) / "export"
        
        with patch('backend.embedding_engine.EmbeddingEngine') as MockEmbedding:
            mock_embedding_engine = Mock()
            mock_embedding_engine.get_embedding_dimension.return_value = 384
            MockEmbedding.return_value = mock_embedding_engine
            
            result = export_manager.create_export_package(output_dir=str(export_dir))
            assert result.success
        
        # Transfer to Pi
        pi_data_dir = Path(pi_config.CHROMADB_PATH).parent
        shutil.copytree(Path(result.package_path) / "chromadb", pi_data_dir / "chromadb")
        shutil.copy(Path(result.package_path) / "app.db", pi_data_dir / "app.db")
        shutil.copy(Path(result.package_path) / "manifest.json", pi_data_dir / "manifest.json")
        
        # Mock Pi with different embedding dimension
        data_loader = DataLoader(pi_config)
        
        # Patch the EmbeddingEngine at the point where it's imported in data_loader
        with patch('backend.data_loader.EmbeddingEngine') as MockEmbedding:
            # Create a mock that returns different dimensions
            mock_embedding_engine = Mock()
            mock_embedding_engine.get_embedding_dimension.return_value = 512  # Different dimension!
            MockEmbedding.return_value = mock_embedding_engine
            
            # Validate manifest should detect mismatch
            manifest_validation = data_loader.validate_manifest()
            
            # Should have error about dimension mismatch
            # The validation compares manifest (384) with model (512)
            assert not manifest_validation.embedding_dimension_match or len(manifest_validation.errors) > 0
            
            # Check that errors mention dimension mismatch
            all_messages = manifest_validation.errors + manifest_validation.warnings
            assert any("dimension" in msg.lower() for msg in all_messages)


class TestResourceMonitoring:
    """Test resource monitoring under load."""
    
    def test_resource_monitoring_under_load(self, pi_config, temp_dir):
        """
        Test resource monitoring during concurrent queries.
        
        Requirements: 13.1-13.5
        """
        resource_monitor = ResourceMonitor(pi_config)
        
        # Test memory usage tracking
        memory_stats = resource_monitor.get_memory_usage()
        assert memory_stats.used_mb > 0
        assert memory_stats.available_mb > 0
        assert 0 <= memory_stats.percent <= 100
        
        # Test query metrics logging
        query_times = [0.5, 1.0, 1.5, 2.0]
        for query_time in query_times:
            resource_monitor.log_query_metrics(query_time, memory_delta=10 * 1024 * 1024)  # 10MB in bytes
        
        # Test health check
        health_status = resource_monitor.get_system_health()
        assert health_status.status in ["healthy", "warning", "critical"]
        assert hasattr(health_status, 'memory_usage_percent')
        assert hasattr(health_status, 'memory_available_mb')
        
        # Test memory threshold checking
        is_critical = resource_monitor.check_memory_threshold()
        assert isinstance(is_critical, bool)
    
    def test_concurrent_query_handling(self, pi_config, sample_documents, temp_dir):
        """
        Test handling of concurrent queries.
        
        Requirements: 8.5
        """
        # Setup Pi with data
        pi_vs = VectorStore(persist_directory=pi_config.CHROMADB_PATH)
        pi_vs.initialize()
        
        chunks = []
        for doc in sample_documents:
            chunk = DocumentChunk(
                content=doc["content"],
                metadata=doc["metadata"],
                embedding=[0.1] * 384
            )
            chunks.append(chunk)
        
        pi_vs.add_chunks(chunks)
        
        # Simulate concurrent queries
        import concurrent.futures
        
        def process_query(query_id):
            """Process a single query."""
            results = pi_vs.query(query_embedding=[0.1] * 384, top_k=3)
            return len(results)
        
        # Run 10 concurrent queries
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_query, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All queries should complete successfully
        assert len(results) == 10
        assert all(r > 0 for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

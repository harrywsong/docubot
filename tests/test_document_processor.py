"""
Tests for document processor orchestrator.

Tests the coordination of folder scanning, file routing, embedding generation,
and vector storage with progress tracking and error handling.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from backend.document_processor import DocumentProcessor, ProcessingResult
from backend.database import DatabaseManager
from backend.folder_manager import FolderManager
from backend.processing_state import ProcessingStateManager
from backend.embedding_engine import EmbeddingEngine
from backend.vector_store import VectorStore
from backend.image_processor import ImageProcessor
from backend.models import DocumentChunk, ImageExtraction


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def db_manager(temp_dir):
    """Create database manager with temporary database."""
    db_path = Path(temp_dir) / "test.db"
    manager = DatabaseManager(str(db_path))
    yield manager
    # Close all connections before cleanup
    manager.close_all()


@pytest.fixture
def folder_manager(db_manager):
    """Create folder manager."""
    return FolderManager(db_manager)


@pytest.fixture
def state_manager(db_manager):
    """Create processing state manager."""
    return ProcessingStateManager(db_manager)


@pytest.fixture
def mock_embedding_engine():
    """Create mock embedding engine."""
    engine = Mock(spec=EmbeddingEngine)
    # Return 384-dimensional zero vectors
    engine.generate_embedding.return_value = [0.0] * 384
    engine.generate_embeddings_batch.return_value = [[0.0] * 384]
    return engine


@pytest.fixture
def mock_vector_store():
    """Create mock vector store."""
    store = Mock(spec=VectorStore)
    store.add_chunks.return_value = None
    return store


@pytest.fixture
def mock_image_processor():
    """Create mock image processor."""
    processor = Mock(spec=ImageProcessor)
    # Return sample extraction
    extraction = ImageExtraction(
        merchant="Test Store",
        date="2024-01-01",
        total_amount=100.0,
        currency="USD",
        line_items=[{"name": "Item 1", "price": 100.0}],
        raw_text="Test Store\nDate: 2024-01-01\nTotal: $100.00"
    )
    processor.process_image.return_value = extraction
    return processor


@pytest.fixture
def document_processor(
    db_manager,
    folder_manager,
    state_manager,
    mock_embedding_engine,
    mock_vector_store,
    mock_image_processor
):
    """Create document processor with mocked dependencies."""
    return DocumentProcessor(
        db_manager=db_manager,
        folder_manager=folder_manager,
        state_manager=state_manager,
        embedding_engine=mock_embedding_engine,
        vector_store=mock_vector_store,
        image_processor=mock_image_processor
    )


def test_process_folders_no_folders(document_processor):
    """Test processing with no watched folders."""
    result = document_processor.process_folders()
    
    assert result.processed == 0
    assert result.skipped == 0
    assert result.failed == 0
    assert len(result.failed_files) == 0


def test_process_folders_empty_folder(document_processor, folder_manager, temp_dir):
    """Test processing an empty folder."""
    # Add empty folder
    folder_manager.add_folder(temp_dir)
    
    result = document_processor.process_folders()
    
    assert result.processed == 0
    assert result.skipped == 0
    assert result.failed == 0


def test_process_text_file_new(
    document_processor,
    folder_manager,
    temp_dir,
    mock_embedding_engine,
    mock_vector_store
):
    """Test processing a new text file."""
    # Create test text file
    test_file = Path(temp_dir) / "test.txt"
    test_file.write_text("This is a test document with enough content to create chunks. " * 20)
    
    # Add folder
    success, msg, folder = folder_manager.add_folder(temp_dir)
    assert success
    
    # Mock embedding generation to return proper number of embeddings
    def mock_batch_embeddings(texts):
        return [[0.0] * 384 for _ in texts]
    
    mock_embedding_engine.generate_embeddings_batch.side_effect = mock_batch_embeddings
    
    # Process folders
    result = document_processor.process_folders()
    
    assert result.processed == 1
    assert result.skipped == 0
    assert result.failed == 0
    
    # Verify embedding generation was called
    assert mock_embedding_engine.generate_embeddings_batch.called
    
    # Verify vector store was updated
    assert mock_vector_store.add_chunks.called


def test_process_text_file_unchanged(
    document_processor,
    folder_manager,
    state_manager,
    temp_dir
):
    """Test skipping unchanged text file."""
    # Create test text file
    test_file = Path(temp_dir) / "test.txt"
    test_file.write_text("Test content " * 100)
    
    # Add folder
    success, msg, folder = folder_manager.add_folder(temp_dir)
    assert success
    
    # Mark file as processed
    state_manager.update_file_state(str(test_file), folder.id, "text")
    
    # Process folders
    result = document_processor.process_folders()
    
    assert result.processed == 0
    assert result.skipped == 1
    assert result.failed == 0


def test_process_image_file_new(
    document_processor,
    folder_manager,
    temp_dir,
    mock_embedding_engine,
    mock_vector_store,
    mock_image_processor
):
    """Test processing a new image file."""
    # Create test image file (empty file is fine for mock)
    test_file = Path(temp_dir) / "receipt.jpg"
    test_file.write_bytes(b"fake image data")
    
    # Add folder
    success, msg, folder = folder_manager.add_folder(temp_dir)
    assert success
    
    # Process folders
    result = document_processor.process_folders()
    
    assert result.processed == 1
    assert result.skipped == 0
    assert result.failed == 0
    
    # Verify image processor was called
    assert mock_image_processor.process_image.called
    
    # Verify embedding generation was called
    assert mock_embedding_engine.generate_embedding.called
    
    # Verify vector store was updated
    assert mock_vector_store.add_chunks.called


def test_process_mixed_files(
    document_processor,
    folder_manager,
    temp_dir,
    mock_embedding_engine,
    mock_vector_store
):
    """Test processing folder with both text and image files."""
    # Create test files
    text_file = Path(temp_dir) / "document.txt"
    text_file.write_text("Test document content " * 100)
    
    image_file = Path(temp_dir) / "receipt.png"
    image_file.write_bytes(b"fake image data")
    
    # Add folder
    success, msg, folder = folder_manager.add_folder(temp_dir)
    assert success
    
    # Mock embedding generation
    def mock_batch_embeddings(texts):
        return [[0.0] * 384 for _ in texts]
    
    mock_embedding_engine.generate_embeddings_batch.side_effect = mock_batch_embeddings
    
    # Process folders
    result = document_processor.process_folders()
    
    assert result.processed == 2
    assert result.skipped == 0
    assert result.failed == 0


def test_process_file_error_handling(
    document_processor,
    folder_manager,
    temp_dir,
    mock_embedding_engine
):
    """Test error handling for individual file failures."""
    # Create test file
    test_file = Path(temp_dir) / "test.txt"
    test_file.write_text("Test content " * 100)
    
    # Add folder
    success, msg, folder = folder_manager.add_folder(temp_dir)
    assert success
    
    # Make embedding generation fail
    mock_embedding_engine.generate_embeddings_batch.side_effect = Exception("Embedding failed")
    
    # Process folders - should log error and continue
    result = document_processor.process_folders()
    
    assert result.processed == 0
    assert result.skipped == 0
    assert result.failed == 1
    assert len(result.failed_files) == 1
    assert test_file.name in result.failed_files[0][0]
    assert "Embedding failed" in result.failed_files[0][1]


def test_process_pdf_file(
    document_processor,
    folder_manager,
    temp_dir,
    mock_embedding_engine,
    mock_vector_store
):
    """Test processing PDF file with page tracking."""
    # Create a simple PDF file
    from pypdf import PdfWriter
    
    pdf_file = Path(temp_dir) / "test.pdf"
    writer = PdfWriter()
    
    # Add a page with text (using a simple approach)
    # Note: This creates an empty page, but our mock will handle it
    writer.add_blank_page(width=200, height=200)
    
    with open(pdf_file, 'wb') as f:
        writer.write(f)
    
    # Add folder
    success, msg, folder = folder_manager.add_folder(temp_dir)
    assert success
    
    # Mock PDF extraction to return content
    with patch('backend.document_processor.extract_from_pdf') as mock_extract:
        mock_extract.return_value = [
            {'text': 'Page 1 content ' * 100, 'page_number': 1}
        ]
        
        # Mock embedding generation
        def mock_batch_embeddings(texts):
            return [[0.0] * 384 for _ in texts]
        
        mock_embedding_engine.generate_embeddings_batch.side_effect = mock_batch_embeddings
        
        # Process folders
        result = document_processor.process_folders()
        
        assert result.processed == 1
        assert result.skipped == 0
        assert result.failed == 0


def test_process_multiple_folders(
    document_processor,
    folder_manager,
    temp_dir,
    mock_embedding_engine,
    mock_vector_store
):
    """Test processing multiple watched folders."""
    # Create two folders with files
    folder1 = Path(temp_dir) / "folder1"
    folder1.mkdir()
    (folder1 / "doc1.txt").write_text("Document 1 content " * 100)
    
    folder2 = Path(temp_dir) / "folder2"
    folder2.mkdir()
    (folder2 / "doc2.txt").write_text("Document 2 content " * 100)
    
    # Add both folders
    folder_manager.add_folder(str(folder1))
    folder_manager.add_folder(str(folder2))
    
    # Mock embedding generation
    def mock_batch_embeddings(texts):
        return [[0.0] * 384 for _ in texts]
    
    mock_embedding_engine.generate_embeddings_batch.side_effect = mock_batch_embeddings
    
    # Process folders
    result = document_processor.process_folders()
    
    assert result.processed == 2
    assert result.skipped == 0
    assert result.failed == 0


def test_processing_result_dataclass():
    """Test ProcessingResult dataclass."""
    result = ProcessingResult(
        processed=5,
        skipped=3,
        failed=1,
        failed_files=[("file.txt", "error message")]
    )
    
    assert result.processed == 5
    assert result.skipped == 3
    assert result.failed == 1
    assert len(result.failed_files) == 1
    assert result.failed_files[0] == ("file.txt", "error message")

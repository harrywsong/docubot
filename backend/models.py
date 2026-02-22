"""
Data models for RAG chatbot.

Defines data classes for folders, files, documents, conversations, and query results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import re


@dataclass
class WatchedFolder:
    """Represents a folder being watched for documents."""
    id: int
    path: str
    added_at: datetime
    
    def validate(self) -> bool:
        """
        Validate folder data.
        
        Returns:
            True if valid, False otherwise
        """
        if not self.path or not isinstance(self.path, str):
            return False
        if not isinstance(self.id, int) or self.id < 0:
            return False
        if not isinstance(self.added_at, datetime):
            return False
        return True


@dataclass
class ProcessedFile:
    """Represents a file that has been processed."""
    id: int
    file_path: str
    folder_id: int
    file_hash: str
    modified_at: datetime
    processed_at: datetime
    file_type: str  # 'text' or 'image'
    
    def validate(self) -> bool:
        """
        Validate processed file data.
        
        Returns:
            True if valid, False otherwise
        """
        if not self.file_path or not isinstance(self.file_path, str):
            return False
        if not isinstance(self.id, int) or self.id < 0:
            return False
        if not isinstance(self.folder_id, int) or self.folder_id < 0:
            return False
        if not self.file_hash or not isinstance(self.file_hash, str):
            return False
        if self.file_type not in ('text', 'image'):
            return False
        if not isinstance(self.modified_at, datetime):
            return False
        if not isinstance(self.processed_at, datetime):
            return False
        return True


@dataclass
class DocumentChunk:
    """Represents a chunk of document content with embeddings."""
    content: str
    metadata: dict
    embedding: Optional[List[float]] = None
    
    def validate(self) -> bool:
        """
        Validate document chunk data.
        
        Returns:
            True if valid, False otherwise
        """
        if not self.content or not isinstance(self.content, str):
            return False
        if not isinstance(self.metadata, dict):
            return False
        # Validate required metadata fields
        required_fields = ['filename', 'folder_path', 'file_type']
        if not all(field in self.metadata for field in required_fields):
            return False
        if self.embedding is not None:
            if not isinstance(self.embedding, list):
                return False
            if not all(isinstance(x, (int, float)) for x in self.embedding):
                return False
        return True


@dataclass
class ImageExtraction:
    """
    Represents extracted data from an image with flexible metadata.
    
    The vision model dynamically determines what fields to extract based on document type.
    All extracted fields are stored in flexible_metadata.
    """
    raw_text: str = ""
    flexible_metadata: dict = field(default_factory=dict)
    
    def validate(self) -> bool:
        """
        Validate image extraction data.
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(self.raw_text, str):
            return False
        if not isinstance(self.flexible_metadata, dict):
            return False
        return True
    
    def format_as_text(self) -> str:
        """
        Format extracted data as structured text for embedding.
        
        Uses flexible_metadata fields (model-determined fields for any document type).
        With qwen3-embedding's huge context (40960 tokens), we can include much more detail.
        
        Returns:
            Formatted text representation
        """
        lines = []
        
        # Use flexible metadata (all extracted fields from any document type)
        if self.flexible_metadata:
            for key, value in self.flexible_metadata.items():
                # Format field name nicely (snake_case to Title Case)
                field_name = key.replace('_', ' ').title()
                # Allow longer values with qwen3-embedding's large context
                value_str = str(value)
                if len(value_str) > 2000:
                    value_str = value_str[:2000] + "..."
                lines.append(f"{field_name}: {value_str}")
        
        # Add raw text for additional context (with generous limit for qwen3-embedding)
        if self.raw_text:
            # Limit raw text to 8000 chars - plenty of context with large embedding model
            raw_preview = self.raw_text[:8000] + "..." if len(self.raw_text) > 8000 else self.raw_text
            lines.append(f"\nRaw Text:\n{raw_preview}")
        
        return "\n".join(lines)


@dataclass
class QueryResult:
    """Represents a search result from vector store."""
    chunk_id: str
    content: str
    metadata: dict
    similarity_score: float
    
    def validate(self) -> bool:
        """
        Validate query result data.
        
        Returns:
            True if valid, False otherwise
        """
        if not self.chunk_id or not isinstance(self.chunk_id, str):
            return False
        if not self.content or not isinstance(self.content, str):
            return False
        if not isinstance(self.metadata, dict):
            return False
        if not isinstance(self.similarity_score, (int, float)):
            return False
        if not (0.0 <= self.similarity_score <= 1.0):
            return False
        return True


@dataclass
class Message:
    """Represents a message in a conversation."""
    id: int
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    sources: Optional[List[dict]]
    created_at: datetime
    
    def validate(self) -> bool:
        """
        Validate message data.
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(self.id, int) or self.id < 0:
            return False
        if not self.conversation_id or not isinstance(self.conversation_id, str):
            return False
        if self.role not in ('user', 'assistant'):
            return False
        if not isinstance(self.content, str):
            return False
        if self.sources is not None:
            if not isinstance(self.sources, list):
                return False
            for source in self.sources:
                if not isinstance(source, dict):
                    return False
        if not isinstance(self.created_at, datetime):
            return False
        return True


@dataclass
class Conversation:
    """Represents a conversation with message history."""
    id: str  # UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = field(default_factory=list)
    
    def validate(self) -> bool:
        """
        Validate conversation data.
        
        Returns:
            True if valid, False otherwise
        """
        if not self.id or not isinstance(self.id, str):
            return False
        # Validate UUID format
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        if not uuid_pattern.match(self.id):
            return False
        if self.title is not None and not isinstance(self.title, str):
            return False
        if not isinstance(self.created_at, datetime):
            return False
        if not isinstance(self.updated_at, datetime):
            return False
        if not isinstance(self.messages, list):
            return False
        # Validate all messages
        for msg in self.messages:
            if not isinstance(msg, Message) or not msg.validate():
                return False
        return True


@dataclass
class ProcessingReport:
    """Report of document processing validation."""
    total_documents: int
    total_chunks: int
    total_embeddings: int
    failed_documents: List[tuple]  # List of (file_path, error) tuples
    missing_embeddings: List[str]  # List of chunk_ids
    incomplete_metadata: List[str]  # List of chunk_ids
    validation_passed: bool


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    package_path: str
    archive_path: str
    size_bytes: int
    statistics: dict
    errors: List[str]
    
    def validate(self) -> bool:
        """
        Validate export result data.
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(self.success, bool):
            return False
        if not self.package_path or not isinstance(self.package_path, str):
            return False
        if not self.archive_path or not isinstance(self.archive_path, str):
            return False
        if not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            return False
        if not isinstance(self.statistics, dict):
            return False
        if not isinstance(self.errors, list):
            return False
        for error in self.errors:
            if not isinstance(error, str):
                return False
        return True


@dataclass
class HealthStatus:
    """System health status for Pi server."""
    status: str  # "healthy", "warning", "critical"
    memory_usage_percent: float
    memory_available_mb: float
    model_loaded: bool
    vector_store_loaded: bool
    total_chunks: int
    last_query_time: Optional[float]
    
    def validate(self) -> bool:
        """
        Validate health status data.
        
        Returns:
            True if valid, False otherwise
        """
        if self.status not in ('healthy', 'warning', 'critical'):
            return False
        if not isinstance(self.memory_usage_percent, (int, float)):
            return False
        if not (0.0 <= self.memory_usage_percent <= 100.0):
            return False
        if not isinstance(self.memory_available_mb, (int, float)):
            return False
        if self.memory_available_mb < 0:
            return False
        if not isinstance(self.model_loaded, bool):
            return False
        if not isinstance(self.vector_store_loaded, bool):
            return False
        if not isinstance(self.total_chunks, int) or self.total_chunks < 0:
            return False
        if self.last_query_time is not None:
            if not isinstance(self.last_query_time, (int, float)):
                return False
            if self.last_query_time < 0:
                return False
        return True


@dataclass
class MergeResult:
    """Result of an incremental merge operation."""
    success: bool
    merged_chunks: int
    updated_chunks: int
    deleted_chunks: int
    errors: List[str]
    merge_time_seconds: float
    
    def validate(self) -> bool:
        """
        Validate merge result data.
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(self.success, bool):
            return False
        if not isinstance(self.merged_chunks, int) or self.merged_chunks < 0:
            return False
        if not isinstance(self.updated_chunks, int) or self.updated_chunks < 0:
            return False
        if not isinstance(self.deleted_chunks, int) or self.deleted_chunks < 0:
            return False
        if not isinstance(self.errors, list):
            return False
        for error in self.errors:
            if not isinstance(error, str):
                return False
        if not isinstance(self.merge_time_seconds, (int, float)):
            return False
        if self.merge_time_seconds < 0:
            return False
        return True


@dataclass
class ManifestValidation:
    """Result of manifest validation."""
    valid: bool
    embedding_dimension_match: bool
    model_compatible: bool
    errors: List[str]
    warnings: List[str]
    
    def validate(self) -> bool:
        """
        Validate manifest validation data.
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(self.valid, bool):
            return False
        if not isinstance(self.embedding_dimension_match, bool):
            return False
        if not isinstance(self.model_compatible, bool):
            return False
        if not isinstance(self.errors, list):
            return False
        for error in self.errors:
            if not isinstance(error, str):
                return False
        if not isinstance(self.warnings, list):
            return False
        for warning in self.warnings:
            if not isinstance(warning, str):
                return False
        return True


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    used_mb: float
    available_mb: float
    total_mb: float
    percent: float
    
    def validate(self) -> bool:
        """
        Validate memory stats data.
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(self.used_mb, (int, float)) or self.used_mb < 0:
            return False
        if not isinstance(self.available_mb, (int, float)) or self.available_mb < 0:
            return False
        if not isinstance(self.total_mb, (int, float)) or self.total_mb < 0:
            return False
        if not isinstance(self.percent, (int, float)):
            return False
        if not (0.0 <= self.percent <= 100.0):
            return False
        return True

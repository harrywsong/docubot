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
    """Represents extracted data from an image (receipt/invoice)."""
    merchant: Optional[str]
    date: Optional[str]
    total_amount: Optional[float]
    currency: Optional[str]
    line_items: List[dict]
    raw_text: str
    
    def validate(self) -> bool:
        """
        Validate image extraction data.
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(self.raw_text, str):
            return False
        if not isinstance(self.line_items, list):
            return False
        # Validate line items structure
        for item in self.line_items:
            if not isinstance(item, dict):
                return False
        # Validate optional fields types
        if self.merchant is not None and not isinstance(self.merchant, str):
            return False
        if self.date is not None and not isinstance(self.date, str):
            return False
        if self.total_amount is not None and not isinstance(self.total_amount, (int, float)):
            return False
        if self.currency is not None and not isinstance(self.currency, str):
            return False
        return True
    
    def format_as_text(self) -> str:
        """
        Format extracted data as structured text for embedding.
        
        Returns:
            Formatted text representation
        """
        lines = []
        if self.merchant:
            lines.append(f"Merchant: {self.merchant}")
        if self.date:
            lines.append(f"Date: {self.date}")
        if self.total_amount is not None:
            currency_str = self.currency or "USD"
            lines.append(f"Total: {currency_str} {self.total_amount:.2f}")
        
        if self.line_items:
            lines.append("\nLine Items:")
            for item in self.line_items:
                item_name = item.get('name', 'Unknown')
                item_price = item.get('price', 0.0)
                lines.append(f"  - {item_name}: {item_price:.2f}")
        
        if self.raw_text:
            lines.append(f"\nRaw Text:\n{self.raw_text}")
        
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

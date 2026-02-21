"""
Conversation manager for RAG chatbot.

Handles conversation and message CRUD operations with SQLite persistence.
"""

import uuid
import json
import logging
from datetime import datetime
from typing import List, Optional
from backend.database import DatabaseManager
from backend.models import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversations and messages with database persistence."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize conversation manager.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
    
    def create_conversation(self, title: Optional[str] = None) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            title: Optional conversation title. If None, will be generated from first message.
        
        Returns:
            Created Conversation object
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.now()
        
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, title, now, now)
            )
        
        logger.info(f"Created conversation {conversation_id}")
        
        return Conversation(
            id=conversation_id,
            title=title,
            created_at=now,
            updated_at=now,
            messages=[]
        )
    
    def list_conversations(self) -> List[Conversation]:
        """
        List all conversations ordered by most recently updated.
        
        Returns:
            List of Conversation objects (without messages loaded)
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                """
            )
            rows = cursor.fetchall()
        
        conversations = []
        for row in rows:
            conversations.append(Conversation(
                id=row['id'],
                title=row['title'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                messages=[]
            ))
        
        logger.debug(f"Listed {len(conversations)} conversations")
        return conversations

    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get a conversation with all its messages.
        
        Args:
            conversation_id: UUID of the conversation
        
        Returns:
            Conversation object with messages, or None if not found
        """
        with self.db.transaction() as conn:
            # Get conversation
            cursor = conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,)
            )
            conv_row = cursor.fetchone()
            
            if not conv_row:
                logger.warning(f"Conversation {conversation_id} not found")
                return None
            
            # Get messages
            cursor = conn.execute(
                """
                SELECT id, conversation_id, role, content, sources, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,)
            )
            message_rows = cursor.fetchall()
        
        # Build message objects
        messages = []
        for row in message_rows:
            sources = json.loads(row['sources']) if row['sources'] else None
            messages.append(Message(
                id=row['id'],
                conversation_id=row['conversation_id'],
                role=row['role'],
                content=row['content'],
                sources=sources,
                created_at=datetime.fromisoformat(row['created_at'])
            ))
        
        conversation = Conversation(
            id=conv_row['id'],
            title=conv_row['title'],
            created_at=datetime.fromisoformat(conv_row['created_at']),
            updated_at=datetime.fromisoformat(conv_row['updated_at']),
            messages=messages
        )
        
        logger.debug(f"Retrieved conversation {conversation_id} with {len(messages)} messages")
        return conversation
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its messages.
        
        Args:
            conversation_id: UUID of the conversation to delete
        
        Returns:
            True if deleted, False if not found
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                DELETE FROM conversations
                WHERE id = ?
                """,
                (conversation_id,)
            )
            deleted = cursor.rowcount > 0
        
        if deleted:
            logger.info(f"Deleted conversation {conversation_id}")
        else:
            logger.warning(f"Conversation {conversation_id} not found for deletion")
        
        return deleted

    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: Optional[List[dict]] = None
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: UUID of the conversation
            role: Message role ('user' or 'assistant')
            content: Message content
            sources: Optional list of source references for assistant messages
        
        Returns:
            Created Message object
        
        Raises:
            ValueError: If conversation not found or role is invalid
        """
        if role not in ('user', 'assistant'):
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")
        
        now = datetime.now()
        sources_json = json.dumps(sources) if sources else None
        
        with self.db.transaction() as conn:
            # Verify conversation exists
            cursor = conn.execute(
                "SELECT id FROM conversations WHERE id = ?",
                (conversation_id,)
            )
            if not cursor.fetchone():
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Insert message
            cursor = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, sources, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, sources_json, now)
            )
            message_id = cursor.lastrowid
            
            # Update conversation timestamp and title if needed
            cursor = conn.execute(
                "SELECT title FROM conversations WHERE id = ?",
                (conversation_id,)
            )
            current_title = cursor.fetchone()['title']
            
            # Generate title from first user message if no title exists
            new_title = current_title
            if not current_title and role == 'user':
                new_title = self._generate_title(content)
            
            conn.execute(
                """
                UPDATE conversations
                SET updated_at = ?, title = ?
                WHERE id = ?
                """,
                (now, new_title, conversation_id)
            )
        
        logger.info(f"Added {role} message to conversation {conversation_id}")
        
        return Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources,
            created_at=now
        )
    
    def _generate_title(self, first_message: str, max_length: int = 50) -> str:
        """
        Generate conversation title from first message.
        
        Args:
            first_message: First user message content
            max_length: Maximum title length
        
        Returns:
            Generated title (preview of first message or timestamp)
        """
        # Clean and truncate message
        title = first_message.strip()
        
        if not title:
            # Fallback to timestamp if message is empty
            return f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Truncate and add ellipsis if needed
        if len(title) > max_length:
            title = title[:max_length].rsplit(' ', 1)[0] + '...'
        
        return title

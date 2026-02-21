"""
Tests for conversation manager.
"""

import pytest
import tempfile
import os
from datetime import datetime
from backend.database import DatabaseManager
from backend.conversation_manager import ConversationManager


@pytest.fixture
def db_manager():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    db = DatabaseManager(db_path)
    yield db
    
    db.close_all()
    os.unlink(db_path)


@pytest.fixture
def conv_manager(db_manager):
    """Create conversation manager with test database."""
    return ConversationManager(db_manager)


def test_create_conversation(conv_manager):
    """Test creating a new conversation."""
    conv = conv_manager.create_conversation(title="Test Conversation")
    
    assert conv.id is not None
    assert conv.title == "Test Conversation"
    assert isinstance(conv.created_at, datetime)
    assert isinstance(conv.updated_at, datetime)
    assert conv.messages == []


def test_create_conversation_without_title(conv_manager):
    """Test creating a conversation without explicit title."""
    conv = conv_manager.create_conversation()
    
    assert conv.id is not None
    assert conv.title is None
    assert conv.messages == []


def test_list_conversations(conv_manager):
    """Test listing all conversations."""
    # Create multiple conversations
    conv1 = conv_manager.create_conversation(title="First")
    conv2 = conv_manager.create_conversation(title="Second")
    conv3 = conv_manager.create_conversation(title="Third")
    
    # List conversations
    conversations = conv_manager.list_conversations()
    
    assert len(conversations) == 3
    # Should be ordered by updated_at DESC (most recent first)
    assert conversations[0].id == conv3.id
    assert conversations[1].id == conv2.id
    assert conversations[2].id == conv1.id


def test_get_conversation(conv_manager):
    """Test retrieving a specific conversation."""
    # Create conversation
    conv = conv_manager.create_conversation(title="Test")
    
    # Retrieve it
    retrieved = conv_manager.get_conversation(conv.id)
    
    assert retrieved is not None
    assert retrieved.id == conv.id
    assert retrieved.title == "Test"
    assert retrieved.messages == []


def test_get_nonexistent_conversation(conv_manager):
    """Test retrieving a conversation that doesn't exist."""
    result = conv_manager.get_conversation("nonexistent-id")
    assert result is None


def test_delete_conversation(conv_manager):
    """Test deleting a conversation."""
    # Create conversation
    conv = conv_manager.create_conversation(title="To Delete")
    
    # Delete it
    deleted = conv_manager.delete_conversation(conv.id)
    assert deleted is True
    
    # Verify it's gone
    retrieved = conv_manager.get_conversation(conv.id)
    assert retrieved is None


def test_delete_nonexistent_conversation(conv_manager):
    """Test deleting a conversation that doesn't exist."""
    deleted = conv_manager.delete_conversation("nonexistent-id")
    assert deleted is False


def test_add_user_message(conv_manager):
    """Test adding a user message to a conversation."""
    # Create conversation
    conv = conv_manager.create_conversation()
    
    # Add user message
    message = conv_manager.add_message(
        conversation_id=conv.id,
        role="user",
        content="Hello, chatbot!"
    )
    
    assert message.id is not None
    assert message.conversation_id == conv.id
    assert message.role == "user"
    assert message.content == "Hello, chatbot!"
    assert message.sources is None
    assert isinstance(message.created_at, datetime)


def test_add_assistant_message_with_sources(conv_manager):
    """Test adding an assistant message with sources."""
    # Create conversation
    conv = conv_manager.create_conversation()
    
    # Add assistant message with sources
    sources = [
        {"filename": "doc1.pdf", "chunk": "relevant text", "score": 0.95},
        {"filename": "doc2.txt", "chunk": "more text", "score": 0.87}
    ]
    message = conv_manager.add_message(
        conversation_id=conv.id,
        role="assistant",
        content="Here's the answer",
        sources=sources
    )
    
    assert message.role == "assistant"
    assert message.sources == sources


def test_add_message_invalid_role(conv_manager):
    """Test adding a message with invalid role."""
    conv = conv_manager.create_conversation()
    
    with pytest.raises(ValueError, match="Invalid role"):
        conv_manager.add_message(
            conversation_id=conv.id,
            role="invalid",
            content="test"
        )


def test_add_message_nonexistent_conversation(conv_manager):
    """Test adding a message to a nonexistent conversation."""
    with pytest.raises(ValueError, match="not found"):
        conv_manager.add_message(
            conversation_id="nonexistent-id",
            role="user",
            content="test"
        )


def test_conversation_with_messages(conv_manager):
    """Test retrieving a conversation with multiple messages."""
    # Create conversation
    conv = conv_manager.create_conversation()
    
    # Add messages
    msg1 = conv_manager.add_message(conv.id, "user", "First question")
    msg2 = conv_manager.add_message(conv.id, "assistant", "First answer")
    msg3 = conv_manager.add_message(conv.id, "user", "Second question")
    
    # Retrieve conversation
    retrieved = conv_manager.get_conversation(conv.id)
    
    assert len(retrieved.messages) == 3
    assert retrieved.messages[0].content == "First question"
    assert retrieved.messages[1].content == "First answer"
    assert retrieved.messages[2].content == "Second question"


def test_title_generation_from_first_message(conv_manager):
    """Test automatic title generation from first user message."""
    # Create conversation without title
    conv = conv_manager.create_conversation()
    
    # Add first user message
    conv_manager.add_message(conv.id, "user", "What is the weather today?")
    
    # Retrieve and check title
    retrieved = conv_manager.get_conversation(conv.id)
    assert retrieved.title == "What is the weather today?"


def test_title_generation_truncation(conv_manager):
    """Test title truncation for long messages."""
    conv = conv_manager.create_conversation()
    
    # Add very long message
    long_message = "This is a very long message " * 20
    conv_manager.add_message(conv.id, "user", long_message)
    
    # Retrieve and check title is truncated
    retrieved = conv_manager.get_conversation(conv.id)
    assert len(retrieved.title) <= 53  # 50 + "..."
    assert retrieved.title.endswith("...")


def test_delete_conversation_cascades_messages(conv_manager):
    """Test that deleting a conversation also deletes its messages."""
    # Create conversation with messages
    conv = conv_manager.create_conversation()
    conv_manager.add_message(conv.id, "user", "Message 1")
    conv_manager.add_message(conv.id, "assistant", "Message 2")
    
    # Delete conversation
    conv_manager.delete_conversation(conv.id)
    
    # Verify conversation and messages are gone
    retrieved = conv_manager.get_conversation(conv.id)
    assert retrieved is None


def test_conversation_updated_at_changes(conv_manager):
    """Test that updated_at changes when messages are added."""
    import time
    
    # Create conversation
    conv = conv_manager.create_conversation()
    original_updated_at = conv.updated_at
    
    # Wait a bit and add message
    time.sleep(0.1)
    conv_manager.add_message(conv.id, "user", "New message")
    
    # Retrieve and check updated_at changed
    retrieved = conv_manager.get_conversation(conv.id)
    assert retrieved.updated_at > original_updated_at

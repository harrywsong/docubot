"""
REST API server for RAG chatbot with vision processing.

Provides endpoints for folder management, document processing, conversations, and queries.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import Config
from backend.database import DatabaseManager
from backend.folder_manager import FolderManager
from backend.document_processor import DocumentProcessor
from backend.processing_state import ProcessingStateManager
from backend.embedding_engine import get_embedding_engine
from backend.vector_store import get_vector_store
from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.conversation_manager import ConversationManager
from backend.query_engine import get_query_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db_manager = None
folder_manager = None
document_processor = None
conversation_manager = None
query_engine = None
ollama_client = None

# Processing state
processing_status = {
    "is_processing": False,
    "processed": 0,
    "skipped": 0,
    "failed": 0,
    "failed_files": []
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global db_manager, folder_manager, document_processor, conversation_manager, query_engine, ollama_client
    
    logger.info("Starting RAG chatbot API server")
    
    # Ensure data directories exist
    Config.ensure_data_directories()
    
    # Initialize database (schema is initialized in __init__)
    db_manager = DatabaseManager(Config.SQLITE_PATH)
    
    # Initialize components
    folder_manager = FolderManager(db_manager)
    state_manager = ProcessingStateManager(db_manager)
    embedding_engine = get_embedding_engine()
    vector_store = get_vector_store()
    ollama_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_MODEL)
    image_processor = ImageProcessor(ollama_client)
    
    document_processor = DocumentProcessor(
        db_manager=db_manager,
        folder_manager=folder_manager,
        state_manager=state_manager,
        embedding_engine=embedding_engine,
        vector_store=vector_store,
        image_processor=image_processor
    )
    
    conversation_manager = ConversationManager(db_manager)
    query_engine = get_query_engine()
    
    logger.info("API server initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down API server")
    if db_manager:
        db_manager.close()


# Create FastAPI app
app = FastAPI(
    title="RAG Chatbot API",
    description="REST API for RAG-powered chatbot with vision processing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class AddFolderRequest(BaseModel):
    """Request model for adding a folder."""
    path: str = Field(..., description="Path to folder to watch")


class AddFolderResponse(BaseModel):
    """Response model for adding a folder."""
    success: bool
    message: str
    folder: Optional[Dict[str, Any]] = None


class RemoveFolderRequest(BaseModel):
    """Request model for removing a folder."""
    path: str = Field(..., description="Path to folder to remove")


class RemoveFolderResponse(BaseModel):
    """Response model for removing a folder."""
    success: bool
    message: str


class FolderListResponse(BaseModel):
    """Response model for listing folders."""
    folders: List[Dict[str, Any]]


# ============================================================================
# Folder Management Endpoints
# ============================================================================

@app.post("/api/folders/add", response_model=AddFolderResponse)
async def add_folder(request: AddFolderRequest):
    """
    Add a folder to the watched folders list.
    
    Validates that the folder exists and is accessible before adding.
    """
    try:
        success, message, folder = folder_manager.add_folder(request.path)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return AddFolderResponse(
            success=True,
            message=message,
            folder={
                "id": folder.id,
                "path": folder.path,
                "added_at": folder.added_at.isoformat()
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add folder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add folder: {str(e)}")


@app.delete("/api/folders/remove", response_model=RemoveFolderResponse)
async def remove_folder(request: RemoveFolderRequest):
    """
    Remove a folder from the watched folders list.
    
    Also removes all associated processed file records.
    """
    try:
        success, message = folder_manager.remove_folder(request.path)
        
        if not success:
            raise HTTPException(status_code=404, detail=message)
        
        return RemoveFolderResponse(
            success=True,
            message=message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove folder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove folder: {str(e)}")


@app.get("/api/folders/list", response_model=FolderListResponse)
async def list_folders():
    """
    List all watched folders.
    
    Returns folders ordered by most recently added.
    """
    try:
        folders = folder_manager.list_folders()
        
        return FolderListResponse(
            folders=[
                {
                    "id": folder.id,
                    "path": folder.path,
                    "added_at": folder.added_at.isoformat()
                }
                for folder in folders
            ]
        )
    
    except Exception as e:
        logger.error(f"Failed to list folders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list folders: {str(e)}")


# ============================================================================
# Document Processing Endpoints
# ============================================================================

class ProcessStartResponse(BaseModel):
    """Response model for starting document processing."""
    success: bool
    message: str
    processing_id: str


class ProcessStatusResponse(BaseModel):
    """Response model for processing status."""
    is_processing: bool
    processed: int
    skipped: int
    failed: int
    failed_files: List[Dict[str, str]]


@app.post("/api/process/start", response_model=ProcessStartResponse)
async def start_processing():
    """
    Start document processing for all watched folders.
    
    Processes documents asynchronously and returns immediately with a processing ID.
    Use /api/process/status or WebSocket /api/process/stream for progress updates.
    """
    global processing_status
    
    try:
        # Check if already processing
        if processing_status["is_processing"]:
            raise HTTPException(status_code=409, detail="Processing already in progress")
        
        # Reset status
        processing_status = {
            "is_processing": True,
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "failed_files": []
        }
        
        # Start processing in background
        asyncio.create_task(run_document_processing())
        
        return ProcessStartResponse(
            success=True,
            message="Document processing started",
            processing_id="current"  # Simple ID for MVP
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start processing: {e}")
        processing_status["is_processing"] = False
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")


@app.get("/api/process/status", response_model=ProcessStatusResponse)
async def get_processing_status():
    """
    Get current document processing status.
    
    Returns counts of processed, skipped, and failed files.
    """
    try:
        return ProcessStatusResponse(
            is_processing=processing_status["is_processing"],
            processed=processing_status["processed"],
            skipped=processing_status["skipped"],
            failed=processing_status["failed"],
            failed_files=[
                {"file": file_path, "error": error}
                for file_path, error in processing_status["failed_files"]
            ]
        )
    
    except Exception as e:
        logger.error(f"Failed to get processing status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing status: {str(e)}")


@app.websocket("/api/process/stream")
async def process_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time processing progress updates.
    
    Sends JSON messages with processing status updates.
    """
    await websocket.accept()
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "status",
            "is_processing": processing_status["is_processing"],
            "processed": processing_status["processed"],
            "skipped": processing_status["skipped"],
            "failed": processing_status["failed"]
        })
        
        # Keep connection alive and send updates
        while True:
            await asyncio.sleep(0.5)  # Poll every 500ms
            
            # Send current status
            await websocket.send_json({
                "type": "status",
                "is_processing": processing_status["is_processing"],
                "processed": processing_status["processed"],
                "skipped": processing_status["skipped"],
                "failed": processing_status["failed"]
            })
            
            # If processing is complete, send final message and close
            if not processing_status["is_processing"] and processing_status["processed"] + processing_status["skipped"] + processing_status["failed"] > 0:
                await websocket.send_json({
                    "type": "complete",
                    "processed": processing_status["processed"],
                    "skipped": processing_status["skipped"],
                    "failed": processing_status["failed"],
                    "failed_files": [
                        {"file": file_path, "error": error}
                        for file_path, error in processing_status["failed_files"]
                    ]
                })
                break
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass


async def run_document_processing():
    """
    Run document processing in background.
    
    Updates global processing_status with progress.
    """
    global processing_status
    
    try:
        logger.info("Starting background document processing")
        
        # Run processing (blocking operation in thread pool)
        result = await asyncio.to_thread(document_processor.process_folders)
        
        # Update status
        processing_status["processed"] = result.processed
        processing_status["skipped"] = result.skipped
        processing_status["failed"] = result.failed
        processing_status["failed_files"] = result.failed_files
        processing_status["is_processing"] = False
        
        logger.info(
            f"Document processing complete: {result.processed} processed, "
            f"{result.skipped} skipped, {result.failed} failed"
        )
    
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        processing_status["is_processing"] = False
        processing_status["failed"] += 1


# ============================================================================
# Conversation Endpoints
# ============================================================================

class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation."""
    title: Optional[str] = Field(None, description="Optional conversation title")


class CreateConversationResponse(BaseModel):
    """Response model for creating a conversation."""
    success: bool
    conversation: Dict[str, Any]


class ConversationListResponse(BaseModel):
    """Response model for listing conversations."""
    conversations: List[Dict[str, Any]]


class ConversationResponse(BaseModel):
    """Response model for getting a conversation."""
    conversation: Dict[str, Any]


class DeleteConversationResponse(BaseModel):
    """Response model for deleting a conversation."""
    success: bool
    message: str


@app.post("/api/conversations/create", response_model=CreateConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    """
    Create a new conversation.
    
    Optionally accepts a title. If no title provided, it will be generated
    from the first user message.
    """
    try:
        conversation = conversation_manager.create_conversation(title=request.title)
        
        return CreateConversationResponse(
            success=True,
            conversation={
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "messages": []
            }
        )
    
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


@app.get("/api/conversations/list", response_model=ConversationListResponse)
async def list_conversations():
    """
    List all conversations.
    
    Returns conversations ordered by most recently updated.
    Does not include messages (use GET /api/conversations/:id for full conversation).
    """
    try:
        conversations = conversation_manager.list_conversations()
        
        return ConversationListResponse(
            conversations=[
                {
                    "id": conv.id,
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                }
                for conv in conversations
            ]
        )
    
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """
    Get a conversation with all its messages.
    
    Returns full conversation history including user and assistant messages.
    """
    try:
        conversation = conversation_manager.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found. It may have been deleted.")
        
        return ConversationResponse(
            conversation={
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "sources": msg.sources,
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in conversation.messages
                ]
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@app.delete("/api/conversations/{conversation_id}", response_model=DeleteConversationResponse)
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation and all its messages.
    
    This operation cannot be undone.
    """
    try:
        success = conversation_manager.delete_conversation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return DeleteConversationResponse(
            success=True,
            message=f"Conversation {conversation_id} deleted successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")


# ============================================================================
# Query Endpoint
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for querying."""
    conversation_id: str = Field(..., description="ID of the conversation")
    question: str = Field(..., description="User's question")


class QueryResponse(BaseModel):
    """Response model for query."""
    answer: str
    sources: List[Dict[str, Any]]
    aggregated_amount: Optional[float] = None
    breakdown: Optional[List[Dict[str, Any]]] = None


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Submit a question and get an answer with sources.
    
    The question is added to the conversation, processed using RAG,
    and the answer is stored in the conversation history.
    
    Returns the answer with source document references.
    """
    try:
        # Validate conversation exists
        conversation = conversation_manager.get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Add user message to conversation
        conversation_manager.add_message(
            conversation_id=request.conversation_id,
            role="user",
            content=request.question
        )
        
        # Process query using RAG
        result = await asyncio.to_thread(
            query_engine.query,
            question=request.question,
            top_k=5,
            timeout_seconds=10
        )
        
        # Add assistant response to conversation
        conversation_manager.add_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=result["answer"],
            sources=result["sources"]
        )
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            aggregated_amount=result.get("aggregated_amount"),
            breakdown=result.get("breakdown")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response. Please try again.")


# ============================================================================
# Health Check and Startup Validation
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    status: str
    ollama_available: bool
    model_available: bool
    database_available: bool
    vector_store_available: bool
    errors: List[str]
    warnings: List[str]


@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Check system health and dependencies.
    
    Validates:
    - Ollama service availability
    - Vision model installation
    - Database connectivity
    - Vector store availability
    
    Returns detailed status and user-friendly error messages for missing dependencies.
    """
    errors = []
    warnings = []
    
    # Check Ollama availability
    ollama_available = False
    model_available = False
    
    try:
        ollama_health = await asyncio.to_thread(ollama_client.health_check)
        ollama_available = ollama_health
        
        if not ollama_available:
            errors.append(
                "Ollama is not running. Please start Ollama with: `ollama serve`"
            )
        else:
            # Check model availability
            model_check = await asyncio.to_thread(ollama_client.check_model_available)
            model_available = model_check
            
            if not model_available:
                errors.append(
                    f"Qwen2.5-VL 7B model not found. Please install with: `ollama pull {Config.OLLAMA_MODEL}`"
                )
    
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        errors.append(f"Failed to check Ollama status: {str(e)}")
    
    # Check database availability
    database_available = False
    try:
        # Simple check - try to query folders table
        folders = folder_manager.list_folders()
        database_available = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        errors.append(f"Database connection error: {str(e)}")
    
    # Check vector store availability
    vector_store_available = False
    try:
        # Try to access vector store
        vector_store = get_vector_store()
        vector_store_available = True
    except Exception as e:
        logger.error(f"Vector store health check failed: {e}")
        errors.append(f"Vector store connection error: {str(e)}")
    
    # Determine overall status
    if errors:
        status = "unhealthy"
    elif warnings:
        status = "degraded"
    else:
        status = "healthy"
    
    return HealthCheckResponse(
        status=status,
        ollama_available=ollama_available,
        model_available=model_available,
        database_available=database_available,
        vector_store_available=vector_store_available,
        errors=errors,
        warnings=warnings
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "RAG Chatbot API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "folders": "/api/folders/*",
            "processing": "/api/process/*",
            "conversations": "/api/conversations/*",
            "query": "/api/query"
        }
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "backend.api:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )

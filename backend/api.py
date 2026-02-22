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
from backend.export_manager import ExportManager
from backend.processing_validator import ProcessingValidator
from backend.resource_monitor import ResourceMonitor
from backend.data_loader import DataLoader

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
export_manager = None
processing_validator = None
resource_monitor = None
data_loader = None

# Processing state
processing_status = {
    "is_processing": False,
    "processed": 0,
    "skipped": 0,
    "failed": 0,
    "failed_files": [],
    "processed_files": [],
    "skipped_files": []
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global db_manager, folder_manager, document_processor, conversation_manager, query_engine, ollama_client, export_manager, processing_validator, resource_monitor, data_loader
    
    logger.info("Starting RAG chatbot API server")
    
    # Ensure data directories exist
    Config.ensure_data_directories()
    
    # Check deployment mode
    if Config.ENABLE_DOCUMENT_PROCESSING:
        # Desktop mode: Full document processing enabled
        logger.info("Starting in DESKTOP mode (document processing enabled)")
        
        # Initialize database (schema is initialized in __init__)
        db_manager = DatabaseManager(Config.SQLITE_PATH)
        
        # Initialize components
        folder_manager = FolderManager(db_manager)
        state_manager = ProcessingStateManager(db_manager)
        embedding_engine = get_embedding_engine()
        vector_store = get_vector_store()
        ollama_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_MODEL)
        # Use vision model for image processing
        vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
        image_processor = ImageProcessor(vision_client)
        
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
        
        # Initialize export and validation components
        export_manager = ExportManager(
            config=Config,
            vector_store=vector_store,
            db_manager=db_manager
        )
        
        processing_validator = ProcessingValidator(
            vector_store=vector_store,
            db_manager=db_manager
        )
        
        # Initialize Pi-specific components
        resource_monitor = ResourceMonitor(config=Config)
        data_loader = DataLoader(config=Config)
        
        # Set initial resource monitor state
        try:
            stats = vector_store.get_stats()
            total_chunks = stats.get('total_chunks', 0)
            resource_monitor.set_vector_store_loaded(True, total_chunks)
            logger.info(f"Resource monitor initialized with {total_chunks} chunks")
        except Exception as e:
            logger.warning(f"Could not initialize resource monitor stats: {e}")
            resource_monitor.set_vector_store_loaded(False, 0)
        
        # Start memory monitoring (logs every 60 seconds)
        resource_monitor.start_monitoring()
        
        logger.info("API server initialized successfully in DESKTOP mode")
    
    else:
        # Pi mode: Read-only mode, load pre-computed data
        logger.info("Starting in PI mode (document processing disabled)")
        
        try:
            # Initialize DataLoader
            data_loader = DataLoader(config=Config)
            
            # Validate manifest on startup
            logger.info("Validating manifest...")
            try:
                manifest_validation = data_loader.validate_manifest()
                
                if not manifest_validation.valid:
                    error_msg = f"Manifest validation failed: {', '.join(manifest_validation.errors)}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                if manifest_validation.warnings:
                    for warning in manifest_validation.warnings:
                        logger.warning(f"Manifest warning: {warning}")
                
                logger.info("Manifest validation passed")
                
            except Exception as e:
                logger.warning(f"Manifest validation failed: {e}")
                logger.warning("Proceeding without manifest validation")
            
            # Load vector store in read-only mode
            logger.info("Loading vector store in read-only mode...")
            try:
                vector_store = data_loader.load_vector_store()
                logger.info("Vector store loaded successfully")
            except Exception as e:
                error_msg = f"Failed to load vector store: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e
            
            # Load database in read-only mode
            logger.info("Loading database in read-only mode...")
            try:
                db_manager = data_loader.load_database()
                logger.info("Database loaded successfully")
            except Exception as e:
                error_msg = f"Failed to load database: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e
            
            # Initialize ResourceMonitor
            logger.info("Initializing resource monitor...")
            resource_monitor = ResourceMonitor(config=Config)
            
            # Set resource monitor state
            try:
                stats = vector_store.get_stats()
                total_chunks = stats.get('total_chunks', 0)
                resource_monitor.set_vector_store_loaded(True, total_chunks)
                logger.info(f"Resource monitor initialized with {total_chunks} chunks")
            except Exception as e:
                logger.warning(f"Could not initialize resource monitor stats: {e}")
                resource_monitor.set_vector_store_loaded(False, 0)
            
            # Start background memory monitoring task
            logger.info("Starting background memory monitoring...")
            resource_monitor.start_monitoring()
            
            # Initialize query components (no document processing)
            conversation_manager = ConversationManager(db_manager)
            query_engine = get_query_engine()
            ollama_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_MODEL)
            
            # Set components not used in Pi mode to None
            folder_manager = None
            document_processor = None
            export_manager = None
            processing_validator = None
            
            logger.info("API server initialized successfully in PI mode")
            
        except Exception as e:
            logger.error(f"Failed to start in PI mode: {e}")
            logger.error("Please ensure the export package has been transferred and extracted correctly")
            raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down API server")
    
    # Stop memory monitoring
    if resource_monitor:
        resource_monitor.stop_monitoring()
    
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


class ListFolderFilesRequest(BaseModel):
    """Request model for listing files in a folder."""
    path: str = Field(..., description="Path to folder")


class ListFolderFilesResponse(BaseModel):
    """Response model for listing files in a folder."""
    files: List[str]


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


@app.post("/api/folders/files", response_model=ListFolderFilesResponse)
async def list_folder_files(request: ListFolderFilesRequest):
    """
    List all files in a specific folder.
    
    Returns list of filenames (not full paths) in the folder.
    """
    try:
        import os
        from pathlib import Path
        
        folder_path = Path(request.path)
        
        if not folder_path.exists():
            raise HTTPException(status_code=404, detail="Folder not found")
        
        if not folder_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        # Get all files (not directories) in the folder
        files = []
        for item in folder_path.iterdir():
            if item.is_file():
                files.append(item.name)
        
        # Sort files alphabetically
        files.sort()
        
        return ListFolderFilesResponse(files=files)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list folder files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list folder files: {str(e)}")


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
            "failed_files": [],
            "processed_files": [],
            "skipped_files": []
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
                    ],
                    "processed_files": processing_status["processed_files"],
                    "skipped_files": processing_status["skipped_files"]
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
        processing_status["processed_files"] = result.processed_files
        processing_status["skipped_files"] = result.skipped_files
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
        
        # Get conversation history for context
        conversation_history = []
        if conversation and conversation.messages:
            # Get last 5 messages for context (excluding the current question)
            recent_messages = conversation.messages[-10:]  # Last 10 messages (5 exchanges)
            for msg in recent_messages:
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Process query using RAG with conversation history
        result = await asyncio.to_thread(
            query_engine.query,
            question=request.question,
            conversation_history=conversation_history,
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
    memory_usage_percent: float
    memory_available_mb: float
    model_loaded: bool
    vector_store_loaded: bool
    total_chunks: int
    ollama_available: bool
    model_available: bool
    database_available: bool
    errors: List[str]
    warnings: List[str]


# ============================================================================
# Export and Validation Models
# ============================================================================

class ExportRequest(BaseModel):
    """Request model for creating export package."""
    output_dir: str = Field(default="pi_export", description="Directory to create export package")
    incremental: bool = Field(default=False, description="Create incremental export")
    since_timestamp: Optional[str] = Field(default=None, description="ISO timestamp for incremental export")


class ExportResponse(BaseModel):
    """Response model for export package creation."""
    success: bool
    package_path: str
    archive_path: str
    size_bytes: int
    size_mb: float
    statistics: Dict[str, Any]
    errors: List[str]


class ValidateExportRequest(BaseModel):
    """Request model for validating export package."""
    package_path: str = Field(..., description="Path to export package directory")


class ValidateExportResponse(BaseModel):
    """Response model for export package validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]


class ProcessingReportResponse(BaseModel):
    """Response model for processing validation report."""
    total_documents: int
    total_chunks: int
    total_embeddings: int
    failed_documents: List[tuple]
    missing_embeddings: List[str]
    incomplete_metadata: List[str]
    validation_passed: bool


@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Check system health and dependencies.
    
    Returns comprehensive health status including:
    - Memory usage (from ResourceMonitor)
    - Model status (loaded/not loaded)
    - Vector store status (loaded/not loaded, chunk count)
    - Ollama service availability
    - Vision model installation
    - Database connectivity
    
    This endpoint is designed for Pi deployments to monitor system health.
    """
    errors = []
    warnings = []
    
    # Get system health from ResourceMonitor
    health_status = None
    if resource_monitor:
        try:
            health_status = resource_monitor.get_system_health()
            logger.info(f"System health: {health_status.status}, memory: {health_status.memory_usage_percent:.1f}%")
        except Exception as e:
            logger.error(f"Failed to get system health from ResourceMonitor: {e}")
            warnings.append(f"Resource monitoring unavailable: {str(e)}")
    
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
            model_check = await asyncio.to_thread(ollama_client.is_model_available)
            model_available = model_check
            
            if not model_available:
                errors.append(
                    f"Qwen2.5-VL 7B model not found. Please install with: `ollama pull {Config.OLLAMA_MODEL}`"
                )
            
            # Update resource monitor model status
            if resource_monitor:
                resource_monitor.set_model_loaded(model_available)
    
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
    vector_store_loaded = False
    total_chunks = 0
    try:
        # Try to access vector store
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        total_chunks = stats.get('total_chunks', 0)
        vector_store_loaded = True
        
        # Update resource monitor
        if resource_monitor:
            resource_monitor.set_vector_store_loaded(True, total_chunks)
    except Exception as e:
        logger.error(f"Vector store health check failed: {e}")
        errors.append(f"Vector store connection error: {str(e)}")
        
        # Update resource monitor
        if resource_monitor:
            resource_monitor.set_vector_store_loaded(False, 0)
    
    # Determine overall status
    if health_status:
        # Use ResourceMonitor status as base
        status = health_status.status
        memory_usage_percent = health_status.memory_usage_percent
        memory_available_mb = health_status.memory_available_mb
        model_loaded = health_status.model_loaded
    else:
        # Fallback if ResourceMonitor unavailable
        if errors:
            status = "unhealthy"
        elif warnings:
            status = "degraded"
        else:
            status = "healthy"
        
        # Try to get memory stats directly
        try:
            import psutil
            memory = psutil.virtual_memory()
            memory_usage_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
        except:
            memory_usage_percent = 0.0
            memory_available_mb = 0.0
        
        model_loaded = model_available
    
    # Override status if there are errors
    if errors:
        status = "unhealthy"
    elif warnings and status == "healthy":
        status = "degraded"
    
    return HealthCheckResponse(
        status=status,
        memory_usage_percent=memory_usage_percent,
        memory_available_mb=memory_available_mb,
        model_loaded=model_loaded,
        vector_store_loaded=vector_store_loaded,
        total_chunks=total_chunks,
        ollama_available=ollama_available,
        model_available=model_available,
        database_available=database_available,
        errors=errors,
        warnings=warnings
    )


# ============================================================================
# Export and Validation Endpoints
# ============================================================================

@app.post("/api/export", response_model=ExportResponse)
async def create_export(request: ExportRequest):
    """
    Create export package for Pi deployment.
    
    Creates a self-contained export package containing:
    - ChromaDB vector store
    - SQLite database
    - Manifest file with model requirements
    - Pi configuration template
    - Deployment instructions
    
    Supports both full and incremental exports.
    """
    if not export_manager:
        raise HTTPException(status_code=500, detail="Export manager not initialized")
    
    try:
        # Parse timestamp if provided
        since_timestamp = None
        if request.since_timestamp:
            from datetime import datetime
            try:
                since_timestamp = datetime.fromisoformat(request.since_timestamp)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid timestamp format: {request.since_timestamp}. Use ISO format (e.g., 2024-01-15T10:30:00)"
                )
        
        # Create export package
        logger.info(f"Creating {'incremental' if request.incremental else 'full'} export package")
        result = await asyncio.to_thread(
            export_manager.create_export_package,
            output_dir=request.output_dir,
            incremental=request.incremental,
            since_timestamp=since_timestamp
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Export failed: {', '.join(result.errors)}"
            )
        
        # Calculate size in MB
        size_mb = result.size_bytes / (1024 * 1024)
        
        logger.info(f"Export package created successfully: {result.archive_path}")
        
        return ExportResponse(
            success=result.success,
            package_path=result.package_path,
            archive_path=result.archive_path,
            size_bytes=result.size_bytes,
            size_mb=round(size_mb, 2),
            statistics=result.statistics,
            errors=result.errors
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/api/export/validate", response_model=ValidateExportResponse)
async def validate_export(package_path: str):
    """
    Validate an export package before transfer.
    
    Checks:
    - Required files and directories exist
    - Manifest is valid and complete
    - ChromaDB directory is not empty
    - Database file is not empty
    
    Args:
        package_path: Path to export package directory
    """
    if not export_manager:
        raise HTTPException(status_code=500, detail="Export manager not initialized")
    
    try:
        logger.info(f"Validating export package: {package_path}")
        
        result = await asyncio.to_thread(
            export_manager.validate_export_package,
            package_path=package_path
        )
        
        if result.valid:
            logger.info("Export package validation passed")
        else:
            logger.warning(f"Export package validation failed: {result.errors}")
        
        return ValidateExportResponse(
            valid=result.valid,
            errors=result.errors,
            warnings=result.warnings
        )
    
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.get("/api/processing/report", response_model=ProcessingReportResponse)
async def get_processing_report():
    """
    Get processing validation report.
    
    Validates all processed documents and returns:
    - Document, chunk, and embedding counts
    - List of chunks missing embeddings
    - List of chunks with incomplete metadata
    - Overall validation status
    
    Used to verify data quality before export.
    """
    if not processing_validator:
        raise HTTPException(status_code=500, detail="Processing validator not initialized")
    
    try:
        logger.info("Generating processing validation report")
        
        report = await asyncio.to_thread(
            processing_validator.validate_processing
        )
        
        if report.validation_passed:
            logger.info("Processing validation passed")
        else:
            logger.warning("Processing validation failed")
        
        return ProcessingReportResponse(
            total_documents=report.total_documents,
            total_chunks=report.total_chunks,
            total_embeddings=report.total_embeddings,
            failed_documents=report.failed_documents,
            missing_embeddings=report.missing_embeddings,
            incomplete_metadata=report.incomplete_metadata,
            validation_passed=report.validation_passed
        )
    
    except Exception as e:
        logger.error(f"Failed to generate processing report: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


# ============================================================================
# Pi-Specific Data Management Endpoints
# ============================================================================

class MergeIncrementalRequest(BaseModel):
    """Request model for merging incremental package."""
    package_path: str = Field(..., description="Path to incremental export package directory")


class MergeIncrementalResponse(BaseModel):
    """Response model for incremental merge."""
    success: bool
    merged_chunks: int
    updated_chunks: int
    deleted_chunks: int
    merge_time_seconds: float
    errors: List[str]


class DataStatsResponse(BaseModel):
    """Response model for data statistics."""
    total_chunks: int
    embedding_dimension: Optional[int]
    last_update: Optional[str]
    vector_store_size_mb: Optional[float]
    database_size_mb: Optional[float]


@app.post("/api/data/merge", response_model=MergeIncrementalResponse)
async def merge_incremental_data(request: MergeIncrementalRequest):
    """
    Merge incremental update package with existing data.
    
    This endpoint is designed for Pi deployment to merge incremental
    updates from the desktop without requiring full redeployment.
    
    The merge operation:
    - Validates package compatibility
    - Merges new chunks into vector store
    - Updates database with new processing state
    - Uses "newer wins" strategy for conflicts
    
    Args:
        request: Contains package_path to incremental export package
        
    Returns:
        MergeIncrementalResponse with merge statistics
    """
    try:
        logger.info(f"Merging incremental package from: {request.package_path}")
        
        # Initialize incremental merger
        from backend.incremental_merger import IncrementalMerger
        
        vector_store = get_vector_store()
        merger = IncrementalMerger(
            vector_store=vector_store,
            db_manager=db_manager
        )
        
        # Perform merge operation
        result = await asyncio.to_thread(
            merger.merge_incremental_package,
            package_path=request.package_path
        )
        
        if not result.success:
            logger.error(f"Merge failed: {result.errors}")
            raise HTTPException(
                status_code=500,
                detail=f"Merge failed: {', '.join(result.errors)}"
            )
        
        logger.info(
            f"Merge completed successfully: "
            f"{result.merged_chunks} merged, "
            f"{result.updated_chunks} updated, "
            f"{result.deleted_chunks} deleted in {result.merge_time_seconds:.2f}s"
        )
        
        return MergeIncrementalResponse(
            success=result.success,
            merged_chunks=result.merged_chunks,
            updated_chunks=result.updated_chunks,
            deleted_chunks=result.deleted_chunks,
            merge_time_seconds=result.merge_time_seconds,
            errors=result.errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Merge operation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Merge operation failed: {str(e)}"
        )


@app.get("/api/data/stats", response_model=DataStatsResponse)
async def get_data_stats():
    """
    Get data statistics for the current deployment.
    
    Returns information about:
    - Total number of chunks in vector store
    - Embedding dimension
    - Last update timestamp (from manifest if available)
    - Vector store size
    - Database size
    
    This endpoint is useful for monitoring data state on Pi deployments.
    """
    try:
        logger.info("Retrieving data statistics")
        
        vector_store = get_vector_store()
        
        # Get vector store stats
        stats = vector_store.get_stats()
        total_chunks = stats.get('total_chunks', 0)
        
        # Get embedding dimension
        embedding_dimension = vector_store.get_embedding_dimension()
        
        # Get last update from manifest if available
        last_update = None
        manifest_path = Config.MANIFEST_PATH
        
        try:
            from pathlib import Path
            import json
            
            manifest_file = Path(manifest_path)
            if manifest_file.exists():
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                    last_update = manifest.get('created_at')
                    logger.info(f"Last update from manifest: {last_update}")
        except Exception as e:
            logger.warning(f"Could not read manifest for last update: {e}")
        
        # Get vector store size
        vector_store_size_mb = None
        try:
            from pathlib import Path
            chromadb_path = Path(Config.CHROMADB_PATH)
            if chromadb_path.exists():
                # Calculate directory size
                total_size = sum(
                    f.stat().st_size 
                    for f in chromadb_path.rglob('*') 
                    if f.is_file()
                )
                vector_store_size_mb = total_size / (1024 * 1024)
                logger.info(f"Vector store size: {vector_store_size_mb:.2f} MB")
        except Exception as e:
            logger.warning(f"Could not calculate vector store size: {e}")
        
        # Get database size
        database_size_mb = None
        try:
            from pathlib import Path
            db_path = Path(Config.SQLITE_PATH)
            if db_path.exists():
                database_size_mb = db_path.stat().st_size / (1024 * 1024)
                logger.info(f"Database size: {database_size_mb:.2f} MB")
        except Exception as e:
            logger.warning(f"Could not calculate database size: {e}")
        
        logger.info(
            f"Data stats: {total_chunks} chunks, "
            f"dimension={embedding_dimension}, "
            f"last_update={last_update}"
        )
        
        return DataStatsResponse(
            total_chunks=total_chunks,
            embedding_dimension=embedding_dimension,
            last_update=last_update,
            vector_store_size_mb=round(vector_store_size_mb, 2) if vector_store_size_mb else None,
            database_size_mb=round(database_size_mb, 2) if database_size_mb else None
        )
        
    except Exception as e:
        logger.error(f"Failed to get data statistics: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get data statistics: {str(e)}"
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
            "query": "/api/query",
            "data": "/api/data/*"
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


@app.post("/api/admin/clear-all-data")
async def clear_all_data():
    """
    Clear all data - vector store and processing state.
    
    WARNING: This is a destructive operation for testing purposes only.
    """
    try:
        logger.warning("Clearing all data (vector store + processing state)")
        
        # Clear vector store
        vs = get_vector_store()
        vs.reset()
        logger.info("Vector store cleared")
        
        # Clear processing state
        with db_manager.transaction() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM processed_files")
            count = cursor.fetchone()[0]
            
            if count > 0:
                conn.execute("DELETE FROM processed_files")
                logger.info(f"Cleared processing state for {count} files")
            else:
                count = 0
        
        return {
            "success": True,
            "message": f"Cleared all data: vector store reset, {count} files removed from processing state"
        }
        
    except Exception as e:
        logger.error(f"Failed to clear data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/open-folder")
async def open_folder(request: dict):
    """
    Open a folder in the system's file explorer.
    
    Args:
        request: Dictionary with 'path' key containing the folder path
    """
    try:
        import subprocess
        import platform
        
        folder_path = request.get('path')
        if not folder_path:
            raise HTTPException(status_code=400, detail="Path is required")
        
        # Verify path exists
        from pathlib import Path
        path = Path(folder_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Path does not exist")
        
        # Open folder based on OS
        system = platform.system()
        
        if system == "Windows":
            # Open folder in Windows Explorer
            subprocess.Popen(['explorer', str(path)])
        elif system == "Darwin":  # macOS
            subprocess.Popen(['open', str(path)])
        else:  # Linux
            subprocess.Popen(['xdg-open', str(path)])
        
        return {"success": True, "message": f"Opened folder: {folder_path}"}
        
    except Exception as e:
        logger.error(f"Failed to open folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

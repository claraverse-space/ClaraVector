from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks

from app.models.responses import (
    DocumentResponse, DocumentListResponse,
    DocumentStatusResponse, DocumentUploadResponse
)
from app.api.dependencies import (
    get_database, get_lancedb, get_document_processor
)
from app.services.database import Database
from app.services.lancedb_service import LanceDBService
from app.services.document_processor import DocumentProcessor
from app.utils.hashing import compute_sha256
from app.config import get_settings


router = APIRouter(tags=["Documents"])


@router.post("/notebooks/{notebook_id}/documents", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    notebook_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Database = Depends(get_database),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """Upload a document to a notebook."""
    settings = get_settings()

    # Check notebook exists
    notebook = await db.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Get file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if not processor.is_supported(ext):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {processor.supported_types}"
        )

    # Read content
    content = await file.read()

    # Check file size
    max_size = settings.max_file_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
        )

    # Compute hash
    file_hash = compute_sha256(content)

    # Create document record
    doc = await db.create_document(
        notebook_id=notebook_id,
        user_id=notebook["user_id"],
        filename=file.filename,
        file_type=ext,
        file_size=len(content),
        file_hash=file_hash
    )

    # Process document in background
    background_tasks.add_task(
        processor.process_document,
        doc["document_id"],
        content,
        ext
    )

    return DocumentUploadResponse(
        document_id=doc["document_id"],
        filename=file.filename,
        file_type=ext,
        file_size=len(content),
        status="pending",
        message="Document uploaded and queued for processing"
    )


@router.get("/notebooks/{notebook_id}/documents", response_model=DocumentListResponse)
async def list_notebook_documents(
    notebook_id: str,
    db: Database = Depends(get_database)
):
    """List all documents in a notebook."""
    notebook = await db.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    documents = await db.get_notebook_documents(notebook_id)

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                document_id=d["document_id"],
                notebook_id=d["notebook_id"],
                user_id=d["user_id"],
                filename=d["filename"],
                file_type=d["file_type"],
                file_size=d["file_size"],
                chunk_count=d["chunk_count"],
                processing_status=d["processing_status"],
                error_message=d["error_message"],
                created_at=d["created_at"],
                processed_at=d["processed_at"]
            )
            for d in documents
        ],
        count=len(documents)
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: Database = Depends(get_database)
):
    """Get document details."""
    doc = await db.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        document_id=doc["document_id"],
        notebook_id=doc["notebook_id"],
        user_id=doc["user_id"],
        filename=doc["filename"],
        file_type=doc["file_type"],
        file_size=doc["file_size"],
        chunk_count=doc["chunk_count"],
        processing_status=doc["processing_status"],
        error_message=doc["error_message"],
        created_at=doc["created_at"],
        processed_at=doc["processed_at"]
    )


@router.get("/documents/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: str,
    db: Database = Depends(get_database)
):
    """Get detailed document processing status."""
    doc = await db.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    queue_status = await db.get_document_queue_status(document_id)

    return DocumentStatusResponse(
        document_id=doc["document_id"],
        processing_status=doc["processing_status"],
        chunk_count=doc["chunk_count"],
        queue_status=queue_status,
        error_message=doc["error_message"]
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    db: Database = Depends(get_database),
    lancedb: LanceDBService = Depends(get_lancedb),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """Delete a document."""
    doc = await db.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete vectors
    await lancedb.delete_document_vectors(doc["user_id"], document_id)

    # Delete file and database record
    await processor.delete_document(document_id, doc["file_type"])

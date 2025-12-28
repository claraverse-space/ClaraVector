from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, Enum):
    PDF = "pdf"
    TXT = "txt"
    MD = "md"
    DOCX = "docx"
    CSV = "csv"
    JSON = "json"
    HTML = "html"
    HTM = "htm"
    PPTX = "pptx"


# User responses
class UserResponse(BaseModel):
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Notebook responses
class NotebookResponse(BaseModel):
    notebook_id: str
    user_id: str
    name: str
    description: Optional[str]
    document_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotebookListResponse(BaseModel):
    notebooks: list[NotebookResponse]
    count: int


# Document responses
class DocumentResponse(BaseModel):
    document_id: str
    notebook_id: str
    user_id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    processing_status: str
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    count: int


class DocumentStatusResponse(BaseModel):
    document_id: str
    processing_status: str
    chunk_count: int
    queue_status: dict  # pending, processing, completed, failed counts
    error_message: Optional[str]


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    message: str


# Query responses
class QueryResultItem(BaseModel):
    chunk_id: str
    document_id: str
    notebook_id: str
    text: str
    score: float


class QueryResponse(BaseModel):
    query: str
    results: list[QueryResultItem]
    result_count: int
    search_time_ms: float


# Queue responses
class QueueStatusResponse(BaseModel):
    pending: int
    processing: int
    completed: int
    failed: int
    estimated_wait_minutes: Optional[float]


# Health responses
class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    nim_connected: bool
    database_connected: bool
    queue_depth: int

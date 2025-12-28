from functools import lru_cache

from app.services.database import Database
from app.services.lancedb_service import LanceDBService
from app.services.nim_client import NIMClient
from app.services.file_storage import FileStorage
from app.services.document_processor import DocumentProcessor
from app.services.embedding_queue import EmbeddingQueueProcessor, get_queue_processor


# Cached service instances
@lru_cache
def get_database() -> Database:
    return Database()


@lru_cache
def get_lancedb() -> LanceDBService:
    return LanceDBService()


@lru_cache
def get_nim_client() -> NIMClient:
    return NIMClient()


@lru_cache
def get_file_storage() -> FileStorage:
    return FileStorage()


@lru_cache
def get_document_processor() -> DocumentProcessor:
    return DocumentProcessor(
        db=get_database(),
        storage=get_file_storage()
    )


def get_embedding_queue() -> EmbeddingQueueProcessor:
    return get_queue_processor()

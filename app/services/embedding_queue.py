import asyncio
from typing import Optional
import logging

from app.config import get_settings
from app.services.database import Database
from app.services.nim_client import NIMClient
from app.services.lancedb_service import LanceDBService


logger = logging.getLogger(__name__)


class EmbeddingQueueProcessor:
    """
    Background processor for embedding queue.
    Respects NVIDIA NIM rate limits (40 RPM).
    """

    def __init__(
        self,
        db: Optional[Database] = None,
        nim_client: Optional[NIMClient] = None,
        lancedb: Optional[LanceDBService] = None
    ):
        self.db = db or Database()
        self.nim_client = nim_client or NIMClient()
        self.lancedb = lancedb or LanceDBService()

        settings = get_settings()
        self.max_retries = settings.max_retries

        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background queue processor."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Embedding queue processor started")

    async def stop(self):
        """Stop the queue processor gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Embedding queue processor stopped")

    async def _process_loop(self):
        """Main processing loop."""
        while self._running:
            try:
                # Get next pending chunk
                chunk = await self.db.get_next_pending_chunk()

                if chunk:
                    await self._process_chunk(chunk)
                else:
                    # No pending chunks, wait before checking again
                    await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processor error: {e}")
                await asyncio.sleep(5.0)

    async def _process_chunk(self, chunk: dict):
        """Process a single chunk: get embedding and store in LanceDB."""
        queue_id = chunk["queue_id"]
        document_id = chunk["document_id"]
        chunk_index = chunk["chunk_index"]
        chunk_text = chunk["chunk_text"]

        try:
            # Get embedding from NIM (rate limited internally)
            embedding = await self.nim_client.get_passage_embedding(chunk_text)

            # Get document info for metadata
            doc = await self.db.get_document(document_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found")

            # Store in LanceDB
            await self.lancedb.add_vector(
                user_id=doc["user_id"],
                document_id=document_id,
                notebook_id=doc["notebook_id"],
                chunk_index=chunk_index,
                text=chunk_text,
                embedding=embedding
            )

            # Mark as completed
            await self.db.mark_chunk_completed(queue_id)

            # Check if document is fully processed
            if await self.db.check_document_completed(document_id):
                await self.db.update_document_status(document_id, "completed")
                logger.info(f"Document {document_id} fully processed")

        except Exception as e:
            logger.error(f"Failed to process chunk {queue_id}: {e}")
            await self.db.mark_chunk_failed(queue_id, str(e), self.max_retries)

            # Check if all chunks failed
            status = await self.db.get_document_queue_status(document_id)
            if status["pending"] == 0 and status["processing"] == 0:
                if status["failed"] > 0 and status["completed"] == 0:
                    await self.db.update_document_status(
                        document_id, "failed",
                        error_message="All chunks failed to process"
                    )


# Global processor instance
_processor: Optional[EmbeddingQueueProcessor] = None


def get_queue_processor() -> EmbeddingQueueProcessor:
    """Get or create the global queue processor."""
    global _processor
    if _processor is None:
        _processor = EmbeddingQueueProcessor()
    return _processor

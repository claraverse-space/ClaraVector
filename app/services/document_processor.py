from pathlib import Path
from typing import Optional
import asyncio

from app.parsers.base import BaseParser
from app.parsers.pdf_parser import PDFParser
from app.parsers.docx_parser import DOCXParser
from app.parsers.pptx_parser import PPTXParser
from app.parsers.html_parser import HTMLParser
from app.parsers.text_parser import TextParser
from app.parsers.csv_parser import CSVParser
from app.parsers.json_parser import JSONParser
from app.parsers.chunker import DocumentChunker
from app.services.database import Database
from app.services.file_storage import FileStorage


class DocumentProcessor:
    """Orchestrates document parsing, chunking, and queue insertion."""

    PARSERS: list[BaseParser] = [
        PDFParser(),
        DOCXParser(),
        PPTXParser(),
        HTMLParser(),
        TextParser(),
        CSVParser(),
        JSONParser(),
    ]

    def __init__(
        self,
        db: Optional[Database] = None,
        storage: Optional[FileStorage] = None,
        chunker: Optional[DocumentChunker] = None
    ):
        self.db = db or Database()
        self.storage = storage or FileStorage()
        self.chunker = chunker or DocumentChunker()

    def get_parser(self, file_type: str) -> Optional[BaseParser]:
        """Get appropriate parser for file type."""
        for parser in self.PARSERS:
            if parser.supports(file_type):
                return parser
        return None

    def is_supported(self, file_type: str) -> bool:
        """Check if file type is supported."""
        return self.get_parser(file_type) is not None

    @property
    def supported_types(self) -> list[str]:
        """List of supported file types."""
        return ["pdf", "docx", "pptx", "html", "htm", "txt", "md", "csv", "json"]

    async def process_document(
        self,
        document_id: str,
        content: bytes,
        file_type: str
    ) -> dict:
        """
        Process a document: save, parse, chunk, and queue for embedding.

        Returns processing result with chunk count.
        """
        try:
            # Update status to processing
            await self.db.update_document_status(document_id, "processing")

            # Save file
            file_path = await self.storage.save_file(document_id, content, file_type)

            # Get parser
            parser = self.get_parser(file_type)
            if not parser:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Parse document (run in executor to not block)
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, parser.parse, file_path)

            if not text or not text.strip():
                raise ValueError("Document contains no extractable text")

            # Chunk the text
            chunks = self.chunker.chunk_text(text)

            if not chunks:
                raise ValueError("Document could not be chunked")

            # Queue chunks for embedding
            await self.db.enqueue_chunks(document_id, chunks)

            # Update document with chunk count
            await self.db.update_document_status(
                document_id,
                "processing",  # Still processing until embeddings are done
                chunk_count=len(chunks)
            )

            return {
                "document_id": document_id,
                "status": "processing",
                "chunk_count": len(chunks),
                "text_length": len(text)
            }

        except Exception as e:
            await self.db.update_document_status(
                document_id,
                "failed",
                error_message=str(e)
            )
            raise

    async def delete_document(self, document_id: str, file_type: str) -> bool:
        """Delete document and its files."""
        # Delete from storage
        await self.storage.delete_file(document_id, file_type)

        # Delete from database (cascades to queue)
        return await self.db.delete_document(document_id)

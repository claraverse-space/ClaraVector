from pathlib import Path
import hashlib
import shutil
from typing import Optional

from app.config import get_settings


class FileStorage:
    """File system storage for uploaded documents."""

    def __init__(self, base_path: Optional[Path] = None):
        settings = get_settings()
        self.base_path = base_path or settings.files_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_document_dir(self, document_id: str) -> Path:
        """Get directory for a document (sharded by first 6 chars)."""
        prefix = document_id[:6]
        return self.base_path / prefix

    def _get_document_path(self, document_id: str, extension: str) -> Path:
        """Get full path for a document."""
        dir_path = self._get_document_dir(document_id)
        return dir_path / f"{document_id}.{extension}"

    async def save_file(self, document_id: str, content: bytes, extension: str) -> Path:
        """Save file content to storage."""
        dir_path = self._get_document_dir(document_id)
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = self._get_document_path(document_id, extension)
        file_path.write_bytes(content)

        return file_path

    async def get_file_path(self, document_id: str, extension: str) -> Optional[Path]:
        """Get path to stored file."""
        file_path = self._get_document_path(document_id, extension)
        return file_path if file_path.exists() else None

    async def delete_file(self, document_id: str, extension: str) -> bool:
        """Delete a stored file."""
        file_path = self._get_document_path(document_id, extension)
        if file_path.exists():
            file_path.unlink()
            # Clean up empty directory
            dir_path = file_path.parent
            if dir_path.exists() and not any(dir_path.iterdir()):
                dir_path.rmdir()
            return True
        return False

    async def delete_user_files(self, document_ids: list[str], extensions: list[str]):
        """Delete all files for a user."""
        for doc_id, ext in zip(document_ids, extensions):
            await self.delete_file(doc_id, ext)

    @staticmethod
    def compute_hash(content: bytes) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content).hexdigest()

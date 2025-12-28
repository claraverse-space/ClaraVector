from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> str:
        """Parse document and return text content."""
        pass

    @abstractmethod
    def supports(self, file_type: str) -> bool:
        """Check if this parser supports the given file type."""
        pass

    def get_metadata(self, file_path: Path) -> dict:
        """Extract metadata from document (override in subclasses)."""
        return {
            "filename": file_path.name,
            "size": file_path.stat().st_size if file_path.exists() else 0
        }

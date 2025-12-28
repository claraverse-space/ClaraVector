from pathlib import Path

from app.parsers.base import BaseParser


class TextParser(BaseParser):
    """Plain text and Markdown parser."""

    def supports(self, file_type: str) -> bool:
        return file_type.lower() in ("txt", "md", "markdown", "text")

    def parse(self, file_path: Path) -> str:
        """Read plain text file."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def get_metadata(self, file_path: Path) -> dict:
        """Get text file metadata."""
        metadata = super().get_metadata(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                metadata["line_count"] = content.count("\n") + 1
                metadata["word_count"] = len(content.split())
        except Exception:
            pass

        return metadata

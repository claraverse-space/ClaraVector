from pathlib import Path
from bs4 import BeautifulSoup

from app.parsers.base import BaseParser


class HTMLParser(BaseParser):
    """HTML document parser using BeautifulSoup."""

    def supports(self, file_type: str) -> bool:
        return file_type.lower() in ("html", "htm")

    def parse(self, file_path: Path) -> str:
        """Extract text from HTML document."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        soup = BeautifulSoup(content, "lxml")

        # Remove script and style elements
        for element in soup(["script", "style", "meta", "link", "noscript"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator="\n")

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n\n".join(lines)

    def get_metadata(self, file_path: Path) -> dict:
        """Extract HTML metadata."""
        metadata = super().get_metadata(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            soup = BeautifulSoup(content, "lxml")

            title_tag = soup.find("title")
            if title_tag:
                metadata["title"] = title_tag.get_text().strip()

            # Get meta description
            desc_tag = soup.find("meta", attrs={"name": "description"})
            if desc_tag and desc_tag.get("content"):
                metadata["description"] = desc_tag["content"]
        except Exception:
            pass

        return metadata

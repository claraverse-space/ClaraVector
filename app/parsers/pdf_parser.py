from pathlib import Path
import fitz  # pymupdf

from app.parsers.base import BaseParser


class PDFParser(BaseParser):
    """PDF document parser using PyMuPDF for robust text extraction."""

    def supports(self, file_type: str) -> bool:
        return file_type.lower() == "pdf"

    def parse(self, file_path: Path) -> str:
        """Extract text from PDF document with better handling of complex content."""
        doc = fitz.open(file_path)
        text_parts = []

        for page_num, page in enumerate(doc):
            # Extract text with better formatting preservation
            # Using "text" extraction with sorting for reading order
            text = page.get_text("text", sort=True)

            if text and text.strip():
                # Clean up the text
                text = self._clean_page_text(text)
                text_parts.append(text)

        doc.close()
        return "\n\n".join(text_parts)

    def _clean_page_text(self, text: str) -> str:
        """Clean extracted text from PDF artifacts."""
        import re

        # Remove excessive whitespace but preserve paragraph breaks
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                # Remove common PDF artifacts
                # Remove standalone numbers that are likely page numbers
                if re.match(r'^\d{1,3}$', line):
                    continue
                # Remove lines that are just symbols
                if re.match(r'^[\-\–\—\=\_\.]+$', line):
                    continue
                cleaned_lines.append(line)

        # Join lines, preserving paragraph structure
        result = []
        current_para = []

        for line in cleaned_lines:
            # Check if line ends with sentence-ending punctuation
            if line and line[-1] in '.!?:':
                current_para.append(line)
                result.append(' '.join(current_para))
                current_para = []
            else:
                current_para.append(line)

        if current_para:
            result.append(' '.join(current_para))

        return '\n\n'.join(result)

    def get_metadata(self, file_path: Path) -> dict:
        """Extract PDF metadata."""
        metadata = super().get_metadata(file_path)

        try:
            doc = fitz.open(file_path)
            metadata["page_count"] = len(doc)

            pdf_metadata = doc.metadata
            if pdf_metadata:
                if pdf_metadata.get("title"):
                    metadata["title"] = pdf_metadata["title"]
                if pdf_metadata.get("author"):
                    metadata["author"] = pdf_metadata["author"]
                if pdf_metadata.get("subject"):
                    metadata["subject"] = pdf_metadata["subject"]

            doc.close()
        except Exception:
            pass

        return metadata

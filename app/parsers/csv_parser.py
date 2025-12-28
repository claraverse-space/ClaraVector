from pathlib import Path
import csv

from app.parsers.base import BaseParser


class CSVParser(BaseParser):
    """CSV file parser."""

    def supports(self, file_type: str) -> bool:
        return file_type.lower() == "csv"

    def parse(self, file_path: Path) -> str:
        """Parse CSV and convert to readable text."""
        text_parts = []

        with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
            # Detect dialect
            sample = f.read(8192)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                dialect = csv.excel

            reader = csv.reader(f, dialect)
            headers = None

            for i, row in enumerate(reader):
                if i == 0:
                    headers = row
                    text_parts.append("Headers: " + " | ".join(headers))
                else:
                    if headers and len(row) == len(headers):
                        # Format as key: value pairs
                        row_text = ", ".join(
                            f"{headers[j]}: {row[j]}"
                            for j in range(len(row))
                            if row[j].strip()
                        )
                    else:
                        row_text = " | ".join(cell for cell in row if cell.strip())

                    if row_text:
                        text_parts.append(f"Row {i}: {row_text}")

        return "\n".join(text_parts)

    def get_metadata(self, file_path: Path) -> dict:
        """Get CSV metadata."""
        metadata = super().get_metadata(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
                metadata["row_count"] = len(rows)
                if rows:
                    metadata["column_count"] = len(rows[0])
        except Exception:
            pass

        return metadata

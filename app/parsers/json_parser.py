from pathlib import Path
import json

from app.parsers.base import BaseParser


class JSONParser(BaseParser):
    """JSON file parser."""

    def supports(self, file_type: str) -> bool:
        return file_type.lower() == "json"

    def parse(self, file_path: Path) -> str:
        """Parse JSON and convert to readable text."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)

        return self._json_to_text(data)

    def _json_to_text(self, data, prefix: str = "") -> str:
        """Recursively convert JSON to readable text."""
        parts = []

        if isinstance(data, dict):
            for key, value in data.items():
                key_path = f"{prefix}.{key}" if prefix else key

                if isinstance(value, (dict, list)):
                    parts.append(f"{key_path}:")
                    parts.append(self._json_to_text(value, key_path))
                else:
                    parts.append(f"{key_path}: {value}")

        elif isinstance(data, list):
            for i, item in enumerate(data):
                item_prefix = f"{prefix}[{i}]" if prefix else f"[{i}]"

                if isinstance(item, (dict, list)):
                    parts.append(self._json_to_text(item, item_prefix))
                else:
                    parts.append(f"{item_prefix}: {item}")

        else:
            parts.append(str(data))

        return "\n".join(parts)

    def get_metadata(self, file_path: Path) -> dict:
        """Get JSON metadata."""
        metadata = super().get_metadata(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)

            if isinstance(data, dict):
                metadata["type"] = "object"
                metadata["key_count"] = len(data)
            elif isinstance(data, list):
                metadata["type"] = "array"
                metadata["item_count"] = len(data)
        except Exception:
            pass

        return metadata

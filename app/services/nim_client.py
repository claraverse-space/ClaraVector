import httpx
import asyncio
import time
import re
import unicodedata
from typing import Optional
import logging

from app.config import get_settings


logger = logging.getLogger(__name__)


class NIMClient:
    """NVIDIA NIM API client for embeddings with rate limiting."""

    # Max input length for NIM embedding API
    # NIM has 512 token limit, ~4 chars per token = ~2000 chars
    # Using 1800 to leave buffer
    MAX_INPUT_LENGTH = 1800

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.nim_api_key
        self.base_url = settings.nim_base_url
        self.model = settings.nim_model
        self.embedding_dim = settings.nim_embedding_dim
        self.min_interval = settings.min_request_interval

        self._last_request_time = 0.0
        self._lock = asyncio.Lock()

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text for the embedding API."""
        if not text:
            return ""

        # Normalize unicode
        text = unicodedata.normalize("NFKC", text)

        # Replace common problematic characters
        replacements = {
            '\x00': '',  # Null bytes
            '\ufffd': '',  # Replacement character
            '\u2028': ' ',  # Line separator
            '\u2029': ' ',  # Paragraph separator
            '\u200b': '',  # Zero-width space
            '\u200c': '',  # Zero-width non-joiner
            '\u200d': '',  # Zero-width joiner
            '\ufeff': '',  # BOM
            # Math symbols to text
            '√': 'sqrt',
            '∑': 'sum',
            '∏': 'product',
            '∫': 'integral',
            '∂': 'd',
            '∇': 'grad',
            '∈': ' in ',
            '∉': ' not in ',
            '⊂': ' subset ',
            '⊆': ' subset ',
            '∩': ' and ',
            '∪': ' or ',
            '≤': '<=',
            '≥': '>=',
            '≠': '!=',
            '≈': '~=',
            '∞': 'inf',
            '±': '+/-',
            '×': 'x',
            '÷': '/',
            '·': '*',
            '°': ' deg',
            # Greek letters
            'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
            'ε': 'epsilon', 'ζ': 'zeta', 'η': 'eta', 'θ': 'theta',
            'ι': 'iota', 'κ': 'kappa', 'λ': 'lambda', 'μ': 'mu',
            'ν': 'nu', 'ξ': 'xi', 'π': 'pi', 'ρ': 'rho',
            'σ': 'sigma', 'τ': 'tau', 'υ': 'upsilon', 'φ': 'phi',
            'χ': 'chi', 'ψ': 'psi', 'ω': 'omega',
            'Α': 'Alpha', 'Β': 'Beta', 'Γ': 'Gamma', 'Δ': 'Delta',
            'Θ': 'Theta', 'Λ': 'Lambda', 'Σ': 'Sigma', 'Φ': 'Phi',
            'Ψ': 'Psi', 'Ω': 'Omega',
            # Arrows
            '→': '->', '←': '<-', '↔': '<->', '⇒': '=>', '⇐': '<=',
            # Subscripts/superscripts to normal
            '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
            '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
            '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
            '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Remove any remaining non-printable characters except common whitespace
        text = ''.join(
            char if (char.isprintable() or char in '\n\t\r ') else ' '
            for char in text
        )

        # Collapse multiple whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Truncate if too long
        if len(text) > self.MAX_INPUT_LENGTH:
            text = text[:self.MAX_INPUT_LENGTH]
            # Try to cut at a sentence boundary
            last_period = text.rfind('. ')
            if last_period > self.MAX_INPUT_LENGTH * 0.8:
                text = text[:last_period + 1]

        return text

    async def _rate_limit(self):
        """Enforce rate limiting."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time

            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)

            self._last_request_time = time.monotonic()

    async def get_embedding(self, text: str, input_type: str = "passage") -> list[float]:
        """
        Get embedding for a single text.

        Args:
            text: Text to embed
            input_type: "passage" for documents, "query" for search queries

        Returns:
            Embedding vector (1024 dimensions for nv-embedqa-e5-v5)
        """
        # Sanitize the text first
        text = self._sanitize_text(text)

        if not text or len(text) < 10:
            raise ValueError("Text too short or empty after sanitization")

        await self._rate_limit()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "input": text,
                    "input_type": input_type,
                    "encoding_format": "float"
                }
            )

            if response.status_code != 200:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = str(error_data)
                except Exception:
                    error_detail = response.text[:500]
                logger.error(f"NIM API error {response.status_code}: {error_detail}")
                logger.error(f"Failed text (first 200 chars): {text[:200]}")
                response.raise_for_status()

            data = response.json()
            return data["data"][0]["embedding"]

    async def get_query_embedding(self, query: str) -> list[float]:
        """Get embedding optimized for search queries."""
        return await self.get_embedding(query, input_type="query")

    async def get_passage_embedding(self, text: str) -> list[float]:
        """Get embedding optimized for document passages."""
        return await self.get_embedding(text, input_type="passage")

    async def health_check(self) -> bool:
        """Check if NIM API is accessible."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return response.status_code == 200
        except Exception:
            return False

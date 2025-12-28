"""
Document chunker with accurate token counting for NIM's 512 token limit.
"""

from typing import Optional
import re
import unicodedata
from app.config import get_settings
from app.utils.tokenizer import get_token_counter, TokenCounter


class DocumentChunker:
    """
    Token-aware text chunker optimized for NIM's embedding API.

    Uses accurate token counting to ensure chunks stay within
    the 512 token limit of NIM's E5-based model.
    """

    # NIM's hard limit
    MAX_TOKENS = 512

    # Safe limit with buffer for edge cases
    SAFE_MAX_TOKENS = 450

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        overlap_tokens: Optional[int] = None,
        min_tokens: int = 20
    ):
        settings = get_settings()
        self.max_tokens = max_tokens or self.SAFE_MAX_TOKENS
        self.overlap_tokens = overlap_tokens or int(self.max_tokens * 0.1)
        self.min_tokens = min_tokens
        self.token_counter = get_token_counter()

        # Sentence separators in priority order
        self.separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text for embedding API compatibility."""
        if not text:
            return ""

        # Normalize unicode characters
        text = unicodedata.normalize("NFKC", text)

        # Replace common math/special symbols with text equivalents
        replacements = {
            '\x00': '', '\ufffd': '', '\u2028': ' ', '\u2029': ' ',
            '\u200b': '', '\u200c': '', '\u200d': '', '\ufeff': '',
            '√': 'sqrt', '∑': 'sum', '∏': 'product', '∫': 'integral',
            '∂': 'd', '∇': 'grad', '∈': ' in ', '∉': ' not in ',
            '⊂': ' subset ', '⊆': ' subset ', '∩': ' and ', '∪': ' or ',
            '≤': '<=', '≥': '>=', '≠': '!=', '≈': '~=', '∞': 'inf',
            '±': '+/-', '×': 'x', '÷': '/', '·': '*', '°': ' deg',
            'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
            'ε': 'epsilon', 'ζ': 'zeta', 'η': 'eta', 'θ': 'theta',
            'ι': 'iota', 'κ': 'kappa', 'λ': 'lambda', 'μ': 'mu',
            'ν': 'nu', 'ξ': 'xi', 'π': 'pi', 'ρ': 'rho',
            'σ': 'sigma', 'τ': 'tau', 'υ': 'upsilon', 'φ': 'phi',
            'χ': 'chi', 'ψ': 'psi', 'ω': 'omega',
            'Α': 'Alpha', 'Β': 'Beta', 'Γ': 'Gamma', 'Δ': 'Delta',
            'Θ': 'Theta', 'Λ': 'Lambda', 'Σ': 'Sigma', 'Φ': 'Phi',
            'Ψ': 'Psi', 'Ω': 'Omega',
            '→': '->', '←': '<-', '↔': '<->', '⇒': '=>', '⇐': '<=',
            '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
            '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
            '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
            '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Remove non-printable characters
        text = ''.join(
            char if (char.isprintable() or char in '\n\t\r ') else ' '
            for char in text
        )

        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return self.token_counter.count_tokens(text)

    def chunk_text(self, text: str) -> list[dict]:
        """
        Split text into token-limited chunks.

        Returns list of chunks, each guaranteed to be under MAX_TOKENS.
        """
        if not text or not text.strip():
            return []

        # Sanitize text first
        text = self._sanitize_text(text)
        text = " ".join(text.split())

        if not text:
            return []

        # Split into sentences first
        sentences = self._split_into_sentences(text)

        # Build chunks from sentences
        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            # If single sentence exceeds limit, split it further
            if sentence_tokens > self.max_tokens:
                # Flush current chunk first
                if current_chunk:
                    chunks.append(self._finalize_chunk(current_chunk, len(chunks)))
                    current_chunk = []
                    current_tokens = 0

                # Split long sentence
                sub_chunks = self._split_long_text(sentence)
                for sub in sub_chunks:
                    chunks.append(self._finalize_chunk([sub], len(chunks)))
                continue

            # Check if adding sentence exceeds limit
            if current_tokens + sentence_tokens > self.max_tokens:
                # Finalize current chunk
                if current_chunk:
                    chunks.append(self._finalize_chunk(current_chunk, len(chunks)))

                # Start new chunk with overlap from previous
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                current_tokens = self.count_tokens(' '.join(current_chunk))
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if self.count_tokens(chunk_text) >= self.min_tokens:
                chunks.append(self._finalize_chunk(current_chunk, len(chunks)))

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_long_text(self, text: str) -> list[str]:
        """Split text that exceeds token limit."""
        chunks = []
        words = text.split()

        current_words = []
        current_tokens = 0

        for word in words:
            word_tokens = self.count_tokens(word)

            if current_tokens + word_tokens > self.max_tokens:
                if current_words:
                    chunks.append(' '.join(current_words))
                current_words = [word]
                current_tokens = word_tokens
            else:
                current_words.append(word)
                current_tokens += word_tokens

        if current_words:
            chunks.append(' '.join(current_words))

        return chunks

    def _get_overlap(self, chunk_parts: list[str]) -> str:
        """Get overlap text from previous chunk."""
        if not chunk_parts:
            return ""

        full_text = ' '.join(chunk_parts)
        words = full_text.split()

        # Take last N words that fit in overlap_tokens
        overlap_words = []
        token_count = 0

        for word in reversed(words):
            word_tokens = self.count_tokens(word)
            if token_count + word_tokens > self.overlap_tokens:
                break
            overlap_words.insert(0, word)
            token_count += word_tokens

        return ' '.join(overlap_words)

    def _finalize_chunk(self, parts: list[str], index: int) -> dict:
        """Create final chunk dict with metadata."""
        text = ' '.join(parts).strip()

        # Final safety truncation
        if self.count_tokens(text) > self.MAX_TOKENS:
            text = self.token_counter.truncate_to_tokens(text, self.SAFE_MAX_TOKENS)

        return {
            "text": text,
            "index": index,
            "token_count": self.count_tokens(text),
            "char_count": len(text)
        }

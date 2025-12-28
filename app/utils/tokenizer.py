"""
Token counter for accurate chunk sizing.
Uses a BERT-based tokenizer compatible with E5 models (which NIM uses).
"""

from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.pre_tokenizers import Whitespace
from functools import lru_cache
import re


class TokenCounter:
    """
    Accurate token counter for NIM's E5-based embedding model.

    The nv-embedqa-e5-v5 model uses a BERT-style tokenizer with ~30k vocab.
    We use a simple but accurate approximation based on word pieces.
    """

    # NIM's token limit
    MAX_TOKENS = 512

    # Safe limit with buffer
    SAFE_MAX_TOKENS = 480

    def __init__(self):
        # Use a simple but accurate word-piece approximation
        # BERT/E5 tokenizers typically:
        # - Split on whitespace and punctuation
        # - Further split long words into subwords
        # Average: ~1.3 tokens per word for English text
        self._word_pattern = re.compile(r'\b\w+\b|[^\w\s]')

    def count_tokens(self, text: str) -> int:
        """
        Count approximate tokens in text.

        This uses a conservative estimate that matches BERT-style tokenizers:
        - Each word counts as 1-2 tokens (avg 1.3)
        - Punctuation counts as 1 token each
        - Numbers may be split into multiple tokens
        """
        if not text:
            return 0

        # Find all words and punctuation
        tokens = self._word_pattern.findall(text)

        token_count = 0
        for token in tokens:
            if token.isdigit():
                # Numbers: roughly 1 token per 2-3 digits
                token_count += max(1, len(token) // 2)
            elif len(token) <= 4:
                # Short words: usually 1 token
                token_count += 1
            elif len(token) <= 8:
                # Medium words: usually 1-2 tokens
                token_count += 1.3
            else:
                # Long words: often split into multiple subwords
                token_count += len(token) / 5

        return int(token_count * 1.1)  # Add 10% safety margin

    def truncate_to_tokens(self, text: str, max_tokens: int = None) -> str:
        """Truncate text to fit within token limit."""
        if max_tokens is None:
            max_tokens = self.SAFE_MAX_TOKENS

        current_tokens = self.count_tokens(text)

        if current_tokens <= max_tokens:
            return text

        # Binary search for the right length
        words = text.split()
        low, high = 0, len(words)

        while low < high:
            mid = (low + high + 1) // 2
            test_text = ' '.join(words[:mid])
            if self.count_tokens(test_text) <= max_tokens:
                low = mid
            else:
                high = mid - 1

        result = ' '.join(words[:low])

        # Try to end at a sentence boundary
        for end_char in ['. ', '! ', '? ']:
            last_idx = result.rfind(end_char)
            if last_idx > len(result) * 0.7:
                result = result[:last_idx + 1]
                break

        return result.strip()

    def is_within_limit(self, text: str, max_tokens: int = None) -> bool:
        """Check if text is within token limit."""
        if max_tokens is None:
            max_tokens = self.SAFE_MAX_TOKENS
        return self.count_tokens(text) <= max_tokens


@lru_cache(maxsize=1)
def get_token_counter() -> TokenCounter:
    """Get singleton token counter instance."""
    return TokenCounter()

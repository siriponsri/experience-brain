from __future__ import annotations

import tiktoken

from .config import Settings


def count_tokens(settings: Settings, text: str) -> int:
    return len(tiktoken.get_encoding(settings.tokenizer_encoding).encode(text))

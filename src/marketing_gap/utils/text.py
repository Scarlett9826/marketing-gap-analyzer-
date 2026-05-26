"""Text utilities: cleaning, matching, and shortening."""

from __future__ import annotations

import re
from typing import Iterable


def shorten(text: str, max_len: int = 140) -> str:
    """Collapse whitespace, drop short bracketed tags, truncate with ellipsis."""
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"\[[^\]]{1,20}\]", "", text)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def matches_any(text: str, aliases: Iterable[str], *, case_insensitive: bool = True) -> bool:
    """Return True if any alias appears in text."""
    if not text:
        return False
    haystack = text.lower() if case_insensitive else text
    for alias in aliases:
        needle = alias.lower() if case_insensitive else alias
        if needle and needle in haystack:
            return True
    return False

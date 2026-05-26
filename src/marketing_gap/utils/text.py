"""Text utilities: cleaning, matching, shortening, and filtering."""

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


def clean_text(text: str) -> str:
    """Remove short bracketed tags (emojis like [doge]) and collapse whitespace."""
    text = (text or "").strip()
    text = re.sub(r"\[[^\]]{1,8}\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_template_rant(text: str) -> bool:
    """Detect copy-paste template rants that flood comment sections.

    These are typically multi-paragraph copy-paste hate comments that repeat
    the brand name many times (e.g., '华为折叠最差 / 最拉' templates).
    """
    text = (text or "").strip()
    # Template rants tend to repeat a brand name 6+ times
    return len(text) >= 100 and text.count("华为") >= 6


def is_low_signal(text: str) -> bool:
    """Return True if the comment is too short / purely punctuation / no analytical value."""
    t = clean_text(text)
    if len(t) < 5:
        return True
    if re.fullmatch(r"[?？!！。.，,~～\s]+", t):
        return True
    return False


def normalize_for_dedup(text: str) -> str:
    """Lowercase + strip punctuation for deduplication key."""
    if not text:
        return ""
    t = text.strip().lower()
    return re.sub(r"[^\w\s]", "", t)[:30]

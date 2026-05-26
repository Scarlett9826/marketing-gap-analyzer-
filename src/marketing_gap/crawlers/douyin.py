"""Douyin (抖音) comment fetcher — wraps MediaCrawler.

Two crawl modes:

- :func:`fetch_search` — keyword search → top videos → comments.
- :func:`fetch_detail` — fixed video-id list → comments.

Both shell out to ``main.py --platform dy`` and normalise the JSON output.
Cookie/QR-code login is delegated to MediaCrawler.

Output schema (after normalisation)::

    {"source": "抖音评论", "post_id": "<comment_id>",
     "note_id": "<aweme_id>", "content": "...", "like": <int>,
     "url": "https://www.douyin.com/video/<aweme_id>", "keyword": "..."}
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .base import write_records
from ._mediacrawler import (
    _find_latest_comments_file,
    resolve_home,
    run_mediacrawler,
)


def normalise_douyin(
    raw_path: Path,
    *,
    keywords: str | None = None,
) -> list[dict[str, Any]]:
    """Convert MediaCrawler's Douyin comment JSON into the mgap comment schema."""
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError(f"Unexpected MediaCrawler payload in {raw_path}")
    out: list[dict[str, Any]] = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("comment_id") or "")
        aweme_id = str(c.get("aweme_id") or "")
        if not cid or not aweme_id:
            continue
        out.append(
            {
                "source": "抖音评论",
                "post_id": cid,
                "note_id": aweme_id,
                "content": str(c.get("content") or "").strip(),
                "like": int(c.get("like_count") or 0),
                "url": f"https://www.douyin.com/video/{aweme_id}",
                "keyword": keywords or "",
            }
        )
    return out


def fetch_search(
    *,
    keywords: str,
    output_path: str | os.PathLike[str],
    start: int = 1,
    login_type: str = "qrcode",
    mediacrawler_home: str | os.PathLike[str] | None = None,
    python_executable: str | None = None,
) -> Path:
    """Run a Douyin keyword search and persist normalised comments."""
    home = resolve_home(mediacrawler_home)
    run_mediacrawler(
        platform="dy",
        crawler_type="search",
        keywords=keywords,
        start=start,
        login_type=login_type,
        save_data_option="json",
        home=home,
        python_executable=python_executable,
    )
    raw = _find_latest_comments_file(home / "data", "dy", "search_comments")
    records = normalise_douyin(raw, keywords=keywords)
    return write_records(records, output_path)


def fetch_detail(
    *,
    output_path: str | os.PathLike[str],
    login_type: str = "qrcode",
    mediacrawler_home: str | os.PathLike[str] | None = None,
    python_executable: str | None = None,
) -> Path:
    """Detail mode — fetch comments for a fixed set of video IDs.

    Configure ``DY_SPECIFIED_ID_LIST`` in MediaCrawler's
    ``config/base_config.py`` before calling.
    """
    home = resolve_home(mediacrawler_home)
    run_mediacrawler(
        platform="dy",
        crawler_type="detail",
        login_type=login_type,
        save_data_option="json",
        home=home,
        python_executable=python_executable,
    )
    raw = _find_latest_comments_file(home / "data", "dy", "search_comments")
    return write_records(normalise_douyin(raw), output_path)


__all__ = ["fetch_search", "fetch_detail", "normalise_douyin"]

"""Zhihu (知乎) comment fetcher — wraps MediaCrawler.

Two crawl modes:

- :func:`fetch_search` — keyword search → top answers/articles/videos → comments.
- :func:`fetch_detail` — fixed content-id list → comments.

Both shell out to ``main.py --platform zhihu`` and normalise the JSON output.
Cookie/QR-code login is delegated to MediaCrawler.
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


def normalise_zhihu(
    raw_path: Path,
    *,
    keywords: str | None = None,
) -> list[dict[str, Any]]:
    """Convert MediaCrawler's Zhihu comment JSON into the mgap comment schema."""
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError(f"Unexpected MediaCrawler payload in {raw_path}")
    out: list[dict[str, Any]] = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("comment_id") or "")
        content_id = str(c.get("content_id") or "")
        content_type = str(c.get("content_type") or "")
        if not cid or not content_id:
            continue
        # Build best-effort URL based on content type
        if content_type == "article":
            url = f"https://zhuanlan.zhihu.com/p/{content_id}"
        elif content_type == "zvideo":
            url = f"https://www.zhihu.com/zvideo/{content_id}"
        else:
            # answer or unknown → use /answer/ which auto-redirects
            url = f"https://www.zhihu.com/answer/{content_id}"
        out.append(
            {
                "source": "知乎评论",
                "post_id": cid,
                "note_id": content_id,
                "content": str(c.get("content") or "").strip(),
                "like": int(c.get("like_count") or 0),
                "url": url,
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
    """Run a Zhihu keyword search and persist normalised comments."""
    home = resolve_home(mediacrawler_home)
    run_mediacrawler(
        platform="zhihu",
        crawler_type="search",
        keywords=keywords,
        start=start,
        login_type=login_type,
        save_data_option="json",
        home=home,
        python_executable=python_executable,
    )
    raw = _find_latest_comments_file(home / "data", "zhihu", "search_comments")
    records = normalise_zhihu(raw, keywords=keywords)
    return write_records(records, output_path)


def fetch_detail(
    *,
    output_path: str | os.PathLike[str],
    login_type: str = "qrcode",
    mediacrawler_home: str | os.PathLike[str] | None = None,
    python_executable: str | None = None,
) -> Path:
    """Detail mode — fetch comments for a fixed set of content IDs.

    Configure ``ZHIHU_SPECIFIED_ID_LIST`` in MediaCrawler's
    ``config/base_config.py`` before calling.
    """
    home = resolve_home(mediacrawler_home)
    run_mediacrawler(
        platform="zhihu",
        crawler_type="detail",
        login_type=login_type,
        save_data_option="json",
        home=home,
        python_executable=python_executable,
    )
    raw = _find_latest_comments_file(home / "data", "zhihu", "search_comments")
    return write_records(normalise_zhihu(raw), output_path)


__all__ = ["fetch_search", "fetch_detail", "normalise_zhihu"]

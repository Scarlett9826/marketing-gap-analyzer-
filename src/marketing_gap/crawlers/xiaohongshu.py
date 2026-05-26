"""Xiaohongshu (小红书 / RED-Note) comment fetcher — wraps MediaCrawler.

Two crawl modes are exposed:

- :func:`fetch_search` — keyword search → top notes → comments.
- :func:`fetch_detail` — fixed note-id list → comments
  (requires fresh ``xsec_token`` values configured in MediaCrawler).

Both modes shell out to ``main.py --platform xhs`` and normalise the JSON
output. Cookie/QR-code login is delegated to MediaCrawler.
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import write_records
from ._mediacrawler import (
    _find_latest_comments_file,
    normalise_xiaohongshu,
    resolve_home,
    run_mediacrawler,
)


def fetch_search(
    *,
    keywords: str,
    output_path: str | os.PathLike[str],
    start: int = 1,
    login_type: str = "qrcode",
    mediacrawler_home: str | os.PathLike[str] | None = None,
    python_executable: str | None = None,
) -> Path:
    home = resolve_home(mediacrawler_home)
    run_mediacrawler(
        platform="xhs",
        crawler_type="search",
        keywords=keywords,
        start=start,
        login_type=login_type,
        save_data_option="json",
        home=home,
        python_executable=python_executable,
    )
    raw = _find_latest_comments_file(home / "data", "xhs", "search_comments")
    return write_records(normalise_xiaohongshu(raw, keywords=keywords), output_path)


def fetch_detail(
    *,
    output_path: str | os.PathLike[str],
    login_type: str = "qrcode",
    mediacrawler_home: str | os.PathLike[str] | None = None,
    python_executable: str | None = None,
) -> Path:
    """Detail mode for a list of note-ids.

    Reminder: detail mode requires fresh ``xsec_token`` strings — RED-Note
    rotates them aggressively (~2 hours).  Configure
    ``XHS_SPECIFIED_ID_LIST`` and ``XHS_SPECIFIED_NOTE_URL_LIST`` in
    MediaCrawler's ``config/base_config.py`` before calling.
    """
    home = resolve_home(mediacrawler_home)
    run_mediacrawler(
        platform="xhs",
        crawler_type="detail",
        login_type=login_type,
        save_data_option="json",
        home=home,
        python_executable=python_executable,
    )
    raw = _find_latest_comments_file(home / "data", "xhs", "search_comments")
    return write_records(normalise_xiaohongshu(raw), output_path)


__all__ = ["fetch_search", "fetch_detail"]

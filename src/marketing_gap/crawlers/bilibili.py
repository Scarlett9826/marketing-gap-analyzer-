"""Bilibili comment fetcher — wraps MediaCrawler.

Typical workflow::

    fetch_search(
        keywords="Pura X Max",
        output_path="data/raw/bili_comments.json",
        mediacrawler_home="~/code/MediaCrawler",
    )

The function shells out to MediaCrawler's ``main.py --platform bili --type search``,
then normalises ``data/bili/json/search_comments_<date>.json`` into the
marketing-gap-analyzer comment schema.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import write_records
from ._mediacrawler import (
    _find_latest_comments_file,
    normalise_bilibili,
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
    """Run a B-station keyword search and persist normalised comments.

    Returns the path the records were written to.
    """
    home = resolve_home(mediacrawler_home)
    run_mediacrawler(
        platform="bili",
        crawler_type="search",
        keywords=keywords,
        start=start,
        login_type=login_type,
        save_data_option="json",
        home=home,
        python_executable=python_executable,
    )
    raw = _find_latest_comments_file(home / "data", "bili", "search_comments")
    records = normalise_bilibili(raw, keywords=keywords)
    return write_records(records, output_path)


def fetch_detail(
    *,
    video_ids: list[str],
    output_path: str | os.PathLike[str],
    login_type: str = "qrcode",
    mediacrawler_home: str | os.PathLike[str] | None = None,
    python_executable: str | None = None,
) -> Path:
    """Detail mode — fetch a fixed list of bvids/aids.

    Note: MediaCrawler reads detail-mode IDs from ``config/base_config.py``
    (``BILI_SPECIFIED_ID_LIST``).  Edit it before invoking, or pass them
    through ``extra_args``.
    """
    home = resolve_home(mediacrawler_home)
    run_mediacrawler(
        platform="bili",
        crawler_type="detail",
        login_type=login_type,
        save_data_option="json",
        home=home,
        python_executable=python_executable,
    )
    raw = _find_latest_comments_file(home / "data", "bili", "search_comments")
    records: list[dict[str, Any]] = normalise_bilibili(raw)
    if video_ids:
        wanted = {str(v) for v in video_ids}
        records = [r for r in records if r.get("note_id") in wanted]
    return write_records(records, output_path)


__all__ = ["fetch_search", "fetch_detail"]

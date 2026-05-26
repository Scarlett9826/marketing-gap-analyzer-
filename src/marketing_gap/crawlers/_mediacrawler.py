"""Thin subprocess wrapper around the third-party MediaCrawler project.

We deliberately do **not** vendor MediaCrawler's source — it is a sizeable
Playwright-based stack with its own update cadence and licence (NON-COMMERCIAL
LEARNING LICENSE 1.1).  Instead we shell out to its ``main.py``, normalise the
JSON it drops in ``data/<platform>/json/`` into the marketing-gap-analyzer
schema, and let users keep MediaCrawler updated independently.

Set ``MEDIACRAWLER_HOME`` (or pass ``mediacrawler_home=...``) to point at a
checkout of https://github.com/NanmiCoder/MediaCrawler.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .base import CrawlerError, write_records


def resolve_home(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Return the path to a MediaCrawler checkout, validated."""
    raw = explicit or os.environ.get("MEDIACRAWLER_HOME")
    if not raw:
        raise CrawlerError(
            "MediaCrawler is required for this platform. "
            "Clone https://github.com/NanmiCoder/MediaCrawler and either "
            "pass --mediacrawler-home or set MEDIACRAWLER_HOME."
        )
    home = Path(raw).expanduser().resolve()
    if not (home / "main.py").exists():
        raise CrawlerError(
            f"MEDIACRAWLER_HOME={home} does not look like a MediaCrawler checkout "
            "(main.py is missing)."
        )
    return home


def run_mediacrawler(
    *,
    platform: str,
    crawler_type: str,
    keywords: str | None = None,
    start: int | None = None,
    login_type: str = "qrcode",
    save_data_option: str = "json",
    extra_args: Iterable[str] = (),
    home: Path | None = None,
    python_executable: str | None = None,
) -> Path:
    """Invoke ``MediaCrawler/main.py`` and return its checkout's ``data`` dir."""
    home = home or resolve_home()
    py = python_executable or shutil.which("python3") or sys.executable
    cmd: list[str] = [
        py,
        "main.py",
        "--platform",
        platform,
        "--type",
        crawler_type,
        "--lt",
        login_type,
        "--save_data_option",
        save_data_option,
    ]
    if keywords:
        cmd.extend(["--keywords", keywords])
    if start is not None:
        cmd.extend(["--start", str(start)])
    cmd.extend(extra_args)

    print(f"$ {' '.join(cmd)} (cwd={home})")
    result = subprocess.run(cmd, cwd=str(home))
    if result.returncode != 0:
        raise CrawlerError(
            f"MediaCrawler exited with code {result.returncode}. "
            "Check its console output for cookie / captcha issues."
        )
    return home / "data"


# ---------------------------------------------------------------------------
# Output discovery & normalisation
# ---------------------------------------------------------------------------


def _find_latest_comments_file(data_root: Path, platform_dir: str, filename_prefix: str) -> Path:
    """Return the most recently modified ``<prefix>_<date>.json`` file."""
    target = data_root / platform_dir / "json"
    if not target.exists():
        raise CrawlerError(
            f"MediaCrawler output dir not found: {target}. "
            "Did the crawler complete successfully?"
        )
    candidates = sorted(
        target.glob(f"{filename_prefix}_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        # Fall back to today's expected file
        today = date.today().isoformat()
        guess = target / f"{filename_prefix}_{today}.json"
        if guess.exists():
            return guess
        raise CrawlerError(
            f"No '{filename_prefix}_*.json' files found in {target}. "
            "MediaCrawler may have failed silently."
        )
    return candidates[0]


def normalise_bilibili(
    raw_path: Path,
    *,
    keywords: str | None = None,
) -> list[dict[str, Any]]:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise CrawlerError(f"Unexpected MediaCrawler payload in {raw_path}")
    out: list[dict[str, Any]] = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("comment_id") or "")
        if not cid:
            continue
        video_id = str(c.get("video_id") or "")
        out.append(
            {
                "source": "B站评论",
                "post_id": cid,
                "note_id": video_id,
                "content": str(c.get("content") or "").strip(),
                "like": int(c.get("like_count") or 0),
                "url": (
                    f"https://www.bilibili.com/video/{video_id}#reply{cid}"
                    if video_id else ""
                ),
                "keyword": keywords or "",
            }
        )
    return out


def normalise_xiaohongshu(
    raw_path: Path,
    *,
    keywords: str | None = None,
) -> list[dict[str, Any]]:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise CrawlerError(f"Unexpected MediaCrawler payload in {raw_path}")
    out: list[dict[str, Any]] = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("comment_id") or "")
        note_id = str(c.get("note_id") or "")
        if not cid or not note_id:
            continue
        # XHS detail URLs require an xsec_token; we leave it blank and let
        # the user paste one back in when sharing the report externally.
        out.append(
            {
                "source": "小红书评论",
                "post_id": cid,
                "note_id": note_id,
                "content": str(c.get("content") or "").strip(),
                "like": int(c.get("like_count") or 0),
                "url": f"https://www.xiaohongshu.com/explore/{note_id}",
                "keyword": keywords or "",
            }
        )
    return out


__all__ = [
    "resolve_home",
    "run_mediacrawler",
    "normalise_bilibili",
    "normalise_xiaohongshu",
    "_find_latest_comments_file",
    "write_records",
]

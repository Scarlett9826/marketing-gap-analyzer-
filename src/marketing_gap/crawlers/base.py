"""Shared building blocks for the bundled crawlers.

This module deliberately stays dependency-light: only :mod:`requests` is
required at runtime, and only when a crawler that uses HTTP is invoked.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping


class CrawlerError(RuntimeError):
    """Raised for non-recoverable crawler failures (bad cookie, schema, etc.)."""


# ---------------------------------------------------------------------------
# Cookie handling
# ---------------------------------------------------------------------------

@dataclass
class CookieFile:
    """A JSON file containing the HTTP headers needed to authenticate.

    Expected schema (all keys optional except ``Cookie``)::

        {
          "Cookie": "SUB=...; SUBP=...; ...",
          "User-Agent": "Mozilla/5.0 ...",
          "x-xsrf-token": "..."
        }

    Use :meth:`load` to read a file from disk and :meth:`as_headers` to obtain
    a dictionary that can be passed straight to :func:`requests.get`.
    """

    path: Path
    data: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "CookieFile":
        p = Path(path)
        if not p.exists():
            raise CrawlerError(
                f"Cookie file not found: {p}\n"
                "Create one by exporting your browser cookies — see "
                "docs/data-collection.md for the recommended workflow."
            )
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CrawlerError(f"Cookie file {p} is not valid JSON: {exc}") from exc

        if not isinstance(data, Mapping) or "Cookie" not in data:
            raise CrawlerError(
                f"Cookie file {p} must be a JSON object with at least a 'Cookie' key."
            )
        cookie_value = str(data["Cookie"]).strip()
        if not cookie_value or "PASTE" in cookie_value.upper():
            raise CrawlerError(
                f"Cookie file {p} still contains a placeholder. "
                "Paste a real Cookie string before running the crawler."
            )
        return cls(path=p, data={str(k): str(v) for k, v in data.items()})

    def as_headers(self, *, referer: str | None = None) -> dict[str, str]:
        headers = dict(self.data)
        headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36",
        )
        if referer:
            headers["Referer"] = referer
        return headers


def load_cookie_header(path: str | os.PathLike[str], *, referer: str | None = None) -> dict[str, str]:
    """Convenience wrapper returning a ready-to-use header dict."""
    return CookieFile.load(path).as_headers(referer=referer)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_records(records: Iterable[Mapping[str, Any]], path: str | os.PathLike[str]) -> Path:
    """Atomically write ``records`` to ``path`` as a JSON array."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(json.dumps(list(records), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(out_path)
    return out_path


def append_records(
    records: Iterable[Mapping[str, Any]],
    path: str | os.PathLike[str],
) -> Path:
    """Read existing JSON array (if any) and append new records, then rewrite.

    Used by long-running crawlers to flush partial progress to disk.
    """
    out_path = Path(path)
    existing: list[Any] = []
    if out_path.exists():
        try:
            loaded = json.loads(out_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = loaded
        except Exception:
            existing = []
    existing.extend(records)
    return write_records(existing, out_path)


# ---------------------------------------------------------------------------
# Politeness helpers
# ---------------------------------------------------------------------------

def polite_sleep(seconds: float) -> None:
    """Sleep wrapper that always yields a positive duration."""
    if seconds > 0:
        time.sleep(seconds)

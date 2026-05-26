"""Official-track data verifier.

For each entry in ``raw_official.json`` that has a ``url``, this module
attempts to:

1. Reach the URL (HEAD, fallback to GET).
2. Confirm the response body contains the content fingerprint
   (first 50 characters of the ``content`` field).

It then updates the ``verifiable`` field on each entry so downstream
steps (extractors, reports) can annotate confidence.

Usage::

    mgap verify-official                    # verifies config.yaml's raw_official
    mgap -c path/to/config.yaml verify-official
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from ..config import Config
from .base import CrawlerError


def verify_entry(
    entry: dict[str, Any],
    *,
    timeout: float = 15.0,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Verify one official document entry and update its ``verifiable`` field.

    The following status taxonomy is used (in order of confidence):

    - ``✅ verified`` — URL returned 200 AND the page text contains the first
      50 characters of ``content``.
    - ``✅ URL reachable`` — URL returned 200 but content fingerprint could
      not be confirmed (JS-rendered, login wall, or content too short).
    - ``⚠️ URL broken`` — HTTP 4xx/5xx.
    - ``❌ unreachable`` — connection refused, timeout, DNS failure.
    - ``⚠️ no URL`` — ``url`` field is empty or missing.
    """
    url = (entry.get("url") or "").strip()
    content = (entry.get("content") or "").strip()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not url:
        entry["verifiable"] = f"⚠️ no URL @ {ts}"
        return entry

    ua = user_agent or (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # --- Step 1: HEAD (lightweight reachability) ---
    try:
        resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            status = f"⚠️ URL broken (HEAD {resp.status_code}) @ {ts}"
            entry["verifiable"] = status
            return entry
        head_ok = True
    except requests.RequestException:
        head_ok = False

    # --- Step 2: GET (fetch body for content fingerprint) ---
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            status = f"⚠️ URL broken (GET {resp.status_code}) @ {ts}"
            entry["verifiable"] = status
            return entry

        # Content fingerprint check
        if content and len(content) >= 30:
            fingerprint = content[:50]
            if fingerprint in resp.text:
                entry["verifiable"] = f"✅ verified @ {ts}"
            else:
                entry["verifiable"] = f"⚠️ content mismatch @ {ts}"
        else:
            entry["verifiable"] = f"✅ URL reachable @ {ts}"

    except requests.RequestException as exc:
        if head_ok:
            # HEAD passed but GET failed (likely a PDF / download URL)
            entry["verifiable"] = f"✅ URL reachable (HEAD 200, GET failed: {type(exc).__name__}) @ {ts}"
        else:
            entry["verifiable"] = f"❌ unreachable ({type(exc).__name__}) @ {ts}"

    return entry


def verify_official(
    config_path: str | Path,
    *,
    output_path: str | Path | None = None,
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    """Verify every entry in ``raw_official.json`` and persist the updates.

    Returns the updated document list.
    """
    cfg = Config(config_path)
    if cfg.raw_official is None or not cfg.raw_official.exists():
        raise FileNotFoundError(f"raw_official not found: {cfg.raw_official}")

    docs = json.loads(cfg.raw_official.read_text(encoding="utf-8"))
    print(f"Verifying {len(docs)} official documents…")

    updated: list[dict[str, Any]] = []
    for i, entry in enumerate(docs, 1):
        src = entry.get("source", "?")
        print(f"  [{i}/{len(docs)}] {src}… ", end="", flush=True)
        try:
            result = verify_entry(entry, timeout=timeout)
            updated.append(result)
            print(result["verifiable"])
        except Exception as exc:
            print(f"❌ error: {exc}")
            updated.append(entry)
        time.sleep(0.3)  # politeness delay between requests

    out = Path(output_path) if output_path else cfg.raw_official
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")

    verified = sum(1 for d in updated if d.get("verifiable", "").startswith("✅"))
    broken = sum(1 for d in updated if "⚠️" in d.get("verifiable", "") or "❌" in d.get("verifiable", ""))
    print(f"\nDone. {verified} verified, {broken} issues → {out}")
    return updated


def summarize_verification(docs: list[dict[str, Any]]) -> str:
    """Produce a human-readable one-liner for the report header."""
    total = len(docs)
    verified = sum(1 for d in docs if d.get("verifiable", "").startswith("✅"))
    broken = sum(1 for d in docs if "⚠️" in d.get("verifiable", "") or "❌" in d.get("verifiable", ""))
    no_url = sum(1 for d in docs if "no URL" in d.get("verifiable", ""))
    parts = [f"✅ {verified} verified"]
    if broken:
        parts.append(f"⚠️ {broken} issues")
    if no_url:
        parts.append(f"⚠️ {no_url} no URL")
    return f"{' · '.join(parts)} (共 {total} 条)"


__all__ = ["verify_entry", "verify_official", "summarize_verification"]

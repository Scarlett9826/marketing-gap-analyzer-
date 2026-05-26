"""Weibo first-level comment crawler.

Hits the same ``weibo.com/ajax/statuses/buildComments`` endpoint that the
official desktop site uses; output is paginated by ``max_id``. Cookie
authentication is mandatory — a logged-out request returns HTTP 200 with an
empty payload.

Public API:

- :func:`fetch_post`        — scrape one weibo URL into a comment list.
- :func:`fetch_many`        — scrape a list of URLs and produce a merged
  ``raw_user.json`` ready to be consumed by ``mgap extract-user``.
- :class:`WeiboCrawlConfig` — runtime knobs (rate limit, max comments, etc.).

The implementation is a hardened port of the standalone ``batch_crawl.py``
script that powered the project's reference dataset (962 comments / 7 weibo
posts in the Pura X Max case study).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

import requests

from .base import (
    CookieFile,
    CrawlerError,
    append_records,
    polite_sleep,
    write_records,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class WeiboCrawlConfig:
    """Knobs that control crawler politeness and output volume."""

    sleep_per_request: float = 0.6
    sleep_per_100: float = 4.0
    max_comments_per_post: int = 800
    fetch_second_level: bool = False
    flush_every: int = 50
    request_timeout: float = 20.0
    consecutive_empty_threshold: int = 2

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "WeiboCrawlConfig":
        if not data:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


# ---------------------------------------------------------------------------
# URL parsing  (weibo BIDs are base-62 encoded)
# ---------------------------------------------------------------------------

_BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _decode_base62(b62: str) -> int:
    n = 0
    for c in b62:
        n = n * 62 + _BASE62.index(c)
    return n


def bid_to_mid(bid: str) -> int:
    """Convert a weibo short-id (BID) to the numeric mid used by the API."""
    parts: list[str] = []
    for i in range(len(bid), 0, -4):
        start = max(i - 4, 0)
        seg = bid[start:i]
        n = str(_decode_base62(seg))
        if start != 0:
            n = n.zfill(7)
        parts.append(n)
    return int("".join(reversed(parts)))


def parse_weibo_url(url: str) -> tuple[str, int, str]:
    """Extract ``(uid, mid, bid)`` from a canonical weibo post URL."""
    clean = url.split("?")[0].rstrip("/")
    parts = clean.split("/")
    if len(parts) < 2:
        raise CrawlerError(f"Cannot parse weibo URL: {url}")
    uid, bid = parts[-2], parts[-1]
    try:
        mid = bid_to_mid(bid)
    except ValueError as exc:
        raise CrawlerError(f"BID '{bid}' is not valid base-62: {exc}") from exc
    return uid, mid, bid


# ---------------------------------------------------------------------------
# Comment parsing
# ---------------------------------------------------------------------------


def _parse_comment(d: dict[str, Any], parent_id: str = "") -> dict[str, Any] | None:
    try:
        idstr = d["idstr"]
    except KeyError:
        return None

    raw_created = d.get("created_at", "")
    try:
        created_at = datetime.strptime(
            raw_created, "%a %b %d %H:%M:%S %z %Y"
        ).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        created_at = raw_created

    user = d.get("user") or {}
    return {
        "comment_id": idstr,
        "parent_comment_id": parent_id,
        "created_at": created_at,
        "user_id": user.get("id", ""),
        "screen_name": user.get("screen_name", ""),
        "content": d.get("text_raw", "") or "",
        "like": d.get("like_counts", 0) or 0,
        "ip_location": (d.get("source") or "")[2:],
        "total_number": d.get("total_number", 0) or 0,
    }


# ---------------------------------------------------------------------------
# Single-post fetcher
# ---------------------------------------------------------------------------


def _fetch_post_meta(bid: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    try:
        r = requests.get(
            f"https://weibo.com/ajax/statuses/show?id={bid}",
            headers=headers,
            timeout=timeout,
        )
        d = r.json()
    except Exception:
        return {"author": "?", "text": "", "comments_count": 0, "attitudes_count": 0}
    return {
        "author": d.get("user", {}).get("screen_name", "?"),
        "text": (d.get("text_raw", "") or "")[:200],
        "comments_count": d.get("comments_count", 0),
        "attitudes_count": d.get("attitudes_count", 0),
        "created_at": d.get("created_at", ""),
    }


def fetch_post(
    url: str,
    *,
    cookie: CookieFile,
    config: WeiboCrawlConfig | None = None,
    progress: Callable[[str], None] | None = None,
    detail_path: Path | None = None,
) -> dict[str, Any]:
    """Fetch all first-level comments from a single weibo post.

    Returns a dict with metadata + ``comments`` list. If ``detail_path`` is
    provided the same dict is flushed to disk every ``flush_every`` comments
    so the run is restart-tolerant.
    """
    cfg = config or WeiboCrawlConfig()
    headers = cookie.as_headers(referer="https://weibo.com/")
    log = progress or (lambda _msg: None)

    uid, mid, bid = parse_weibo_url(url)
    meta = _fetch_post_meta(bid, headers, cfg.request_timeout)
    log(f"  @{meta['author']} 💬{meta.get('comments_count', '?')} text={meta['text'][:80]}")

    comments: list[dict[str, Any]] = []
    max_id: str | int = ""
    page = 0
    consecutive_empty = 0

    def _checkpoint() -> None:
        if detail_path is None:
            return
        write_records(
            [
                {
                    "url": url,
                    "author": meta["author"],
                    "uid": uid,
                    "mid": mid,
                    "bid": bid,
                    "comments_count_total": meta.get("comments_count", 0),
                    "comments_fetched": len(comments),
                    "comments": comments,
                }
            ],
            detail_path,
        )

    while True:
        if len(comments) >= cfg.max_comments_per_post:
            log(f"  reached cap {cfg.max_comments_per_post}, stopping")
            break
        page += 1
        endpoint = (
            "https://weibo.com/ajax/statuses/buildComments"
            f"?flow=1&is_reload=1&id={mid}&is_show_bulletin=2&is_mix=0"
            + (f"&max_id={max_id}" if max_id else "")
            + f"&count=20&uid={uid}&fetch_level=0&locale=zh-CN"
        )
        try:
            resp = requests.get(endpoint, headers=headers, timeout=cfg.request_timeout).json()
        except Exception as exc:
            log(f"  ! request failed page={page}: {exc}")
            time.sleep(5)
            continue

        datas = resp.get("data") or []
        if not datas:
            consecutive_empty += 1
            if consecutive_empty >= cfg.consecutive_empty_threshold:
                log("  empty payload twice — stopping")
                break
        else:
            consecutive_empty = 0

        for d in datas:
            parsed = _parse_comment(d)
            if parsed:
                comments.append(parsed)

        if cfg.fetch_second_level:
            for d in datas:
                if (d.get("total_number") or 0) <= 0:
                    continue
                sub_max: str | int = ""
                sub_count = 0
                while sub_count < 30:
                    sub_endpoint = (
                        "https://weibo.com/ajax/statuses/buildComments"
                        f"?flow=1&is_reload=1&id={d['idstr']}&is_show_bulletin=2&is_mix=0"
                        + (f"&max_id={sub_max}" if sub_max else "")
                        + f"&count=20&uid={uid}&fetch_level=1&locale=zh-CN"
                    )
                    try:
                        sub_resp = requests.get(
                            sub_endpoint, headers=headers, timeout=cfg.request_timeout
                        ).json()
                    except Exception:
                        break
                    for sd in sub_resp.get("data") or []:
                        parsed = _parse_comment(sd, parent_id=d["idstr"])
                        if parsed:
                            comments.append(parsed)
                            sub_count += 1
                    sub_max = sub_resp.get("max_id", 0)
                    if not sub_max:
                        break
                    polite_sleep(cfg.sleep_per_request)

        # checkpoint
        if cfg.flush_every > 0 and len(comments) % cfg.flush_every < 20 and comments:
            _checkpoint()

        if len(comments) % 100 < 20 and comments:
            log(f"  fetched {len(comments)}/{meta.get('comments_count', '?')}")
            polite_sleep(cfg.sleep_per_100)

        next_max = resp.get("max_id", 0)
        if not next_max:
            log("  pagination ended (max_id=0)")
            break
        max_id = next_max
        polite_sleep(cfg.sleep_per_request)

    _checkpoint()
    return {
        "url": url,
        "author": meta["author"],
        "uid": uid,
        "mid": mid,
        "bid": bid,
        "comments_count_total": meta.get("comments_count", 0),
        "comments_fetched": len(comments),
        "comments": comments,
    }


# ---------------------------------------------------------------------------
# Multi-post orchestrator
# ---------------------------------------------------------------------------


def fetch_many(
    urls: Iterable[str],
    *,
    cookie_path: str | Path,
    output_dir: str | Path,
    merged_output: str | Path | None = None,
    config: WeiboCrawlConfig | None = None,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Fetch comments for a list of weibo URLs and write a merged JSON file.

    The merged file conforms to the schema expected by
    :func:`marketing_gap.extractors.user.extract_user` so it can be plugged
    straight into ``raw_user`` of a config.
    """
    cfg = config or WeiboCrawlConfig()
    log = progress or print
    cookie = CookieFile.load(cookie_path)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    merged_path = Path(merged_output) if merged_output else out_dir / "weibo_all_comments.json"

    all_records: list[dict[str, Any]] = []
    for i, url in enumerate(list(urls), 1):
        log(f"\n[{i}] {url}")
        try:
            uid, mid, bid = parse_weibo_url(url)
        except CrawlerError as exc:
            log(f"  ! skip — {exc}")
            continue
        # author name not known yet; reuse bid for filename safety
        detail_path = out_dir / f"{uid}_{bid}.json"
        try:
            result = fetch_post(
                url,
                cookie=cookie,
                config=cfg,
                progress=log,
                detail_path=detail_path,
            )
        except CrawlerError as exc:
            log(f"  ! crawl failed: {exc}")
            continue
        log(f"  ✓ {result['comments_fetched']} comments → {detail_path.name}")
        for c in result["comments"]:
            all_records.append(
                {
                    "source": "微博评论",
                    "post_id": str(c["comment_id"]),
                    "note_id": str(result["mid"]),
                    "content": c["content"],
                    "like": c.get("like", 0),
                    "url": f"{result['url']}#comment-{c['comment_id']}",
                }
            )

    write_records(all_records, merged_path)
    log(f"\n✓ merged {len(all_records)} records → {merged_path}")
    return merged_path


__all__ = [
    "WeiboCrawlConfig",
    "bid_to_mid",
    "parse_weibo_url",
    "fetch_post",
    "fetch_many",
]

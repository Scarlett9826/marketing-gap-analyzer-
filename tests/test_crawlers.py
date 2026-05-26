"""Unit tests for crawler helpers (no network).

We exercise:
- weibo BID → MID conversion (canonical examples)
- weibo URL parsing edge cases
- cookie loader rejecting placeholders / missing keys
- MediaCrawler output normalisers (bili + xhs schemas)
- write_records / append_records round-trip
"""

from __future__ import annotations

import json

import pytest

from marketing_gap.crawlers import weibo
from marketing_gap.crawlers._mediacrawler import (
    normalise_bilibili,
    normalise_xiaohongshu,
)
from marketing_gap.crawlers.base import (
    CookieFile,
    CrawlerError,
    append_records,
    write_records,
)


# ---------------------------------------------------------------------------
# weibo URL & BID parsing
# ---------------------------------------------------------------------------

def test_bid_to_mid_known_examples():
    # Captured from the live API: bid → mid for the Pura X Max corpus.
    assert weibo.bid_to_mid("QBGttc1BD") == 5289814112866113
    # Round-trip: same BID twice should map to the same number.
    assert weibo.bid_to_mid("QEz7LqPbO") == weibo.bid_to_mid("QEz7LqPbO")
    # MID for any well-formed BID must be a positive integer.
    assert weibo.bid_to_mid("Abc1234") > 0


def test_parse_weibo_url_strips_query():
    uid, mid, bid = weibo.parse_weibo_url("https://weibo.com/7928198622/QBGttc1BD?refer_flag=1001030103_")
    assert uid == "7928198622"
    assert bid == "QBGttc1BD"
    assert mid == 5289814112866113


def test_parse_weibo_url_rejects_garbage():
    with pytest.raises(CrawlerError):
        weibo.parse_weibo_url("not-a-url")


# ---------------------------------------------------------------------------
# Cookie loader
# ---------------------------------------------------------------------------

def test_cookie_file_missing(tmp_path):
    with pytest.raises(CrawlerError, match="not found"):
        CookieFile.load(tmp_path / "missing.json")


def test_cookie_file_placeholder_rejected(tmp_path):
    p = tmp_path / "ck.json"
    p.write_text(json.dumps({"Cookie": "PASTE_REAL_COOKIE_HERE"}), encoding="utf-8")
    with pytest.raises(CrawlerError, match="placeholder"):
        CookieFile.load(p)


def test_cookie_file_requires_cookie_key(tmp_path):
    p = tmp_path / "ck.json"
    p.write_text(json.dumps({"User-Agent": "Mozilla"}), encoding="utf-8")
    with pytest.raises(CrawlerError, match="Cookie"):
        CookieFile.load(p)


def test_cookie_file_as_headers_injects_ua(tmp_path):
    p = tmp_path / "ck.json"
    p.write_text(json.dumps({"Cookie": "SUB=foo"}), encoding="utf-8")
    headers = CookieFile.load(p).as_headers(referer="https://weibo.com/")
    assert headers["Cookie"] == "SUB=foo"
    assert "Mozilla" in headers["User-Agent"]
    assert headers["Referer"] == "https://weibo.com/"


# ---------------------------------------------------------------------------
# MediaCrawler normalisers
# ---------------------------------------------------------------------------

def test_normalise_bilibili(tmp_path):
    sample = [
        {
            "comment_id": "299817811233",
            "video_id": "116594336600271",
            "content": "小艺有时候跟个ZZ一样",
            "like_count": 98,
        },
        # Garbage entries should be skipped.
        {"video_id": "no-id-here"},
        "not a dict",
    ]
    p = tmp_path / "raw.json"
    p.write_text(json.dumps(sample), encoding="utf-8")
    out = normalise_bilibili(p, keywords="Pura X")
    assert len(out) == 1
    assert out[0]["source"] == "B站评论"
    assert out[0]["post_id"] == "299817811233"
    assert out[0]["note_id"] == "116594336600271"
    assert out[0]["like"] == 98
    assert "bilibili.com/video/" in out[0]["url"]
    assert out[0]["keyword"] == "Pura X"


def test_normalise_xiaohongshu(tmp_path):
    sample = [
        {
            "comment_id": "6a0f05dd000000002b027b0b",
            "note_id": "6a0e89a3000000003700f804",
            "content": "可能膜是有点问题",
            "like_count": "0",
        }
    ]
    p = tmp_path / "raw.json"
    p.write_text(json.dumps(sample), encoding="utf-8")
    out = normalise_xiaohongshu(p)
    assert len(out) == 1
    assert out[0]["source"] == "小红书评论"
    assert out[0]["like"] == 0
    assert out[0]["url"].endswith("/6a0e89a3000000003700f804")


# ---------------------------------------------------------------------------
# write/append helpers
# ---------------------------------------------------------------------------

def test_write_and_append_records(tmp_path):
    p = tmp_path / "out.json"
    write_records([{"id": 1}], p)
    assert json.loads(p.read_text(encoding="utf-8")) == [{"id": 1}]
    append_records([{"id": 2}], p)
    assert json.loads(p.read_text(encoding="utf-8")) == [{"id": 1}, {"id": 2}]

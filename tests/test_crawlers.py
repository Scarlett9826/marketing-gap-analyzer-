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
from marketing_gap.crawlers.zhihu import normalise_zhihu
from marketing_gap.crawlers.douyin import normalise_douyin
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

def test_normalise_zhihu(tmp_path):
    sample = [
        {
            "comment_id": "zh123456",
            "content_id": "ans789",
            "content_type": "answer",
            "content": "这个产品确实不错",
            "like_count": 42,
        },
        {
            "comment_id": "zh789012",
            "content_id": "art345",
            "content_type": "article",
            "content": "分析得很透彻",
            "like_count": 7,
        },
    ]
    p = tmp_path / "raw.json"
    p.write_text(json.dumps(sample), encoding="utf-8")
    out = normalise_zhihu(p, keywords="Pura X")
    assert len(out) == 2
    assert out[0]["source"] == "知乎评论"
    assert out[0]["post_id"] == "zh123456"
    assert out[0]["note_id"] == "ans789"
    assert out[0]["like"] == 42
    assert "zhihu.com/answer/ans789" in out[0]["url"]
    assert out[1]["source"] == "知乎评论"
    assert "zhuanlan.zhihu.com/p/art345" in out[1]["url"]
    assert out[0]["keyword"] == "Pura X"


def test_normalise_douyin(tmp_path):
    sample = [
        {
            "comment_id": "dy123",
            "aweme_id": "video456",
            "content": "这个视频拍的太好了",
            "like_count": 999,
        },
    ]
    p = tmp_path / "raw.json"
    p.write_text(json.dumps(sample), encoding="utf-8")
    out = normalise_douyin(p, keywords="Pura X")
    assert len(out) == 1
    assert out[0]["source"] == "抖音评论"
    assert out[0]["post_id"] == "dy123"
    assert out[0]["note_id"] == "video456"
    assert out[0]["like"] == 999
    assert "douyin.com/video/video456" in out[0]["url"]


# ---------------------------------------------------------------------------
# verify_official tests
# ---------------------------------------------------------------------------

class _MockResponse:
    """Minimal requests.Response stand-in for mocking."""
    def __init__(self, status_code=200, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


def test_verify_entry_no_url():
    from marketing_gap.crawlers.verify_official import verify_entry
    entry = {"source": "test", "content": "some body"}
    result = verify_entry(entry)
    assert "no URL" in result["verifiable"]


def test_verify_entry_empty_url():
    from marketing_gap.crawlers.verify_official import verify_entry
    entry = {"url": "", "content": "some body"}
    result = verify_entry(entry)
    assert "no URL" in result["verifiable"]


def test_verify_entry_content_match(monkeypatch):
    import requests
    from marketing_gap.crawlers.verify_official import verify_entry

    body = "Prefix: Pura X is the best phone ever made! Extra text beyond — this is on the page."
    fingerprint_50 = body[:50]  # "Prefix: Pura X is the best phone ever made! Extra text"

    def mock_head(*args, **kwargs):
        return _MockResponse(status_code=200)
    def mock_get(*args, **kwargs):
        return _MockResponse(status_code=200, text=body)

    monkeypatch.setattr(requests, "head", mock_head)
    monkeypatch.setattr(requests, "get", mock_get)

    entry = {
        "source": "产品页",
        "url": "https://example.com/pura-x",
        "content": body + " More text beyond the body in the entry field.",
    }
    result = verify_entry(entry)
    assert result["verifiable"].startswith("✅ verified")


def test_verify_entry_content_mismatch(monkeypatch):
    import requests
    from marketing_gap.crawlers.verify_official import verify_entry

    def mock_head(*args, **kwargs):
        return _MockResponse(status_code=200)
    def mock_get(*args, **kwargs):
        return _MockResponse(status_code=200, text="Some completely different content")

    monkeypatch.setattr(requests, "head", mock_head)
    monkeypatch.setattr(requests, "get", mock_get)

    entry = {
        "source": "产品页",
        "url": "https://example.com/pura-x",
        "content": "This is the Pura X content fingerprint here with more text",
    }
    result = verify_entry(entry)
    assert "⚠️" in result["verifiable"] or "content mismatch" in result["verifiable"]


def test_verify_entry_url_broken(monkeypatch):
    import requests
    from marketing_gap.crawlers.verify_official import verify_entry

    def mock_head(*args, **kwargs):
        return _MockResponse(status_code=404)

    monkeypatch.setattr(requests, "head", mock_head)

    entry = {
        "source": "产品页",
        "url": "https://example.com/not-found",
        "content": "some content",
    }
    result = verify_entry(entry)
    assert "URL broken" in result["verifiable"]


def test_verify_entry_unreachable(monkeypatch):
    import requests
    from marketing_gap.crawlers.verify_official import verify_entry

    def mock_both(*args, **kwargs):
        raise requests.ConnectionError("DNS failure")

    monkeypatch.setattr(requests, "head", mock_both)
    monkeypatch.setattr(requests, "get", mock_both)

    entry = {
        "source": "产品页",
        "url": "https://example.com/broken",
        "content": "some content",
    }
    result = verify_entry(entry)
    assert "unreachable" in result["verifiable"]


def test_verify_entry_short_content(monkeypatch):
    import requests
    from marketing_gap.crawlers.verify_official import verify_entry

    def mock_head(*args, **kwargs):
        return _MockResponse(status_code=200)
    def mock_get(*args, **kwargs):
        return _MockResponse(status_code=200, text="Hello World")

    monkeypatch.setattr(requests, "head", mock_head)
    monkeypatch.setattr(requests, "get", mock_get)

    entry = {
        "source": "产品页",
        "url": "https://example.com/",
        "content": "Hi",
    }
    result = verify_entry(entry)
    # content < 30 chars → only URL reachable check
    assert "✅ URL reachable" in result["verifiable"]


def test_summarize_verification():
    from marketing_gap.crawlers.verify_official import summarize_verification
    docs = [
        {"verifiable": "✅ verified @ 2026-05-26"},
        {"verifiable": "✅ URL reachable @ 2026-05-26"},
        {"verifiable": "⚠️ URL broken @ 2026-05-26"},
        {"verifiable": "❌ unreachable @ 2026-05-26"},
        {"verifiable": "⚠️ no URL @ 2026-05-26"},
    ]
    s = summarize_verification(docs)
    assert "2 verified" in s
    assert "3 issues" in s
    assert "1 no URL" in s
    assert "5 条" in s


def test_write_and_append_records(tmp_path):
    p = tmp_path / "out.json"
    write_records([{"id": 1}], p)
    assert json.loads(p.read_text(encoding="utf-8")) == [{"id": 1}]
    append_records([{"id": 2}], p)
    assert json.loads(p.read_text(encoding="utf-8")) == [{"id": 1}, {"id": 2}]

"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Network isolation: every test gets fake HTTP by default
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal ``requests.Response`` stand-in for offline tests."""

    def __init__(self, status_code: int = 404, text: str = "", url: str = ""):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code} for {self.url}")

    def json(self) -> dict:
        return {"data": []}


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    """Auto-applied: replace ``requests.head`` / ``requests.get`` with fakes.

    Tests that need specific HTTP behaviour can override the fakes by
    calling ``monkeypatch.setattr(requests, "head", ...)`` themselves.
    """
    import requests

    def fake_head(url, *args, **kwargs):
        return _FakeResponse(status_code=404, url=url)

    def fake_get(url, *args, **kwargs):
        # Local-loopback test endpoints stay local; everything else is 404.
        if "localhost" in url or "127.0.0.1" in url:
            raise requests.ConnectionError(f"refused (test): {url}")
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr(requests, "head", fake_head)
    monkeypatch.setattr(requests, "get", fake_get)
    yield


SAMPLE_OFFICIAL = [
    {
        "source": "Product Page",
        "type": "产品页文案",
        "content": "搭载全新鸿蒙HarmonyOS 6系统和麒麟9030Pro芯片，潜望长焦支持100倍变焦",
        "url": "https://example.com/p",
        "verifiable": "test",
    },
    {
        "source": "Launch Slogan",
        "type": "Slogan",
        "content": "岂止于阔 — 阔折叠重新定义大屏",
        "url": "",
        "verifiable": "test",
    },
    {
        "source": "KOL Review",
        "type": "KOL评测",
        "content": "鸿蒙生态进步明显，但价格 13999 元偏贵",
        "url": "",
        "verifiable": "test",
    },
]

SAMPLE_USER = [
    {"source": "微博评论", "post_id": "1", "note_id": "n1", "content": "鸿蒙好用，应用适配也变好了"},
    {"source": "微博评论", "post_id": "2", "note_id": "n1", "content": "价格太贵了，13999 买不起"},
    {"source": "微博评论", "post_id": "3", "note_id": "n1", "content": "价格劝退，性价比一塌糊涂"},
    {"source": "微博评论", "post_id": "4", "note_id": "n1", "content": "麒麟9030 性能不错"},
    {"source": "B站评论", "post_id": "5", "note_id": "v1", "content": "重量太重，单手握持不舒服"},
    {"source": "B站评论", "post_id": "6", "note_id": "v1", "content": "电池续航一天没问题"},
    {"source": "B站评论", "post_id": "7", "note_id": "v1", "content": "潜望长焦拍演唱会真的牛"},
    {"source": "B站评论", "post_id": "8", "note_id": "v1", "content": "价格不行，太贵"},
]

SAMPLE_DICT_OFFICIAL = {
    "鸿蒙HarmonyOS6": ["鸿蒙", "HarmonyOS"],
    "麒麟9030Pro": ["麒麟9030", "麒麟"],
    "潜望长焦": ["潜望", "长焦", "100倍"],
    "大阔折叠形态": ["阔折叠", "岂止于阔"],
    "13999元价格": ["13999", "万元"],
}

SAMPLE_DICT_USER = {
    "鸿蒙HarmonyOS6": ["鸿蒙", "harmonyos"],
    "麒麟9030Pro": ["麒麟", "9030"],
    "潜望长焦": ["长焦", "潜望", "100倍"],
    "电池续航": ["电池", "续航", "电量"],
    "重量": ["重量", "重", "单手"],
    "价格": ["价格", "贵", "便宜", "13999"],
    "应用适配": ["适配", "应用"],
}


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a fully-functional project directory in tmp."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "raw_official.json").write_text(
        json.dumps(SAMPLE_OFFICIAL, ensure_ascii=False), encoding="utf-8"
    )
    (data_dir / "raw_user.json").write_text(
        json.dumps(SAMPLE_USER, ensure_ascii=False), encoding="utf-8"
    )

    config = {
        "project": {
            "name": "Test Product",
            "brand": "TestBrand",
            "description": "test",
            "data_date": "2026-05-26",
        },
        "paths": {
            "raw_user": "data/raw_user.json",
            "raw_official": "data/raw_official.json",
            "outputs": "output",
        },
        "thresholds": {
            "OFFICIAL_HIGH_THRESHOLD": 3,
            "USER_HIGH_MENTION_THRESHOLD": 2,
            "SENTIMENT_POSITIVE_THRESHOLD": 0.1,
            "SENTIMENT_NEGATIVE_THRESHOLD": -0.2,
        },
        "dictionaries": {
            "official_selling_points": SAMPLE_DICT_OFFICIAL,
            "user_selling_points": SAMPLE_DICT_USER,
        },
    }
    import yaml
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return config_path

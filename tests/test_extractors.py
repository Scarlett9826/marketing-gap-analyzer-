"""Tests for extractors (rule-based path; LLM disabled by no API key)."""

from __future__ import annotations

import json
from pathlib import Path

from marketing_gap.config import Config
from marketing_gap.extractors.official import extract_official, rule_based_extract as rb_official
from marketing_gap.extractors.user import extract_user, rule_based_extract as rb_user


def test_rule_based_official_extract() -> None:
    text = "搭载鸿蒙HarmonyOS 6 + 麒麟9030Pro，支持潜望长焦"
    points = rb_official(text, {
        "鸿蒙HarmonyOS6": ["鸿蒙", "HarmonyOS"],
        "麒麟9030Pro": ["麒麟"],
        "潜望长焦": ["潜望"],
        "未提及": ["abc"],
    })
    assert "鸿蒙HarmonyOS6" in points
    assert "麒麟9030Pro" in points
    assert "潜望长焦" in points
    assert "未提及" not in points


def test_rule_based_user_extract_with_sentiment() -> None:
    pos = {"好用", "好"}
    neg = {"贵", "差"}

    # Negative content
    items = rb_user("价格太贵了，性价比差", {
        "价格": ["价格", "贵"],
        "电池": ["电池"],
    }, pos, neg)
    assert any(i["point"] == "价格" and i["sentiment"] == "negative" for i in items)

    # Positive content
    items = rb_user("电池好用，续航也好", {"电池": ["电池"]}, pos, neg)
    assert any(i["point"] == "电池" and i["sentiment"] == "positive" for i in items)


def test_extract_official_runs_end_to_end(sample_project: Path) -> None:
    result = extract_official(sample_project)
    assert "summary" in result
    assert result["summary"]["total_official_docs"] == 3
    points = {item["selling_point"] for item in result["selling_points_ranked"]}
    # Should hit several from the dictionary
    assert len(points) >= 3
    # Slogan weight=5 should boost 大阔折叠形态
    if "大阔折叠形态" in points:
        item = next(x for x in result["selling_points_ranked"] if x["selling_point"] == "大阔折叠形态")
        assert item["weighted_score"] >= 5

    # Output file written
    out = sample_project.parent / "output" / "official_selling_points.json"
    assert out.exists()
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk["summary"]["total_official_docs"] == 3


def test_extract_user_runs_end_to_end(sample_project: Path) -> None:
    result = extract_user(sample_project)
    assert result["summary"]["total_user_comments"] == 8
    points = {item["selling_point"] for item in result["user_voice_ranked"]}
    assert "价格" in points
    # 价格 should be negative (3 negative comments mention 贵)
    price = next(x for x in result["user_voice_ranked"] if x["selling_point"] == "价格")
    assert price["negative"] >= 2
    assert price["sentiment_score"] < 0

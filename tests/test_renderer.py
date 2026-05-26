"""Tests for renderers.feishu_md."""

from __future__ import annotations

from pathlib import Path

from marketing_gap.analysis.gap_matrix import run_gap_analysis
from marketing_gap.extractors.official import extract_official
from marketing_gap.extractors.user import extract_user
from marketing_gap.renderers.feishu_md import (
    auto_summary,
    feishu_postprocess,
    pick_evidence,
    render,
)


def test_full_pipeline_render(sample_project: Path) -> None:
    extract_official(sample_project)
    extract_user(sample_project)
    run_gap_analysis(sample_project)
    md = render(sample_project)

    assert "# 「Test Product」竞品营销 GAP 分析报告" in md
    assert "TL;DR" in md
    assert "GAP 矩阵" in md
    assert "价格" in md
    # Brand name should be inserted
    assert "TestBrand" in md
    # Output file written
    out = sample_project.parent / "output" / "report.md"
    assert out.exists()
    assert out.read_text(encoding="utf-8") == md


def test_auto_summary_uses_brand() -> None:
    item = {
        "selling_point": "价格",
        "official_weighted_score": 2,
        "official_raw_count": 1,
        "user_total_mentions": 5,
        "user_positive": 0,
        "user_negative": 3,
        "sentiment_score": -0.5,
        "category": "④ 用户自发心智",
    }
    s = auto_summary(item, brand="Apple")
    assert "Apple" in s
    assert "价格" in s
    assert "5 条" in s


def test_pick_evidence_uses_aliases() -> None:
    raw_user = [
        {"source": "微博评论", "post_id": "1", "note_id": "n", "content": "电池续航不够"},
        {"source": "微博评论", "post_id": "2", "note_id": "n", "content": "屏幕很好"},
        {"source": "微博评论", "post_id": "3", "note_id": "n", "content": "电量掉得快"},
    ]
    user_dict = {"电池续航": ["电池", "续航", "电量"]}
    item = {"selling_point": "电池续航",
            "user_negative_examples": [], "user_positive_examples": []}
    evidences = pick_evidence(item, raw_user, user_dict, max_count=4)
    contents = [e["content"] for e in evidences]
    assert "电池续航不够" in contents
    assert "电量掉得快" in contents
    assert "屏幕很好" not in contents


def test_pick_evidence_empty_when_nothing_matches() -> None:
    raw_user = [{"source": "微博评论", "post_id": "1", "note_id": "n", "content": "屏幕很好"}]
    user_dict = {"电池续航": ["电池"]}
    item = {"selling_point": "电池续航",
            "user_negative_examples": [], "user_positive_examples": []}
    evidences = pick_evidence(item, raw_user, user_dict)
    assert evidences == []


def test_feishu_postprocess_chinese_colon() -> None:
    raw = "测试: 内容\n链接: https://example.com"
    out = feishu_postprocess(raw)
    assert "测试：" in out
    # URL colon must be preserved
    assert "https://example.com" in out

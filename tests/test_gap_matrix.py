"""Tests for analysis.gap_matrix."""

from __future__ import annotations

import json
from pathlib import Path

from marketing_gap.analysis.gap_matrix import (
    CATEGORY_BACKFIRE,
    CATEGORY_INVISIBLE,
    CATEGORY_RESONANCE,
    CATEGORY_USER_DRIVEN,
    CATEGORY_WEAK,
    classify,
    run_gap_analysis,
)
from marketing_gap.extractors.official import extract_official
from marketing_gap.extractors.user import extract_user


def test_classify_backfire() -> None:
    assert classify(True, True, -0.5, 0.1, -0.2) == CATEGORY_BACKFIRE


def test_classify_resonance() -> None:
    assert classify(True, True, 0.5, 0.1, -0.2) == CATEGORY_RESONANCE


def test_classify_invisible() -> None:
    assert classify(True, False, 0.0, 0.1, -0.2) == CATEGORY_INVISIBLE


def test_classify_user_driven() -> None:
    assert classify(False, True, 0.0, 0.1, -0.2) == CATEGORY_USER_DRIVEN


def test_classify_weak() -> None:
    assert classify(False, False, 0.0, 0.1, -0.2) == CATEGORY_WEAK


def test_pipeline_produces_gap_matrix(sample_project: Path) -> None:
    extract_official(sample_project)
    extract_user(sample_project)
    matrix = run_gap_analysis(sample_project)

    assert isinstance(matrix, list)
    assert len(matrix) > 0

    # Check 价格 is classified as user-driven (officials say 13999, users say "贵" 3x)
    price = next((m for m in matrix if m["selling_point"] == "价格"), None)
    assert price is not None
    assert price["sentiment_score"] < 0
    # With low official weight + negative user, should be user-driven OR backfire
    assert price["category"] in (CATEGORY_USER_DRIVEN, CATEGORY_BACKFIRE)

    # Output file written
    out = sample_project.parent / "output" / "gap_matrix.json"
    assert out.exists()
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert len(on_disk) == len(matrix)

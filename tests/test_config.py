"""Tests for marketing_gap.config."""

from __future__ import annotations

from pathlib import Path

from marketing_gap.config import Config, DEFAULT_NEGATIVE_WORDS, DEFAULT_POSITIVE_WORDS


def test_load_basic(sample_project: Path) -> None:
    cfg = Config(sample_project)
    assert cfg.project_name == "Test Product"
    assert cfg.brand_name == "TestBrand"
    assert cfg.data_date == "2026-05-26"
    assert cfg.threshold_official_high == 3
    assert cfg.threshold_user_high_mention == 2


def test_dictionaries(sample_project: Path) -> None:
    cfg = Config(sample_project)
    assert "鸿蒙HarmonyOS6" in cfg.official_dict
    assert "鸿蒙" in cfg.official_dict["鸿蒙HarmonyOS6"]
    assert "电池续航" in cfg.user_dict


def test_default_sentiment_words_when_unset(sample_project: Path) -> None:
    cfg = Config(sample_project)
    # Should use built-in defaults since YAML doesn't override
    assert "好" in cfg.positive_words or len(cfg.positive_words) > 0
    assert "差" in cfg.negative_words or len(cfg.negative_words) > 0
    assert cfg.positive_words == DEFAULT_POSITIVE_WORDS
    assert cfg.negative_words == DEFAULT_NEGATIVE_WORDS


def test_paths_resolved_absolute(sample_project: Path) -> None:
    cfg = Config(sample_project)
    assert cfg.raw_official is not None
    assert cfg.raw_official.is_absolute()
    assert cfg.raw_official.exists()


def test_source_weights_merged(sample_project: Path) -> None:
    cfg = Config(sample_project)
    weights = cfg.source_weights
    assert weights["Slogan"] == 5
    assert weights["产品页文案"] == 4
    assert weights["default"] == 1


def test_missing_config_uses_empty(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nope.yaml"
    cfg = Config(nonexistent)
    assert cfg.project_name == "Unnamed Product"
    assert cfg.threshold_official_high == 5  # default


def test_env_priority_over_environ(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "from-env")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("project:\n  name: x\n", encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=from-dotenv\n", encoding="utf-8")
    cfg = Config(cfg_file)
    assert cfg.deepseek_api_key == "from-dotenv"

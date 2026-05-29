"""Tests for marketing_gap.config."""

from __future__ import annotations

from pathlib import Path

import pytest

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


# --- Strict mode tests ---


def test_missing_config_uses_empty(tmp_path: Path) -> None:
    """Lenient mode (default): missing file gives defaults, no error."""
    nonexistent = tmp_path / "nope.yaml"
    cfg = Config(nonexistent)
    assert cfg.project_name == "Unnamed Product"
    assert cfg.threshold_official_high == 5


def test_missing_config_strict_raises(tmp_path: Path) -> None:
    """Strict mode: missing config file raises FileNotFoundError."""
    nonexistent = tmp_path / "nope.yaml"
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        Config(nonexistent, strict=True)


def test_strict_mode_requires_paths_section(tmp_path: Path) -> None:
    """Strict mode: missing 'paths' section raises ValueError."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("project:\n  name: x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required config section: 'paths'"):
        Config(cfg_file, strict=True)


def test_lenient_mode_allows_minimal_config(tmp_path: Path) -> None:
    """Lenient mode (default): minimal config is accepted."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("project:\n  name: x\n", encoding="utf-8")
    cfg = Config(cfg_file)
    assert cfg.project_name == "x"


def test_env_priority_over_environ(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "from-env")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "project:\n  name: x\npaths:\n  raw_user: u.json\n  raw_official: o.json\n",
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=from-dotenv\n", encoding="utf-8")
    cfg = Config(cfg_file)
    assert cfg.deepseek_api_key == "from-dotenv"


def test_mgap_strict_env_enables_strict(tmp_path: Path, monkeypatch) -> None:
    """Setting MGAP_STRICT=1 activates strict validation."""
    monkeypatch.setenv("MGAP_STRICT", "1")
    nonexistent = tmp_path / "nope.yaml"
    with pytest.raises(FileNotFoundError):
        Config(nonexistent)


def test_mgap_strict_env_case_insensitive(tmp_path: Path, monkeypatch) -> None:
    """MGAP_STRICT accepts 'True', 'true', '1', 'yes'."""
    for val in ("1", "true", "True", "yes", "YES"):
        monkeypatch.setenv("MGAP_STRICT", val)
        with pytest.raises(FileNotFoundError):
            Config(tmp_path / "nope.yaml")


def test_strict_false_overrides_env(tmp_path: Path, monkeypatch) -> None:
    """Explicit strict=False overrides MGAP_STRICT env."""
    monkeypatch.setenv("MGAP_STRICT", "1")
    nonexistent = tmp_path / "nope.yaml"
    cfg = Config(nonexistent, strict=False)
    assert cfg.project_name == "Unnamed Product"


# --- Data integrity validation tests ---


def test_validate_official_data_valid() -> None:
    data = [
        {"source": "S1", "type": "Slogan", "content": "Hello"},
        {"source": "S2", "type": "KOL评测", "content": "World"},
    ]
    assert Config.validate_official_data(data) == []


def test_validate_official_data_missing_field() -> None:
    data = [{"source": "S1", "type": "Slogan"}]  # missing content
    errors = Config.validate_official_data(data)
    assert any("content" in e for e in errors)


def test_validate_official_data_bad_type() -> None:
    data = [{"source": "S1", "type": "未知类型", "content": "X"}]
    errors = Config.validate_official_data(data)
    assert any("未知类型" in e for e in errors)


def test_validate_official_data_not_a_list() -> None:
    errors = Config.validate_official_data({"not": "a list"})
    assert any("array" in e.lower() for e in errors)


def test_validate_user_data_valid() -> None:
    data = [
        {"source": "微博", "content": "不错"},
        {"source": "B站", "content": "太贵了"},
    ]
    assert Config.validate_user_data(data) == []


def test_validate_user_data_missing_content() -> None:
    data = [{"source": "微博"}]  # missing content
    errors = Config.validate_user_data(data)
    assert any("content" in e for e in errors)


def test_validate_user_data_empty_content() -> None:
    data = [{"source": "微博", "content": "  "}]
    errors = Config.validate_user_data(data)
    assert any("short" in e.lower() or "empty" in e.lower() for e in errors)


def test_load_and_validate_json_official(tmp_path: Path) -> None:
    import json
    data = [{"source": "S1", "type": "Slogan", "content": "Hi"}]
    p = tmp_path / "official.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    records, errors = Config.load_and_validate_json(p, validator="official")
    assert len(records) == 1
    assert errors == []


def test_load_and_validate_json_user(tmp_path: Path) -> None:
    import json
    data = [{"source": "微博", "content": "好用"}]
    p = tmp_path / "user.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    records, errors = Config.load_and_validate_json(p, validator="user")
    assert len(records) == 1
    assert errors == []


# --- Model capability detection tests ---


def test_llm_available_false_when_no_key(sample_project: Path) -> None:
    cfg = Config(sample_project)
    assert cfg.llm_available is False


def test_llm_available_true_when_key_set(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("project:\n  name: x\npaths:\n  raw_user: u.json\n  raw_official: o.json\n", encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=sk-test\n", encoding="utf-8")
    cfg = Config(cfg_file)
    assert cfg.llm_available is True


def test_check_model_no_key_returns_unavailable(sample_project: Path) -> None:
    cfg = Config(sample_project)
    info = cfg.check_model_capability()
    assert info["available"] is False
    assert "No API key" in info["error"]


def test_check_model_bad_endpoint_returns_error(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("project:\n  name: x\npaths:\n  raw_user: u.json\n  raw_official: o.json\n", encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=sk-test\nLLM_BASE_URL=http://localhost:99999\n", encoding="utf-8")
    cfg = Config(cfg_file)
    info = cfg.check_model_capability()
    assert info["available"] is False
    assert info["error"] is not None

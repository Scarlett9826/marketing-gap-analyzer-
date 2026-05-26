"""Configuration loader.

Loads from (later overrides earlier):
  1. Built-in generic defaults (sentiment words, source weights)
  2. .env file (secrets)
  3. YAML config file (project-specific settings + dictionaries)

Selling-point dictionaries are intentionally NOT hardcoded — they are
product-category specific and must be supplied via YAML config.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


# ── Generic sentiment words (Chinese, applicable to any product) ──
DEFAULT_POSITIVE_WORDS: set[str] = {
    "好", "好用", "棒", "强", "顶", "稳", "香", "丝滑", "完美",
    "支持", "靠谱", "进步", "可圈可点", "实力", "护城河", "够用", "不错",
    "喜欢", "牛", "牛逼", "干净", "纯净",
}

DEFAULT_NEGATIVE_WORDS: set[str] = {
    "差", "烂", "拉胯", "翻车", "不行", "失望", "劝退", "慢", "重", "贵",
    "用不上", "用不到", "没意义", "噱头", "大于实用", "一塌糊涂", "中庸",
    "卡顿", "发烫", "发热", "缩水", "差距", "限",
}

# ── Generic source weights (override per project in YAML) ──
DEFAULT_SOURCE_WEIGHTS: dict[str, int] = {
    "Slogan": 5,
    "产品页文案": 4,
    "发布会现场": 3,
    "深度长文": 3,
    "卖点拆解": 2,
    "预热海报": 2,
    "官方笔记": 2,
    "KOL评测": 2,
    "媒体转引的疑似Slogan": 2,
    "default": 1,
}


def load_yaml(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_dotenv(path: str | Path | None = None) -> dict[str, str]:
    env: dict[str, str] = {}
    if path is None:
        path = Path.cwd() / ".env"
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


class Config:
    """Unified configuration for a GAP analysis run."""

    def __init__(
        self,
        config_path: str | Path,
        env_path: str | Path | None = None,
    ) -> None:
        self._raw: dict[str, Any] = {}
        p = Path(config_path)
        if p.exists():
            self._raw = load_yaml(config_path)
        # Look for .env next to config first, then cwd
        self._env_path = Path(env_path) if env_path else self._find_env(p)
        self._env = load_dotenv(self._env_path)

        config_dir = p.resolve().parent
        self.config_path = p.resolve()
        self.project_dir = config_dir

        paths = self._raw.get("paths", {})
        self.raw_official = self._resolve(config_dir, paths.get("raw_official", ""))
        self.raw_user = self._resolve(config_dir, paths.get("raw_user", ""))
        self.outputs = self._resolve(config_dir, paths.get("outputs", ""))

    @staticmethod
    def _find_env(config_path: Path) -> Path | None:
        for candidate in (
            config_path.resolve().parent / ".env",
            Path.cwd() / ".env",
        ):
            if candidate.exists():
                return candidate
        return None

    def _resolve(self, base: Path, path: str) -> Path | None:
        if not path:
            return None
        p = Path(path)
        return p if p.is_absolute() else (base / p).resolve()

    # ── Project info ──
    @property
    def project_name(self) -> str:
        return self._raw.get("project", {}).get("name", "Unnamed Product")

    @property
    def brand_name(self) -> str:
        """Brand name used in report copy (e.g. '华为', 'Apple')."""
        return self._raw.get("project", {}).get("brand", "竞品官方")

    @property
    def product_description(self) -> str:
        return self._raw.get("project", {}).get("description", "")

    @property
    def data_date(self) -> str:
        return self._raw.get("project", {}).get("data_date", "")

    # ── Thresholds ──
    @property
    def threshold_official_high(self) -> int:
        return int(self._raw.get("thresholds", {}).get("OFFICIAL_HIGH_THRESHOLD", 5))

    @property
    def threshold_user_high_mention(self) -> int:
        return int(self._raw.get("thresholds", {}).get("USER_HIGH_MENTION_THRESHOLD", 4))

    @property
    def threshold_sentiment_negative(self) -> float:
        return float(self._raw.get("thresholds", {}).get("SENTIMENT_NEGATIVE_THRESHOLD", -0.2))

    @property
    def threshold_sentiment_positive(self) -> float:
        return float(self._raw.get("thresholds", {}).get("SENTIMENT_POSITIVE_THRESHOLD", 0.1))

    # ── Source weights ──
    @property
    def source_weights(self) -> dict[str, int]:
        merged = dict(DEFAULT_SOURCE_WEIGHTS)
        merged.update(self._raw.get("official", {}).get("source_weights", {}))
        return merged

    # ── Dictionaries (loaded from YAML, fallback to empty) ──
    def _load_dict(self, key: str) -> dict[str, list[str]]:
        """Load a {canonical: [aliases]} dictionary from config."""
        d = self._raw.get("dictionaries", {}).get(key, {}) or {}
        # Support both inline dict and external file reference
        if isinstance(d, str):
            ref = self._resolve(self.config_path.parent, d)
            if ref and ref.exists():
                d = load_yaml(ref)
        return {k: list(v or []) for k, v in d.items()}

    def _load_word_set(self, key: str, default: set[str]) -> set[str]:
        words = self._raw.get("dictionaries", {}).get(key)
        if not words:
            return set(default)
        return set(words)

    @property
    def official_dict(self) -> dict[str, list[str]]:
        return self._load_dict("official_selling_points")

    @property
    def user_dict(self) -> dict[str, list[str]]:
        return self._load_dict("user_selling_points")

    @property
    def positive_words(self) -> set[str]:
        return self._load_word_set("positive_words", DEFAULT_POSITIVE_WORDS)

    @property
    def negative_words(self) -> set[str]:
        return self._load_word_set("negative_words", DEFAULT_NEGATIVE_WORDS)

    # ── Secrets (.env or environment) ──
    def _secret(self, key: str, default: str = "") -> str:
        return self._env.get(key) or os.environ.get(key, default)

    @property
    def deepseek_api_key(self) -> str:
        return self._secret("DEEPSEEK_API_KEY")

    @property
    def llm_base_url(self) -> str:
        return self._secret("LLM_BASE_URL", "https://api.deepseek.com")

    @property
    def llm_model(self) -> str:
        return self._secret("LLM_MODEL", "deepseek-chat")

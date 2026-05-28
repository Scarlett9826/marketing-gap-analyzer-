"""Configuration loader.

Loads from (later overrides earlier):
  1. Built-in generic defaults (sentiment words, source weights)
  2. .env file (secrets)
  3. YAML config file (project-specific settings + dictionaries)

Selling-point dictionaries are intentionally NOT hardcoded — they are
product-category specific and must be supplied via YAML config.

Strict mode can be enabled via the ``MGAP_STRICT`` environment variable
or the ``strict`` parameter on :class:`Config`.  When active, missing
data files and incomplete YAML schemas raise errors instead of warnings.
"""

from __future__ import annotations

import json
import os
import sys
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
    """Unified configuration for a GAP analysis run.

    Parameters
    ----------
    config_path:
        Path to the YAML configuration file.
    env_path:
        Optional explicit ``.env`` file path.  When *None* the loader
        searches next to the config file and in the current working
        directory.
    strict:
        When *True*, missing data files and invalid schemas raise errors
        immediately.  When *None* the value is read from the
        ``MGAP_STRICT`` environment variable (``"1"``/``"true"`` to
        enable), falling back to *False* for backward compatibility.
    """

    def __init__(
        self,
        config_path: str | Path,
        env_path: str | Path | None = None,
        strict: bool | None = None,
    ) -> None:
        self._raw: dict[str, Any] = {}
        p = Path(config_path)

        # Resolve strict mode: explicit param > env var > default (False)
        if strict is None:
            env_val = os.environ.get("MGAP_STRICT", "").lower()
            strict = env_val in ("1", "true", "yes")
        self._strict = strict

        if not p.exists():
            if strict:
                raise FileNotFoundError(f"Config file not found: {config_path}")
            # Lenient: proceed with empty config, defaults everywhere
            self._env_path = None
            self._env = {}
            self.config_path = Path(config_path).resolve()
            self.project_dir = self.config_path.parent
            self.raw_official = None
            self.raw_user = None
            self.outputs = None
            return

        try:
            self._raw = load_yaml(config_path)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in config file: {e}")

        self._validate_config(strict)

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

        self._validate_data_files(strict)

    def _validate_config(self, strict: bool = False) -> None:
        """Validate required configuration fields.

        In lenient mode, missing sections are silently tolerated so that
        callers that only need partial config (e.g. API keys) are not
        blocked.  In strict mode every omission is an error.
        """
        required_sections = ["project", "paths"]
        for section in required_sections:
            if section not in self._raw:
                if strict:
                    raise ValueError(f"Missing required config section: '{section}'")
                return

        project = self._raw.get("project", {})
        if not project.get("name"):
            if strict:
                raise ValueError("Missing required field: 'project.name'")

        paths = self._raw.get("paths", {})
        if not paths.get("raw_official"):
            if strict:
                raise ValueError("Missing required field: 'paths.raw_official'")
        if not paths.get("raw_user"):
            if strict:
                raise ValueError("Missing required field: 'paths.raw_user'")
    
    def _validate_data_files(self, strict: bool = False) -> None:
        """Validate that referenced data files exist.

        In lenient mode, missing files produce a warning on stderr.
        In strict mode a :class:`FileNotFoundError` is raised.
        """
        errors: list[str] = []

        if self.raw_official and not self.raw_official.exists():
            errors.append(f"Official data file not found: {self.raw_official}")

        if self.raw_user and not self.raw_user.exists():
            errors.append(f"User data file not found: {self.raw_user}")

        if not errors:
            return

        if strict:
            raise FileNotFoundError("; ".join(errors))

        print("Warning: Data files missing:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("Analysis may fail or produce incomplete results.", file=sys.stderr)
    
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
    def category_description(self) -> str:
        """Product category / positioning description (e.g. '大阔折叠屏旗舰')."""
        return self._raw.get("project", {}).get("category", "")

    @property
    def min_comment_length(self) -> int:
        return int(self._raw.get("extractors", {}).get("user", {}).get("min_comment_length", 5))

    @property
    def max_comment_length(self) -> int:
        return int(self._raw.get("extractors", {}).get("user", {}).get("max_comment_length", 500))

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

    # ── Data integrity validation ──

    OFFICIAL_SCHEMA = {
        "required_fields": {"source", "type", "content"},
        "optional_fields": {"url", "verifiable"},
        "allowed_types": {
            "Slogan", "产品页文案", "发布会现场", "深度长文", "卖点拆解",
            "预热海报", "官方笔记", "KOL评测", "媒体转引的疑似Slogan",
        },
    }

    USER_SCHEMA = {
        "required_fields": {"source", "content"},
        "optional_fields": {"post_id", "note_id", "like", "url", "keyword"},
    }

    @classmethod
    def validate_official_data(cls, data: list[dict]) -> list[str]:
        """Validate official document data against the expected schema.

        Returns a list of human-readable error descriptions.  An empty
        list means the data is valid.
        """
        errors: list[str] = []
        if not isinstance(data, list):
            return ["Official data must be a JSON array"]
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"[{i}] Entry is not a dict")
                continue
            for field in cls.OFFICIAL_SCHEMA["required_fields"]:
                if field not in item or not item[field]:
                    errors.append(f"[{i}] Missing required field '{field}'")
            item_type = item.get("type", "")
            if item_type and item_type not in cls.OFFICIAL_SCHEMA["allowed_types"]:
                errors.append(
                    f"[{i}] Unknown type '{item_type}'; expected one of "
                    f"{sorted(cls.OFFICIAL_SCHEMA['allowed_types'])}"
                )
        return errors

    @classmethod
    def validate_user_data(cls, data: list[dict]) -> list[str]:
        """Validate user comment data against the expected schema.

        Returns a list of human-readable error descriptions.  An empty
        list means the data is valid.
        """
        errors: list[str] = []
        if not isinstance(data, list):
            return ["User data must be a JSON array"]
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"[{i}] Entry is not a dict")
                continue
            for field in cls.USER_SCHEMA["required_fields"]:
                if field not in item or not item[field]:
                    errors.append(f"[{i}] Missing required field '{field}'")
            content = item.get("content", "")
            if isinstance(content, str) and len(content.strip()) < 2:
                errors.append(f"[{i}] 'content' is empty or too short")
        return errors

    @classmethod
    def load_and_validate_json(
        cls,
        path: Path,
        *,
        validator: str = "official",
    ) -> tuple[list[dict], list[str]]:
        """Load a JSON file and validate its structure.

        Parameters
        ----------
        path:
            Path to the JSON file.
        validator:
            ``"official"`` or ``"user"`` — selects the schema.

        Returns
        -------
        A tuple ``(records, errors)``.  *errors* is empty when valid.
        """
        raw = json.loads(path.read_text(encoding="utf-8"))
        if validator == "official":
            return raw, cls.validate_official_data(raw)
        return raw, cls.validate_user_data(raw)

    # ── Model capability detection ──

    @property
    def llm_available(self) -> bool:
        """Return *True* when an API key is configured."""
        return bool(self.deepseek_api_key)

    def check_model_capability(self) -> dict[str, Any]:
        """Probe the configured LLM endpoint and return capability info.

        Returns a dict with keys:
        - ``available`` (bool): whether the endpoint responded successfully.
        - ``model`` (str): model name from the response.
        - ``error`` (str | None): error message on failure.
        """
        if not self.deepseek_api_key:
            return {
                "available": False,
                "model": self.llm_model,
                "error": "No API key configured",
            }

        import requests as _requests

        try:
            resp = _requests.get(
                f"{self.llm_base_url.rstrip('/')}/v1/models",
                headers={"Authorization": f"Bearer {self.deepseek_api_key}"},
                timeout=10,
            )
            resp.raise_for_status()
            models = resp.json().get("data", [])
            model_ids = [m.get("id", "") for m in models if isinstance(m, dict)]
            return {
                "available": True,
                "model": self.llm_model,
                "models_found": model_ids,
                "error": None,
            }
        except Exception as exc:
            return {
                "available": False,
                "model": self.llm_model,
                "error": str(exc),
            }

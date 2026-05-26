"""Shared LLM client.

Wraps OpenAI-compatible chat completions API (DeepSeek, OpenAI, Moonshot, etc.)
with safe JSON parsing and graceful fallback.
"""

from __future__ import annotations

import json
import re
from typing import Any

import requests

from ..config import Config


def strip_code_fence(text: str) -> str:
    """Strip ```json ... ``` fences from an LLM response."""
    text = text.strip()
    text = re.sub(r"^```(?:json|JSON)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def chat_json(prompt: str, cfg: Config, *, timeout: int = 30) -> Any | None:
    """Call the configured LLM and parse a JSON response.

    Returns None on any failure (network, parse, missing key) — caller should
    fall back to rule-based logic.
    """
    if not cfg.deepseek_api_key:
        return None

    try:
        resp = requests.post(
            f"{cfg.llm_base_url.rstrip('/')}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": cfg.llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(strip_code_fence(content))
    except Exception:
        return None

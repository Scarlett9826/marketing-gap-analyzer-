"""Official track: extract selling points from competitor official marketing copy.

Input:  JSON array of official documents [{source, type, content, url, verifiable}, ...]
Output: JSON with ranked selling points (weighted by source importance).
"""

from __future__ import annotations
import json
import re
import requests
from collections import Counter
from pathlib import Path
from typing import Any

from ..config import Config


def rule_based_extract(text: str, dict_map: dict[str, list[str]]) -> list[str]:
    """Rule-based keyword matching fallback."""
    found = []
    for canonical, aliases in dict_map.items():
        for alias in aliases:
            if alias in text:
                found.append(canonical)
                break
    return found[:5]


def call_llm_extract(text: str, cfg: Config, dict_map: dict[str, list[str]]) -> list[str]:
    """Extract top-5 selling points via LLM, fallback to rule-based."""
    api_key = cfg.deepseek_api_key
    if not api_key:
        return rule_based_extract(text, dict_map)

    try:
        prompt = f"""You are a senior product marketing analyst. From the following competitor marketing copy, extract the TOP 5 selling points the author is actively emphasizing.

Requirements:
1. Must be specific technology/feature names (e.g. "HarmonyOS NEXT", "Kirin 9020", "Red Maple Camera"), NOT generic words like "smooth", "beautiful", "flagship".
2. Use unified standardized naming (e.g. unify "native HarmonyOS" and "HarmonyOS NEXT" as "HarmonyOS NEXT").
3. Output ONLY a JSON array. Example: ["HarmonyOS NEXT", "Kirin 9020", "Satellite Communication"]
4. If no specific selling points found, return []

Copy:
\"\"\"
{text}
\"\"\""""

        resp = requests.post(
            f"{cfg.llm_base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": cfg.llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=30,
        )
        content = resp.json()["choices"][0]["message"]["content"].strip()
        content = re.sub(r"^```(json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
        return json.loads(content)
    except Exception:
        return rule_based_extract(text, dict_map)


def extract_official(config_path: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    """Run official selling point extraction.

    Args:
        config_path: Path to YAML config file.
        output_path: Path to write output JSON. If None, derived from config.

    Returns:
        Dict with summary and ranked selling points.
    """
    cfg = Config(config_path)
    if cfg.raw_official is None or not cfg.raw_official.exists():
        raise FileNotFoundError(f"Raw official data not found: {cfg.raw_official}")

    docs = json.loads(cfg.raw_official.read_text(encoding="utf-8"))
    print(f"Loaded {len(docs)} official documents")

    dict_map = cfg.official_dict
    weights = cfg.source_weights

    raw_counter: Counter = Counter()
    weighted_counter: Counter = Counter()
    point_to_sources: dict[str, list[str]] = {}

    for i, doc in enumerate(docs, 1):
        print(f"  [{i}/{len(docs)}] {doc.get('source', '?')} - {doc.get('type', '')}")
        points = call_llm_extract(doc.get("content", ""), cfg, dict_map)
        w = weights.get(doc.get("type", ""), weights.get("default", 1))

        for p in points:
            raw_counter[p] += 1
            weighted_counter[p] += w
            point_to_sources.setdefault(p, []).append(f"{doc.get('source','?')}/{doc.get('type','?')}")

    result = {
        "summary": {
            "total_official_docs": len(docs),
            "unique_selling_points": len(raw_counter),
        },
        "selling_points_ranked": [
            {
                "selling_point": p,
                "raw_count": raw_counter[p],
                "weighted_score": weighted_counter[p],
                "sources": list(set(point_to_sources.get(p, []))),
            }
            for p, _ in weighted_counter.most_common()
        ],
    }

    if output_path is None and cfg.outputs:
        output_path = Path(cfg.outputs) / "official_selling_points.json"
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Written to {output_path}")

    # Print top 10
    print("\nTop 10 official selling points:")
    for item in result["selling_points_ranked"][:10]:
        print(f"  {item['selling_point']:20s}  freq={item['raw_count']:2d}  weighted={item['weighted_score']:2d}")

    return result

"""Official track: extract selling points from competitor official marketing copy.

Input  schema: [{source, type, content, url, verifiable}, ...]
Output schema: {summary, selling_points_ranked: [{selling_point, raw_count,
                weighted_score, sources}, ...]}
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ..config import Config
from ..utils.llm import chat_json


PROMPT_TEMPLATE = """你是一名资深产品营销分析师。请从下面这段竞品官方营销文案中，提取作者**主动强调**的 TOP 5 卖点。

要求：
1. 必须是具体的技术/功能名称（例如「鸿蒙HarmonyOS6」「麒麟9030Pro」「潜望长焦」），不要笼统词（如「丝滑」「好看」「旗舰」）。
2. 用统一的标准化命名（例如「原生鸿蒙」「HarmonyOS 6」统一成「鸿蒙HarmonyOS6」）。
3. **只输出一个 JSON 数组**，例如 ["鸿蒙HarmonyOS6", "麒麟9030Pro", "卫星通信"]。
4. 如果文案中没有具体卖点，返回 []。

文案：
\"\"\"
{text}
\"\"\""""


def rule_based_extract(text: str, dict_map: dict[str, list[str]], top_n: int = 5) -> list[str]:
    """Rule-based: scan for any alias of each canonical term."""
    if not text or not dict_map:
        return []
    found: list[str] = []
    for canonical, aliases in dict_map.items():
        for alias in aliases:
            if alias and alias in text:
                found.append(canonical)
                break
    return found[:top_n]


def llm_extract(text: str, cfg: Config, dict_map: dict[str, list[str]]) -> list[str]:
    """Try LLM, fall back to dict matching on any failure."""
    if not text:
        return []
    result = chat_json(PROMPT_TEMPLATE.format(text=text), cfg)
    if isinstance(result, list) and all(isinstance(x, str) for x in result):
        return result[:5]
    return rule_based_extract(text, dict_map)


def extract_official(
    config_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run official selling point extraction."""
    cfg = Config(config_path)
    if cfg.raw_official is None or not cfg.raw_official.exists():
        raise FileNotFoundError(f"raw_official not found: {cfg.raw_official}")

    docs, schema_errors = Config.load_and_validate_json(cfg.raw_official, validator="official")
    if schema_errors:
        import sys
        print(f"Warning: raw_official has {len(schema_errors)} schema issue(s):", file=sys.stderr)
        for err in schema_errors[:5]:
            print(f"  - {err}", file=sys.stderr)
        if len(schema_errors) > 5:
            print(f"  ... and {len(schema_errors) - 5} more", file=sys.stderr)
    print(f"Loaded {len(docs)} official documents")

    dict_map = cfg.official_dict
    weights = cfg.source_weights

    raw_counter: Counter[str] = Counter()
    weighted_counter: Counter[str] = Counter()
    point_to_sources: dict[str, set[str]] = {}

    for i, doc in enumerate(docs, 1):
        src = doc.get("source", "?")
        typ = doc.get("type", "")
        print(f"  [{i}/{len(docs)}] {src} - {typ}")

        points = llm_extract(doc.get("content", ""), cfg, dict_map)
        w = weights.get(typ, weights.get("default", 1))

        for p in points:
            raw_counter[p] += 1
            weighted_counter[p] += w
            point_to_sources.setdefault(p, set()).add(f"{src}/{typ}")

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
                "sources": sorted(point_to_sources.get(p, [])),
            }
            for p, _ in weighted_counter.most_common()
        ],
    }

    out = _resolve_output(output_path, cfg, "official_selling_points.json")
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Written to {out}")

    print("\nTop 10 official selling points:")
    for item in result["selling_points_ranked"][:10]:
        print(f"  {item['selling_point']:20s}  freq={item['raw_count']:2d}  weighted={item['weighted_score']:2d}")

    return result


def _resolve_output(output_path: str | Path | None, cfg: Config, default_name: str) -> Path | None:
    if output_path:
        return Path(output_path)
    if cfg.outputs:
        return Path(cfg.outputs) / default_name
    return None

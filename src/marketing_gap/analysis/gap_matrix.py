"""GAP matrix analysis: cross-reference official vs user data.

Each selling point is classified into one of:
  ① 渗透成功 (Resonance)     official pushed + user high-mention + sentiment positive
  ② 渗透失败 (Invisible)      official pushed + user low-mention
  ③ 翻车 (Backfire)           official pushed + user high-mention + sentiment negative
  ④ 用户自发心智 (User-driven) official not pushed + user high-mention
  — 信号弱 (Weak signal)      everything else
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ..config import Config


CATEGORY_BACKFIRE = "③ 翻车"
CATEGORY_RESONANCE = "① 渗透成功"
CATEGORY_RESONANCE_NEUTRAL = "① 渗透成功(中性)"
CATEGORY_INVISIBLE = "② 渗透失败"
CATEGORY_USER_DRIVEN = "④ 用户自发心智"
CATEGORY_WEAK = "—（信号弱）"

CATEGORY_ORDER = [
    CATEGORY_BACKFIRE,
    CATEGORY_USER_DRIVEN,
    CATEGORY_RESONANCE,
    CATEGORY_RESONANCE_NEUTRAL,
    CATEGORY_INVISIBLE,
    CATEGORY_WEAK,
]


def classify(
    official_pushed: bool,
    user_high_mention: bool,
    sentiment: float,
    sent_pos_threshold: float,
    sent_neg_threshold: float,
) -> str:
    if official_pushed and user_high_mention:
        if sentiment <= sent_neg_threshold:
            return CATEGORY_BACKFIRE
        if sentiment >= sent_pos_threshold:
            return CATEGORY_RESONANCE
        return CATEGORY_RESONANCE_NEUTRAL
    if official_pushed and not user_high_mention:
        return CATEGORY_INVISIBLE
    if not official_pushed and user_high_mention:
        return CATEGORY_USER_DRIVEN
    return CATEGORY_WEAK


def run_gap_analysis(
    config_path: str | Path,
    official_path: str | Path | None = None,
    user_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    cfg = Config(config_path)

    if official_path is None and cfg.outputs:
        official_path = Path(cfg.outputs) / "official_selling_points.json"
    if user_path is None and cfg.outputs:
        user_path = Path(cfg.outputs) / "user_voice.json"
    if output_path is None and cfg.outputs:
        output_path = Path(cfg.outputs) / "gap_matrix.json"

    if not official_path or not Path(official_path).exists():
        raise FileNotFoundError(f"official_selling_points.json not found: {official_path}")
    if not user_path or not Path(user_path).exists():
        raise FileNotFoundError(f"user_voice.json not found: {user_path}")

    official = json.loads(Path(official_path).read_text(encoding="utf-8"))
    user = json.loads(Path(user_path).read_text(encoding="utf-8"))

    official_map = {x["selling_point"]: x for x in official["selling_points_ranked"]}
    user_map = {x["selling_point"]: x for x in user["user_voice_ranked"]}

    all_points = sorted(set(official_map.keys()) | set(user_map.keys()))

    OFF_HIGH = cfg.threshold_official_high
    USER_HIGH = cfg.threshold_user_high_mention
    SENT_NEG = cfg.threshold_sentiment_negative
    SENT_POS = cfg.threshold_sentiment_positive

    matrix: list[dict[str, Any]] = []
    for p in all_points:
        o = official_map.get(p)
        u = user_map.get(p)

        official_weight = o["weighted_score"] if o else 0
        official_count = o["raw_count"] if o else 0
        user_total = u["total_mentions"] if u else 0
        user_pos = u["positive"] if u else 0
        user_neg = u["negative"] if u else 0
        sentiment = u["sentiment_score"] if u else 0.0

        penetration = round(user_total / official_weight, 2) if official_weight > 0 else None

        category = classify(
            official_weight >= OFF_HIGH,
            user_total >= USER_HIGH,
            sentiment,
            SENT_POS,
            SENT_NEG,
        )

        matrix.append({
            "selling_point": p,
            "official_weighted_score": official_weight,
            "official_raw_count": official_count,
            "user_total_mentions": user_total,
            "user_positive": user_pos,
            "user_negative": user_neg,
            "sentiment_score": sentiment,
            "penetration_ratio": penetration,
            "category": category,
            "user_negative_examples": u.get("example_negative", []) if u else [],
            "user_positive_examples": u.get("example_positive", []) if u else [],
        })

    cat_rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    matrix.sort(key=lambda x: (
        cat_rank.get(x["category"], 99),
        -x["official_weighted_score"],
        -x["user_total_mentions"],
    ))

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"GAP matrix written to {out}")

    cat_counter = Counter(m["category"] for m in matrix)
    print(f"\n{len(all_points)} selling points classified:")
    for cat, n in cat_counter.most_common():
        print(f"  {cat}: {n}")

    return matrix

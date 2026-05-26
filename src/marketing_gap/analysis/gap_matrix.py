"""GAP matrix analysis: cross-reference official vs. user data to classify each selling point.

Output categories:
  ① 渗透成功 (Resonance)     : official pushed + user mentions high + sentiment positive
  ② 渗透失败 (Invisible)      : official pushed + user mentions low
  ③ 翻车 (Backfire)           : official pushed + user mentions high + sentiment negative
  ④ 用户自发心智 (Distortion) : official not pushed + user mentions high
  — 信号弱 (Weak signal)      : everything else
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional

from ..config import Config


def classify(official_pushed: bool, user_high_mention: bool, sentiment: float,
             sent_pos: float, sent_neg: float) -> str:
    if official_pushed and user_high_mention and sentiment >= sent_pos:
        return "① 渗透成功"
    if official_pushed and user_high_mention and sentiment <= sent_neg:
        return "③ 翻车"
    if official_pushed and not user_high_mention:
        return "② 渗透失败"
    if not official_pushed and user_high_mention:
        return "④ 用户自发心智"
    if official_pushed and user_high_mention:
        return "① 渗透成功(中性)"
    return "—（信号弱）"


def run_gap_analysis(config_path: str | Path,
                     official_path: str | Path | None = None,
                     user_path: str | Path | None = None,
                     output_path: str | Path | None = None) -> list[dict]:
    """Run GAP matrix analysis.

    Args:
        config_path: Path to YAML config file.
        official_path: Path to official_selling_points.json (optional, uses config default).
        user_path: Path to user_voice.json (optional, uses config default).
        output_path: Path to write gap_matrix.json (optional, uses config default).

    Returns:
        List of dicts: each selling point with category and metadata.
    """
    cfg = Config(config_path)

    if official_path is None and cfg.outputs:
        official_path = Path(cfg.outputs) / "official_selling_points.json"
    if user_path is None and cfg.outputs:
        user_path = Path(cfg.outputs) / "user_voice.json"
    if output_path is None and cfg.outputs:
        output_path = Path(cfg.outputs) / "gap_matrix.json"

    official = json.loads(Path(official_path).read_text(encoding="utf-8"))
    user = json.loads(Path(user_path).read_text(encoding="utf-8"))

    official_map = {x["selling_point"]: x for x in official["selling_points_ranked"]}
    user_map = {x["selling_point"]: x for x in user["user_voice_ranked"]}

    all_points = sorted(set(official_map.keys()) | set(user_map.keys()))

    OFF_HIGH = cfg.threshold_official_high
    USER_HIGH = cfg.threshold_user_high_mention
    SENT_NEG = cfg.threshold_sentiment_negative
    SENT_POS = cfg.threshold_sentiment_positive

    matrix = []
    for p in all_points:
        o = official_map.get(p)
        u = user_map.get(p)

        official_weight = o["weighted_score"] if o else 0
        official_count = o["raw_count"] if o else 0
        user_total = u["total_mentions"] if u else 0
        user_pos = u["positive"] if u else 0
        user_neg = u["negative"] if u else 0
        sentiment = u["sentiment_score"] if u else 0

        if official_weight > 0 and user_total >= 0:
            penetration = round(user_total / official_weight, 2)
        else:
            penetration = None

        official_pushed = official_weight >= OFF_HIGH
        user_high_mention = user_total >= USER_HIGH
        category = classify(official_pushed, user_high_mention, sentiment, SENT_POS, SENT_NEG)

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

    # Sort: most impactful categories first
    cat_order = {"③ 翻车": 0, "① 渗透成功": 1, "① 渗透成功(中性)": 1,
                 "② 渗透失败": 2, "④ 用户自发心智": 3, "—（信号弱）": 4}
    matrix.sort(key=lambda x: (cat_order.get(x["category"], 9),
                                -x["official_weighted_score"],
                                -x["user_total_mentions"]))

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"GAP matrix written to {output_path}")

    from collections import Counter
    cat_counter = Counter(m["category"] for m in matrix)
    print(f"\n{len(all_points)} selling points classified:")
    for cat, n in cat_counter.most_common():
        print(f"  {cat}: {n}")

    return matrix

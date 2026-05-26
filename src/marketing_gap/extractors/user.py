"""User track: extract selling points and sentiment from user comments.

Input  schema: [{source, post_id, note_id, content}, ...]
Output schema: {summary, user_voice_ranked: [{selling_point, total_mentions,
                positive, neutral, negative, sentiment_score,
                example_positive, example_negative}, ...]}
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..config import Config
from ..utils.llm import chat_json


# NOTE: literal braces in JSON example are escaped ({{ }}) for str.format()
PROMPT_TEMPLATE = """你是一名资深用户研究员。请分析下面这条用户评论，抽取用户**自发提及**的具体产品特性，并标注情感倾向。

要求：
1. 只抽取具体特性（如「电池」「重量」「屏幕」「拍照」「价格」「充电」「系统」），不要笼统词（如「好」「差」）。
2. 情感：positive（赞美/期待）、neutral（陈述事实）、negative（吐槽/抱怨）。
3. 用标准化短名（4-6 个汉字以内）。
4. **只输出一个 JSON 数组**，例如 [{{"point":"电池续航","sentiment":"positive"}},{{"point":"价格","sentiment":"negative"}}]
5. 没有具体特性返回 []。

评论：
\"\"\"
{text}
\"\"\""""


def rule_based_extract(
    text: str,
    dict_map: dict[str, list[str]],
    positive_words: set[str],
    negative_words: set[str],
) -> list[dict[str, str]]:
    """Match canonical terms via aliases, score sentiment by word counts."""
    if not text or not dict_map:
        return []
    text_lower = text.lower()
    pos_count = sum(1 for w in positive_words if w in text)
    neg_count = sum(1 for w in negative_words if w in text)
    if pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    seen: set[str] = set()
    found: list[dict[str, str]] = []
    for canonical, aliases in dict_map.items():
        if canonical in seen:
            continue
        for alias in aliases:
            if alias and alias.lower() in text_lower:
                found.append({"point": canonical, "sentiment": sentiment})
                seen.add(canonical)
                break
    return found


def llm_extract(
    text: str,
    cfg: Config,
    dict_map: dict[str, list[str]],
    positive_words: set[str],
    negative_words: set[str],
) -> list[dict[str, str]]:
    if not text:
        return []
    result = chat_json(PROMPT_TEMPLATE.format(text=text), cfg)
    if isinstance(result, list):
        cleaned = []
        for item in result:
            if not isinstance(item, dict) or "point" not in item:
                continue
            sentiment = item.get("sentiment", "neutral")
            if sentiment not in ("positive", "neutral", "negative"):
                sentiment = "neutral"
            cleaned.append({"point": str(item["point"]), "sentiment": sentiment})
        if cleaned:
            return cleaned
    return rule_based_extract(text, dict_map, positive_words, negative_words)


def extract_user(
    config_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run user comment extraction."""
    cfg = Config(config_path)
    if cfg.raw_user is None or not cfg.raw_user.exists():
        raise FileNotFoundError(f"raw_user not found: {cfg.raw_user}")

    comments = json.loads(cfg.raw_user.read_text(encoding="utf-8"))
    print(f"Loaded {len(comments)} user comments")

    dict_map = cfg.user_dict
    positive_words = cfg.positive_words
    negative_words = cfg.negative_words

    point_voice: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"positive": [], "neutral": [], "negative": []}
    )
    point_examples: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"positive": [], "neutral": [], "negative": []}
    )

    for i, c in enumerate(comments, 1):
        if i % 50 == 0:
            print(f"  Progress {i}/{len(comments)}")
        extracted = llm_extract(
            c.get("content", ""), cfg, dict_map, positive_words, negative_words
        )
        for item in extracted:
            p = item["point"]
            s = item["sentiment"]
            point_voice[p][s].append(c.get("post_id", ""))
            if len(point_examples[p][s]) < 2:
                point_examples[p][s].append(c.get("content", ""))

    result_list = []
    for point, voice in point_voice.items():
        pos = len(voice["positive"])
        neu = len(voice["neutral"])
        neg = len(voice["negative"])
        total = pos + neu + neg
        result_list.append({
            "selling_point": point,
            "total_mentions": total,
            "positive": pos,
            "neutral": neu,
            "negative": neg,
            "sentiment_score": round((pos - neg) / total, 2) if total else 0.0,
            "example_positive": point_examples[point]["positive"],
            "example_negative": point_examples[point]["negative"],
        })
    result_list.sort(key=lambda x: x["total_mentions"], reverse=True)

    result = {
        "summary": {
            "total_user_comments": len(comments),
            "unique_user_mentioned_points": len(result_list),
        },
        "user_voice_ranked": result_list,
    }

    out = _resolve_output(output_path, cfg, "user_voice.json")
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Written to {out}")

    print("\nTop 15 user discussed points:")
    print(f"  {'Point':20s}  {'Total':>5s}  {'Pos':>3s}  {'Neu':>3s}  {'Neg':>3s}  Sentiment")
    for item in result_list[:15]:
        print(
            f"  {item['selling_point']:20s}  {item['total_mentions']:5d}  "
            f"{item['positive']:3d}  {item['neutral']:3d}  {item['negative']:3d}  "
            f"{item['sentiment_score']:+.2f}"
        )

    return result


def _resolve_output(output_path: str | Path | None, cfg: Config, default_name: str) -> Path | None:
    if output_path:
        return Path(output_path)
    if cfg.outputs:
        return Path(cfg.outputs) / default_name
    return None

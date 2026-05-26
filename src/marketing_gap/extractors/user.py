"""User track: extract selling points and sentiment from user comments.

Input:  JSON array of user comments [{source, post_id, note_id, content}, ...]
Output: JSON with ranked selling points (positive/neutral/negative counts + examples).
"""

from __future__ import annotations
import json
import re
import requests
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..config import Config


def rule_based_user_extract(text: str, dict_map: dict[str, list[str]],
                            positive_words: set[str], negative_words: set[str]) -> list[dict]:
    """Rule-based: match keywords, assign sentiment."""
    text_lower = text.lower()
    found = []
    for canonical, aliases in dict_map.items():
        for alias in aliases:
            if alias.lower() in text_lower:
                pos = sum(1 for w in positive_words if w in text)
                neg = sum(1 for w in negative_words if w in text)
                if pos > neg:
                    sentiment = "positive"
                elif neg > pos:
                    sentiment = "negative"
                else:
                    sentiment = "neutral"
                found.append({"point": canonical, "sentiment": sentiment})
                break
    dedup = {}
    for f in found:
        if f["point"] not in dedup:
            dedup[f["point"]] = f
    return list(dedup.values())


def call_llm_user_extract(text: str, cfg: Config, dict_map: dict[str, list[str]],
                          positive_words: set[str], negative_words: set[str]) -> list[dict]:
    """Extract selling points + sentiment via LLM, fallback to rule-based."""
    if not cfg.deepseek_api_key:
        return rule_based_user_extract(text, dict_map, positive_words, negative_words)

    try:
        prompt = f"""You are a senior user researcher analyzing mobile phone product reviews.

Task: From this user review, extract the specific product features the user **spontaneously mentions**, and tag each with sentiment.

Requirements:
1. Only extract concrete features (e.g. "battery", "weight", "screen", "camera", "price", "charging speed", "OS"), NOT vague terms like "good" or "bad".
2. Sentiment: "positive" (praise), "neutral" (factual), "negative" (complaint).
3. Use standardized short names (4-6 Chinese characters).
4. Output ONLY a JSON array. Example: [{"point":"HarmonyOS","sentiment":"positive"},{"point":"Charging","sentiment":"negative"}]
5. Return [] if no specific features found.

Review:
\"\"\"
{text}
\"\"\""""

        resp = requests.post(
            f"{cfg.llm_base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {cfg.deepseek_api_key}", "Content-Type": "application/json"},
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
        return rule_based_user_extract(text, dict_map, positive_words, negative_words)


def extract_user(config_path: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    """Run user comment extraction.

    Args:
        config_path: Path to YAML config file.
        output_path: Path to write output JSON.

    Returns:
        Dict with summary and ranked user voice data.
    """
    cfg = Config(config_path)
    if cfg.raw_user is None or not cfg.raw_user.exists():
        raise FileNotFoundError(f"Raw user data not found: {cfg.raw_user}")

    comments = json.loads(cfg.raw_user.read_text(encoding="utf-8"))
    print(f"Loaded {len(comments)} user comments")

    dict_map = cfg.user_dict
    positive_words = cfg.positive_words
    negative_words = cfg.negative_words

    point_voice: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"positive": [], "neutral": [], "negative": []})
    point_examples: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"positive": [], "neutral": [], "negative": []})

    for i, c in enumerate(comments, 1):
        if i % 10 == 0:
            print(f"  Progress {i}/{len(comments)}")
        extracted = call_llm_user_extract(c.get("content", ""), cfg, dict_map, positive_words, negative_words)
        for item in extracted:
            p = item["point"]
            s = item.get("sentiment", "neutral")
            if s not in ("positive", "neutral", "negative"):
                s = "neutral"
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
            "sentiment_score": round((pos - neg) / total, 2) if total else 0,
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

    if output_path is None and cfg.outputs:
        output_path = Path(cfg.outputs) / "user_voice.json"
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Written to {output_path}")

    print(f"\nTop 15 user discussed points:")
    print(f"  {'Point':20s}  {'Total':>3s}  {'Pos':>3s}  {'Neu':>3s}  {'Neg':>3s}  Sentiment")
    for item in result_list[:15]:
        print(f"  {item['selling_point']:20s}  {item['total_mentions']:3d}  {item['positive']:3d}  {item['neutral']:3d}  {item['negative']:3d}  {item['sentiment_score']:+.2f}")

    return result

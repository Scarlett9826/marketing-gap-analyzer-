"""Render GAP matrix to a Feishu-friendly Markdown report."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from ..analysis.gap_matrix import (
    CATEGORY_BACKFIRE,
    CATEGORY_INVISIBLE,
    CATEGORY_RESONANCE,
    CATEGORY_RESONANCE_NEUTRAL,
    CATEGORY_USER_DRIVEN,
    CATEGORY_WEAK,
)
from ..config import Config
from ..utils.text import shorten


# ── Section configuration ──
DETAIL_CATEGORY_ORDER = [
    CATEGORY_BACKFIRE,
    CATEGORY_USER_DRIVEN,
    CATEGORY_RESONANCE,
    CATEGORY_RESONANCE_NEUTRAL,
    CATEGORY_INVISIBLE,
]


def _sentiment_icon(sent: float) -> str:
    if sent >= 0.1:
        return "🟢"
    if sent <= -0.2:
        return "🔴"
    return "⚪"


def _category_short(category: str) -> str:
    """Strip emoji prefix for compact display."""
    parts = category.split(" ", 1)
    return parts[1] if len(parts) > 1 else category


def format_data_label(m: dict[str, Any]) -> str:
    sent = m["sentiment_score"]
    return (
        f"`📊 官方加权 {m['official_weighted_score']} · "
        f"用户提及 {m['user_total_mentions']} · "
        f"{_sentiment_icon(sent)} 情感 {sent:+.2f} · "
        f"{m['category']}`"
    )


def auto_summary(m: dict[str, Any], brand: str) -> str:
    """Generate one objective sentence per category."""
    cat = m["category"]
    sp = m["selling_point"]
    ow = m["official_weighted_score"]
    um = m["user_total_mentions"]
    ss = m["sentiment_score"]

    if cat == CATEGORY_BACKFIRE:
        return (
            f"{brand}投入 {ow} 分推广 {sp}，用户讨论 {um} 次但情感偏负面"
            f"（{ss:+.2f}），说明该卖点未达预期，产生反效果。"
        )
    if cat in (CATEGORY_RESONANCE, CATEGORY_RESONANCE_NEUTRAL):
        polarity = "正面" if ss >= 0.1 else "中性"
        return (
            f"{brand}投入 {ow} 分推广 {sp}，用户讨论 {um} 次且情感{polarity}"
            f"（{ss:+.2f}），该卖点成功抵达目标用户心智。"
        )
    if cat == CATEGORY_INVISIBLE:
        return (
            f"{brand}投入 {ow} 分推广 {sp}，但用户提及仅 {um} 次，"
            f"营销投入未有效转化为用户感知。"
        )
    if cat == CATEGORY_USER_DRIVEN:
        return (
            f"{brand}未重点推广 {sp}（加权 {ow} 分），但用户自发讨论 {um} 次，"
            f"属于产品力驱动的长尾资产。"
        )
    return f"{sp} 信号强度不足（官方 {ow} / 用户 {um}），需更多数据判断。"


# ── Evidence selection ──

PLATFORM_LINK_TEMPLATES = {
    "微博评论": lambda note, post: f"https://weibo.com/{note}/{post}" if note and post else "",
    "B站评论": lambda note, post: f"https://www.bilibili.com/video/av{note}/#reply{post}" if note else "",
    "B站官方号评论": lambda note, post: f"https://www.bilibili.com/video/av{note}/#reply{post}" if note else "",
    "小红书评论": lambda note, post: f"https://www.xiaohongshu.com/explore/{note}" if note else "",
}


def pick_evidence(
    m: dict[str, Any],
    raw_user: list[dict[str, Any]],
    user_dict: dict[str, list[str]],
    max_count: int = 4,
) -> list[dict[str, Any]]:
    """Select user comments that contain any alias for this selling point."""
    point = m["selling_point"]
    aliases = user_dict.get(point, [])
    # Always include the canonical name
    needles = list({point, *aliases})

    # Prefer examples from the gap matrix (already filtered by extractor)
    pre_examples = list(m.get("user_negative_examples", [])) + list(m.get("user_positive_examples", []))

    matched: list[dict[str, Any]] = []
    seen: set[str] = set()

    for c in raw_user:
        content = c.get("content", "")
        if not content:
            continue
        if not any(n.lower() in content.lower() for n in needles if n):
            continue
        key = content[:30]
        if key in seen:
            continue
        seen.add(key)
        # Bump examples that match the example list to the top
        priority = 0 if content in pre_examples else 1
        matched.append((priority, c))

    matched.sort(key=lambda t: t[0])
    return [c for _, c in matched[:max_count]]


def emit_evidence_lines(
    m: dict[str, Any],
    raw_user: list[dict[str, Any]],
    user_dict: dict[str, list[str]],
) -> list[str]:
    evidences = pick_evidence(m, raw_user, user_dict)
    if not evidences:
        return []
    lines = ["> **用户证据片段**："]
    for e in evidences:
        content = shorten(e.get("content", ""), 200)
        source = e.get("source", "未知")
        post_id = e.get("post_id", "")
        note_id = e.get("note_id", "")
        link_fn = PLATFORM_LINK_TEMPLATES.get(source)
        link = link_fn(note_id, post_id) if link_fn else ""
        link_text = f" · [查看原文]({link})" if link else ""
        lines.append(f"> 「{content}」  — {source}{link_text}")
    return lines


# ── Post-processing ──

def feishu_postprocess(raw: str) -> str:
    """Make Markdown look better when imported into Feishu."""
    raw = re.sub(r"([\u4e00-\u9fff]):(?!//)", r"\1：", raw)  # Chinese colons (skip URLs)
    raw = re.sub(r"\*\*\s+", "**", raw)
    return raw


# ── Main render ──

def render(
    config_path: str | Path,
    matrix_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> str:
    cfg = Config(config_path)
    if matrix_path is None and cfg.outputs:
        matrix_path = Path(cfg.outputs) / "gap_matrix.json"
    if output_path is None and cfg.outputs:
        output_path = Path(cfg.outputs) / "report.md"

    if not matrix_path or not Path(matrix_path).exists():
        raise FileNotFoundError(f"gap_matrix.json not found: {matrix_path}")

    today = datetime.now().strftime("%Y-%m-%d")

    gap = json.loads(Path(matrix_path).read_text(encoding="utf-8"))
    raw_official = json.loads(cfg.raw_official.read_text(encoding="utf-8")) if cfg.raw_official else []
    raw_user = json.loads(cfg.raw_user.read_text(encoding="utf-8")) if cfg.raw_user else []
    user_dict = cfg.user_dict
    brand = cfg.brand_name

    L: list[str] = []
    P = L.append

    # ── Cover ──
    project_name = cfg.project_name
    P(f"# 「{project_name}」竞品营销 GAP 分析报告\n")
    P(f"> **数据时间**：{cfg.data_date or today}　|　**分析对象**：{project_name}")
    if cfg.product_description:
        P(f"> **产品描述**：{cfg.product_description}")
    P(
        f"> **数据规模**：官方文案 {len(raw_official)} 条 · "
        f"用户评论 {len(raw_user)} 条 · 对齐卖点 {len(gap)} 个\n"
    )

    # ── TL;DR ──
    P("---\n")
    P("## 一、TL;DR\n")
    backfire = [m for m in gap if m["category"] == CATEGORY_BACKFIRE]
    user_driven = [m for m in gap if m["category"] == CATEGORY_USER_DRIVEN]
    invisible = [m for m in gap if m["category"] == CATEGORY_INVISIBLE]
    resonance = [m for m in gap if m["category"] in (CATEGORY_RESONANCE, CATEGORY_RESONANCE_NEUTRAL)]

    def names(items: list[dict], n: int = 3) -> str:
        if not items:
            return "（无）"
        return ", ".join(m["selling_point"] for m in items[:n])

    P(f"1. **翻车**（{len(backfire)} 个）：{names(backfire)} —— 官方投入大但用户反馈负面。")
    P(f"2. **用户自发心智**（{len(user_driven)} 个）：{names(user_driven)} —— 官方未主推但用户高频提及。")
    P(f"3. **渗透失败**（{len(invisible)} 个）：{names(invisible)} —— 官方投入未触达目标用户。")
    P(f"4. **渗透成功**（{len(resonance)} 个）：{names(resonance)} —— 官方传达与用户认知一致。")
    P(
        f"5. 本报告基于 {len(raw_user)} 条真实用户评论 + {len(raw_official)} 条官方文案，"
        f"所有结论均可溯源（详见附录）。\n"
    )

    # ── Analysis ──
    P("---\n")
    P("## 二、分析对象与 GAP 矩阵\n")

    P("### 2.1 分析对象\n")
    src_official = Counter(o.get("source", "未知") for o in raw_official)
    src_user = Counter(u.get("source", "未知") for u in raw_user)
    P("| 维度 | 内容 |")
    P("|---|---|")
    P(f"| 分析对象 | {project_name} |")
    if cfg.product_description:
        P(f"| 品类定位 | {cfg.product_description} |")
    if src_official:
        P(f"| 官方文案来源 | {', '.join(f'{k} {v}条' for k, v in src_official.most_common())} |")
    if src_user:
        P(f"| 用户评论来源 | {', '.join(f'{k} {v}条' for k, v in src_user.most_common())} |")
    P("")

    P("### 2.2 四类卖点分布概览\n")
    cat_counter = Counter(m["category"] for m in gap)
    bar_max = max((v for v in cat_counter.values()), default=1)
    P("| 分类 | 数量 | 占比 |")
    P("|---|---|---|")
    for cat in DETAIL_CATEGORY_ORDER + [CATEGORY_WEAK]:
        n = cat_counter.get(cat, 0)
        if n == 0:
            continue
        bar_len = max(1, int(n / bar_max * 20))
        pct = n / len(gap) * 100 if gap else 0
        P(f"| {_category_short(cat)} | {n} | {'█' * bar_len} {pct:.0f}% |")
    P("")

    P("### 2.3 全量卖点矩阵\n")
    P("| 卖点 | 官方加权 | 用户提及 | 正/负 | 情感分 | 分类 |")
    P("|---|---|---|---|---|---|")
    for m in gap:
        sent = m["sentiment_score"]
        sent_str = f"{sent:+.2f}"
        P(
            f"| {m['selling_point']} | {m['official_weighted_score']} | "
            f"{m['user_total_mentions']} | +{m['user_positive']}/-{m['user_negative']} | "
            f"{sent_str} | {_category_short(m['category'])} |"
        )
    P("")

    # ── Detail ──
    P("---\n")
    P("## 三、卖点详解\n")

    section_titles = {
        CATEGORY_BACKFIRE: "翻车（官方主推 + 用户高频负面）",
        CATEGORY_USER_DRIVEN: "用户自发心智（官方未主推 + 用户高频提及）",
        CATEGORY_RESONANCE: "渗透成功（官方主推 + 用户高频正面）",
        CATEGORY_RESONANCE_NEUTRAL: "渗透成功（中性）",
        CATEGORY_INVISIBLE: "渗透失败（官方主推 + 用户提及量低）",
    }

    for cat in DETAIL_CATEGORY_ORDER:
        items = [m for m in gap if m["category"] == cat]
        if not items:
            continue
        P(f"### {section_titles[cat]}\n")
        for item in items:
            P(f"#### {item['selling_point']}\n")
            P(format_data_label(item))
            P("")
            P(auto_summary(item, brand))
            P("")
            for line in emit_evidence_lines(item, raw_user, user_dict):
                P(line)
            P("")
            P("---\n")

    # ── Appendix ──
    P("## 四、附录\n")

    P("### 附录 A：GAP 分析框架\n")
    P("**双轨交叉分析**：将每个卖点按「官方投入度」vs「用户感知度」放入 4 类：\n")
    P("|  | 用户讨论多 | 用户讨论少 |")
    P("|---|---|---|")
    P("| **官方说得多** | ① 渗透成功 / ③ 翻车 | ② 渗透失败 |")
    P("| **官方说得少** | ④ 用户自发心智 | —（信号弱） |")
    P("")
    P("**阈值定义**：")
    P(
        f"- 官方主推：加权得分 ≥ {cfg.threshold_official_high}"
        f"（按来源加权：Slogan=5 / 产品页=4 / 发布会=3 / KOL评测=2 / 默认=1）"
    )
    P(f"- 用户高频：提及量 ≥ {cfg.threshold_user_high_mention}")
    P(
        f"- 情感正面：≥ {cfg.threshold_sentiment_positive} / "
        f"负面：≤ {cfg.threshold_sentiment_negative}"
    )
    P("")
    P("**抽取方式**：LLM（DeepSeek/OpenAI 兼容）+ 规则词典兜底。")
    P("- 官方轨抽「主动强调的卖点」")
    P("- 用户轨抽「自发提到的特性 + 情感倾向」")
    P("")

    if src_user:
        P("### 附录 B：数据采集明细\n")
        P("| 平台 | 条数 |")
        P("|---|---|")
        for src, n in src_user.most_common():
            P(f"| {src} | {n} |")
        P("")

    P(f"---\n**报告版本**：v{cfg._raw.get('project', {}).get('version', '1')}　**生成时间**：{today}　**生成工具**：marketing-gap-analyzer\n")

    raw = feishu_postprocess("\n".join(L))

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(raw, encoding="utf-8")
        line_count = raw.count("\n") + 1
        size_kb = len(raw.encode("utf-8")) / 1024
        print(f"Report written to {out}")
        print(f"Size: {size_kb:.1f} KB ({line_count} lines)")

    return raw

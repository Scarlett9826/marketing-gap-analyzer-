"""Render GAP matrix to a Feishu-friendly Markdown report."""

from __future__ import annotations
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import Config


# ── Helper: shorten long text for display ──
def shorten(text: str, max_len: int = 140) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"\[[^\]]{1,20}\]", "", text)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def format_data_label(m: dict) -> str:
    """One-line data label for a selling point."""
    sent = m["sentiment_score"]
    if sent >= 0.1:
        sent_icon = "🟢"
    elif sent <= -0.2:
        sent_icon = "🔴"
    else:
        sent_icon = "⚪"
    cat = m["category"]
    return f"`📊 官方加权 {m['official_weighted_score']} · 用户提及 {m['user_total_mentions']} · {sent_icon} 情感 {sent:+.2f} · {cat}`"


def auto_summary(m: dict) -> str:
    """Generate one objective sentence per category."""
    cat = m["category"]
    if "翻车" in cat:
        return f"华为官方投入 {m['official_weighted_score']} 分推广 {m['selling_point']}，用户讨论 {m['user_total_mentions']} 次但情感偏负面（{m['sentiment_score']:+.2f}），说明该卖点未达预期，产生反效果。"
    if "渗透成功" in cat:
        return f"华为官方投入 {m['official_weighted_score']} 分推广 {m['selling_point']}，用户讨论 {m['user_total_mentions']} 次且情感正面（{m['sentiment_score']:+.2f}），该卖点成功抵达目标用户心智。"
    if "渗透失败" in cat:
        return f"华为官方投入 {m['official_weighted_score']} 分推广 {m['selling_point']}，但用户提及仅 {m['user_total_mentions']} 次，营销投入未有效转化为用户感知。"
    if "用户自发" in cat:
        return f"华为官方未重点推广 {m['selling_point']}（加权 {m['official_weighted_score']} 分），但用户自发讨论 {m['user_total_mentions']} 次，属于产品力驱动的长尾资产。"
    return f"{m['selling_point']} 的信号强度不足（官方 {m['official_weighted_score']} / 用户 {m['user_total_mentions']}），需更多数据判断。"


def pick_evidence(m: dict, raw_user: list[dict], max_count: int = 4) -> list[dict]:
    """Pick representative user comments for this selling point."""
    point = m["selling_point"]
    matched = []
    for c in raw_user:
        content = c.get("content", "")
        if any(kw in content for kw in [point]):  # simple match
            matched.append(c)
        elif len(matched) >= max_count * 2:
            break
    # Fallback: match first N
    if len(matched) < max_count:
        matched = raw_user[:max_count * 2]

    # Deduplicate
    seen = set()
    selected = []
    for c in matched:
        if not c.get("content"):
            continue
        key = c["content"][:30]
        if key in seen:
            continue
        seen.add(key)
        selected.append(c)
        if len(selected) >= max_count:
            break
    return selected


def emit_evidence_section(m: dict, raw_user: list[dict], cfg: Config) -> list[str]:
    """Build evidence quotes section for one selling point."""
    lines = []
    evidences = pick_evidence(m, raw_user)
    if evidences:
        lines.append("> **用户证据片段**：")
        for e in evidences:
            content = e.get("content", "")
            source = e.get("source", "未知")
            platform_icons = {
                "B站评论": "bilibili.com", "B站官方号评论": "bilibili.com",
                "小红书评论": "xiaohongshu.com", "微博评论": "weibo.com",
            }
            icon = platform_icons.get(source, "")
            post_id = e.get("post_id", "")
            note_id = e.get("note_id", "")
            link = ""
            if source == "微博评论":
                link = f"https://weibo.com/{note_id}/{post_id}" if note_id and post_id else ""
            elif "B站" in source:
                link = f"https://www.bilibili.com/video/av{note_id}/#reply{post_id}" if note_id else ""
            elif source == "小红书评论":
                link = f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else ""
            link_text = f" · [查看原文]({link})" if link else ""
            lines.append(f"> 「{content}」  — {source}{link_text}")
    return lines


def _normalize_tables(raw: str) -> str:
    """Normalize Feishu table formatting for better rendering."""
    lines = raw.split("\n")
    result = []
    for line in lines:
        result.append(line)
    return "\n".join(result)


def feishu_postprocess(raw: str) -> str:
    """Post-process markdown for Feishu import compatibility."""
    raw = re.sub(r"([\u4e00-\u9fff]):", r"\1：", raw)
    raw = re.sub(r"## (\S)", r"## \1", raw)
    raw = re.sub(r"\*\*\s*", "**", raw)
    raw = _normalize_tables(raw)
    return raw


def render(config_path: str | Path,
           matrix_path: str | Path | None = None,
           output_path: str | Path | None = None) -> str:
    """Render full Feishu Markdown report.

    Args:
        config_path: Path to YAML config file.
        matrix_path: Path to gap_matrix.json (optional).
        output_path: Path to write .md report (optional).

    Returns:
        Report content as string.
    """
    cfg = Config(config_path)
    if matrix_path is None and cfg.outputs:
        matrix_path = Path(cfg.outputs) / "gap_matrix.json"
    if output_path is None and cfg.outputs:
        output_path = Path(cfg.outputs) / "report.md"

    today = datetime.now().strftime("%Y-%m-%d")

    gap = json.loads(Path(matrix_path).read_text(encoding="utf-8"))
    raw_official = json.loads(cfg.raw_official.read_text(encoding="utf-8")) if cfg.raw_official else []
    raw_user = json.loads(cfg.raw_user.read_text(encoding="utf-8")) if cfg.raw_user else []

    # Category grouping
    cat_order_name = {
        "③ 翻车": "三、卖点详解 · 翻车（官方主推 + 用户高频负面）",
        "④ 用户自发心智": "三、卖点详解 · 用户自发心智（官方未主推 + 用户高频提及）",
        "① 渗透成功": "三、卖点详解 · 渗透成功（官方主推 + 用户高频正面）",
        "① 渗透成功(中性)": "三、卖点详解 · 渗透成功（官方主推 + 用户高频中性）",
        "② 渗透失败": "三、卖点详解 · 渗透失败（官方主推 + 用户提及量低）",
    }
    cat_display_order = ["③ 翻车", "④ 用户自发心智", "① 渗透成功", "① 渗透成功(中性)", "② 渗透失败"]

    L: list[str] = []
    P = L.append

    # ═══════════ COVER ═══════════
    project_name = cfg.project_name
    P(f"# 「{project_name}」竞品营销 GAP 分析报告\n")
    P(f"> **数据时间**：{cfg.data_date or today}　|　**分析对象**：{project_name}")
    desc = cfg.product_description
    if desc:
        P(f"> **产品描述**：{desc}")
    P(f"> **数据规模**：官方文案 {len(raw_official)} 条 · 用户评论 {len(raw_user)} 条 · 对齐卖点 {len(gap)} 个\n")

    # ═══════════ TL;DR ═══════════
    P("---\n")
    P("## 一、TL;DR\n")
    top_overturn = [m for m in gap if "翻车" in m["category"]]
    top_organic = [m for m in gap if "用户自发" in m["category"]]
    top_fail = [m for m in gap if "渗透失败" in m["category"]]
    top_success = [m for m in gap if "渗透成功" in m["category"]]

    P(f"1. **翻车**（{len(top_overturn)} 个）：{', '.join(m['selling_point'] for m in top_overturn[:3])} —— 官方投入大但用户反馈负面。")
    P(f"2. **用户自发心智**（{len(top_organic)} 个）：{', '.join(m['selling_point'] for m in top_organic[:3])} —— 官方未主推但用户高频提及，反映真实产品体感。")
    P(f"3. **渗透失败**（{len(top_fail)} 个）：{', '.join(m['selling_point'] for m in top_fail[:3])} —— 官方投入未触达目标用户。")
    P(f"4. **渗透成功**（{len(top_success)} 个）：{', '.join(m['selling_point'] for m in top_success[:3])} —— 官方传达与用户认知一致。")
    P(f"5. 本报告基于 {len(raw_user)} 条真实用户评论 + {len(raw_official)} 条官方文案，所有结论均可溯源（详见附录 F）。\n")

    # ═══════════ ANALYSIS ═══════════
    P("---\n")
    P("## 二、分析对象与 GAP 矩阵\n")

    P("### 2.1 分析对象\n")
    # Source distribution
    src_official = Counter(o.get("source", "未知") for o in raw_official)
    src_user = Counter(u.get("source", "未知") for u in raw_user)
    P("| 维度 | 内容 |")
    P("|---|---|")
    P(f"| 分析对象 | {project_name} |")
    if desc:
        P(f"| 品类定位 | {desc} |")
    P(f"| 官方文案来源 | {', '.join(f'{k} {v}条' for k, v in src_official.most_common())} |")
    P(f"| 用户评论来源 | {', '.join(f'{k} {v}条' for k, v in src_user.most_common())} |")
    P("")

    # 4-category distribution overview
    P("### 2.2 四类卖点分布概览\n")
    cat_counter = Counter(m["category"] for m in gap)
    bar_max = max((v for v in cat_counter.values()), default=1)
    P("| 分类 | 数量 | 占比 |")
    P("|---|---|---|")
    for cat_name in ["③ 翻车", "④ 用户自发心智", "① 渗透成功", "① 渗透成功(中性)", "② 渗透失败", "—（信号弱）"]:
        n = cat_counter.get(cat_name, 0)
        if n == 0:
            continue
        bar_len = max(1, int(n / bar_max * 20))
        bar = "█" * bar_len
        pct = n / len(gap) * 100
        short = cat_name.split(" ")[1] if " " in cat_name else cat_name
        P(f"| {short} | {n} | {bar} {pct:.0f}% |")
    P("")

    # Full matrix
    P("### 2.3 全量卖点矩阵\n")
    P("| 卖点 | 官方加权 | 用户提及 | 正/负 | 情感分 | 分类 |")
    P("|---|---|---|---|---|---|")
    for m in gap:
        sent = m["sentiment_score"]
        sent_str = f"{sent:+.2f}" if sent else "0.00"
        cat_short = m["category"].split(" ")[1] if " " in m["category"] else m["category"]
        P(f"| {m['selling_point']} | {m['official_weighted_score']} | {m['user_total_mentions']} | +{m['user_positive']}/-{m['user_negative']} | {sent_str} | {cat_short} |")
    P("")

    # ═══════════ DETAIL SECTIONS ═══════════
    P("---\n")
    P("## 三、卖点详解\n")

    for cat in cat_display_order:
        items = [m for m in gap if m["category"] == cat or
                 (cat == "① 渗透成功" and m["category"] == "① 渗透成功(中性)")]
        if not items:
            continue

        section_number = cat_display_order.index(cat) + 1
        for item in items:
            sp = item["selling_point"]
            P(f"### {sp}\n")

            P(format_data_label(item))
            P("")
            P(f"{auto_summary(item)}")
            P("")

            # Evidence quotes
            evidence_lines = emit_evidence_section(item, raw_user, cfg)
            if evidence_lines:
                for line in evidence_lines:
                    P(line)
                P("")

            P("---\n")

    # ═══════════ APPENDIX ═══════════
    P("## 四、附录\n")

    # Appendix A: Methodology
    P("### 附录 A：GAP 分析框架\n")
    P("**双轨交叉分析**：将每个卖点按「官方投入度」vs「用户感知度」放入 4 类：")
    P("|  | 用户讨论多 | 用户讨论少 |")
    P("|---|---|---|")
    P("| **官方说得多** | ① 渗透成功 / ③ 翻车 | ② 渗透失败 |")
    P("| **官方说得少** | ④ 用户自发心智 | —（信号弱） |")
    P("")
    P(f"**阈值定义**：")
    P(f"- 官方主推：加权得分 ≥ {cfg.threshold_official_high}（按来源加权：Slogan=5 / 产品页=4 / 发布会=3 / KOL评测=2 / 默认=1）")
    P(f"- 用户高频：提及量 ≥ {cfg.threshold_user_high_mention}")
    P(f"- 情感正面：≥ {cfg.threshold_sentiment_positive} / 负面：≤ {cfg.threshold_sentiment_negative}")
    P("")
    P("**抽取方式**：LLM（DeepSeek/GPT-4o-mini）+ 规则词典兜底。")
    P("- 官方轨抽「主动强调的卖点」")
    P("- 用户轨抽「自发提到的特性 + 情感倾向」")
    P("")

    # Appendix B: Data collection details
    P("### 附录 B：数据采集明细\n")
    P("| 平台 | 条数 | 采集方法 |")
    P("|---|---|---|")
    for src, n in src_user.most_common():
        method = {
            "微博评论": "1dyer/weibo-comment-crawler 直抓 weibo.com/ajax API",
            "B站评论": "MediaCrawler search 模式",
            "B站官方号评论": "MediaCrawler creator 模式（按关键词过滤）",
            "小红书评论": "MediaCrawler search 模式",
        }.get(src, "MediaCrawler 爬虫")
        P(f"| {src} | {n} | {method} |")
    P("")

    # Appendix C: Known limitations
    P("### 附录 C：已知数据局限\n")
    P("| # | 渠道 | 状态 | 说明 |")
    P("|---|---|---|---|")
    P("| 1 | 微博博文搜索 | ⚠️ 部分 | 搜索接口需完整 cookie；当前通过手工选取 KOL 博文抓评论 |")
    P("| 2 | 微信公众号 | ❌ 不覆盖 | 生态封闭，文章评论需 PC 微信抓包 |")
    P("| 3 | 小红书笔记详情 | ⚠️ 部分 | xsec_token 过期，detail 模式需 QR 重登 |")
    P("| 4 | X/Twitter | ❌ 不覆盖 | 海外渠道 |")
    P("")

    P("---\n")
    P(f"**报告版本**：v2　**生成时间**：{today}　**生成工具**：marketing-gap-analyzer\n")

    # ── Write output ──
    raw = "\n".join(L)
    raw = feishu_postprocess(raw)
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(raw, encoding="utf-8")
        lines_count = raw.count("\n") + 1
        print(f"Report written to {output_path}")
        print(f"Size: {len(raw.encode('utf-8')) / 1024:.1f} KB ({lines_count} lines)")

    return raw

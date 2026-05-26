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
from ..utils.text import (
    clean_text,
    is_low_signal,
    is_template_rant,
    normalize_for_dedup,
    shorten,
)


# ── Section configuration ──
DETAIL_CATEGORY_ORDER = [
    CATEGORY_BACKFIRE,
    CATEGORY_USER_DRIVEN,
    CATEGORY_RESONANCE,
    CATEGORY_RESONANCE_NEUTRAL,
    CATEGORY_INVISIBLE,
]


def _category_short(category: str) -> str:
    """Strip emoji prefix for compact display."""
    parts = category.split(" ", 1)
    return parts[1] if len(parts) > 1 else category


def _category_emoji(cat: str) -> str:
    if "翻车" in cat:
        return "🚨 翻车"
    if "渗透成功" in cat:
        return "✅ 渗透成功"
    if "渗透失败" in cat:
        return "⚠️ 渗透失败"
    if "用户自发" in cat:
        return "💡 用户自发心智"
    return "— 信号弱"


def _sentiment_icon(sent: float) -> str:
    if sent >= 0.1:
        return "🟢"
    if sent <= -0.2:
        return "🔴"
    return "⚪"


def _sentiment_label(score: float) -> str:
    if score >= 0.1:
        return "正面"
    if score <= -0.2:
        return "负面"
    return "中性"


def format_data_label(m: dict[str, Any]) -> str:
    pos = m["user_positive"]
    neg = m["user_negative"]
    u_total = m["user_total_mentions"]
    neu = u_total - pos - neg
    sent = m["sentiment_score"]
    o_score = m["official_weighted_score"]
    o_count = m["official_raw_count"]
    cat = _category_emoji(m["category"])
    parts = [f"📊 官方加权 **{o_score}**（{o_count} 条文案）"]
    if u_total > 0:
        parts.append(f"用户提及 **{u_total}**（情感 **{sent:+.2f}**，正/中/负 {pos}/{neu}/{neg}）")
    else:
        parts.append("用户提及 **0**")
    parts.append(f"**{cat}**")
    return " · ".join(parts)


def auto_summary(m: dict[str, Any], brand: str) -> str:
    """Generate one objective sentence per category, brand-parameterized."""
    sp = m["selling_point"]
    o_score = m["official_weighted_score"]
    o_count = m["official_raw_count"]
    u_total = m["user_total_mentions"]
    pos, neg = m["user_positive"], m["user_negative"]
    sent = m["sentiment_score"]
    cat = m["category"]

    if "翻车" in cat:
        return (
            f"{brand}在 {o_count} 条文案里集中投放此卖点，但用户 {u_total} 次讨论中情感分 "
            f"{sent:+.2f}（负向 {neg} 条 vs 正向 {pos} 条），说明该卖点未达预期、产生反效果。"
        )
    if "渗透成功" in cat:
        if sent >= 0.1:
            return (
                f"{brand}主推（加权 {o_score}），用户 {u_total} 次讨论且情感整体正面（{sent:+.2f}），"
                f"该卖点成功抵达目标用户心智。"
            )
        return (
            f"{brand}主推（加权 {o_score}），用户 {u_total} 次讨论但情感呈两极/中性"
            f"（正 {pos}、中 {u_total - pos - neg}、负 {neg}）。"
        )
    if "渗透失败" in cat:
        return (
            f"{brand}在 {o_count} 条文案里强调（加权 {o_score}），但用户讨论仅 {u_total} 次，"
            f"营销投入未有效转化为用户感知。"
        )
    if "用户自发" in cat:
        return (
            f"{brand}未重点推广 {sp}（加权 {o_score}），但用户在 {u_total} 条讨论中自发提及，"
            f"情感 {sent:+.2f}（正 {pos}、中 {u_total - pos - neg}、负 {neg}），"
            f"属于产品力驱动的长尾资产。"
        )
    return f"官方加权 {o_score}、用户提及 {u_total}，双轨信号都偏弱。"


# ── Evidence selection ──

PLATFORM_LINK_TEMPLATES = {
    "微博评论": lambda note, post: f"https://weibo.com/{note}/{post}" if note and post else "",
    "B站评论": lambda note, post: f"https://www.bilibili.com/video/av{note}/#reply{post}" if note else "",
    "B站官方号评论": lambda note, post: f"https://www.bilibili.com/video/av{note}/#reply{post}" if note else "",
    "小红书评论": lambda note, post: f"https://www.xiaohongshu.com/explore/{note}" if note else "",
}


def comment_url(c: dict) -> str | None:
    """Construct best-effort permalink from a comment record."""
    src = c.get("source", "")
    note_id = c.get("note_id", "")
    post_id = c.get("post_id", "")
    if "微博" in src:
        if note_id and post_id:
            return f"https://weibo.com/{note_id}/{post_id}#cm{post_id}"
        return None
    if "B站" in src or "B" in src:
        vid = c.get("video_id") or note_id
        rpid = post_id
        if vid and rpid:
            return f"https://www.bilibili.com/video/av{vid}/#reply{rpid}"
        if vid:
            return f"https://www.bilibili.com/video/av{vid}/"
        return None
    if "小红书" in src:
        if note_id:
            return f"https://www.xiaohongshu.com/explore/{note_id}"
        return None
    return None


def fmt_evidence(c: dict, max_chars: int = 200) -> str:
    """Render one evidence comment as a Feishu-friendly quote line."""
    text = shorten(c.get("content", ""), max_chars)
    src = c.get("source", "?")
    like = int(c.get("like", c.get("like_count", 0)))
    like_part = f" 👍{like}" if like else ""
    url = comment_url(c)
    link_part = f" · [查看原文]({url})" if url else " · _原文链接缺失_"
    return f"> 「{text}」  — {src}{like_part}{link_part}"


def pick_evidence(
    m: dict[str, Any],
    raw_user: list[dict[str, Any]],
    user_dict: dict[str, list[str]],
    max_count: int = 4,
    *,
    sentiment_filter: str | None = None,
    min_chars: int = 5,
    max_chars: int = 500,
) -> list[dict[str, Any]]:
    """Select representative user comments for a selling point.

    Filters: low-signal, template rant, length bounds, sentiment.
    Sorting: like-count descending, then content-length ascending.
    Dedup: by normalised text key.
    """
    point = m["selling_point"]
    aliases = user_dict.get(point, [])
    needles = list({point, *aliases})

    # Prefer examples from the gap matrix
    pre_examples = set(
        list(m.get("user_negative_examples", []))
        + list(m.get("user_positive_examples", []))
    )

    pool: list[dict[str, Any]] = []
    seen: set[str] = set()

    for c in raw_user:
        content = c.get("content", "")
        if not content:
            continue
        if is_low_signal(content) or is_template_rant(content):
            continue
        if len(content.strip()) < min_chars or len(content.strip()) > max_chars:
            continue
        if sentiment_filter:
            comment_sent = c.get("sentiment", c.get("rule_sentiment", ""))
            if comment_sent and comment_sent != sentiment_filter:
                continue
        if not any(n.lower() in content.lower() for n in needles if n):
            continue
        dedup_key = normalize_for_dedup(content)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        pool.append(c)

    # Sort: like desc, then content length asc (shorter = punchier)
    pool.sort(key=lambda x: (
        -(int(x.get("like", x.get("like_count", 0)))),
        len(x.get("content", "")),
    ))

    # Boost pre_examples to top
    boost_pool: list[tuple[int, dict]] = [
        (0 if c.get("content", "") in pre_examples else 1, c)
        for c in pool
    ]
    boost_pool.sort(key=lambda t: t[0])
    return [c for _, c in boost_pool[:max_count]]


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
        lines.append(fmt_evidence(e))
    return lines


# ── Post-processing (Feishu paste compatibility) ──

_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def _normalize_table_row(line: str) -> str:
    """Normalise a table row: remove cell-level bold, pad ` | ` spacing."""
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return line
    inner = s[1:-1]
    cells = inner.split("|")
    norm_cells: list[str] = []
    for cell in cells:
        c = cell.strip()
        c = re.sub(r"\*\*(.+?)\*\*", r"\1", c)  # remove cell-level bold
        norm_cells.append(c)
    return "| " + " | ".join(norm_cells) + " |"


def _normalize_table_separator(line: str) -> str:
    """Normalise `|---|---|` → `| --- | --- |`, preserving alignment markers."""
    s = line.strip()
    if not _TABLE_SEP_RE.match(s):
        return line
    inner = s.strip("|")
    parts = [p.strip() for p in inner.split("|")]
    norm_parts = []
    for p in parts:
        if p.startswith(":") and p.endswith(":"):
            norm_parts.append(":---:")
        elif p.startswith(":"):
            norm_parts.append(":---")
        elif p.endswith(":"):
            norm_parts.append("---:")
        else:
            norm_parts.append("---")
    return "| " + " | ".join(norm_parts) + " |"


def _normalize_tables(text: str) -> str:
    """Scan for markdown tables and normalise rows + separators."""
    lines = text.split("\n")
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if _TABLE_LINE_RE.match(line) and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1].strip()):
            if out and out[-1].strip() != "":
                out.append("")
            table_lines = [_normalize_table_row(line), _normalize_table_separator(lines[i + 1])]
            j = i + 2
            while j < n and _TABLE_LINE_RE.match(lines[j]):
                table_lines.append(_normalize_table_row(lines[j]))
                j += 1
            out.extend(table_lines)
            if j < n and lines[j].strip() != "":
                out.append("")
            i = j
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def feishu_postprocess(raw: str) -> str:
    """Clean Markdown so it looks correct when pasted into Feishu.

    Known Feishu MD parser quirks handled:
    1. Fenced code blocks → 4-space indented (Feishu doesn't render ``` blocks)
    2. Adjacent `> 「` evidence quotes need blank lines between them
    3. Tables: cell-level bold removed, alignment padded, spacing normalised
    4. `---` horizontal rules need blank lines on both sides
    5. Trailing whitespace stripped
    6. 3+ consecutive blank lines collapsed to 2
    7. `$$...$$` LaTeX blocks removed
    8. Chinese colons normalised (": " → "：")
    """
    # 1) Fenced code blocks → indented
    def _fenced_to_indent(m: re.Match) -> str:
        body = m.group(1)
        indented = "\n".join("    " + ln for ln in body.strip().split("\n"))
        return indented + "\n"

    raw = re.sub(
        r"^```(?:\w+)?\n(.*?)\n```(?:\n|$)",
        _fenced_to_indent,
        raw,
        flags=re.MULTILINE | re.DOTALL,
    )

    # 2) Blank lines between adjacent evidence quotes
    lines = raw.split("\n")
    out: list[str] = []
    for i, line in enumerate(lines):
        out.append(line)
        if i + 1 < len(lines):
            cur_quote = line.lstrip().startswith("> 「")
            nxt_quote = lines[i + 1].lstrip().startswith("> 「")
            if cur_quote and nxt_quote:
                out.append("")
    raw = "\n".join(out)

    # 3) Table normalisation
    raw = _normalize_tables(raw)

    # 4) `---` needs blank lines on both sides
    raw = re.sub(r"([^\n])\n---\n", r"\1\n\n---\n", raw)
    raw = re.sub(r"\n---\n([^\n])", r"\n---\n\n\1", raw)

    # 5) Strip trailing whitespace
    raw = re.sub(r"[ \t]+\n", "\n", raw)

    # 6) Collapse 3+ blank lines to 2
    raw = re.sub(r"\n{4,}", "\n\n\n", raw)

    # 7) Strip LaTeX blocks
    raw = re.sub(r"\$\$.*?\$\$", "", raw, flags=re.S)

    # 8) Chinese colons
    raw = re.sub(r"([\u4e00-\u9fff]):(?!//)", r"\1：", raw)

    return raw.strip() + "\n"


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
    P("> 附录提供完整的方法论、数据采集明细、以及数据可验证性声明，确保所有结论可溯源、可复核。\n")

    # ---------- Appendix A: GAP framework ----------
    P("### 附录 A：GAP 分析框架\n")
    P("**双轨交叉分析**：将每个卖点按「官方投入度」vs「用户感知度」放入 4 类：\n")
    P("|  | 用户讨论多 | 用户讨论少 |")
    P("|---|---|---|")
    P("| **官方说得多** | ① 渗透成功 / ③ 翻车 | ② 渗透失败 |")
    P("| **官方说得少** | ④ 用户自发心智 | —（信号弱） |")
    P("")
    P("**阈值定义**（来自 `config.yaml` / `gap_matrix.py`）：")
    P(f"- 官方主推：加权得分 ≥ {cfg.threshold_official_high}"
      f"（按来源加权：Slogan=5 / 产品页=4 / 发布会=3 / KOL评测=2 / 默认=1）")
    P(f"- 用户高频：提及量 ≥ {cfg.threshold_user_high_mention}")
    P(f"- 情感正面：≥ {cfg.threshold_sentiment_positive} / "
      f"负面：≤ {cfg.threshold_sentiment_negative}")
    P("")
    P("**抽取方式**：LLM（DeepSeek/OpenAI 兼容）+ 规则词典兜底。")
    P("- 官方轨抽「主动强调的卖点」")
    P("- 用户轨抽「自发提到的特性 + 情感倾向」")
    P("")

    # ---------- Appendix B: Data collection log ----------
    if src_user:
        P("### 附录 B：数据采集明细\n")
        P("#### B.1 官方轨\n")
        P("| 来源 | 条数 | 类型 |")
        P("|---|---|---|")
        for o in raw_official:
            P(f"| {o.get('source', '?')} | 1 | {o.get('type', '?')} |")
        P("")
        P("#### B.2 用户轨\n")
        P("| 平台 | 条数 |")
        P("|---|---|")
        for src, n in src_user.most_common():
            P(f"| {src} | {n} |")
        P("")

    # ---------- Appendix F: Data verifiability ----------
    P("### 附录 F：数据可验证性声明\n")
    P("> 本附录详细说明每条数据的来源验证方式，确保报告中的每一个结论都可溯源。\n")

    P("#### F.1 方法论\n")
    P("**双轨对照分析**：每条官方卖点的抽取按来源类型加权（Slogan=5、产品页=4、发布会=3、KOL评测=2、默认=1），"
      "用户评论用 LLM + 规则词典抽取自发提及的特性和情感倾向。两个轨道交叉比对后按阈值分为 4 类。\n")
    P("所有结论均有原始评论或文案支持，在报告中标注为**用户证据片段**。\n")

    P("#### F.2 审计日志\n")
    P(f"- **报告生成时间**：{today}")
    P(f"- **官方文案数量**：{len(raw_official)} 条")
    P(f"- **用户评论数量**：{len(raw_user)} 条")
    P(f"- **对齐后卖点数量**：{len(gap)} 个")
    has_key = bool(cfg._secret("DEEPSEEK_API_KEY"))
    P(f"- **LLM API 状态**：{'已配置' if has_key else '未配置（降级为规则词典）'}")
    P(f"- **官方加权阈值**：OFFICIAL_HIGH_THRESHOLD = {cfg.threshold_official_high}")
    P(f"- **用户高频阈值**：USER_HIGH_MENTION_THRESHOLD = {cfg.threshold_user_high_mention}")
    P(f"- **情感正/负阈值**：{cfg.threshold_sentiment_positive} / {cfg.threshold_sentiment_negative}")
    P("")

    P("#### F.3 数据采集说明\n")
    P("| 渠道 | 采集方式 | 说明 |")
    P("|---|---|---|")
    P("| 官方文案 | 手动收集（官网 / 发布会 / 公众号 / KOL 评测） | 每条标注 source / type / url / verifiable 字段 |")
    P("| 微博评论 | `mgap fetch weibo` 直抓 `weibo.com/ajax/statuses/buildComments` API | 需 Cookie 认证，仅一级评论 |")
    P("| B站评论 | MediaCrawler search 模式 | Playwright 自动化浏览器，需要时 QR 扫码 |")
    P("| 小红书评论 | MediaCrawler search 模式 | Playwright 自动化浏览器，xsec_token 约 2h 过期 |")
    P("")

    P("#### F.4 已知数据局限\n")
    P("以下渠道在本轮分析中存在覆盖盲区，结论以已采集到的数据为准。\n")
    P("| # | 渠道 | 状态 | 说明 |")
    P("| - | --- | --- | --- |")
    P("| 1 | 微信公众号评论 | ❌ 不覆盖 | 微信生态封闭，需 PC 微信 + Fiddler 抓包，成本过高 |")
    P("| 2 | 微博博文搜索 | ⚠️ 部分 | 公开搜索需 SUBP cookie，未全程启用。通过手工选取 KOL URL 替代 |")
    P("| 3 | 小红书详情页 | ⚠️ 部分 | xsec_token 过期需 QR 重登，detail 模式未覆盖 |")
    P("| 4 | X/Twitter 等海外渠道 | ❌ 不覆盖 | 本报告仅分析国内中文平台 |")
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

"""Render GAP matrix to a self-contained HTML report.

Usage::

    mgap -c config.yaml render --format html
    mgap -c config.yaml render --format both
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from ..config import Config


def _shorten(text: str, max_len: int = 120) -> str:
    import re
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"\[[^\]]{1,8}\]", "", text)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def _category_class(cat: str) -> str:
    if "翻车" in cat:
        return "cat-overturn"
    if "渗透成功" in cat:
        return "cat-success"
    if "渗透失败" in cat:
        return "cat-fail"
    if "用户自发" in cat:
        return "cat-organic"
    return "cat-weak"


def _category_badge(cat: str) -> str:
    if "翻车" in cat:
        return "🚨 翻车"
    if "渗透成功" in cat:
        return "✅ 渗透成功"
    if "渗透失败" in cat:
        return "⚠️ 渗透失败"
    if "用户自发" in cat:
        return "💡 用户自发"
    return "— 信号弱"


def _sent_html(sent: float) -> str:
    if sent >= 0.1:
        return f'<span class="sent-pos">+{sent:.2f}</span>'
    if sent <= -0.2:
        return f'<span class="sent-neg">{sent:+.2f}</span>'
    return f'<span class="sent-neutral">{sent:+.2f}</span>'


def _render_quote_card(text: str) -> str:
    return f'<div class="quote">"{escape(text)}"</div>'


def _dedupe_quotes(quotes: list[str], max_count: int = 3) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in sorted(quotes, key=len):
        s = _shorten(q, 100)
        key = s[:30]
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= max_count:
            break
    return out


def _render_gap_card(
    item: dict[str, Any],
    cat_cls: str,
    badge: str,
    neg_quotes: list[str],
    pos_quotes: list[str],
) -> str:
    sp = item["selling_point"]
    off_score = item["official_weighted_score"]
    off_count = item["official_raw_count"]
    user_total = item["user_total_mentions"]
    pos = item["user_positive"]
    neg = item["user_negative"]
    sent = item["sentiment_score"]

    quotes_html = ""
    if neg_quotes:
        quotes_html += '<div class="quotes-block"><div class="quotes-label sent-neg">⚠️ 用户负向声音</div>'
        for q in neg_quotes:
            quotes_html += _render_quote_card(q)
        quotes_html += "</div>"
    if pos_quotes:
        quotes_html += '<div class="quotes-block"><div class="quotes-label sent-pos">👍 用户正向声音</div>'
        for q in pos_quotes:
            quotes_html += _render_quote_card(q)
        quotes_html += "</div>"

    return f"""
    <div class="gap-card {cat_cls}">
      <div class="gap-card-head">
        <h3>{escape(sp)}</h3>
        <span class="cat-badge {cat_cls}">{badge}</span>
      </div>
      <div class="gap-metrics">
        <div class="m"><span class="m-num">{off_score}</span><span class="m-lbl">官方加权</span></div>
        <div class="m"><span class="m-num">{off_count}</span><span class="m-lbl">官方频次</span></div>
        <div class="m"><span class="m-num">{user_total}</span><span class="m-lbl">用户提及</span></div>
        <div class="m"><span class="m-num"><span class="sent-pos">+{pos}</span>/<span class="sent-neg">-{neg}</span></span><span class="m-lbl">正/负</span></div>
        <div class="m"><span class="m-num">{_sent_html(sent)}</span><span class="m-lbl">情感分</span></div>
      </div>
      {quotes_html}
    </div>
    """


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f6fa; color: #2d3436; line-height: 1.7; }
.container { max-width: 1180px; margin: 0 auto; padding: 40px 24px; }
.header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: white; border-radius: 16px; padding: 48px; margin-bottom: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.12); }
.header h1 { font-size: 30px; margin-bottom: 8px; }
.header .subtitle { font-size: 15px; opacity: 0.85; margin-bottom: 16px; }
.header .meta { font-size: 13px; opacity: 0.75; line-height: 1.9; }
.header .badge { display: inline-block; background: rgba(255,255,255,0.15); color: white; padding: 3px 12px; border-radius: 12px; font-size: 12px; margin-right: 4px; margin-bottom: 4px; }
.section { background: white; border-radius: 12px; padding: 32px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.section h2 { font-size: 22px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 3px solid #0984e3; display: inline-block; }
.section h2 .small { font-size: 14px; font-weight: normal; color: #636e72; margin-left: 8px; }
.metrics { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.metric-card { background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%); border: 1px solid #e1e4e8; border-radius: 12px; padding: 20px 24px; text-align: center; flex: 1; min-width: 140px; }
.metric-card .num { font-size: 36px; font-weight: 700; color: #0984e3; }
.metric-card .label { font-size: 13px; color: #636e72; margin-top: 4px; }
.metric-card.green .num { color: #00b894; }
.metric-card.red .num { color: #d63031; }
.metric-card.yellow .num { color: #f39c12; }
.metric-card.purple .num { color: #9b59b6; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; margin: 2px 4px 2px 0; }
.badge-blue { background: #d6eaf8; color: #1a5276; }
.badge-purple { background: #e8daef; color: #6c3483; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13.5px; }
th { background: #0984e3; color: white; padding: 10px 12px; text-align: left; font-weight: 600; }
td { padding: 8px 12px; border-bottom: 1px solid #eee; }
tr:hover { background: #f1f2f6; }
tr.cat-overturn { background: #ffe5e5; }
tr.cat-success { background: #d4edda; }
tr.cat-fail { background: #fff3cd; }
tr.cat-organic { background: #e8daef; }
tr.cat-weak { background: #f5f5f5; color: #999; }
.sent-pos { color: #00b894; font-weight: 600; }
.sent-neg { color: #d63031; font-weight: 600; }
.sent-neutral { color: #636e72; font-weight: 600; }
.gap-card { background: #fff; border-radius: 10px; padding: 20px; margin-bottom: 16px; border-left: 4px solid #ddd; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.gap-card.cat-overturn { border-left-color: #d63031; background: linear-gradient(135deg, #fff 0%, #ffe5e5 100%); }
.gap-card.cat-success { border-left-color: #00b894; background: linear-gradient(135deg, #fff 0%, #d4edda 100%); }
.gap-card.cat-fail { border-left-color: #fdcb6e; background: linear-gradient(135deg, #fff 0%, #fff3cd 100%); }
.gap-card.cat-organic { border-left-color: #9b59b6; background: linear-gradient(135deg, #fff 0%, #e8daef 100%); }
.gap-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.gap-card-head h3 { font-size: 18px; }
.cat-badge { font-size: 12px; padding: 3px 10px; border-radius: 10px; font-weight: 600; }
.cat-badge.cat-overturn { background: #d63031; color: white; }
.cat-badge.cat-success { background: #00b894; color: white; }
.cat-badge.cat-fail { background: #fdcb6e; color: #856404; }
.cat-badge.cat-organic { background: #9b59b6; color: white; }
.cat-badge.cat-weak { background: #b2bec3; color: white; }
.gap-metrics { display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.gap-metrics .m { background: rgba(255,255,255,0.7); padding: 8px 14px; border-radius: 8px; text-align: center; min-width: 80px; }
.gap-metrics .m-num { display: block; font-size: 18px; font-weight: 700; color: #2d3436; }
.gap-metrics .m-lbl { display: block; font-size: 11px; color: #636e72; margin-top: 2px; }
.quotes-block { margin-top: 10px; }
.quotes-label { font-size: 12px; font-weight: 600; margin-bottom: 4px; }
.quote { background: rgba(255,255,255,0.9); border-left: 3px solid #b2bec3; padding: 8px 12px; margin: 4px 0; font-size: 12.5px; color: #555; border-radius: 0 6px 6px 0; }
.toc { background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 24px; }
.toc h3 { margin-bottom: 12px; font-size: 16px; }
.toc a { display: inline-block; margin: 4px 8px 4px 0; padding: 4px 12px; background: white; border-radius: 14px; font-size: 13px; color: #0984e3; text-decoration: none; border: 1px solid #e1e4e8; }
.toc a:hover { background: #0984e3; color: white; }
@media (max-width: 768px) { .gap-metrics .m { flex: 1; min-width: 70px; } }
"""


def render_html(
    config_path: str | Path,
    matrix_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> str:
    cfg = Config(config_path)
    if matrix_path is None and cfg.outputs:
        matrix_path = Path(cfg.outputs) / "gap_matrix.json"
    if output_path is None and cfg.outputs:
        output_path = Path(cfg.outputs) / "report.html"

    if not matrix_path or not Path(matrix_path).exists():
        raise FileNotFoundError(f"gap_matrix.json not found: {matrix_path}")

    gap = json.loads(Path(matrix_path).read_text(encoding="utf-8"))
    raw_official = json.loads(cfg.raw_official.read_text(encoding="utf-8")) if cfg.raw_official else []
    raw_user = json.loads(cfg.raw_user.read_text(encoding="utf-8")) if cfg.raw_user else []
    brand = cfg.brand_name
    project_name = cfg.project_name
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Source distribution
    src_user = Counter(u.get("source", "未知") for u in raw_user)
    src_official = Counter(o.get("source", "未知") for o in raw_official)

    # Group items by category
    groups: dict[str, list[dict]] = {
        "翻车": [], "渗透成功": [], "渗透失败": [], "用户自发": [], "弱": [],
    }
    for item in gap:
        c = item["category"]
        if "翻车" in c:
            groups["翻车"].append(item)
        elif "渗透成功" in c:
            groups["渗透成功"].append(item)
        elif "渗透失败" in c:
            groups["渗透失败"].append(item)
        elif "用户自发" in c:
            groups["用户自发"].append(item)
        else:
            groups["弱"].append(item)

    # Matrix table rows
    rows = ""
    for item in gap:
        sp = item["selling_point"]
        c = item["category"]
        cls = _category_class(c)
        sent = item["sentiment_score"]
        rows += f"""<tr class="{cls}">
          <td><strong>{escape(sp)}</strong></td>
          <td>{item['official_weighted_score']}</td>
          <td>{item['official_raw_count']}</td>
          <td>{item['user_total_mentions']}</td>
          <td><span class="sent-pos">+{item['user_positive']}</span> / <span class="sent-neg">-{item['user_negative']}</span></td>
          <td>{_sent_html(sent)}</td>
          <td>{_category_badge(c)}</td>
        </tr>
        """

    # Section cards
    def _render_section(items: list[dict]) -> str:
        parts: list[str] = []
        for item in items:
            cat = item["category"]
            neg_quotes = _dedupe_quotes(item.get("user_negative_examples", []), max_count=2)
            pos_quotes = _dedupe_quotes(item.get("user_positive_examples", []), max_count=2)
            parts.append(
                _render_gap_card(item, _category_class(cat), _category_badge(cat), neg_quotes, pos_quotes)
            )
        return "".join(parts)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(project_name)} · GAP 分析报告</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>📊 {escape(project_name)} · 营销宣发 GAP 分析报告</h1>
  <div class="subtitle">官方 messaging vs 用户感知 · 双轨对照框架</div>
  <div class="meta">
    分析时间：{today}<br>
    <span class="badge">官方轨：{len(raw_official)} 条</span>
    <span class="badge">用户轨：{len(raw_user)} 条</span>
    <span class="badge">对齐卖点：{len(gap)} 个</span>
    <span class="badge">流水线：mgap fetch + mgap analyze</span>
  </div>
</div>

<div class="toc">
  <h3>📑 报告导航</h3>
  <a href="#data">① 数据采集</a>
  <a href="#matrix">② GAP 矩阵</a>
  <a href="#overturn">③ 翻车点</a>
  <a href="#success">④ 渗透成功</a>
  <a href="#fail">⑤ 渗透失败</a>
  <a href="#organic">⑥ 用户自发心智</a>
</div>

<div class="section" id="data">
  <h2>① 数据采集 <span class="small">真实双轨数据</span></h2>
  <div class="metrics">
    <div class="metric-card"><div class="num">{len(raw_official)}</div><div class="label">官方文案</div></div>
    <div class="metric-card green"><div class="num">{len(raw_user)}</div><div class="label">用户评论</div></div>
    <div class="metric-card purple"><div class="num">{len(gap)}</div><div class="label">对齐卖点</div></div>
  </div>
  <h3 style="margin-top:20px;font-size:15px;">官方轨来源</h3>
  <div style="margin:8px 0;">{' '.join(f'<span class="badge badge-purple">{escape(s)}: {c}</span>' for s, c in src_official.most_common())}</div>
  <h3 style="margin-top:16px;font-size:15px;">用户轨来源</h3>
  <div style="margin:8px 0;">{' '.join(f'<span class="badge badge-blue">{escape(s)}: {c}</span>' for s, c in src_user.most_common())}</div>
</div>

<div class="section" id="matrix">
  <h2>② GAP 矩阵总览 <span class="small">{len(gap)} 个卖点 · 按 4 类涂色</span></h2>
  <table>
    <thead>
      <tr>
        <th>卖点</th><th>官方加权</th><th>官方频次</th><th>用户提及</th><th>用户正/负</th><th>情感分</th><th>分类</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</div>

<div class="section" id="overturn">
  <h2>🚨 ③ 翻车 <span class="small">{len(groups['翻车'])} 个</span></h2>
  {_render_section(groups['翻车']) or '<p style="color:#999">本轮无翻车点。</p>'}
</div>

<div class="section" id="success">
  <h2>✅ ④ 渗透成功 <span class="small">{len(groups['渗透成功'])} 个</span></h2>
  {_render_section(groups['渗透成功']) or '<p style="color:#999">本轮无渗透成功点。</p>'}
</div>

<div class="section" id="fail">
  <h2>⚠️ ⑤ 渗透失败 <span class="small">{len(groups['渗透失败'])} 个</span></h2>
  {_render_section(groups['渗透失败']) or '<p style="color:#999">无</p>'}
</div>

<div class="section" id="organic">
  <h2>💡 ⑥ 用户自发心智 <span class="small">{len(groups['用户自发'])} 个</span></h2>
  {_render_section(groups['用户自发']) or '<p style="color:#999">无</p>'}
</div>

<div class="section" style="text-align:center;color:#636e72;font-size:13px;">
  <p>📊 数据流水线：<strong>mgap fetch</strong> (crawlers) → <strong>mgap analyze</strong> (extract + matrix + render)</p>
  <p style="margin-top:8px;">generated by <strong>marketing-gap-analyzer</strong> · all data verifiable</p>
</div>

</div>
</body>
</html>"""

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        size_kb = len(html.encode("utf-8")) / 1024
        print(f"HTML report written to {out}")
        print(f"Size: {size_kb:.1f} KB")

    return html

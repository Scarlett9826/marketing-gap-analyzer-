# marketing-gap-analyzer

> **End-to-end competitor marketing GAP analysis tool.**  
> Fetch raw user comments from Weibo / Bilibili / Xiaohongshu / Zhihu / Douyin,
> extract what competitors push officially, cross-reference the two, and produce a
> Feishu-ready Markdown (or HTML) report — all from a single CLI.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

---

## Why

Product Marketing Managers spend weeks combing through competitor press releases,
KOL reviews, and social comments to figure out **what their next product
messaging should be**.

This tool automates the full pipeline: data collection → official selling-point
extraction → user voice + sentiment analysis → GAP matrix classification →
rendered report.

---

## The 4 Categories

| | Users talk about it a lot | Users barely mention it |
|---|---|---|
| **Competitor pushes it hard** | ① Resonance ✅ / ③ Backfire 🚨 | ② Invisible ⚠️ |
| **Competitor barely mentions it** | ④ User-driven 💡 | — Weak signal |

| Category | Meaning | What to do |
|---|---|---|
| **① Resonance** | Competitor landed the message; users repeat it positively | Match or counter with a stronger claim |
| **② Invisible** | Competitor wasted marketing budget; message didn't land | Avoid the same mistake; investigate why |
| **③ Backfire** | Users heard it and hate it; product reality ≠ marketing | Your competitive opening |
| **④ User-driven** | Users discuss it without prompting; reflects real product experience | Genuine value — claim or fix |

---

## Quickstart

### 1. Install

```bash
pip install -e .
# pip install -r requirements.txt  (if you have one)
```

Optional — for Bilibili / Xiaohongshu crawling:

```bash
git clone https://github.com/NanmiCoder/MediaCrawler
cd MediaCrawler && pip install -r requirements.txt && playwright install chromium
export MEDIACRAWLER_HOME=/path/to/MediaCrawler
```

### 2. Set up API key (recommended)

```bash
cp .env.example .env
# Edit .env with your DeepSeek/OpenAI key
# Without an LLM key, the tool falls back to dictionary matching (demo only).
```

### 3. Fetch user comments

```bash
# Weibo: prepare a cookie file first (see docs/data-collection.md)
echo "https://weibo.com/7928198622/QBGttc1BD" > urls.txt
mgap fetch weibo --urls urls.txt --cookie weibo_cookie.json -o data/raw_user.json
```

### 4. Prepare official marketing copy

Create `data/raw_official.json` with your competitor's official copy:
```json
[
  {
    "source": "Product Page",
    "type": "产品页文案",
    "content": "Full marketing copy text...",
    "url": "https://example.com/product",
    "verifiable": "fetched 2026-05-26 status 200"
  }
]
```

### 5. Configure and run

Copy [`config/default.yaml`](config/default.yaml) to `config.yaml`, set the
project name / brand, and provide selling-point dictionaries (required for
rule-based fallback).

```bash
mgap -c config.yaml analyze
```

This runs: `extract-official → extract-user → gap-matrix → render`.

Output goes to your `paths.outputs` directory (default `output/`):
- `official_selling_points.json`
- `user_voice.json`
- `gap_matrix.json`
- `report.md` (Feishu-ready Markdown)

---

## CLI

```
mgap [-c CONFIG] [COMMAND] [-o OUTPUT]

Commands:
  analyze                     Run full pipeline (default)
  extract-official            Step 1 — official selling points
  extract-user                Step 2 — user voice
  gap-matrix                  Step 3 — classification matrix
  render                      Step 4 — report (--format feishu|html|both)

  fetch weibo                 Collect Weibo first-level comments
  fetch bilibili              Search + collect Bilibili comments
  fetch xiaohongshu           Search + collect Xiaohongshu comments
  fetch zhihu                 Search + collect Zhihu comments
  fetch douyin                Search + collect Douyin comments

Examples:
  mgap                                                # uses ./config.yaml
  mgap -c examples/huawei-pura-x-max/config.yaml analyze
  mgap -c config.yaml render --format both            # MD + HTML
  mgap fetch weibo --urls urls.txt --cookie cookie.json -o data/raw_user.json
```

---

## Full Example

See the [Huawei Pura X Max case study](examples/huawei-pura-x-max/) for a
complete walkthrough with real data (962 user comments, 39 official documents,
40 classified selling points).

---

## Limitations

- **WeChat public-account comments**: not collected (no public API; requires
  PC WeChat + Fiddler/mitmproxy capture).
- **Weibo keyword search**: requires a SUBP cookie that expires quickly.
  Current workflow uses manually selected KOL post URLs.
- **Xiaohongshu detail mode**: requires fresh `xsec_token` values (~2-hour
  lifetime). QR re-login needed.
- **LLM fallback**: without `DEEPSEEK_API_KEY`, extraction degrades to
  hardcoded dictionary matching. **Do not present output as a real analysis**
  without LLM — the dictionary has no product-specific aliases until you
  configure them.

---

## Documentation

- [`docs/methodology.md`](docs/methodology.md) — GAP framework explanation
- [`docs/architecture.md`](docs/architecture.md) — Module structure & data flow
- [`docs/customization.md`](docs/customization.md) — Customization guide
- [`docs/data-collection.md`](docs/data-collection.md) — Cookie setup, rate limits,
  MediaCrawler integration

---

## License

MIT — see [LICENSE](LICENSE).

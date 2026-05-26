# marketing-gap-analyzer

> Compare what competitors say vs. what users actually talk about.
> Identify which selling points penetrate, which backfire, and which reflect
> genuine user needs.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

---

## Why

Product Marketing Managers spend weeks combing through competitor press releases,
KOL reviews, and social comments to figure out **what their next product
messaging should be**.

This tool automates the core analysis: cross-reference competitor official
selling points against real user discussions from social platforms, and classify
every selling point into 4 actionable categories.

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
# or
pip install -r requirements.txt
```

### 2. Prepare Data

Two JSON files are required.

**`data/raw_official.json`** — competitor's official marketing copy:
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

**`data/raw_user.json`** — user comments from social platforms:
```json
[
  {
    "source": "微博评论",
    "post_id": "5103030394562112",
    "note_id": "数码闲聊站",
    "content": "这价格也太贵了..."
  }
]
```

### 3. Configure

Copy [`config/default.yaml`](config/default.yaml) to your project and customize.
At minimum, set the project name, brand, and selling-point dictionaries.

### 4. (Optional) Set LLM Key

```bash
cp .env.example .env
# Edit .env with your DeepSeek/OpenAI key
```

Without an LLM key, the tool falls back to dictionary keyword matching.

### 5. Run

```bash
mgap -c config.yaml analyze
```

This runs the full 4-step pipeline:

1. Extract official selling points
2. Extract user voice (mentions + sentiment)
3. Build GAP matrix (cross-reference & classify)
4. Render Feishu Markdown report

Output goes to your configured `outputs/` directory.

---

## CLI

```
mgap [-c CONFIG] [COMMAND] [-o OUTPUT]

Commands:
  analyze            Run full pipeline (default)
  extract-official   Step 1 only — official selling points
  extract-user       Step 2 only — user voice
  gap-matrix         Step 3 only — classification matrix
  render             Step 4 only — Feishu Markdown report

Examples:
  mgap                                    # uses ./config.yaml, runs analyze
  mgap -c examples/foo/config.yaml
  mgap -c config.yaml extract-user -o out/voice.json
```

---

## Full Example

See the [Huawei Pura X Max case study](examples/huawei-pura-x-max/) for a
complete walkthrough with real data (962 user comments, 39 official documents,
40 classified selling points).

---

## Data Collection

The pipeline is data-source-agnostic — it works with any platform as long as
you provide the JSON files. For Chinese social media we recommend:

- **Weibo**: [1dyer/weibo-comment-crawler](https://github.com/1dyer/weibo-comment-crawler)
- **Bilibili / Xiaohongshu**: [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)

---

## Customization

See [docs/customization.md](docs/customization.md) for detailed guides on:

- Adapting to a new product category
- Adjusting thresholds for your data volume
- Adding new source platforms
- Writing a custom renderer

---

## Documentation

- [`docs/methodology.md`](docs/methodology.md) — GAP framework explanation
- [`docs/architecture.md`](docs/architecture.md) — Module structure & data flow
- [`docs/customization.md`](docs/customization.md) — Customization guide

---

## License

MIT — see [LICENSE](LICENSE).

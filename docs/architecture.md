# Architecture

## Directory Structure

```
marketing-gap-analyzer/
├── src/marketing_gap/
│   ├── __init__.py
│   ├── cli.py                 # CLI entry point (mgap command)
│   ├── config.py              # Config loader (YAML + .env)
│   ├── extractors/
│   │   ├── official.py        # Official selling point extraction
│   │   └── user.py            # User voice extraction
│   ├── analysis/
│   │   └── gap_matrix.py      # GAP matrix classification
│   ├── renderers/
│   │   └── feishu_md.py       # Feishu Markdown report
│   └── utils/
│       ├── llm.py             # OpenAI-compatible chat JSON helper
│       └── text.py            # Text helpers (shorten, alias matching)
├── config/
│   └── default.yaml           # Default configuration template
├── examples/
│   └── huawei-pura-x-max/     # Complete case study
├── tests/                     # Pytest unit tests
├── docs/
│   ├── methodology.md         # GAP framework explanation
│   ├── architecture.md        # This file
│   └── customization.md       # Customization guide
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
└── LICENSE
```

## Module Dependency

```
cli.py
  ├── config.py            ← .env + config.yaml
  ├── utils/llm.py         ← config.py
  ├── extractors/official.py  ← config.py + utils/llm.py
  ├── extractors/user.py      ← config.py + utils/llm.py
  ├── analysis/gap_matrix.py  ← config.py
  └── renderers/feishu_md.py  ← config.py + utils/text.py
```

## Data Flow

```
                  ┌─────────────────────┐
                  │  raw_official.json   │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  extract_official() │──→ official_selling_points.json
                  │  LLM / dict fallback│
                  └─────────────────────┘
                             │
                             │   ┌─────────────────────┐
                             │   │  raw_user.json       │
                             │   └──────────┬──────────┘
                             │              │
                             │              ▼
                             │   ┌─────────────────────┐
                             │   │  extract_user()     │──→ user_voice.json
                             │   │  LLM / dict fallback│
                             │   └─────────────────────┘
                             │              │
                             └──────┬───────┘
                                    ▼
                         ┌─────────────────────┐
                         │  run_gap_analysis() │──→ gap_matrix.json
                         │  threshold classify │
                         └─────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  render()           │──→ report.md
                         │  Feishu Markdown    │
                         └─────────────────────┘
```

## Config Priority

Settings are loaded in this order (later overrides earlier):
1. Built-in Python defaults (sentiment words, source weights)
2. `.env` file (LLM secrets)
3. `config.yaml` (project-specific settings + selling-point dictionaries)
4. Command-line `--output` overrides for individual steps

## Data Format Specifications

### `raw_official.json` (input)
```json
[
  {
    "source": "源名称",
    "type": "Slogan | 产品页文案 | 发布会现场 | 深度长文 | 卖点拆解 | KOL评测",
    "content": "完整文案内容",
    "url": "https://...",
    "verifiable": "验证方式"
  }
]
```

### `raw_user.json` (input)
```json
[
  {
    "source": "微博评论 | B站评论 | 小红书评论 | ...",
    "post_id": "唯一评论 ID",
    "note_id": "原帖/视频/笔记 ID",
    "content": "评论内容"
  }
]
```

### `gap_matrix.json` (output)
```json
[
  {
    "selling_point": "卖点名称",
    "official_weighted_score": 32,
    "official_raw_count": 13,
    "user_total_mentions": 104,
    "user_positive": 6,
    "user_negative": 21,
    "sentiment_score": -0.14,
    "penetration_ratio": 3.25,
    "category": "③ 翻车",
    "user_negative_examples": ["..."],
    "user_positive_examples": ["..."]
  }
]
```

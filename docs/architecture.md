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
│   │   ├── feishu_md.py       # Feishu Markdown report
│   │   └── html.py            # HTML report (optional)
│   └── utils/
│       └── text_clean.py      # Text cleaning utilities
├── config/
│   └── default.yaml           # Default configuration template
├── examples/
│   └── huawei-pura-x-max/     # Complete case study
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
  ├── config.py          ← .env + config.yaml
  ├── extractors/official.py
  │     └── config.py (dictionaries, weights)
  ├── extractors/user.py
  │     └── config.py (dictionaries, sentiment words)
  ├── analysis/gap_matrix.py
  │     └── config.py (thresholds)
  └── renderers/feishu_md.py
        └── config.py (project name, paths)
```

## Data Flow

```
                   ┌─────────────────────┐
                   │  raw_official.json   │
                   │  (JSON array)         │
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
                              │   │  (JSON array)         │
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
1. Built-in Python defaults (in `config.py`)
2. `.env` file (secrets like API keys)
3. `config.yaml` (project-specific settings)
4. Command-line arguments

## Data Format Specifications

### raw_official.json (input)
```json
[
  {
    "source": "源名称",
    "type": "来源类型 (Slogan/产品页文案/发布会/...)", 
    "content": "完整文案内容",
    "url": "https://...",
    "verifiable": "验证方式"
  }
]
```

### raw_user.json (input)
```json
[
  {
    "source": "平台名称",
    "post_id": "唯一标识",
    "note_id": "笔记/视频ID",
    "content": "评论内容"
  }
]
```

### gap_matrix.json (output)
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
    "category": "③ 翻车",
    "user_negative_examples": ["..."],
    "user_positive_examples": ["..."]
  }
]
```

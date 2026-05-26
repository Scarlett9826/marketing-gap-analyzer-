# Customization Guide

## 1. Analyze a Different Product

Create a new directory with your own data:

```
my-product-analysis/
├── data/
│   ├── raw_official.json     # Competitor docs
│   └── raw_user.json         # User comments
├── config.yaml               # Your config
└── output/                   # Generated reports
```

Copy `config/default.yaml` (or `examples/huawei-pura-x-max/config.yaml`) and update:

```yaml
project:
  name: "Your Product"
  brand: "BrandName"          # Used in report copy ("BrandName invested X points...")
  description: "Category positioning"
  data_date: "2026-01-01"

paths:
  raw_user: "data/raw_user.json"
  raw_official: "data/raw_official.json"
  outputs: "output"
```

## 2. Adjust Thresholds

Pick thresholds based on data volume:

| Data volume | OFFICIAL_HIGH | USER_HIGH |
|---|---|---|
| 100-500 comments | 3 | 2 |
| 500-2000 | 5 | 4 |
| 2000+ | 8 | 8 |

## 3. Customize Selling-Point Dictionaries

Dictionaries are now defined per-project in `config.yaml` — no code edits needed.

```yaml
dictionaries:
  official_selling_points:
    "卖点A": ["关键词1", "关键词2"]
    "卖点B": ["关键词3"]
  user_selling_points:
    "电池续航": ["电池", "续航", "电量", "耗电"]
    "价格":     ["价格", "贵", "便宜", "性价比"]
```

For long lists, store dictionaries in a separate YAML file and reference it:

```yaml
dictionaries:
  official_selling_points: dictionaries/official.yaml
  user_selling_points:     dictionaries/user.yaml
```

## 4. Override Sentiment Words

Built-in Chinese sentiment words cover common cases. To override:

```yaml
dictionaries:
  positive_words: ["好", "棒", "顶", "丝滑"]
  negative_words: ["差", "烂", "翻车", "拉胯"]
```

## 5. Adjust Source Weights

```yaml
official:
  source_weights:
    Slogan: 5
    产品页文案: 4
    发布会现场: 3
    自定义来源类型: 2
    default: 1
```

## 6. Use LLM Extraction

Set your API key in `.env` next to `config.yaml`:

```env
DEEPSEEK_API_KEY=sk-your-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

Compatible providers (OpenAI chat-completions API):

| Provider | LLM_BASE_URL | LLM_MODEL |
|---|---|---|
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` |
| OpenAI | `https://api.openai.com` | `gpt-4o-mini` |
| Moonshot | `https://api.moonshot.cn` | `moonshot-v1-8k` |

Without an API key, the tool falls back to dictionary matching.

## 7. Add a New Platform

Add a fresh source name to `raw_user.json`:

```json
{
  "source": "新平台名称",
  "post_id": "unique_id",
  "note_id": "parent_id",
  "content": "评论内容"
}
```

Then add a link template in `src/marketing_gap/renderers/feishu_md.py` →
`PLATFORM_LINK_TEMPLATES`:

```python
PLATFORM_LINK_TEMPLATES["新平台名称"] = lambda note, post: f"https://example.com/{note}/{post}"
```

## 8. Custom Renderer

Drop a new module in `src/marketing_gap/renderers/` exposing a `render(config_path, ...)`
function. Wire it up by importing in `cli.py` or by calling it directly from your own script.

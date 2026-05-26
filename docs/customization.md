# Customization Guide

## 1. Analyze a Different Product

Create a new directory with your own data:

```
my-product-analysis/
├── data/
│   ├── raw_official.json     # Your competitor's docs
│   └── raw_user.json         # Your user comments
├── config.yaml               # Your config
└── output/                   # Generated reports
```

Copy `examples/huawei-pura-x-max/config.yaml` and update:

```yaml
project:
  name: "品牌名称 产品型号"
  description: "品类定位"
  data_date: "2026-12-01"

paths:
  raw_user: "data/raw_user.json"
  raw_official: "data/raw_official.json"
  outputs: "output"
```

## 2. Adjust Thresholds

Based on your data volume:

| Data volume | OFFICIAL_HIGH | USER_HIGH |
|---|---|---|
| 100-500 comments | 3 | 2 |
| 500-2000 | 5 | 4 |
| 2000+ | 8 | 8 |

## 3. Customize Dictionaries

Edit `src/marketing_gap/config.py`:

### Official selling point dictionary
Update `DEFAULT_OFFICIAL_DICT` — each entry maps a standardized selling point name to its keyword aliases:

```python
DEFAULT_OFFICIAL_DICT = {
    "新卖点名称": ["关键词1", "关键词2", "关键词3"],
}
```

### User selling point dictionary
Update `DEFAULT_USER_DICT` — same structure, but user-facing language:

```python
DEFAULT_USER_DICT = {
    "电池续航": ["电池", "续航", "电量", "耗电"],
}
```

### Sentiment words
Update `DEFAULT_POSITIVE_WORDS` and `DEFAULT_NEGATIVE_WORDS`:

```python
DEFAULT_POSITIVE_WORDS = {"好", "快", "强", "喜欢", ...}
DEFAULT_NEGATIVE_WORDS = {"差", "慢", "弱", "讨厌", ...}
```

## 4. Add a New Platform

1. Add your crawler in `src/marketing_gap/crawlers/`
2. Output data in the same `raw_user.json` format:
   ```json
   {
     "source": "新平台名称",
     "post_id": "unique_id",
     "note_id": "parent_id",
     "content": "评论内容"
   }
   ```
3. Update `feishu_md.py` to add evidence links for the new platform

## 5. Add Source Weights

In `config.yaml`:
```yaml
official:
  source_weights:
    新来源类型: 5
    default: 1
```

## 6. Use LLM Extraction

Set your API key in `.env`:
```env
DEEPSEEK_API_KEY=sk-your-key
```

Without LLM, the tool falls back to rule-based keyword matching (less accurate but works offline).

## 7. Create a Custom Renderer

Subclass or copy the renderer in `src/marketing_gap/renderers/`. The renderer receives the gap_matrix and returns a string.

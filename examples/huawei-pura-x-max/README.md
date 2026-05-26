# Huawei Pura X Max — Complete Case Study

This directory contains a complete GAP analysis for the **Huawei Pura X Max**, a foldable flagship phone launched in April 2026.

## Data

| Source | Count | Method |
|---|---|---|
| Official documents | 39 | Product page, launch event, KOL reviews, media articles |
| User comments | 962 | Weibo (549), Bilibili (337), Xiaohongshu (76) |
| Classified selling points | 40 | Across 4 GAP categories |

## Quick Results

### Top User-Discussed Points
| Point | Mentions | Sentiment |
|---|---|---|
| Price | 263 | -0.49 (very negative) |
| Brand/Huawei | 154 | -0.29 |
| Wide Foldable Form | 104 | -0.14 |
| vs Apple | 102 | -0.28 |
| vs Xiaomi | 84 | -0.27 |

### Category Distribution
- ④ User-driven: 19 points
- ② Invisible: 6 points
- ① Resonance: 4 points
- ③ Backfire: featured in report

## Run It

```bash
mgap --config config.yaml analyze
```

## Files

| File | Description |
|---|---|
| `config.yaml` | Analysis configuration |
| `data/raw_official.json` | 39 competitor marketing documents |
| `data/raw_user.json` | 962 real user comments |
| `output/report.md` | Generated Feishu Markdown report |
| `output/gap_matrix.json` | Full classification matrix |

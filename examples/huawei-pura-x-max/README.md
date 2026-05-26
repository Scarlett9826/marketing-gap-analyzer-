# Huawei Pura X Max — Complete Case Study

A full GAP analysis for the **Huawei Pura X Max**, a foldable flagship launched
April 2026. Demonstrates how to use `marketing-gap-analyzer` end-to-end.

## Data

| Source | Count |
|---|---|
| Official documents | 39 (product page, launch event, KOL reviews, media articles) |
| User comments | 962 (Weibo 549, Bilibili 337, Xiaohongshu 76) |

Comment crawling tools used:
- Weibo: [1dyer/weibo-comment-crawler](https://github.com/1dyer/weibo-comment-crawler)
- Bilibili / Xiaohongshu: [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)

## Run

```bash
mgap -c config.yaml analyze
```

This regenerates everything in `output/`:

| File | Purpose |
|---|---|
| `official_selling_points.json` | Step 1 output — ranked official selling points |
| `user_voice.json` | Step 2 output — user mentions + sentiment per topic |
| `gap_matrix.json` | Step 3 output — full classification matrix |
| `report.md` | Step 4 output — Feishu Markdown report |

## Files in This Directory

| File | Description |
|---|---|
| `config.yaml` | Analysis config + product-specific dictionaries |
| `data/raw_official.json` | 39 competitor marketing documents |
| `data/raw_user.json` | 962 anonymized user comments |
| `output/report.md` | Pre-generated Feishu Markdown report |

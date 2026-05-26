# marketing-gap-analyzer

> **Competitor marketing GAP analysis tool** — compare what competitors say vs. what users actually talk about. Identify which selling points penetrate, which backfire, and which are genuine user needs.

---

## Why

Product Marketing Managers (PMMs) spend weeks manually combing through competitor press releases, KOL reviews, and social comments to figure out: **"What should our next product messaging be?"**

This tool automates the core analysis: align competitor official selling points against real user discussions from social platforms, and classify every selling point into 4 actionable categories.

---

## The 4 Categories

| | Users talk about it a lot | Users barely mention it |
|---|---|---|
| **Competitor pushes it hard** | ① Resonance ✅ / ③ Backfire 🚨 | ② Invisible ⚠️ |
| **Competitor barely mentions it** | ④ User-driven 💡 | — Weak signal |

**Actionable insight per category:**
- **① Resonance**: The competitor landed this point. Match or counter.
- **② Invisible**: They wasted marketing spend. Don't make the same mistake.
- **③ Backfire**: Real product gap. Your opportunity to win on this dimension.
- **④ User-driven**: Genuine user needs they're ignoring. Claim this territory.

---

## Quickstart

### Prerequisites
- Python 3.10+
- `pip install pyyaml requests`

### 1. Prepare your data

You need two JSON files:

**`raw_official.json`** — competitor's official marketing copy:
```json
[
  {
    "source": "华为商城产品页",
    "type": "产品页文案",
    "content": "华为Pura X Max搭载全新鸿蒙HarmonyOS 6系统...",
    "url": "https://example.com/product",
    "verifiable": "webfetch 验证 URL 返回200"
  }
]
```

**`raw_user.json`** — user comments from social platforms:
```json
[
  {
    "source": "微博评论",
    "post_id": "123456",
    "note_id": "789012",
    "content": "这个价格也太贵了..."
  }
]
```

### 2. Create a config file

Copy `examples/huawei-pura-x-max/config.yaml` and customize the project name and thresholds.

### 3. Run the full pipeline

```bash
mgap --config your-project/config.yaml analyze
```

This runs 4 steps:
1. Extract official selling points from your documents
2. Extract user voice from comments  
3. Cross-reference → GAP matrix
4. Render → Feishu-friendly Markdown report

Output goes to `your-project/output/`.

---

## Full Example

See the [Huawei Pura X Max case study](examples/huawei-pura-x-max/) for a complete walkthrough with real data (962 user comments, 39 official documents).

---

## Commands

| Command | Description |
|---|---|
| `mgap -c config.yaml analyze` | Full pipeline (default) |
| `mgap -c config.yaml extract-official` | Step 1 only |
| `mgap -c config.yaml extract-user` | Step 2 only |
| `mgap -c config.yaml gap-matrix` | Step 3 only |
| `mgap -c config.yaml render` | Step 4 only |

---

## Data Collection

The analysis pipeline is data-source-agnostic — it works with any platform data as long as you provide the JSON files.

For Chinese social media collection, we recommend:
- **Weibo**: [1dyer/weibo-comment-crawler](https://github.com/1dyer/weibo-comment-crawler)
- **Bilibili / Xiaohongshu**: [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)

---

## Customization

- **Selling point dictionaries**: Edit `config.py`'s `DEFAULT_OFFICIAL_DICT` / `DEFAULT_USER_DICT` for your product category
- **Thresholds**: Adjust in `config.yaml` (`OFFICIAL_HIGH_THRESHOLD`, `USER_HIGH_MENTION_THRESHOLD`, etc.)
- **Source weights**: Customize per-source weights in `config.yaml`

---

## License

MIT

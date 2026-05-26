# Data Collection Guide

This document covers how to acquire raw comment data for the three supported
platforms. The `mgap fetch` CLI wraps the logic described here.

---

## Weibo

### Cookie acquisition

1. Open Chrome DevTools → **Network** tab.
2. Navigate to `https://weibo.com/` and log in if needed.
3. Find any XHR request to `weibo.com/ajax/...` (e.g., `statuses/show`).
4. Copy the full `Cookie:` request header value.
5. Save as a JSON file (e.g. `weibo_cookie.json`):

```json
{
  "Cookie": "SUB=_2A...; SUBP=...; ALF=...",
  "User-Agent": "Mozilla/5.0 ...",
  "x-xsrf-token": "..."
}
```

Only the `Cookie` key is strictly required; `User-Agent` defaults to a
modern Chrome value if omitted.

### Running

```bash
mgap fetch weibo --urls urls.txt --cookie weibo_cookie.json -o data/raw_user.json
```

`urls.txt` should contain one weibo post URL per line (lines starting with
`#` are skipped).

### Rate limits

- ``--sleep`` defaults to **0.6 s** between requests — do not lower below 0.3.
- ``--max-comments`` defaults to **800** per post (prevents infinite crawl on
  viral threads).
- 100+ comment thresholds trigger an extra 4 s delay.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Empty `data` payloads | Cookie expired | Re-export from DevTools |
| HTTP 403 | IP / rate-limit block | Wait 10 min, reduce concurrency |
| `max_id=0` stops too early | Not a bug — server has no more pages | Verify with browser |

---

## Bilibili

Uses the third-party `MediaCrawler` project. Install:

```bash
git clone https://github.com/NanmiCoder/MediaCrawler
cd MediaCrawler
pip install -r requirements.txt
playwright install chromium
```

Then set `MEDIACRAWLER_HOME`:

```bash
export MEDIACRAWLER_HOME=/path/to/MediaCrawler
```

### Running

```bash
mgap fetch bilibili --keywords "Pura X Max" -o data/bili_comments.json
```

The first run requires a QR-code scan (weibo login). After that, cookies are
persisted.

---

## Xiaohongshu (RED-Note)

Same MediaCrawler dependency as Bilibili.

### Running

```bash
mgap fetch xiaohongshu --keywords "Pura X Max" -o data/xhs_comments.json
```

### Detail mode

Xiaohongshu rotates `xsec_token` values aggressively (~2-hour lifetime).
Detail-mode crawling (specific note IDs) requires fresh tokens. For ad-hoc
analysis, the search mode covers the top ~120 notes.

---

## Schema Reference

Every `mgap fetch` output file conforms to the same schema so it can be
plugged straight into `config.yaml` as `paths.raw_user`:

```json
[
  {
    "source": "微博评论" | "B站评论" | "小红书评论" | "知乎评论" | "抖音评论",
    "post_id": "299817811233",
    "note_id": "116594336600271",
    "content": "comment text",
    "like": 98,
    "url": "https://...",
    "keyword": "search term"        // optional, present for search-mode
  }
]
```

---

## Verifiability

Every comment record includes a `url` field with a best-effort permalink:

- **Weibo**: `https://weibo.com/{uid}/{bid}#cm{comment_id}` — scrolls to the
  specific comment on the post page.
- **Bilibili**: `https://www.bilibili.com/video/av{vid}/#reply{rpid}` — scrolls
  to the specific reply.
- **Xiaohongshu**: `https://www.xiaohongshu.com/explore/{note_id}` — links to
  the note page; comment anchoring requires `xsec_token` which is not preserved
  by search-mode.

Cookie / token expiry may break older URLs — use the audit log in the report
appendix to retrace.

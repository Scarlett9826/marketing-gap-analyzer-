# GAP Analysis Methodology

## Core Concept

The GAP (Gap Analysis of Positioning) framework is a structured way to compare **what a competitor says about their product** vs. **what users actually talk about**. The gap between these two reveals which marketing investments are working, which are wasted, and where genuine user needs exist.

## The 2×2 Matrix

Every selling point is classified into one of 4 quadrants:

```
                    User mentions HIGH     User mentions LOW
                    ─────────────────      ────────────────
Competitor pushes   │  ① Resonance       │  ② Invisible
      HIGH          │  ✅ 渗透成功        │  ⚠️ 渗透失败
                    │                     │
Competitor pushes   │  ③ Backfire /       │  ④ Weak signal
      LOW           │  ④ User-driven     │  — 信号弱
                    │  💡 用户自发心智    │
```

### ① Resonance (渗透成功)
- **Condition**: Official weighted ≥ threshold AND user mentions ≥ threshold AND sentiment ≥ positive threshold
- **Meaning**: The competitor successfully landed this message. Users accept and repeat it.
- **Action**: Match or counter with a stronger claim.

### ② Invisible (渗透失败)
- **Condition**: Official weighted ≥ threshold AND user mentions < threshold
- **Meaning**: The competitor spent marketing resources but the message didn't reach users.
- **Action**: Either the point doesn't matter to users, or the messaging angle was wrong.
- **Example**: "Kirin 9030 Pro" — official pushed it hard but almost no one mentioned it.

### ③ Backfire (翻车)
- **Condition**: Official weighted >= threshold AND user mentions >= threshold AND sentiment ≤ negative threshold
- **Meaning**: Users heard the message — and they hate it. Product reality doesn't match marketing claims.
- **Action**: Your competitive opportunity. Users are primed to hear a better alternative.
- **Example**: "大阔折叠形态" — Huawei's #1 selling point with highest official investment, yet users complain about it.

### ④ User-driven (用户自发心智)
- **Condition**: Official weighted < threshold AND user mentions ≥ threshold
- **Meaning**: Users are discussing this without being prompted by marketing. It reflects genuine product experience.
- **Action**: This is the real product value. Either claim this territory or address the pain point.
- **Example**: "价格" / "重量" / "应用适配" — all heavily discussed by users but barely pushed by Huawei.

## Threshold Determination

Thresholds are configurable in `config.yaml`:

| Threshold | Default | Meaning |
|---|---|---|
| `OFFICIAL_HIGH_THRESHOLD` | 5 | Minimum weighted score to count as "pushed" |
| `USER_HIGH_MENTION_THRESHOLD` | 4 | Minimum user mentions to count as "high discussion" |
| `SENTIMENT_POSITIVE_THRESHOLD` | 0.1 | Sentiment score ≥ this = positive |
| `SENTIMENT_NEGATIVE_THRESHOLD` | -0.2 | Sentiment score ≤ this = negative |

Adjust these based on your data volume: for smaller datasets (50-200 comments), lower thresholds. For large datasets (1000+), higher thresholds.

## Source Weighting

Not all official documents are equal. A Slogan (weight=5) reflects more marketing intent than a KOL review (weight=2). Weights are applied when aggregating official selling point mentions.

| Source Type | Weight | Rationale |
|---|---|---|
| Slogan / 口号 | 5 | Core marketing message |
| Product page / 产品页 | 4 | Direct marketing investment |
| Launch event / 发布会 | 3 | Major PR push |
| Deep review / 深度长文 | 3 | Influencer engagement |
| KOL review / KOL评测 | 2 | Paid/sponsored |
| Social post / 官方笔记 | 2 | Ongoing engagement |
| Default | 1 | All other sources |

## Data Pipeline

```
Raw Data (JSON) → ① Extract Official Points → ② Extract User Voice
                                            ↓
                                    ③ GAP Matrix
                                            ↓
                                   ④ Report (Markdown)
```

### ① Official Extraction
- Uses LLM (DeepSeek/GPT) to extract top-5 selling points from each document
- Falls back to keyword dictionary matching when no API key is set
- Weighs each mention by document source type

### ② User Voice Extraction
- Uses LLM to extract selling points + sentiment (positive/neutral/negative) from each comment
- Falls back to keyword + sentiment word matching
- Aggregates: total mentions, positive count, neutral count, negative count, sentiment score

### ③ GAP Matrix
- Cross-references official vs. user data
- Applies thresholds to classify each point
- Includes penetration ratio (user mentions / official weight) for relative comparison

### ④ Report
- Renders to Feishu-friendly Markdown
- Sections: TL;DR → Analysis Overview → Detail per Category → Appendix

## Known Limitations

1. **Sentiment accuracy**: Rule-based sentiment can miss sarcasm, irony, and context
2. **Dictionary maintenance**: Product-specific dictionaries need updating per generation
3. **Sample bias**: Results reflect only the platforms you have data from
4. **Temporal effects**: Sentiment can shift rapidly after product launch

# CineMatch: hybrid weight tuning

Generated 2026-11-22 17:49 UTC by `python -m ml.tune`.

## Setup

- Users: 341 | catalogue pool: 936 movies | K = 10
- Per-user temporal split: 60% train / 20% validation / 20% test; relevant = rated >= 4
- Grid step 0.25; weights restricted to content + collab >= 0.3
- Weights were chosen on the validation split only. The test split was used once, afterwards.

## Weights

- Chosen on validation: **content 0.00, collab 0.75, pop 0.25** (validation NDCG@10 0.120)
- Current `.env` defaults: content 0.50, collab 0.30, pop 0.20 (before the adaptive ramp)

## Test results (NDCG@10, 95% bootstrap interval over users)

| Model | NDCG |
|---|---|
| Hybrid, current weights | 0.069 [0.054, 0.084] |
| Hybrid, tuned weights | 0.134 [0.115, 0.156] |
| Popularity baseline | 0.130 [0.110, 0.150] |

Tuned minus current, per user: +0.066 [+0.042, +0.086]. The interval for the difference excludes 0, so the improvement is measurable.

## Validation grid (top 10)

| Weights | Validation NDCG |
|---|---|
| content 0.00, collab 0.75, pop 0.25 | 0.1201 |
| content 0.00, collab 0.50, pop 0.50 | 0.1192 |
| content 0.25, collab 0.25, pop 0.50 | 0.1171 |
| content 0.25, collab 0.50, pop 0.25 | 0.1098 |
| content 0.00, collab 1.00, pop 0.00 | 0.0921 |
| content 0.25, collab 0.75, pop 0.00 | 0.0911 |
| content 0.50, collab 0.00, pop 0.50 | 0.0739 |
| content 0.50, collab 0.25, pop 0.25 | 0.0623 |
| content 0.50, collab 0.50, pop 0.00 | 0.0525 |
| content 0.75, collab 0.00, pop 0.25 | 0.0491 |

## Notes

- Popularity metadata is a current snapshot, which can favour the popularity baseline slightly.
- Compare the tuned hybrid with popularity honestly: if popularity still wins, say so.

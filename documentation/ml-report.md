# CineMatch: recommender evaluation

Generated 2026-11-20 09:07 UTC by `python -m ml.evaluate`. Every number below was computed from the data described here.

## Data

| Item | Value |
|---|---|
| Source | MovieLens (ml-32m), restricted to movies matched to the catalogue via TMDB id |
| Catalogue movies in evaluation pool | 334 |
| Ratings on pool movies | 22586 |
| Users with any such rating | 7781 |
| Users evaluated | 302 |
| Training ratings | 7458 |
| Held-out ratings | 1849 |
| Held-out relevant movies | 1046 |
| Selection rules | user has >= 10 ratings, a liked movie in train and a relevant movie in test |
| Collaborative model | trained on the training ratings |
| Average hybrid weights | content 0.57, collab 0.20, pop 0.23, pref 0.00 |
| Seed | 42 |

## Results at K = 5

Mean over evaluated users, with a 95% bootstrap confidence interval over users.

| Model | Precision@5 | Recall@5 | NDCG@5 | Catalogue coverage |
|---|---|---|---|---|
| random | 0.015 [0.009, 0.021] | 0.026 [0.015, 0.039] | 0.024 [0.014, 0.035] | 99.4% |
| popularity | 0.103 [0.087, 0.120] | 0.179 [0.147, 0.209] | 0.159 [0.133, 0.186] | 6.0% |
| content | 0.026 [0.018, 0.034] | 0.046 [0.029, 0.063] | 0.042 [0.027, 0.056] | 44.3% |
| collaborative | 0.068 [0.054, 0.083] | 0.110 [0.087, 0.137] | 0.102 [0.080, 0.126] | 35.0% |
| hybrid | 0.048 [0.038, 0.059] | 0.084 [0.061, 0.105] | 0.072 [0.055, 0.092] | 43.1% |

## Results at K = 10

Mean over evaluated users, with a 95% bootstrap confidence interval over users.

| Model | Precision@10 | Recall@10 | NDCG@10 | Catalogue coverage |
|---|---|---|---|---|
| random | 0.013 [0.009, 0.018] | 0.040 [0.026, 0.055] | 0.029 [0.019, 0.041] | 100.0% |
| popularity | 0.076 [0.067, 0.086] | 0.253 [0.218, 0.290] | 0.186 [0.163, 0.213] | 9.0% |
| content | 0.023 [0.018, 0.028] | 0.077 [0.057, 0.096] | 0.054 [0.039, 0.070] | 63.5% |
| collaborative | 0.055 [0.046, 0.064] | 0.175 [0.146, 0.203] | 0.124 [0.104, 0.148] | 43.7% |
| hybrid | 0.043 [0.036, 0.050] | 0.148 [0.120, 0.176] | 0.097 [0.078, 0.116] | 61.7% |

## Results at K = 20

Mean over evaluated users, with a 95% bootstrap confidence interval over users.

| Model | Precision@20 | Recall@20 | NDCG@20 | Catalogue coverage |
|---|---|---|---|---|
| random | 0.014 [0.011, 0.018] | 0.085 [0.063, 0.108] | 0.045 [0.033, 0.058] | 100.0% |
| popularity | 0.051 [0.045, 0.058] | 0.323 [0.286, 0.359] | 0.210 [0.185, 0.238] | 14.1% |
| content | 0.026 [0.022, 0.030] | 0.168 [0.138, 0.198] | 0.085 [0.068, 0.104] | 81.4% |
| collaborative | 0.044 [0.038, 0.051] | 0.269 [0.233, 0.305] | 0.157 [0.136, 0.182] | 61.1% |
| hybrid | 0.037 [0.032, 0.043] | 0.236 [0.200, 0.271] | 0.128 [0.109, 0.148] | 77.2% |

## Method

- Per-user temporal split: each user's latest 20% of ratings (at least 1) are the test set.
- Relevant = held-out movie rated >= 4. Unrated and low-rated movies count as not relevant.
- Candidates for each user = the evaluation pool minus movies already in that user's training ratings.
- User profiles (content) and the SVD model (collaborative) are fitted on training ratings only.
- TF-IDF is fitted on movie text only (no ratings), so it carries no interaction leakage.
- Popularity uses TMDB rating and vote metadata, not the evaluation ratings. That metadata is a current snapshot, so it can be slightly newer than the test period.
- Hybrid weights come from `.env` and were not tuned on this test set. MMR diversity is switched off here because these are accuracy metrics.
- Users with equal timestamps (rating in one sitting) are split by movie id, which is arbitrary within that batch.

## How to read this

- A model is only useful if it beats the random and popularity baselines by more than the confidence intervals. Overlapping intervals mean no real difference was measured.
- Small user counts give wide intervals. Do not quote differences smaller than the interval.

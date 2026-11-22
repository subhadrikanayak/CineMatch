"""Tune hybrid weights on a VALIDATION split, then report ONCE on an untouched TEST split.

Per user (sorted by time): oldest 60% = train, next 20% = validation, latest 20% = test.
  Stage 1: models fit on train        -> weights chosen by NDCG@K on validation only.
  Stage 2: models fit on train + val  -> final comparison on test (never used for choosing).

Run from D:\\CineMatch:
    python -m ml.tune --path dataset/raw/ml-32m
"""
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml.collaborative import CollaborativeModel
from ml.content_based import ContentModel
from ml.data import load_movies_df
from ml.evaluate import bootstrap_ci, load_movielens, load_tmdb_map, rank, user_metrics
from ml.hybrid import HybridRecommender, UserSignals

log = logging.getLogger("tune")


def split3(ratings: pd.DataFrame, min_ratings: int, frac: float, threshold: float):
    r = ratings.sort_values(["user_id", "ts", "movie_id"], kind="stable")
    r = r[r.groupby("user_id")["movie_id"].transform("size") >= min_ratings]
    tr, va, te = [], [], []
    for _, g in r.groupby("user_id", sort=False):
        n = len(g)
        k = max(1, int(round(n * frac)))
        tr.append(g.iloc[: n - 2 * k])
        va.append(g.iloc[n - 2 * k: n - k])
        te.append(g.iloc[n - k:])
    if not tr:
        raise SystemExit("No users have enough ratings. Try --min-ratings 8.")
    tr, va, te = pd.concat(tr), pd.concat(va), pd.concat(te)
    liked = lambda d: set(d.loc[d["rating"] >= threshold, "user_id"])
    keep = liked(tr) & liked(va) & liked(te)       # a liked movie in every part
    pick = lambda d: d[d["user_id"].isin(keep)]
    return pick(tr), pick(va), pick(te)


def grid(step: float) -> list[dict]:
    n = int(round(1 / step))
    out = []
    for c in range(n + 1):
        for cf in range(n + 1 - c):
            out.append({"content": c * step, "collab": cf * step,
                        "pop": (n - c - cf) * step, "pref": 0.0})
    return out


def by_user(df: pd.DataFrame) -> dict:
    return {int(u): {int(m): float(r) for m, r in zip(g["movie_id"], g["rating"])}
            for u, g in df.groupby("user_id")}


def relevant(df: pd.DataFrame, threshold: float) -> dict:
    return {int(u): {int(m) for m, r in zip(g["movie_id"], g["rating"]) if r >= threshold}
            for u, g in df.groupby("user_id")}


def ndcg_scores(engine, history: dict, target: dict, k: int, weights) -> list[float]:
    out = []
    for uid, seen in history.items():
        cand = [m for m in engine.ids if m not in seen]
        recs = engine.recommend(UserSignals(user_id=uid, ratings=dict(seen)), cand,
                                k=k, weights=weights, diversify=False)
        out.append(user_metrics([r.movie_id for r in recs], target[uid], k)[2])
    return out


def popularity_scores(engine, history: dict, target: dict, k: int) -> list[float]:
    out = []
    for uid, seen in history.items():
        cand = [m for m in engine.ids if m not in seen]
        idx = np.array([engine.pos[m] for m in cand])
        out.append(user_metrics(rank(cand, engine.wr[idx]), target[uid], k)[2])
    return out


def fmt(w: dict) -> str:
    return f"content {w['content']:.2f}, collab {w['collab']:.2f}, pop {w['pop']:.2f}"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", type=Path, required=True, help="MovieLens folder")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--step", type=float, default=0.25, help="grid step (0.1 is finer but slower)")
    ap.add_argument("--min-ratings", type=int, default=10)
    ap.add_argument("--threshold", type=float, default=4.0)
    ap.add_argument("--min-personal", type=float, default=0.3,
                    help="content + collab weight must be at least this (keeps it personalised)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("documentation/ml-tuning.md"))
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    movies = load_movies_df()
    ratings, pool = load_movielens(a.path, load_tmdb_map())
    train, val, test = split3(ratings, a.min_ratings, 0.2, a.threshold)
    n_users = int(train["user_id"].nunique())
    if n_users < 30:
        log.warning("Only %d users qualify; results will be noisy.", n_users)

    df = movies[movies["id"].isin(set(pool))].reset_index(drop=True)
    ids = df["id"].tolist()
    content = ContentModel.fit(df)            # text only, no ratings, so no leakage

    # ---- Stage 1: choose weights on VALIDATION (models see train only) ----
    eng1 = HybridRecommender(df, content, CollaborativeModel.fit(train, ids))
    hist1, tgt1 = by_user(train), relevant(val, a.threshold)
    combos = [w for w in grid(a.step) if w["content"] + w["collab"] >= a.min_personal - 1e-9]
    rows = []
    for i, w in enumerate(combos, 1):
        s = ndcg_scores(eng1, hist1, tgt1, a.k, w)
        rows.append((float(np.mean(s)), w))
        print(f"  [{i}/{len(combos)}] {fmt(w)} -> validation NDCG@{a.k} {np.mean(s):.4f}")
    rows.sort(key=lambda r: -r[0])
    best_val, best_w = rows[0]
    print(f"\nChosen on validation: {fmt(best_w)} (NDCG@{a.k} {best_val:.4f})")

    # ---- Stage 2: ONE look at the test set (models see train + val) ----
    trval = pd.concat([train, val])
    eng2 = HybridRecommender(df, content, CollaborativeModel.fit(trval, ids))
    hist2, tgt2 = by_user(trval), relevant(test, a.threshold)
    users = sorted(hist2)
    default_s = np.array(ndcg_scores(eng2, hist2, tgt2, a.k, None))        # current .env weights
    tuned_s = np.array(ndcg_scores(eng2, hist2, tgt2, a.k, best_w))
    pop_s = np.array(popularity_scores(eng2, hist2, tgt2, a.k))
    diff = tuned_s - default_s
    d_lo, d_hi = bootstrap_ci(diff, rng)

    def row(name, s):
        lo, hi = bootstrap_ci(s, rng)
        return f"| {name} | {s.mean():.3f} [{lo:.3f}, {hi:.3f}] |"

    verdict = ("The interval for the difference excludes 0, so the improvement is measurable."
               if d_lo > 0 else
               "The interval for the difference includes 0 (or is negative), so NO real improvement "
               "was measured over the current weights.")
    L = [f"# CineMatch: hybrid weight tuning", "",
         f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `python -m ml.tune`.", "",
         "## Setup", "",
         f"- Users: {len(users)} | catalogue pool: {len(df)} movies | K = {a.k}",
         f"- Per-user temporal split: 60% train / 20% validation / 20% test; relevant = rated >= {a.threshold:g}",
         f"- Grid step {a.step}; weights restricted to content + collab >= {a.min_personal}",
         "- Weights were chosen on the validation split only. The test split was used once, afterwards.", "",
         "## Weights", "",
         f"- Chosen on validation: **{fmt(best_w)}** (validation NDCG@{a.k} {best_val:.3f})",
         "- Current `.env` defaults: content 0.50, collab 0.30, pop 0.20 (before the adaptive ramp)", "",
         f"## Test results (NDCG@{a.k}, 95% bootstrap interval over users)", "",
         "| Model | NDCG |", "|---|---|",
         row("Hybrid, current weights", default_s), row("Hybrid, tuned weights", tuned_s),
         row("Popularity baseline", pop_s), "",
         f"Tuned minus current, per user: {diff.mean():+.3f} [{d_lo:+.3f}, {d_hi:+.3f}]. {verdict}", "",
         "## Validation grid (top 10)", "", "| Weights | Validation NDCG |", "|---|---|"]
    L += [f"| {fmt(w)} | {v:.4f} |" for v, w in rows[:10]]
    L += ["", "## Notes", "",
          "- Popularity metadata is a current snapshot, which can favour the popularity baseline slightly.",
          "- Compare the tuned hybrid with popularity honestly: if popularity still wins, say so."]
    md = "\n".join(L) + "\n"
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(md, encoding="utf-8")
    print("\n" + md)
    print(f"Saved to {a.out}")


if __name__ == "__main__":
    main()
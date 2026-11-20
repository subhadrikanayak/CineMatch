"""Offline evaluation of CineMatch's recommenders.

Method
  - Per-user TEMPORAL split: each user's most recent 20% of ratings are held out.
  - Every model is fitted on the training part only.
  - A held-out movie is "relevant" if the user rated it >= the threshold (default 4).
  - Metrics: Precision@K, Recall@K, NDCG@K (binary relevance), catalogue coverage.
  - Nothing is hard-coded: every number is computed from the data you give it.

Run from D:\\CineMatch:
    python -m ml.evaluate --source movielens --path dataset/raw/ml-32m
    python -m ml.evaluate --source db
"""
import argparse
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models import Movie, UserRating
from ml.collaborative import MIN_RATINGS, MIN_USERS, CollaborativeModel
from ml.content_based import ContentModel
from ml.data import load_movies_df
from ml.hybrid import HybridRecommender, UserSignals

log = logging.getLogger("evaluate")
COLS = ["user_id", "movie_id", "rating", "ts"]


# ------------------------------------------------------------------ metrics
def user_metrics(ranked: list, relevant: set, k: int) -> tuple[float, float, float]:
    """Precision@K, Recall@K, NDCG@K for one user (binary relevance)."""
    hits = [1 if m in relevant else 0 for m in ranked[:k]]
    h = sum(hits)
    dcg = sum(1.0 / np.log2(i + 2) for i, x in enumerate(hits) if x)
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))
    return h / k, h / len(relevant), (dcg / idcg if idcg > 0 else 0.0)


def bootstrap_ci(values, rng, n: int = 1000) -> tuple[float, float]:
    a = np.asarray(values, dtype=float)
    if len(a) < 2:
        return float("nan"), float("nan")
    means = np.array([a[rng.integers(0, len(a), len(a))].mean() for _ in range(n)])
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def rank(cand: list, scores) -> list:
    order = np.argsort(-np.asarray(scores, dtype=float), kind="stable")
    return [cand[i] for i in order]


# ------------------------------------------------------------------ data
def load_db_ratings() -> pd.DataFrame:
    with SessionLocal() as db:
        rows = db.execute(select(UserRating.user_id, UserRating.movie_id,
                                 UserRating.rating, UserRating.rated_at)).all()
    if not rows:
        return pd.DataFrame(columns=COLS)
    df = pd.DataFrame(rows, columns=COLS)
    df["ts"] = pd.to_datetime(df["ts"]).astype("int64")
    return df


def load_tmdb_map() -> dict:
    with SessionLocal() as db:
        return {t: i for i, t in db.execute(select(Movie.id, Movie.tmdb_id)).all()}


def load_movielens(path: Path, tmdb_to_id: dict):
    """Keep only MovieLens ratings of movies that exist in the CineMatch catalogue
    (matched through TMDB ids). Returns (ratings, pool_of_catalogue_ids)."""
    links_f, ratings_f = path / "links.csv", path / "ratings.csv"
    for f in (links_f, ratings_f):
        if not f.exists():
            raise SystemExit(f"Missing {f}. Unzip MovieLens so ratings.csv and links.csv are in that folder.")
    links = pd.read_csv(links_f).dropna(subset=["tmdbId"])
    links["tmdbId"] = links["tmdbId"].astype(int)
    links = links[links["tmdbId"].isin(tmdb_to_id)]
    ml_to_id = {int(m): tmdb_to_id[int(t)] for m, t in zip(links["movieId"], links["tmdbId"])}
    pool = sorted(set(ml_to_id.values()))
    parts = []
    for chunk in pd.read_csv(ratings_f, chunksize=2_000_000):
        c = chunk[chunk["movieId"].isin(ml_to_id)]
        if len(c):
            parts.append(c)
    if not parts:
        return pd.DataFrame(columns=COLS), pool
    r = pd.concat(parts, ignore_index=True)
    out = pd.DataFrame({
        "user_id": r["userId"].astype(int),
        "movie_id": r["movieId"].map(ml_to_id).astype(int),
        "rating": r["rating"].astype(float),
        "ts": r["timestamp"].astype("int64"),
    })
    out = out.sort_values("ts").drop_duplicates(["user_id", "movie_id"], keep="last")
    return out, pool


def temporal_split(ratings: pd.DataFrame, min_ratings: int, test_frac: float, threshold: float):
    r = ratings.sort_values(["user_id", "ts", "movie_id"], kind="stable")
    r = r[r.groupby("user_id")["movie_id"].transform("size") >= min_ratings]
    train_parts, test_parts = [], []
    for _, g in r.groupby("user_id", sort=False):
        n_test = max(1, int(round(len(g) * test_frac)))
        train_parts.append(g.iloc[:-n_test])
        test_parts.append(g.iloc[-n_test:])
    if not train_parts:
        return pd.DataFrame(columns=COLS), pd.DataFrame(columns=COLS)
    train, test = pd.concat(train_parts), pd.concat(test_parts)
    # a user needs a liked movie in train (to build a profile) and a relevant one in test
    keep = (set(train.loc[train["rating"] >= threshold, "user_id"])
            & set(test.loc[test["rating"] >= threshold, "user_id"]))
    return train[train["user_id"].isin(keep)], test[test["user_id"].isin(keep)]


# ------------------------------------------------------------------ report
def render(a, info: dict, ks: list, results: dict, n_pool: int, warnings: list, rng) -> str:
    L = ["# CineMatch: recommender evaluation", "",
         f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `python -m ml.evaluate`. "
         "Every number below was computed from the data described here.", "",
         "## Data", "", "| Item | Value |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in info.items()]
    if warnings:
        L += ["", "## Warnings", ""] + [f"- {w}" for w in warnings]
    for k in ks:
        L += ["", f"## Results at K = {k}", "",
              "Mean over evaluated users, with a 95% bootstrap confidence interval over users.", "",
              f"| Model | Precision@{k} | Recall@{k} | NDCG@{k} | Catalogue coverage |",
              "|---|---|---|---|---|"]
        for name, per_k in results.items():
            d = per_k[k]
            cells = []
            for m in ("precision", "recall", "ndcg"):
                lo, hi = bootstrap_ci(d[m], rng)
                cells.append(f"{np.mean(d[m]):.3f} [{lo:.3f}, {hi:.3f}]")
            L.append(f"| {name} | " + " | ".join(cells) + f" | {len(d['items']) / n_pool:.1%} |")
    L += ["", "## Method", "",
          f"- Per-user temporal split: each user's latest {a.test_frac:.0%} of ratings (at least 1) are the test set.",
          f"- Relevant = held-out movie rated >= {a.threshold:g}. Unrated and low-rated movies count as not relevant.",
          "- Candidates for each user = the evaluation pool minus movies already in that user's training ratings.",
          "- User profiles (content) and the SVD model (collaborative) are fitted on training ratings only.",
          "- TF-IDF is fitted on movie text only (no ratings), so it carries no interaction leakage.",
          "- Popularity uses TMDB rating and vote metadata, not the evaluation ratings. That metadata is a "
          "current snapshot, so it can be slightly newer than the test period.",
          "- Hybrid weights come from `.env` and were not tuned on this test set. MMR diversity is switched "
          "off here because these are accuracy metrics.",
          "- Users with equal timestamps (rating in one sitting) are split by movie id, which is arbitrary "
          "within that batch.", "",
          "## How to read this", "",
          "- A model is only useful if it beats the random and popularity baselines by more than the "
          "confidence intervals. Overlapping intervals mean no real difference was measured.",
          "- Small user counts give wide intervals. Do not quote differences smaller than the interval."]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main
def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["db", "movielens"], required=True)
    ap.add_argument("--path", type=Path, help="MovieLens folder (with ratings.csv and links.csv)")
    ap.add_argument("--min-ratings", type=int, default=10)
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--threshold", type=float, default=4.0)
    ap.add_argument("--ks", type=int, nargs="+", default=[5, 10, 20])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("documentation/ml-report.md"))
    a = ap.parse_args()
    if a.min_ratings < 5:
        raise SystemExit("--min-ratings must be at least 5")
    if a.source == "movielens" and not a.path:
        raise SystemExit("--path is required for --source movielens")
    rng = np.random.default_rng(a.seed)

    movies = load_movies_df()
    if movies.empty:
        raise SystemExit("No movies in the database.")

    if a.source == "db":
        ratings, pool = load_db_ratings(), movies["id"].tolist()
        source = "Real CineMatch user ratings (database)"
    else:
        ratings, pool = load_movielens(a.path, load_tmdb_map())
        source = f"MovieLens ({a.path.name}), restricted to movies matched to the catalogue via TMDB id"

    info = {"Source": source, "Catalogue movies in evaluation pool": len(pool),
            "Ratings on pool movies": len(ratings),
            "Users with any such rating": int(ratings["user_id"].nunique()) if len(ratings) else 0}
    print(f"Pool: {len(pool)} movies. Ratings on them: {len(ratings)}.")

    train, test = temporal_split(ratings, a.min_ratings, a.test_frac, a.threshold)
    n_users = int(train["user_id"].nunique()) if len(train) else 0
    if n_users == 0 or len(pool) < 30:
        raise SystemExit(
            f"Not enough data to evaluate: {n_users} usable user(s) with >= {a.min_ratings} ratings "
            f"(a liked movie in train and in test), pool of {len(pool)} movies. "
            "Try --min-ratings 5, a bigger MovieLens download, or wait for real CineMatch users.")

    ks = sorted(k for k in set(a.ks) if k <= len(pool) // 2)
    if not ks:
        raise SystemExit("Pool too small for the requested K values.")

    df = movies[movies["id"].isin(set(pool))].reset_index(drop=True)
    content = ContentModel.fit(df)
    collab = CollaborativeModel.fit(train, df["id"].tolist())
    engine = HybridRecommender(df, content, collab)

    train_by = {int(u): {int(m): float(r) for m, r in zip(g["movie_id"], g["rating"])}
                for u, g in train.groupby("user_id")}
    rel_by = {int(u): {int(m) for m, r in zip(g["movie_id"], g["rating"]) if r >= a.threshold}
              for u, g in test.groupby("user_id")}

    store = defaultdict(lambda: defaultdict(lambda: {"precision": [], "recall": [], "ndcg": [], "items": set()}))
    wsum, wn, cf_fallback = defaultdict(float), 0, 0

    for n, (uid, seen) in enumerate(train_by.items(), 1):
        rel = rel_by[uid]
        cand = [m for m in engine.ids if m not in seen]
        idx = np.array([engine.pos[m] for m in cand])
        pop = engine.wr[idx]

        rankings = {
            "random": [cand[i] for i in rng.permutation(len(cand))],
            "popularity": rank(cand, pop),
        }
        prof = content.profile_from_weights({m: r - 3.0 for m, r in seen.items()})
        rankings["content"] = rank(cand, content.scores(prof, idx) if prof is not None else pop)
        if collab.ready:
            p = collab.predict(uid, cand)
            if p is None:
                cf_fallback += 1
            rankings["collaborative"] = rank(cand, p if p is not None else pop)
        recs = engine.recommend(UserSignals(user_id=uid, ratings=dict(seen)), cand,
                                k=max(ks), diversify=False)
        if recs:
            rankings["hybrid"] = [r.movie_id for r in recs]
            for key, v in recs[0].weights.items():
                wsum[key] += v
            wn += 1

        for name, ranked in rankings.items():
            for k in ks:
                p_, r_, n_ = user_metrics(ranked, rel, k)
                d = store[name][k]
                d["precision"].append(p_); d["recall"].append(r_); d["ndcg"].append(n_)
                d["items"].update(ranked[:k])
        if n % 200 == 0:
            print(f"  evaluated {n}/{len(train_by)} users")

    info.update({
        "Users evaluated": n_users,
        "Training ratings": len(train), "Held-out ratings": len(test),
        "Held-out relevant movies": sum(len(v) for v in rel_by.values()),
        "Selection rules": f"user has >= {a.min_ratings} ratings, a liked movie in train and a relevant movie in test",
        "Collaborative model": ("trained on the training ratings" if collab.ready else
                                f"NOT trained (needs {MIN_RATINGS}+ ratings from {MIN_USERS}+ users); "
                                "it is excluded from the table"),
        "Average hybrid weights": ", ".join(f"{k} {v / wn:.2f}" for k, v in wsum.items()) if wn else "n/a",
        "Seed": a.seed,
    })
    if cf_fallback:
        info["Users where collaborative fell back to popularity"] = cf_fallback

    warnings = []
    if n_users < 30:
        warnings.append(f"Only {n_users} users were evaluated. Differences between models are "
                        "not statistically meaningful at this size.")
    if info["Held-out relevant movies"] < 100:
        warnings.append("Fewer than 100 relevant held-out movies, so the metrics are very noisy.")
    if not collab.ready:
        warnings.append("Collaborative filtering could not be trained on this data, so the hybrid "
                        "ran without it (its weight is 0).")

    results = {name: dict(per_k) for name, per_k in store.items()}
    md = render(a, info, ks, results, len(df), warnings, rng)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(md, encoding="utf-8")
    print("\n" + md)
    print(f"Saved to {a.out}")


if __name__ == "__main__":
    main()
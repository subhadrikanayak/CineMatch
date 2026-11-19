import logging
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics.pairwise import linear_kernel

from backend.app.core.config import settings
from ml.collaborative import CollaborativeModel
from ml.content_based import ContentModel
from ml.data import load_movies_df, slug
from ml.diversity import mmr
from ml.explain import build_reasons
from ml.popularity import weighted_rating
from ml.utils import minmax

log = logging.getLogger("ml.hybrid")


@dataclass
class UserSignals:
    user_id: int | None = None
    ratings: dict[int, float] = field(default_factory=dict)     # movie_id -> 0.5..5
    liked_ids: set[int] = field(default_factory=set)
    disliked_ids: set[int] = field(default_factory=set)
    watchlist_ids: set[int] = field(default_factory=set)
    seen_ids: set[int] = field(default_factory=set)             # excluded from results
    fav_languages: set[str] = field(default_factory=set)        # codes: hi, te, ta, ml, kn
    fav_genres: set[str] = field(default_factory=set)
    fav_actor_ids: set[int] = field(default_factory=set)


@dataclass
class Recommendation:
    movie_id: int
    score: float
    match_percent: int
    components: dict
    weights: dict
    reasons: list


class HybridRecommender:
    def __init__(self, df, content: ContentModel, collab: CollaborativeModel):
        self.df = df.reset_index(drop=True)
        self.content = content
        self.collab = collab
        self.ids = self.df["id"].tolist()
        self.pos = {m: i for i, m in enumerate(self.ids)}
        self.records = self.df.to_dict("records")
        self.wr = weighted_rating(self.df).to_numpy()

    @classmethod
    def load(cls):
        df = load_movies_df()
        if df.empty:
            raise RuntimeError("No movies in the database. Run the TMDB ingestion first.")
        return cls(df, ContentModel.load_or_fit(df), CollaborativeModel.load_or_empty())

    # ---------- components ----------
    def _profile(self, s: UserSignals):
        w: dict[int, float] = {}
        for mid, r in s.ratings.items():
            w[mid] = r - 3.0                      # 5 -> +2, 4 -> +1, 2 -> -1
        for mid in s.liked_ids:
            w[mid] = max(w.get(mid, 0.0), 1.5)
        for mid in s.watchlist_ids:
            w.setdefault(mid, 0.5)
        for mid in s.disliked_ids:
            w[mid] = -1.5
        if any(v > 0 for v in w.values()):
            return self.content.profile_from_weights(w)
        # cold start: build the profile from selected preferences
        text = " ".join([f"gen_{slug(g)}" for g in s.fav_genres] * 3
                        + [f"act_{a}" for a in s.fav_actor_ids] * 2)
        return self.content.profile_from_text(text) if text else None

    def _preference(self, s: UserSignals, idx):
        parts = []
        if s.fav_languages:
            parts.append(np.array([1.0 if self.records[i]["language_code"] in s.fav_languages
                                   else 0.0 for i in idx]))
        if s.fav_genres:
            d = min(2, len(s.fav_genres))
            parts.append(np.array([min(1.0, len(set(self.records[i]["genres"]) & s.fav_genres) / d)
                                   for i in idx]))
        if not parts:
            return np.zeros(len(idx)), False
        return np.mean(parts, axis=0), True

    # ---------- main entry ----------
    def recommend(self, signals: UserSignals, candidate_ids=None, k: int = 20,
                  weights: dict | None = None, diversify: bool = True,
                  mmr_lambda: float | None = None, min_rating: float | None = None):
        """candidate_ids must already satisfy every hard filter (language, rating,
        year...). The hybrid score only ranks them and never widens the set."""
        excluded = (set(signals.seen_ids) | set(signals.ratings)
                    | set(signals.disliked_ids) | set(signals.liked_ids))
        pool_ids = self.ids if candidate_ids is None else candidate_ids
        ids = [m for m in pool_ids if m in self.pos and m not in excluded]
        if not ids:
            return []
        idx = np.array([self.pos[m] for m in ids])

        profile = self._profile(signals)
        content_raw = self.content.scores(profile, idx) if profile is not None else None

        n_ratings = len(signals.ratings)
        cf_raw = None
        if signals.user_id is not None and n_ratings >= 5:
            cf_raw = self.collab.predict(signals.user_id, ids)

        pref_raw, has_pref = self._preference(signals, idx)

        # ---- adaptive weights (cold start -> popularity + preferences) ----
        base = {"content": settings.W_CONTENT, "collab": settings.W_COLLAB,
                "pop": settings.W_POPULARITY, "pref": settings.W_PREFERENCE}
        if weights:
            base.update(weights)
        ramp = 0.0 if n_ratings < 5 else 0.33 if n_ratings < 15 else 0.66 if n_ratings < 30 else 1.0
        w = {
            "content": base["content"] if content_raw is not None else 0.0,
            "collab": base["collab"] * ramp if cf_raw is not None else 0.0,
            "pop": base["pop"],
            "pref": base["pref"] if has_pref else 0.0,
        }
        total = sum(w.values())
        if total <= 0:
            w, total = {"content": 0.0, "collab": 0.0, "pop": 1.0, "pref": 0.0}, 1.0
        w = {k_: v / total for k_, v in w.items()}

        zeros = np.zeros(len(idx))
        comp = {
            "content": minmax(content_raw) if content_raw is not None else zeros,
            "collab": minmax(cf_raw) if cf_raw is not None else zeros,
            "pop": minmax(self.wr[idx]),
            "pref": pref_raw,
        }
        final = sum(w[c] * comp[c] for c in comp)

        # ---- ranking + diversity ----
        order = np.argsort(-final, kind="stable")
        if diversify and len(order) > k:
            lam = settings.MMR_LAMBDA if mmr_lambda is None else mmr_lambda
            pool = order[: max(k * 4, 40)]
            chosen = mmr(final[pool], self.content.similarity(idx[pool]), k, lam)
            picked = [int(pool[i]) for i in chosen]
        else:
            picked = [int(p) for p in order[:k]]

        # ---- explanations ----
        liked_movies = ({m for m, r in signals.ratings.items() if r >= 4}
                        | set(signals.liked_ids))
        liked_pos = [self.pos[m] for m in liked_movies if m in self.pos]
        taste_genres = [g for g, _ in Counter(
            g for p in liked_pos for g in self.records[p]["genres"]).most_common(3)]
        sel_idx = idx[picked]
        nearest = []
        if liked_pos:
            S = linear_kernel(self.content.matrix[sel_idx], self.content.matrix[liked_pos])
            for row in S:
                j = int(row.argmax())
                nearest.append((self.records[liked_pos[j]], float(row[j])))

        results = []
        for r, p in enumerate(picked):
            i = int(idx[p])
            rec = self.records[i]
            comps = {c: round(float(comp[c][p]), 4) for c in comp}
            score = float(final[p])
            results.append(Recommendation(
                movie_id=rec["id"], score=round(score, 4),
                match_percent=int(round(score * 100)),
                components=comps, weights={c: round(v, 3) for c, v in w.items()},
                reasons=build_reasons(rec, comps, w, signals, taste_genres,
                                      nearest[r] if nearest else None,
                                      float(self.wr[i]), min_rating),
            ))
        return results
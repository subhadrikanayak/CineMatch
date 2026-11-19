import logging
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

log = logging.getLogger("ml.collab")
ARTIFACT = Path(__file__).parent / "artifacts" / "collab.joblib"

MIN_RATINGS = 30   # below this the model would be noise, so it stays off
MIN_USERS = 5


class CollaborativeModel:
    def __init__(self, user_index=None, movie_index=None, pred=None):
        self.user_index = user_index or {}
        self.movie_index = movie_index or {}
        self.pred = pred                      # users x movies, predicted ratings (0.5..5)

    @property
    def ready(self) -> bool:
        return self.pred is not None

    @classmethod
    def fit(cls, ratings, movie_ids, n_components: int = 20):
        movie_index = {m: i for i, m in enumerate(movie_ids)}
        df = ratings[ratings["movie_id"].isin(movie_index)]
        if len(df) < MIN_RATINGS or df["user_id"].nunique() < MIN_USERS:
            log.info("Collaborative model OFF: %d ratings from %d users (need %d / %d).",
                     len(df), df["user_id"].nunique(), MIN_RATINGS, MIN_USERS)
            return cls()
        users = sorted(df["user_id"].unique())
        user_index = {u: i for i, u in enumerate(users)}
        user_mean = df.groupby("user_id")["rating"].mean()
        vals = (df["rating"] - df["user_id"].map(user_mean)).to_numpy(dtype=float)
        rows = df["user_id"].map(user_index).to_numpy()
        cols = df["movie_id"].map(movie_index).to_numpy()
        R = csr_matrix((vals, (rows, cols)), shape=(len(users), len(movie_ids)))
        k = min(n_components, min(R.shape) - 1)
        if k < 2:
            return cls()
        svd = TruncatedSVD(n_components=k, random_state=42)
        U = svd.fit_transform(R)
        means = user_mean.reindex(users).to_numpy()[:, None]
        pred = np.clip(U @ svd.components_ + means, 0.5, 5.0).astype(np.float32)
        log.info("Collaborative model ON: %d users, %d ratings, %d factors.", len(users), len(df), k)
        return cls(user_index, movie_index, pred)

    def save(self, path: Path = ARTIFACT):
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"user_index": self.user_index, "movie_index": self.movie_index,
                     "pred": self.pred}, path)

    @classmethod
    def load_or_empty(cls, path: Path = ARTIFACT):
        if path.exists():
            d = joblib.load(path)
            return cls(d["user_index"], d["movie_index"], d["pred"])
        return cls()

    def predict(self, user_id: int, movie_ids: list[int]):
        """Predicted ratings aligned with movie_ids, or None if unavailable for this user."""
        if not self.ready or user_id not in self.user_index:
            return None
        row = self.pred[self.user_index[user_id]]
        vals = np.array([row[self.movie_index[m]] if m in self.movie_index else np.nan
                         for m in movie_ids], dtype=float)
        if np.isnan(vals).all():
            return None
        vals[np.isnan(vals)] = np.nanmean(vals)
        return vals
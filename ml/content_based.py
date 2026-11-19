import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from ml.data import build_soup

log = logging.getLogger("ml.content")
ARTIFACT = Path(__file__).parent / "artifacts" / "content.joblib"


class ContentModel:
    def __init__(self, vectorizer, matrix, movie_ids):
        self.vectorizer = vectorizer
        self.matrix = matrix                      # rows are L2-normalised
        self.movie_ids = list(movie_ids)
        self.index = {mid: i for i, mid in enumerate(self.movie_ids)}

    @classmethod
    def fit(cls, df):
        soups = [build_soup(r) for r in df.to_dict("records")]
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                              min_df=2, max_features=30000, sublinear_tf=True)
        return cls(vec, vec.fit_transform(soups), df["id"].tolist())

    def save(self, path: Path = ARTIFACT):
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"vectorizer": self.vectorizer, "matrix": self.matrix,
                     "movie_ids": self.movie_ids}, path)

    @classmethod
    def load_or_fit(cls, df, path: Path = ARTIFACT):
        if path.exists():
            d = joblib.load(path)
            if d["movie_ids"] == df["id"].tolist():
                return cls(d["vectorizer"], d["matrix"], d["movie_ids"])
            log.warning("Content artifact is out of date; refitting in memory. Run: python -m ml.train")
        return cls.fit(df)

    # ---- user profile vectors ----
    def profile_from_weights(self, weights: dict[int, float]):
        rows, w = [], []
        for mid, wt in weights.items():
            i = self.index.get(mid)
            if i is not None and wt != 0:
                rows.append(i)
                w.append(wt)
        if not rows:
            return None
        prof = np.asarray(self.matrix[rows].T @ np.array(w)).ravel()
        n = np.linalg.norm(prof)
        return prof / n if n > 0 else None

    def profile_from_text(self, text: str):
        prof = self.vectorizer.transform([text]).toarray().ravel()
        n = np.linalg.norm(prof)
        return prof / n if n > 0 else None

    # ---- scoring ----
    def scores(self, profile, idx) -> np.ndarray:
        return np.asarray(self.matrix[idx] @ profile).ravel()

    def similarity(self, idx) -> np.ndarray:
        sub = self.matrix[idx]
        return linear_kernel(sub, sub)

    def similar(self, movie_id: int, top_n: int = 10):
        i = self.index.get(movie_id)
        if i is None:
            return []
        sims = linear_kernel(self.matrix[i], self.matrix).ravel()
        sims[i] = -1
        order = np.argsort(-sims)[:top_n]
        return [(self.movie_ids[j], float(sims[j])) for j in order]
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

log = logging.getLogger("ml.semantic")
ART = Path(__file__).parent / "artifacts"
EMB_FILE = ART / "semantic_embeddings.npy"
IDS_FILE = ART / "semantic_ids.json"
MODEL_NAME = "all-MiniLM-L6-v2"

LANGS = {"hindi": "hi", "bollywood": "hi", "telugu": "te", "tollywood": "te",
         "tamil": "ta", "kollywood": "ta", "malayalam": "ml", "mollywood": "ml",
         "kannada": "kn", "sandalwood": "kn"}

# multi-word phrases first so "romantic comedy" is caught before "romantic"
GENRE_WORDS = [("romantic comedy", "Rom-Com"), ("rom-com", "Rom-Com"), ("romcom", "Rom-Com"),
               ("science fiction", "Sci-Fi"), ("sci-fi", "Sci-Fi"), ("scifi", "Sci-Fi"),
               ("thrillers", "Thriller"), ("thriller", "Thriller"), ("action", "Action"),
               ("comedies", "Comedy"), ("comedy", "Comedy"), ("romance", "Romance"),
               ("romantic", "Romance"), ("mystery", "Mystery"), ("horror", "Horror"),
               ("drama", "Drama"), ("adventure", "Adventure"), ("crime", "Crime"),
               ("family", "Family"), ("animated", "Animation"), ("animation", "Animation"),
               ("fantasy", "Fantasy")]

FILLER = {"suggest", "recommend", "me", "a", "an", "the", "movie", "movies", "film", "films",
          "show", "find", "want", "something", "give", "some", "with", "that", "has", "have",
          "good", "best", "please", "i", "need", "looking", "for", "of", "in", "to", "is",
          "and", "or", "it", "its"}


@dataclass
class ParsedQuery:
    languages: list = field(default_factory=list)
    genres: list = field(default_factory=list)
    year_min: int | None = None
    year_max: int | None = None
    min_rating: float | None = None
    text: str = ""


def parse_query(query: str) -> ParsedQuery:
    """Explicit cues (language, genre, year, rating) become HARD filters.
    Whatever is left is matched against movie descriptions."""
    t = " " + query.lower() + " "
    p = ParsedQuery()
    for word, code in LANGS.items():
        if re.search(rf"\b{re.escape(word)}\b", t):
            if code not in p.languages:
                p.languages.append(code)
            t = re.sub(rf"\b{re.escape(word)}\b", " ", t)
    for word, genre in GENRE_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", t):
            if genre not in p.genres:
                p.genres.append(genre)
            t = re.sub(rf"\b{re.escape(word)}\b", " ", t)
    m = re.search(r"\b(?:after|since|from)\s+(\d{4})\b", t)
    if m:
        p.year_min = int(m.group(1))
        t = t.replace(m.group(0), " ")
    m = re.search(r"\b(?:before|until|till)\s+(\d{4})\b", t)
    if m:
        p.year_max = int(m.group(1))
        t = t.replace(m.group(0), " ")
    m = re.search(r"\b(?:above|over|rated|at least|minimum)\s+(\d(?:\.\d)?)\b", t)
    if m:
        p.min_rating = float(m.group(1))
        t = t.replace(m.group(0), " ")
    p.text = " ".join(w for w in re.findall(r"[a-z][a-z'-]+", t) if w not in FILLER)
    return p


class SemanticIndex:
    def __init__(self, df):
        self.ids = df["id"].tolist()
        self.pos = {m: i for i, m in enumerate(self.ids)}
        self.texts = [f"{r['title']}. {' '.join(r['genres'])}. {r['keywords']}. {r['overview']}"
                      for r in df.to_dict("records")]
        self.vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        self.matrix = self.vec.fit_transform(self.texts)
        self.emb = None
        self.model = None
        self.engine = "tfidf"
        self._try_embeddings()

    def _try_embeddings(self):
        if not (EMB_FILE.exists() and IDS_FILE.exists()):
            return
        try:
            if json.loads(IDS_FILE.read_text()) != self.ids:
                log.warning("Embeddings are out of date; run python -m ml.build_embeddings")
                return
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(MODEL_NAME)
            self.emb = np.load(EMB_FILE)
            self.engine = "sentence-transformers"
        except Exception as exc:
            log.warning("Sentence Transformers unavailable (%s); using TF-IDF.", exc)
            self.emb = self.model = None

    def search(self, text: str, ids: list[int]) -> dict[int, float]:
        valid = [i for i in ids if i in self.pos]
        if not valid:
            return {}
        idx = np.array([self.pos[i] for i in valid])
        if self.emb is not None:
            q = self.model.encode([text], normalize_embeddings=True)[0]
            sims = self.emb[idx] @ q
        else:
            q = self.vec.transform([text])
            sims = (self.matrix[idx] @ q.T).toarray().ravel()
        return dict(zip(valid, (float(s) for s in sims)))

    def matched_terms(self, text: str, movie_id: int) -> list[str]:
        q = {w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in ENGLISH_STOP_WORDS}
        d = set(re.findall(r"[a-z]{3,}", self.texts[self.pos[movie_id]].lower()))
        return sorted(q & d)
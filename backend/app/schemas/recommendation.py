from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.repositories.movie_repository import MovieFilters
from backend.app.schemas.movie import MovieCard

LANG_CODES = {"hi", "te", "ta", "ml", "kn"}
WEIGHT_KEYS = {"content", "collab", "pop", "pref"}

MATCH_NOTE = ("Match % comes from the hybrid score, normalised within the movies that "
              "passed your filters. It ranks movies against each other; it is not a "
              "prediction of your rating.")


class FilterIn(BaseModel):
    languages: list[str] = Field(default_factory=list, description="hi, te, ta, ml, kn")
    genres: list[str] = Field(default_factory=list)
    genre_match: Literal["any", "all"] = "any"
    actor_ids: list[int] = Field(default_factory=list)
    director_ids: list[int] = Field(default_factory=list)
    min_rating: float | None = Field(None, ge=0, le=10)
    year_min: int | None = Field(None, ge=1900, le=2100)
    year_max: int | None = Field(None, ge=1900, le=2100)
    runtime_min: int | None = Field(None, ge=0)
    runtime_max: int | None = Field(None, ge=0)
    q: str | None = Field(None, max_length=100)

    @field_validator("languages")
    @classmethod
    def _langs(cls, v):
        v = [x.lower() for x in v]
        bad = set(v) - LANG_CODES
        if bad:
            raise ValueError(f"Unknown language code(s): {sorted(bad)}. Use hi, te, ta, ml, kn")
        return v

    def to_filters(self) -> MovieFilters:
        return MovieFilters(
            languages=self.languages, genres=self.genres, genre_match=self.genre_match,
            actor_ids=self.actor_ids, director_ids=self.director_ids,
            min_rating=self.min_rating, year_min=self.year_min, year_max=self.year_max,
            runtime_min=self.runtime_min, runtime_max=self.runtime_max, q=self.q,
        )


class RecommendIn(FilterIn):
    k: int = Field(20, ge=1, le=50)
    diversify: bool = True
    mmr_lambda: float | None = Field(None, ge=0, le=1)
    weights: dict[str, float] | None = Field(None, description="optional: content, collab, pop, pref")

    @field_validator("weights")
    @classmethod
    def _weights(cls, v):
        if v is None:
            return v
        if set(v) - WEIGHT_KEYS or any(x < 0 for x in v.values()):
            raise ValueError("weights keys must be among content, collab, pop, pref and non-negative")
        return v


class MoodIn(FilterIn):
    mood: str
    k: int = Field(20, ge=1, le=50)


class SemanticIn(FilterIn):
    query: str = Field(min_length=3, max_length=300)
    k: int = Field(20, ge=1, le=50)


class SurpriseIn(FilterIn):
    outside_comfort_zone: bool = False


class RecommendationOut(BaseModel):
    movie: MovieCard
    match_percent: int
    score: float
    components: dict[str, float]
    weights: dict[str, float]
    reasons: list[str]


class RecommendationList(BaseModel):
    items: list[RecommendationOut]
    candidates: int
    personalised: bool
    collaborative_active: bool
    weights_used: dict[str, float]
    note: str = MATCH_NOTE


class GemOut(BaseModel):
    movie: MovieCard
    gem_score: float
    popularity_percentile: int
    reasons: list[str]


class GemList(BaseModel):
    items: list[GemOut]
    thresholds: dict[str, float]
    note: str = ("Thresholds are computed from your catalogue. A movie needs a credible "
                 "number of votes AND modest popularity AND a high weighted rating.")


class SimilarOut(BaseModel):
    movie: MovieCard
    similarity: float
    shared_genres: list[str]
    shared_cast: list[str]
    same_director: bool


class SemanticItem(BaseModel):
    movie: MovieCard
    similarity: float | None
    match_percent: int
    reasons: list[str]


class SemanticOut(BaseModel):
    engine: str
    parsed: dict
    items: list[SemanticItem]
    candidates: int
    note: str | None = None


class SurpriseOut(BaseModel):
    movie: MovieCard
    reasons: list[str]
    candidates: int


class CompareMovie(MovieCard):
    directors: list[str]


class CompareOut(BaseModel):
    a: CompareMovie
    b: CompareMovie
    shared_genres: list[str]
    same_language: bool
    rating_difference: float | None
    higher_rated: int | None
    more_popular: int | None
    year_gap: int | None
    content_similarity: float | None
    warnings: list[str]
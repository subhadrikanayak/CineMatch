import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.schemas.movie import MovieCard, PersonOut

LANG_CODES = {"hi", "te", "ta", "ml", "kn"}


def _dedupe(seq):
    return list(dict.fromkeys(seq))


class RatingIn(BaseModel):
    rating: float = Field(ge=0.5, le=5)

    @field_validator("rating")
    @classmethod
    def _half_steps(cls, v):
        if (v * 2) % 1 != 0:
            raise ValueError("Rating must be in steps of 0.5 (0.5, 1, 1.5 ... 5)")
        return v


class ActivityItem(BaseModel):
    movie: MovieCard
    at: datetime | None = None
    rating: float | None = None


class ActivityPage(BaseModel):
    items: list[ActivityItem]
    total: int
    page: int
    page_size: int
    pages: int


def make_page(items, total, page, page_size) -> ActivityPage:
    return ActivityPage(items=items, total=total, page=page, page_size=page_size,
                        pages=math.ceil(total / page_size) if total else 0)


class PreferencesIn(BaseModel):
    languages: list[str] = Field(default_factory=list, max_length=5, description="hi, te, ta, ml, kn")
    genres: list[str] = Field(default_factory=list, max_length=14)
    actor_ids: list[int] = Field(default_factory=list, max_length=20)

    @field_validator("languages")
    @classmethod
    def _langs(cls, v):
        v = _dedupe(x.lower() for x in v)
        bad = set(v) - LANG_CODES
        if bad:
            raise ValueError(f"Unknown language code(s): {sorted(bad)}. Use hi, te, ta, ml, kn")
        return v

    @field_validator("genres", "actor_ids")
    @classmethod
    def _unique(cls, v):
        return _dedupe(v)


class LanguageOut(BaseModel):
    code: str
    name: str


class PreferencesOut(BaseModel):
    languages: list[LanguageOut]
    genres: list[str]
    actors: list[PersonOut]


class FeedbackIn(BaseModel):
    movie_id: int
    feedback_type: Literal["like", "dislike", "comment"]
    comment: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def _need_comment(self):
        if self.feedback_type == "comment" and not (self.comment and self.comment.strip()):
            raise ValueError("A comment is required when feedback_type is 'comment'")
        return self


class FeedbackOut(BaseModel):
    id: int
    movie_id: int
    feedback_type: str
    comment: str | None
    created_at: datetime | None


class ShareItem(BaseModel):
    name: str
    code: str | None = None
    percent: float


class PersonCount(BaseModel):
    id: int
    name: str
    movies: int


class TasteProfileOut(BaseModel):
    enough_data: bool
    based_on: dict[str, int]
    declared: dict[str, list[str]]
    genres: list[ShareItem]
    languages: list[ShareItem]
    decades: list[ShareItem]
    top_actors: list[PersonCount]
    top_directors: list[PersonCount]
    avg_runtime: int | None
    avg_release_year: int | None
    avg_public_rating: float | None
    own_average_rating: float | None
    avoided_genres: list[str]
    note: str
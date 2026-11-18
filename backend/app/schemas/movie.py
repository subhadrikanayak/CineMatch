from pydantic import BaseModel

from backend.app.models import Movie

IMG = "https://image.tmdb.org/t/p"


def _img(path: str | None, size: str) -> str | None:
    return f"{IMG}/{size}{path}" if path else None


def effective_rating(m: Movie) -> tuple[float | None, int | None, str | None]:
    """Prefer IMDb rating when present; otherwise the TMDB rating, labelled as TMDB.
    A TMDB rating with zero votes is treated as 'no rating'."""
    if m.imdb_rating is not None:
        return round(m.imdb_rating, 1), m.imdb_votes, "imdb"
    if m.tmdb_rating and m.tmdb_votes:
        return round(m.tmdb_rating, 1), m.tmdb_votes, "tmdb"
    return None, None, None


class MovieCard(BaseModel):
    id: int
    tmdb_id: int
    title: str
    release_year: int | None
    runtime: int | None
    language: str
    genres: list[str]
    rating: float | None
    rating_source: str | None
    votes: int | None
    popularity: float | None
    poster_url: str | None


class PersonOut(BaseModel):
    id: int
    name: str
    gender: str | None = None
    profile_url: str | None = None
    character: str | None = None
    order: int | None = None


class StreamingOut(BaseModel):
    provider: str
    logo_url: str | None
    offer_type: str
    region: str


class MovieDetail(MovieCard):
    original_title: str | None
    overview: str | None
    keywords: list[str]
    backdrop_url: str | None
    release_date: str | None
    dubbed_languages: str | None
    imdb_id: str | None
    cast: list[PersonOut]
    directors: list[PersonOut]
    streaming: list[StreamingOut]


class MoviePage(BaseModel):
    items: list[MovieCard]
    total: int
    page: int
    page_size: int
    pages: int


def to_card(m: Movie) -> MovieCard:
    rating, votes, source = effective_rating(m)
    return MovieCard(
        id=m.id, tmdb_id=m.tmdb_id, title=m.title,
        release_year=m.release_year, runtime=m.runtime,
        language=m.language.name,
        genres=[g.name for g in m.genres],
        rating=rating, rating_source=source, votes=votes,
        popularity=m.popularity, poster_url=_img(m.poster_path, "w342"),
    )
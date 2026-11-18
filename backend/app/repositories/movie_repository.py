from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import (
    Genre, Language, Movie, MovieCast, MovieDirector, MovieGenre,
)


@dataclass
class MovieFilters:
    languages: list[str] = field(default_factory=list)   # codes: hi, te, ta, ml, kn
    genres: list[str] = field(default_factory=list)      # genre names
    genre_match: str = "any"                             # any | all
    actor_ids: list[int] = field(default_factory=list)   # ALL listed actors must be in the movie
    director_ids: list[int] = field(default_factory=list)
    min_rating: float | None = None
    year_min: int | None = None
    year_max: int | None = None
    runtime_min: int | None = None
    runtime_max: int | None = None
    q: str | None = None
    sort: str = "popularity"


def rating_expr():
    return func.coalesce(Movie.imdb_rating, Movie.tmdb_rating)


def build_conditions(f: MovieFilters) -> list:
    c = []
    if f.languages:
        c.append(Movie.original_language_id.in_(
            select(Language.id).where(Language.code.in_(f.languages))))
    if f.genres:
        sub = (select(MovieGenre.movie_id).join(Genre, Genre.id == MovieGenre.genre_id)
               .where(Genre.name.in_(f.genres)).group_by(MovieGenre.movie_id))
        if f.genre_match == "all":
            sub = sub.having(func.count(func.distinct(Genre.id)) == len(set(f.genres)))
        c.append(Movie.id.in_(sub))
    for aid in f.actor_ids:
        c.append(Movie.id.in_(select(MovieCast.movie_id).where(MovieCast.actor_id == aid)))
    for did in f.director_ids:
        c.append(Movie.id.in_(select(MovieDirector.movie_id).where(MovieDirector.director_id == did)))
    if f.min_rating is not None:
        c.append(rating_expr() >= f.min_rating)
    if f.year_min is not None:
        c.append(Movie.release_year >= f.year_min)
    if f.year_max is not None:
        c.append(Movie.release_year <= f.year_max)
    if f.runtime_min is not None:
        c.append(Movie.runtime >= f.runtime_min)
    if f.runtime_max is not None:
        c.append(Movie.runtime <= f.runtime_max)
    if f.q:
        like = f"%{f.q.strip()}%"
        c.append(or_(Movie.title.like(like), Movie.original_title.like(like),
                     Movie.keywords_text.like(like), Movie.overview.like(like)))
    return c


def _order(sort: str):
    options = {
        "popularity": Movie.popularity.desc(),
        "rating": rating_expr().desc(),
        "year": Movie.release_year.desc(),
        "title": Movie.title.asc(),
    }
    return [options.get(sort, options["popularity"]), Movie.id.asc()]


def search_movies(db: Session, f: MovieFilters, page: int, page_size: int):
    conditions = build_conditions(f)
    total = db.scalar(select(func.count(Movie.id)).where(*conditions)) or 0
    stmt = (
        select(Movie).where(*conditions).order_by(*_order(f.sort))
        .options(selectinload(Movie.language), selectinload(Movie.genres))
        .offset((page - 1) * page_size).limit(page_size)
    )
    return list(db.scalars(stmt).all()), total
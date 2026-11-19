import re

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.db.session import SessionLocal
from backend.app.models import Movie, MovieCast, UserRating


def slug(text: str) -> str:
    return re.sub(r"\W+", "_", text.lower()).strip("_")


def load_movies_df() -> pd.DataFrame:
    stmt = (
        select(Movie)
        .options(
            selectinload(Movie.language),
            selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.cast).selectinload(MovieCast.actor),
        )
        .order_by(Movie.id)
    )
    rows = []
    with SessionLocal() as db:
        for m in db.scalars(stmt):
            if m.imdb_rating is not None:
                rating, votes, src = m.imdb_rating, m.imdb_votes or 0, "imdb"
            elif m.tmdb_rating and m.tmdb_votes:
                rating, votes, src = m.tmdb_rating, m.tmdb_votes, "tmdb"
            else:
                rating, votes, src = None, 0, None
            cast = m.cast[:10]
            rows.append({
                "id": m.id,
                "title": m.title,
                "language": m.language.name,
                "language_code": m.language.code,
                "release_year": m.release_year,
                "genres": [g.name for g in m.genres],
                "director_ids": [d.id for d in m.directors],
                "cast_ids": [c.actor_id for c in cast],
                "cast_names": [c.actor.name for c in cast],
                "keywords": m.keywords_text or "",
                "overview": m.overview or "",
                "rating": rating,
                "votes": votes,
                "rating_source": src,
            })
    return pd.DataFrame(rows)


def load_ratings_df() -> pd.DataFrame:
    with SessionLocal() as db:
        rows = db.execute(
            select(UserRating.user_id, UserRating.movie_id, UserRating.rating)
        ).all()
    return pd.DataFrame(rows, columns=["user_id", "movie_id", "rating"])


def build_soup(r: dict) -> str:
    """Text used for TF-IDF. Genre and director tokens are repeated to give them more weight."""
    parts = [f"gen_{slug(g)}" for g in r["genres"]] * 3
    parts += [f"dir_{d}" for d in r["director_ids"]] * 2
    parts += [f"act_{a}" for a in r["cast_ids"][:5]]
    if r["keywords"]:
        parts.append(r["keywords"].replace(",", " "))
    if r["overview"]:
        parts.append(r["overview"])
    return " ".join(parts)
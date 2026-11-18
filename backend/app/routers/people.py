import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.deps import movie_filters
from backend.app.models import Actor, Director, MovieCast
from backend.app.repositories.movie_repository import MovieFilters, search_movies
from backend.app.schemas.movie import IMG, MoviePage, PersonOut, to_card

router = APIRouter(prefix="/people", tags=["People"])


def _person(a: Actor) -> PersonOut:
    return PersonOut(id=a.id, name=a.name, gender=a.gender,
                     profile_url=f"{IMG}/w185{a.profile_path}" if a.profile_path else None)


@router.get("", response_model=list[PersonOut])
def search_actors(
    q: str = Query(..., min_length=2, max_length=100),
    gender: str | None = Query(None, pattern="^(male|female|other)$"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """gender=male -> actors, gender=female -> actresses."""
    stmt = select(Actor).where(Actor.name.like(f"%{q}%"))
    if gender:
        stmt = stmt.where(Actor.gender == gender)
    stmt = stmt.order_by(Actor.popularity.desc()).limit(limit)
    return [_person(a) for a in db.scalars(stmt)]


@router.get("/directors", response_model=list[PersonOut])
def search_directors(q: str = Query(..., min_length=2), limit: int = Query(20, ge=1, le=50),
                     db: Session = Depends(get_db)):
    rows = db.scalars(select(Director).where(Director.name.like(f"%{q}%")).limit(limit))
    return [PersonOut(id=d.id, name=d.name,
                      profile_url=f"{IMG}/w185{d.profile_path}" if d.profile_path else None)
            for d in rows]


@router.get("/together", response_model=MoviePage)
def movies_together(
    a: int = Query(..., description="actor id"),
    b: int = Query(..., description="second actor id"),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    movies, total = search_movies(db, MovieFilters(actor_ids=[a, b]), page, page_size)
    return MoviePage(items=[to_card(m) for m in movies], total=total, page=page,
                     page_size=page_size, pages=math.ceil(total / page_size) if total else 0)


@router.get("/{actor_id}")
def actor_profile(actor_id: int, db: Session = Depends(get_db)):
    a = db.get(Actor, actor_id)
    if not a:
        raise HTTPException(404, "Person not found")
    count = db.scalar(select(func.count()).select_from(MovieCast).where(MovieCast.actor_id == a.id))
    return {**_person(a).model_dump(), "movie_count": count}


@router.get("/{actor_id}/movies", response_model=MoviePage)
def filmography(
    actor_id: int,
    filters: MovieFilters = Depends(movie_filters),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Filmography; language, genre, rating and year filters all still apply."""
    if not db.get(Actor, actor_id):
        raise HTTPException(404, "Person not found")
    filters.actor_ids = list({*filters.actor_ids, actor_id})
    movies, total = search_movies(db, filters, page, page_size)
    return MoviePage(items=[to_card(m) for m in movies], total=total, page=page,
                     page_size=page_size, pages=math.ceil(total / page_size) if total else 0)
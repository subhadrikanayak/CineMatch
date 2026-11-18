import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.session import get_db
from backend.app.deps import get_optional_user, movie_filters
from backend.app.models import (
    Genre, Language, Movie, MovieCast, StreamingAvailability, StreamingProvider,
    User, WatchHistory,
)
from backend.app.repositories.movie_repository import MovieFilters, search_movies
from backend.app.schemas.movie import (
    IMG, MovieDetail, MoviePage, PersonOut, StreamingOut, effective_rating, to_card,
)

router = APIRouter(tags=["Movies"])


@router.get("/movies", response_model=MoviePage)
def list_movies(
    filters: MovieFilters = Depends(movie_filters),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    movies, total = search_movies(db, filters, page, page_size)
    return MoviePage(
        items=[to_card(m) for m in movies], total=total, page=page,
        page_size=page_size, pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/movies/{movie_id}", response_model=MovieDetail)
def movie_detail(
    movie_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    m = db.scalar(
        select(Movie).where(Movie.id == movie_id).options(
            selectinload(Movie.language), selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.cast).selectinload(MovieCast.actor),
        )
    )
    if not m:
        raise HTTPException(404, "Movie not found")

    if user:  # feeds "recently viewed" and the taste profile
        db.add(WatchHistory(user_id=user.id, movie_id=m.id, event_type="viewed"))
        db.commit()

    rows = db.execute(
        select(StreamingAvailability, StreamingProvider)
        .join(StreamingProvider, StreamingProvider.id == StreamingAvailability.provider_id)
        .where(StreamingAvailability.movie_id == m.id)
    ).all()

    card = to_card(m)
    rating, votes, source = effective_rating(m)
    return MovieDetail(
        **card.model_dump(),
        original_title=m.original_title, overview=m.overview,
        keywords=[k.strip() for k in (m.keywords_text or "").split(",") if k.strip()],
        backdrop_url=f"{IMG}/w780{m.backdrop_path}" if m.backdrop_path else None,
        release_date=m.release_date.isoformat() if m.release_date else None,
        dubbed_languages=m.dubbed_languages, imdb_id=m.imdb_id,
        cast=[PersonOut(
            id=c.actor.id, name=c.actor.name, gender=c.actor.gender,
            profile_url=f"{IMG}/w185{c.actor.profile_path}" if c.actor.profile_path else None,
            character=c.character_name, order=c.cast_order,
        ) for c in m.cast],
        directors=[PersonOut(id=d.id, name=d.name,
                             profile_url=f"{IMG}/w185{d.profile_path}" if d.profile_path else None)
                   for d in m.directors],
        streaming=[StreamingOut(
            provider=p.name,
            logo_url=f"{IMG}/w92{p.logo_path}" if p.logo_path else None,
            offer_type=a.offer_type, region=a.region,
        ) for a, p in rows],
    )


@router.get("/meta/filters")
def filter_options(db: Session = Depends(get_db)):
    from sqlalchemy import func
    years = db.execute(select(func.min(Movie.release_year), func.max(Movie.release_year))).one()
    return {
        "languages": [{"code": l.code, "name": l.name} for l in db.scalars(select(Language))],
        "genres": [g.name for g in db.scalars(select(Genre).order_by(Genre.name))],
        "year_range": {"min": years[0], "max": years[1]},
        "sort_options": ["popularity", "rating", "year", "title"],
    }
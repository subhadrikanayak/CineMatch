from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.session import get_db
from backend.app.models import Movie
from backend.app.schemas.movie import to_card
from backend.app.schemas.recommendation import CompareMovie, CompareOut
from backend.app.services.recommender_service import get_engine

router = APIRouter(prefix="/compare", tags=["Compare"])


@router.get("", response_model=CompareOut)
def compare(a: int = Query(..., description="movie id"), b: int = Query(..., description="movie id"),
            db: Session = Depends(get_db)):
    if a == b:
        raise HTTPException(400, "Choose two different movies")
    movies = {m.id: m for m in db.scalars(
        select(Movie).where(Movie.id.in_([a, b])).options(
            selectinload(Movie.language), selectinload(Movie.genres), selectinload(Movie.directors)))}
    if len(movies) != 2:
        raise HTTPException(404, "One or both movies not found")

    def build(m: Movie) -> CompareMovie:
        return CompareMovie(**to_card(m).model_dump(), directors=[d.name for d in m.directors])

    A, B = build(movies[a]), build(movies[b])
    warnings = []

    diff = higher = None
    if A.rating is not None and B.rating is not None:
        if A.rating_source == B.rating_source:
            diff = round(abs(A.rating - B.rating), 1)
            if diff > 0:
                higher = a if A.rating > B.rating else b
        else:
            warnings.append("Ratings come from different sources (IMDb vs TMDB), so they "
                            "are not directly comparable.")
    else:
        warnings.append("At least one movie has no rating yet.")

    popular = None
    if A.popularity is not None and B.popularity is not None and A.popularity != B.popularity:
        popular = a if A.popularity > B.popularity else b

    sim = None
    idx = get_engine().content.index
    if a in idx and b in idx:
        m = get_engine().content.matrix
        sim = round(float((m[idx[a]] @ m[idx[b]].T).toarray()[0, 0]), 3)

    return CompareOut(
        a=A, b=B,
        shared_genres=[g for g in A.genres if g in B.genres],
        same_language=A.language == B.language,
        rating_difference=diff, higher_rated=higher, more_popular=popular,
        year_gap=abs(A.release_year - B.release_year) if A.release_year and B.release_year else None,
        content_similarity=sim, warnings=warnings,
    )
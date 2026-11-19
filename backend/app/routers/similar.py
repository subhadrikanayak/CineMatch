from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.recommendation import SimilarOut
from backend.app.services.recommender_service import cards_for, get_engine

router = APIRouter(tags=["Similar"])


@router.get("/movies/{movie_id}/similar", response_model=list[SimilarOut])
def similar_movies(movie_id: int, limit: int = Query(10, ge=1, le=30),
                   language: list[str] | None = Query(None),
                   db: Session = Depends(get_db)):
    """TF-IDF + cosine similarity over genres, cast, directors, keywords and overview."""
    engine = get_engine()
    if movie_id not in engine.pos:
        raise HTTPException(404, "Movie not in the recommender yet. Run `python -m ml.train` and restart.")
    pairs = engine.content.similar(movie_id, top_n=len(engine.ids))
    if language:
        wanted = {x.lower() for x in language}
        pairs = [(m, s) for m, s in pairs if engine.records[engine.pos[m]]["language_code"] in wanted]
    pairs = [(m, s) for m, s in pairs if s > 0][:limit]

    seed = engine.records[engine.pos[movie_id]]
    cards = cards_for(db, [m for m, _ in pairs])
    out = []
    for m, sim in pairs:
        if m not in cards:
            continue
        rec = engine.records[engine.pos[m]]
        shared_cast = [n for a, n in zip(rec["cast_ids"], rec["cast_names"]) if a in set(seed["cast_ids"])]
        out.append(SimilarOut(
            movie=cards[m], similarity=round(sim, 3),
            shared_genres=[g for g in rec["genres"] if g in seed["genres"]],
            shared_cast=shared_cast,
            same_director=bool(set(rec["director_ids"]) & set(seed["director_ids"])),
        ))
    return out
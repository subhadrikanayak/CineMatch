from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import Actor
from backend.app.repositories.movie_repository import MovieFilters, search_movies
from backend.app.schemas.movie import IMG, MovieCard, PersonOut, to_card
from backend.app.schemas.recommendation import SemanticIn, SemanticItem, SemanticOut
from backend.app.services.recommender_service import (
    candidate_ids, cards_for, get_engine, get_semantic,
)
from ml.semantic import parse_query

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("")
def quick_search(q: str = Query(..., min_length=2, max_length=100),
                 limit: int = Query(8, ge=1, le=20), db: Session = Depends(get_db)):
    """Navbar autocomplete: matching movies and people."""
    movies, _ = search_movies(db, MovieFilters(q=q), 1, limit)
    people = db.scalars(select(Actor).where(Actor.name.like(f"%{q}%"))
                        .order_by(Actor.popularity.desc()).limit(limit))
    return {
        "movies": [to_card(m) for m in movies],
        "people": [PersonOut(id=a.id, name=a.name, gender=a.gender,
                             profile_url=f"{IMG}/w185{a.profile_path}" if a.profile_path else None)
                   for a in people],
    }


@router.post("/semantic", response_model=SemanticOut)
def semantic_search(body: SemanticIn, db: Session = Depends(get_db)):
    engine = get_engine()
    index = get_semantic()
    parsed = parse_query(body.query)

    f = body.to_filters()           # filters chosen in the UI win; the query only fills gaps
    f.languages = f.languages or parsed.languages
    f.genres = f.genres or parsed.genres
    f.year_min = f.year_min if f.year_min is not None else parsed.year_min
    f.year_max = f.year_max if f.year_max is not None else parsed.year_max
    f.min_rating = f.min_rating if f.min_rating is not None else parsed.min_rating

    cands = candidate_ids(db, f)
    ids = cands if cands is not None else list(engine.ids)
    applied = {"languages": f.languages, "genres": f.genres, "year_min": f.year_min,
               "year_max": f.year_max, "min_rating": f.min_rating,
               "description_text": parsed.text}

    note = None
    items: list[SemanticItem] = []
    if parsed.text:
        sims = {m: s for m, s in index.search(parsed.text, ids).items() if s > 0}
        top = sorted(sims.items(), key=lambda x: -x[1])[: body.k]
        best = top[0][1] if top else 1.0
        cards = cards_for(db, [m for m, _ in top])
        for m, s in top:
            if m not in cards:
                continue
            reasons = []
            if f.languages:
                reasons.append(f"Language: {cards[m].language}")
            if f.genres:
                reasons.append("Genre: " + ", ".join(g for g in cards[m].genres if g in f.genres))
            terms = index.matched_terms(parsed.text, m)
            reasons.append(f"Description matches: {', '.join(terms[:5])}" if terms
                           else f"Semantically close to your description (cosine {s:.2f})")
            items.append(SemanticItem(movie=cards[m], similarity=round(s, 3),
                                      match_percent=int(round(s / best * 100)), reasons=reasons))
        if not items:
            note = "No movie descriptions matched your wording. Try different words."
    else:
        recs = engine.recommend(build_empty(), ids, k=body.k, min_rating=f.min_rating)
        cards = cards_for(db, [r.movie_id for r in recs])
        items = [SemanticItem(movie=cards[r.movie_id], similarity=None,
                              match_percent=r.match_percent, reasons=r.reasons)
                 for r in recs if r.movie_id in cards]
        note = "Your query only contained filters, so results are ranked by weighted rating."

    if index.engine == "tfidf":
        extra = ("Matching uses TF-IDF on movie descriptions (word overlap, not true "
                 "meaning). Install Sentence Transformers for deeper semantic matching.")
        note = f"{note} {extra}" if note else extra
    return SemanticOut(engine=index.engine, parsed=applied, items=items,
                       candidates=len(ids), note=note)


def build_empty():
    from ml.hybrid import UserSignals
    return UserSignals()
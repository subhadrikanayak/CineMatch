import random

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.deps import get_current_user, get_optional_user, movie_filters
from backend.app.models import User
from backend.app.repositories.movie_repository import MovieFilters
from backend.app.schemas.recommendation import (
    GemList, GemOut, RecommendIn, RecommendationList, SurpriseIn, SurpriseOut,
)
from backend.app.services.recommender_service import (
    build_signals, candidate_ids, cards_for, comfort_zone, get_engine, has_signal,
    log_history, popularity_map, to_out,
)
from ml.hidden_gems import find_gems

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _package(db, engine, recs, signals, cands) -> RecommendationList:
    return RecommendationList(
        items=to_out(db, recs),
        candidates=len(cands) if cands is not None else len(engine.ids),
        personalised=has_signal(signals),
        collaborative_active=bool(recs and recs[0].weights.get("collab", 0) > 0),
        weights_used=recs[0].weights if recs else {},
    )


@router.post("", response_model=RecommendationList)
def recommend(body: RecommendIn, db: Session = Depends(get_db),
              user: User | None = Depends(get_optional_user)):
    """Hard filters run first; the hybrid model only ranks what survives them."""
    engine = get_engine()
    cands = candidate_ids(db, body.to_filters())
    signals = build_signals(db, user)
    recs = engine.recommend(signals, cands, k=body.k, weights=body.weights,
                            diversify=body.diversify, mmr_lambda=body.mmr_lambda,
                            min_rating=body.min_rating)
    log_history(db, user, recs, "hybrid")
    return _package(db, engine, recs, signals, cands)


@router.get("/me", response_model=RecommendationList)
def my_recommendations(filters: MovieFilters = Depends(movie_filters),
                       k: int = Query(20, ge=1, le=50),
                       db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    engine = get_engine()
    cands = candidate_ids(db, filters)
    signals = build_signals(db, user)
    recs = engine.recommend(signals, cands, k=k, min_rating=filters.min_rating)
    log_history(db, user, recs, "hybrid")
    return _package(db, engine, recs, signals, cands)


@router.get("/hidden-gems", response_model=GemList)
def hidden_gems(filters: MovieFilters = Depends(movie_filters),
                limit: int = Query(20, ge=1, le=50),
                min_votes: int = Query(50, ge=1),
                db: Session = Depends(get_db)):
    engine = get_engine()
    cands = candidate_ids(db, filters)
    rows, th = find_gems(engine.df, popularity_map(db), cands, min_votes=min_votes, limit=limit)
    cards = cards_for(db, [int(r["id"]) for r in rows])
    items = []
    for r in rows:
        mid = int(r["id"])
        if mid not in cards:
            continue
        pct = int(round(r["pop_pct"] * 100))
        src = (r["rating_source"] or "").upper()
        items.append(GemOut(
            movie=cards[mid], gem_score=round(float(r["gem_score"]), 3),
            popularity_percentile=pct,
            reasons=[
                f"Weighted rating {r['wr']:.1f}/10 ({src}) from {int(r['votes'])} votes: "
                f"enough votes to be credible",
                f"Lesser-known: more popular than only {pct}% of the catalogue",
            ],
        ))
    return GemList(items=items, thresholds={k_: round(v, 2) for k_, v in th.items()})


@router.post("/surprise", response_model=SurpriseOut)
def surprise(body: SurpriseIn, db: Session = Depends(get_db),
             user: User | None = Depends(get_optional_user)):
    """A random pick. Randomness is the feature here; no score is invented."""
    engine = get_engine()
    signals = build_signals(db, user)
    base = candidate_ids(db, body.to_filters())
    pool = base if base is not None else list(engine.ids)
    skip = signals.seen_ids | set(signals.ratings) | signals.disliked_ids
    pool = [m for m in pool if m in engine.pos and m not in skip]
    if not pool:
        raise HTTPException(404, "No unseen movies match those filters")
    reasons = [f"Randomly picked from {len(pool)} unseen movie(s) matching your filters"]

    if body.outside_comfort_zone:
        langs, genres = comfort_zone(engine, signals)
        if not langs and not genres:
            reasons.append("No taste data yet, so this is a plain random pick")
        else:
            rec_of = lambda m: engine.records[engine.pos[m]]
            strict = [m for m in pool if rec_of(m)["language_code"] not in langs
                      and not set(rec_of(m)["genres"]) & genres]
            relaxed = [m for m in pool if rec_of(m)["language_code"] not in langs
                       or not set(rec_of(m)["genres"]) & genres]
            if strict:
                pool = strict
                reasons.append("Outside your usual languages and genres")
            elif relaxed:
                pool = relaxed
                reasons.append("Outside your usual language or genres (no movie differed in both)")
            else:
                reasons.append("Nothing in this selection is outside your usual taste")

    pick = random.choice(pool)
    cards = cards_for(db, [pick])
    return SurpriseOut(movie=cards[pick], reasons=reasons, candidates=len(pool))
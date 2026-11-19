from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.deps import get_optional_user
from backend.app.models import User
from backend.app.schemas.recommendation import MoodIn, RecommendationList
from backend.app.services.recommender_service import (
    build_signals, candidate_ids, get_engine, has_signal, ids_with_any_genre,
    log_history, to_out,
)
from ml.mood_profiles import MOODS, mood_seed, normalize_mood

router = APIRouter(prefix="/moods", tags=["Mood"])


@router.get("")
def list_moods():
    return [{"id": k, "label": v["label"], "genres": v["genres"]} for k, v in MOODS.items()]


@router.post("/recommend", response_model=RecommendationList)
def mood_recommend(body: MoodIn, db: Session = Depends(get_db),
                   user: User | None = Depends(get_optional_user)):
    key = normalize_mood(body.mood)
    mood = MOODS.get(key)
    if not mood:
        raise HTTPException(400, f"Unknown mood. Choose from: {', '.join(MOODS)}")
    engine = get_engine()

    base = candidate_ids(db, body.to_filters())
    mood_ids = ids_with_any_genre(db, mood["genres"])
    cands = [m for m in (base if base is not None else engine.ids) if m in mood_ids]

    signals = build_signals(db, user)
    recs = engine.recommend(signals, cands, k=body.k, seed_text=mood_seed(mood),
                            weights={"content": 0.7, "pop": 0.15},
                            min_rating=body.min_rating)
    for r in recs:
        genres = engine.records[engine.pos[r.movie_id]]["genres"]
        overlap = [g for g in genres if g in mood["genres"]]
        r.reasons.insert(0, f"Fits the {mood['label']} mood ({', '.join(overlap)})")
        del r.reasons[5:]
    log_history(db, user, recs, "mood")

    return RecommendationList(
        items=to_out(db, recs), candidates=len(cands), personalised=has_signal(signals),
        collaborative_active=bool(recs and recs[0].weights.get("collab", 0) > 0),
        weights_used=recs[0].weights if recs else {},
    )
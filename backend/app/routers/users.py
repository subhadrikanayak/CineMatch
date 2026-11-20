from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.deps import get_current_user
from backend.app.models import (
    Actor, Genre, Language, RecommendationFeedback, User, UserPreference, UserRating,
    Watchlist, WatchHistory,
)
from backend.app.schemas.movie import IMG, PersonOut
from backend.app.schemas.user import (
    ActivityItem, ActivityPage, LanguageOut, PreferencesIn, PreferencesOut,
    TasteProfileOut, make_page,
)
from backend.app.services.recommender_service import cards_for
from backend.app.services.taste_service import compute_taste

router = APIRouter(prefix="/users/me", tags=["User"])


def _prefs_out(db: Session, user_id: int) -> PreferencesOut:
    rows = db.execute(select(UserPreference.pref_type, UserPreference.ref_id)
                      .where(UserPreference.user_id == user_id)).all()
    ids = lambda t: [r for k, r in rows if k == t]
    langs = db.scalars(select(Language).where(Language.id.in_(ids("language"))).order_by(Language.name))
    genres = db.scalars(select(Genre).where(Genre.id.in_(ids("genre"))).order_by(Genre.name))
    actors = db.scalars(select(Actor).where(Actor.id.in_(ids("actor"))).order_by(Actor.name))
    return PreferencesOut(
        languages=[LanguageOut(code=l.code, name=l.name) for l in langs],
        genres=[g.name for g in genres],
        actors=[PersonOut(id=a.id, name=a.name, gender=a.gender,
                          profile_url=f"{IMG}/w185{a.profile_path}" if a.profile_path else None)
                for a in actors],
    )


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _prefs_out(db, user.id)


@router.put("/preferences", response_model=PreferencesOut)
def set_preferences(body: PreferencesIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """Replaces ALL your favourites with exactly what you send."""
    langs = list(db.scalars(select(Language).where(Language.code.in_(body.languages))))
    genres = list(db.scalars(select(Genre).where(Genre.name.in_(body.genres))))
    actors = list(db.scalars(select(Actor).where(Actor.id.in_(body.actor_ids))))
    bad_genres = set(body.genres) - {g.name for g in genres}
    bad_actors = set(body.actor_ids) - {a.id for a in actors}
    if bad_genres:
        raise HTTPException(400, f"Unknown genre(s): {sorted(bad_genres)}")
    if bad_actors:
        raise HTTPException(400, f"Unknown actor id(s): {sorted(bad_actors)}")

    db.execute(delete(UserPreference).where(UserPreference.user_id == user.id))
    db.add_all(
        [UserPreference(user_id=user.id, pref_type="language", ref_id=l.id) for l in langs]
        + [UserPreference(user_id=user.id, pref_type="genre", ref_id=g.id) for g in genres]
        + [UserPreference(user_id=user.id, pref_type="actor", ref_id=a.id) for a in actors])
    db.commit()
    return _prefs_out(db, user.id)


@router.get("/taste-profile", response_model=TasteProfileOut)
def taste_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return compute_taste(db, user)


@router.get("/history", response_model=ActivityPage)
def watched_history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Movies you marked as watched (or rated)."""
    cond = (WatchHistory.user_id == user.id, WatchHistory.event_type == "watched")
    total = db.scalar(select(func.count()).select_from(WatchHistory).where(*cond)) or 0
    rows = list(db.scalars(select(WatchHistory).where(*cond)
                           .order_by(WatchHistory.occurred_at.desc(), WatchHistory.id.desc())
                           .offset((page - 1) * page_size).limit(page_size)))
    cards = cards_for(db, [r.movie_id for r in rows])
    items = [ActivityItem(movie=cards[r.movie_id], at=r.occurred_at)
             for r in rows if r.movie_id in cards]
    return make_page(items, total, page, page_size)


@router.get("/recent", response_model=list[ActivityItem])
def recently_viewed(limit: int = Query(12, ge=1, le=50), db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """Detail pages you opened lately, newest first, one entry per movie."""
    last = func.max(WatchHistory.occurred_at)
    rows = db.execute(
        select(WatchHistory.movie_id, last.label("t"))
        .where(WatchHistory.user_id == user.id, WatchHistory.event_type == "viewed")
        .group_by(WatchHistory.movie_id).order_by(last.desc()).limit(limit)).all()
    cards = cards_for(db, [m for m, _ in rows])
    return [ActivityItem(movie=cards[m], at=t) for m, t in rows if m in cards]


@router.get("/movie-state/{movie_id}")
def movie_state(movie_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """Everything the movie page needs to draw its buttons correctly."""
    rating = db.scalar(select(UserRating.rating).where(
        UserRating.user_id == user.id, UserRating.movie_id == movie_id))
    on_list = db.scalar(select(Watchlist.id).where(
        Watchlist.user_id == user.id, Watchlist.movie_id == movie_id)) is not None
    watched = db.scalar(select(WatchHistory.id).where(
        WatchHistory.user_id == user.id, WatchHistory.movie_id == movie_id,
        WatchHistory.event_type == "watched")) is not None
    reaction = db.scalar(select(RecommendationFeedback.feedback_type).where(
        RecommendationFeedback.user_id == user.id, RecommendationFeedback.movie_id == movie_id,
        RecommendationFeedback.feedback_type.in_(["like", "dislike"]))
        .order_by(RecommendationFeedback.id.desc()).limit(1))
    return {"rating": rating, "in_watchlist": on_list, "watched": watched, "reaction": reaction}
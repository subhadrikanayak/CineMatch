import logging
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.deps import movie_filters, require_admin
from backend.app.models import (
    Genre, Language, Movie, MovieGenre, RecommendationFeedback, RecommendationHistory,
    StreamingAvailability, User, UserRating, Watchlist, WatchHistory,
)
from backend.app.repositories.movie_repository import MovieFilters, search_movies
from backend.app.schemas.movie import MoviePage, to_card
from backend.app.services.recommender_service import cards_for, holder, load_engine
from ml.collaborative import MIN_RATINGS, MIN_USERS, CollaborativeModel
from ml.content_based import ContentModel
from ml.data import load_movies_df, load_ratings_df

log = logging.getLogger("admin")
router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])

ROOT = Path(__file__).resolve().parents[3]            # D:\CineMatch
INGEST_LOG = ROOT / "ml" / "artifacts" / "ingest.log"
_retrain_lock = threading.Lock()
_ingest: dict = {"proc": None, "log": None, "started": None, "pages": None, "languages": None}

EVENTS = [("views", WatchHistory, [WatchHistory.event_type == "viewed"]),
          ("ratings", UserRating, []),
          ("watchlist", Watchlist, [])]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _count(db: Session, model, *conds) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*conds)) or 0


# ---------------------------------------------------------------- overview
@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    week = _now() - timedelta(days=7)
    active = db.scalar(select(func.count(func.distinct(WatchHistory.user_id)))
                       .where(WatchHistory.occurred_at >= week)) or 0
    rating_users = db.scalar(select(func.count(func.distinct(UserRating.user_id)))) or 0
    by_source = {(k or "none"): v for k, v in db.execute(
        select(Movie.ratings_source, func.count()).group_by(Movie.ratings_source)).all()}
    eng = holder.engine
    return {
        "users": _count(db, User), "movies": _count(db, Movie),
        "ratings": _count(db, UserRating), "watchlist_items": _count(db, Watchlist),
        "feedback": _count(db, RecommendationFeedback),
        "recommendations_served": _count(db, RecommendationHistory),
        "active_users_7d": active,
        "catalogue": {
            "by_rating_source": by_source,
            "with_imdb_rating": _count(db, Movie, Movie.imdb_rating.is_not(None)),
            "missing_overview": _count(db, Movie, Movie.overview.is_(None)),
            "missing_poster": _count(db, Movie, Movie.poster_path.is_(None)),
            "with_streaming_data": db.scalar(
                select(func.count(func.distinct(StreamingAvailability.movie_id)))) or 0,
        },
        "engine": {
            "loaded": eng is not None,
            "movies_in_model": len(eng.ids) if eng else 0,
            "collaborative_ready": bool(eng and eng.collab.ready),
            "semantic_engine": holder.semantic.engine if holder.semantic else None,
            "ratings_in_db": _count(db, UserRating), "users_who_rated": rating_users,
            "ratings_needed": MIN_RATINGS, "users_needed": MIN_USERS,
        },
    }


@router.get("/movies", response_model=MoviePage)
def catalogue(filters: MovieFilters = Depends(movie_filters),
              page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
              db: Session = Depends(get_db)):
    import math
    movies, total = search_movies(db, filters, page, page_size)
    return MoviePage(items=[to_card(m) for m in movies], total=total, page=page,
                     page_size=page_size, pages=math.ceil(total / page_size) if total else 0)


# ---------------------------------------------------------------- activity
def _cnt(model, *extra):
    return (select(func.count()).select_from(model)
            .where(model.user_id == User.id, *extra).correlate(User).scalar_subquery())


@router.get("/users-activity")
def users_activity(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                   db: Session = Depends(get_db)):
    last_seen = (select(func.max(WatchHistory.occurred_at))
                 .where(WatchHistory.user_id == User.id).correlate(User).scalar_subquery())
    stmt = (select(User.id, User.username, User.created_at,
                   _cnt(UserRating).label("ratings"),
                   _cnt(Watchlist).label("watchlist"),
                   _cnt(WatchHistory, WatchHistory.event_type == "viewed").label("views"),
                   _cnt(RecommendationHistory).label("recommendations_received"),
                   last_seen.label("last_active"))
            .order_by(last_seen.desc(), User.id.desc())
            .offset((page - 1) * page_size).limit(page_size))
    return {"items": [dict(r._mapping) for r in db.execute(stmt)],
            "total": _count(db, User), "page": page, "page_size": page_size}


@router.get("/popular-movies")
def popular_movies(by: str = Query("views", pattern="^(views|ratings|watchlist)$"),
                   limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    _, model, conds = next(e for e in EVENTS if e[0] == by)
    n = func.count().label("n")
    rows = db.execute(select(model.movie_id, n).where(*conds)
                      .group_by(model.movie_id).order_by(n.desc()).limit(limit)).all()
    cards = cards_for(db, [m for m, _ in rows])
    return [{"movie": cards[m], "count": c} for m, c in rows if m in cards]


# ---------------------------------------------------------------- trends
def _engagement(db: Session, via_genre: bool) -> dict[str, dict]:
    label = Genre.name if via_genre else Language.name
    out: dict[str, dict] = {}
    for key, model, conds in EVENTS:
        if via_genre:
            stmt = (select(label, func.count()).select_from(model)
                    .join(MovieGenre, MovieGenre.movie_id == model.movie_id)
                    .join(Genre, Genre.id == MovieGenre.genre_id))
        else:
            stmt = (select(label, func.count()).select_from(model)
                    .join(Movie, Movie.id == model.movie_id)
                    .join(Language, Language.id == Movie.original_language_id))
        for name, c in db.execute(stmt.where(*conds).group_by(label)).all():
            out.setdefault(name, {})[key] = c
    return out


def _trends(db: Session, via_genre: bool):
    if via_genre:
        cat = db.execute(select(Genre.name, func.count(MovieGenre.movie_id))
                         .select_from(Genre).outerjoin(MovieGenre, MovieGenre.genre_id == Genre.id)
                         .group_by(Genre.name)).all()
    else:
        cat = db.execute(select(Language.name, func.count(Movie.id))
                         .select_from(Language).outerjoin(Movie, Movie.original_language_id == Language.id)
                         .group_by(Language.name)).all()
    eng = _engagement(db, via_genre)
    rows = []
    for name, in_catalogue in cat:
        e = eng.get(name, {})
        v, r, w = e.get("views", 0), e.get("ratings", 0), e.get("watchlist", 0)
        rows.append({"name": name, "catalogue": in_catalogue, "views": v, "ratings": r,
                     "watchlist": w, "engagement": v + r + w})
    return sorted(rows, key=lambda x: (-x["engagement"], -x["catalogue"]))


@router.get("/trends/languages")
def language_trends(db: Session = Depends(get_db)):
    return _trends(db, via_genre=False)


@router.get("/trends/genres")
def genre_trends(db: Session = Depends(get_db)):
    return _trends(db, via_genre=True)


# ---------------------------------------------------------------- analytics
@router.get("/recommendation-analytics")
def recommendation_analytics(db: Session = Depends(get_db)):
    """Recommendations are logged only for logged-in users, so these count what they were shown."""
    by_source = [{"source": s, "served": n, "avg_match_percent": round(float(a or 0) * 100, 1)}
                 for s, n, a in db.execute(
                     select(RecommendationHistory.source, func.count(), func.avg(RecommendationHistory.score))
                     .group_by(RecommendationHistory.source))]
    n = func.count().label("n")
    top = db.execute(select(RecommendationHistory.movie_id, n).group_by(RecommendationHistory.movie_id)
                     .order_by(n.desc()).limit(10)).all()
    cards = cards_for(db, [m for m, _ in top])
    day = func.date(RecommendationHistory.created_at)
    since = _now() - timedelta(days=14)
    daily = [{"date": d, "served": c} for d, c in db.execute(
        select(day, func.count()).where(RecommendationHistory.created_at >= since)
        .group_by(day).order_by(day))]
    fb = dict(db.execute(select(RecommendationFeedback.feedback_type, func.count())
                         .group_by(RecommendationFeedback.feedback_type)).all())
    likes, dislikes = fb.get("like", 0), fb.get("dislike", 0)
    return {
        "total_served": _count(db, RecommendationHistory),
        "users_served": db.scalar(select(func.count(func.distinct(RecommendationHistory.user_id)))) or 0,
        "by_source": by_source,
        "most_recommended": [{"movie": cards[m], "times": c} for m, c in top if m in cards],
        "last_14_days": daily,
        "feedback": {"likes": likes, "dislikes": dislikes, "comments": fb.get("comment", 0),
                     "like_rate_percent": round(likes / (likes + dislikes) * 100, 1)
                     if likes + dislikes else None},
    }


# ---------------------------------------------------------------- maintenance
@router.post("/retrain")
def retrain():
    """Refit TF-IDF and the SVD model on the current database, save them, reload the engine."""
    if not _retrain_lock.acquire(blocking=False):
        raise HTTPException(409, "A retrain is already running")
    try:
        df = load_movies_df()
        if df.empty:
            raise HTTPException(400, "No movies in the database")
        content = ContentModel.fit(df)
        content.save()
        ratings = load_ratings_df()
        collab = CollaborativeModel.fit(ratings, df["id"].tolist())
        collab.save()
        load_engine()
        return {"movies": len(df), "tfidf_features": int(content.matrix.shape[1]),
                "ratings_used": len(ratings), "collaborative_ready": collab.ready,
                "semantic_engine": holder.semantic.engine if holder.semantic else None,
                "note": "If you use Sentence Transformers, also run python -m ml.build_embeddings."}
    finally:
        _retrain_lock.release()


class IngestIn(BaseModel):
    pages: int = Field(2, ge=1, le=10, description="pages per language, 20 movies per page")
    languages: list[str] = Field(default_factory=lambda: ["hi", "te", "ta", "ml", "kn"])


def _ingest_running() -> bool:
    p = _ingest["proc"]
    return p is not None and p.poll() is None


@router.post("/ingest", status_code=202)
def start_ingest(body: IngestIn):
    """Runs the TMDB ingestion script in the background. Needs your VPN on."""
    if _ingest_running():
        raise HTTPException(409, "An ingestion is already running")
    if not settings.TMDB_API_KEY:
        raise HTTPException(400, "TMDB_API_KEY is empty in .env")
    bad = set(body.languages) - {"hi", "te", "ta", "ml", "kn"}
    if bad:
        raise HTTPException(400, f"Unknown language code(s): {sorted(bad)}")
    if _ingest["log"]:
        _ingest["log"].close()
    INGEST_LOG.parent.mkdir(parents=True, exist_ok=True)
    logf = open(INGEST_LOG, "w", encoding="utf-8")
    cmd = [sys.executable, "-m", "backend.scripts.ingest_tmdb",
           "--pages", str(body.pages), "--languages", *body.languages]
    _ingest.update(proc=subprocess.Popen(cmd, cwd=ROOT, stdout=logf, stderr=subprocess.STDOUT),
                   log=logf, started=_now().isoformat(), pages=body.pages, languages=body.languages)
    return {"status": "started", "pages": body.pages, "languages": body.languages,
            "next": "Poll GET /admin/ingest/status. When finished, call POST /admin/retrain."}


@router.get("/ingest/status")
def ingest_status():
    p = _ingest["proc"]
    lines = []
    if INGEST_LOG.exists():
        lines = INGEST_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-15:]
    return {"running": _ingest_running(), "started": _ingest["started"],
            "exit_code": None if p is None or p.poll() is None else p.poll(),
            "pages": _ingest["pages"], "languages": _ingest["languages"], "last_log_lines": lines}
import logging
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import (
    Genre, Language, Movie, MovieGenre, RecommendationFeedback, RecommendationHistory,
    User, UserPreference, UserRating, Watchlist, WatchHistory,
)
from backend.app.repositories.movie_repository import MovieFilters, build_conditions
from backend.app.schemas.movie import MovieCard, to_card
from backend.app.schemas.recommendation import RecommendationOut
from ml.hybrid import HybridRecommender, Recommendation, UserSignals
from ml.semantic import SemanticIndex

log = logging.getLogger("recommender_service")


class _Holder:
    engine: HybridRecommender | None = None
    semantic: SemanticIndex | None = None


holder = _Holder()


def load_engine() -> None:
    try:
        holder.engine = HybridRecommender.load()
        holder.semantic = SemanticIndex(holder.engine.df)
        log.info("Recommendation engine ready: %d movies, collaborative=%s, semantic=%s",
                 len(holder.engine.ids), holder.engine.collab.ready, holder.semantic.engine)
    except Exception as exc:
        holder.engine = holder.semantic = None
        log.error("Recommendation engine NOT loaded: %s", exc)


def get_engine() -> HybridRecommender:
    if holder.engine is None:
        raise HTTPException(503, "Recommendation engine not loaded. Load movies, run "
                                 "`python -m ml.train`, then restart the API.")
    return holder.engine


def get_semantic() -> SemanticIndex:
    get_engine()
    return holder.semantic


def build_signals(db: Session, user: User | None) -> UserSignals:
    if user is None:
        return UserSignals()
    s = UserSignals(user_id=user.id)
    s.ratings = {r.movie_id: r.rating for r in
                 db.scalars(select(UserRating).where(UserRating.user_id == user.id))}
    s.watchlist_ids = set(db.scalars(select(Watchlist.movie_id).where(Watchlist.user_id == user.id)))
    s.seen_ids = set(db.scalars(select(WatchHistory.movie_id).where(
        WatchHistory.user_id == user.id, WatchHistory.event_type == "watched")))
    for fb in db.scalars(select(RecommendationFeedback).where(
            RecommendationFeedback.user_id == user.id,
            RecommendationFeedback.feedback_type.in_(["like", "dislike"]))
            .order_by(RecommendationFeedback.id)):          # latest feedback wins
        if fb.feedback_type == "like":
            s.liked_ids.add(fb.movie_id)
            s.disliked_ids.discard(fb.movie_id)
        else:
            s.disliked_ids.add(fb.movie_id)
            s.liked_ids.discard(fb.movie_id)
    prefs = db.execute(select(UserPreference.pref_type, UserPreference.ref_id)
                       .where(UserPreference.user_id == user.id)).all()
    lang_ids = [r for t, r in prefs if t == "language"]
    genre_ids = [r for t, r in prefs if t == "genre"]
    if lang_ids:
        s.fav_languages = set(db.scalars(select(Language.code).where(Language.id.in_(lang_ids))))
    if genre_ids:
        s.fav_genres = set(db.scalars(select(Genre.name).where(Genre.id.in_(genre_ids))))
    s.fav_actor_ids = {r for t, r in prefs if t == "actor"}
    return s


def has_signal(s: UserSignals) -> bool:
    return bool(s.ratings or s.liked_ids or s.watchlist_ids
                or s.fav_languages or s.fav_genres or s.fav_actor_ids)


def candidate_ids(db: Session, f: MovieFilters) -> list[int] | None:
    """None means 'no hard filters'. Otherwise the ids that satisfy every filter."""
    conds = build_conditions(f)
    if not conds:
        return None
    return list(db.scalars(select(Movie.id).where(*conds)))


def ids_with_any_genre(db: Session, names: list[str]) -> set[int]:
    return set(db.scalars(
        select(MovieGenre.movie_id).join(Genre, Genre.id == MovieGenre.genre_id)
        .where(Genre.name.in_(names)).distinct()))


def popularity_map(db: Session) -> dict:
    return {i: p for i, p in db.execute(select(Movie.id, Movie.popularity)).all()}


def cards_for(db: Session, ids: list[int]) -> dict[int, MovieCard]:
    if not ids:
        return {}
    stmt = (select(Movie).where(Movie.id.in_(ids))
            .options(selectinload(Movie.language), selectinload(Movie.genres)))
    return {m.id: to_card(m) for m in db.scalars(stmt)}


def to_out(db: Session, recs: list[Recommendation]) -> list[RecommendationOut]:
    cards = cards_for(db, [r.movie_id for r in recs])
    return [RecommendationOut(movie=cards[r.movie_id], match_percent=r.match_percent,
                              score=r.score, components=r.components, weights=r.weights,
                              reasons=r.reasons)
            for r in recs if r.movie_id in cards]


def log_history(db: Session, user: User | None, recs: list[Recommendation], source: str) -> None:
    if user is None or not recs:
        return
    db.add_all([RecommendationHistory(
        user_id=user.id, movie_id=r.movie_id, score=r.score, source=source,
        explanation={"match_percent": r.match_percent, "components": r.components,
                     "weights": r.weights, "reasons": r.reasons},
    ) for r in recs])
    db.commit()


def comfort_zone(engine: HybridRecommender, s: UserSignals):
    liked = {m for m, r in s.ratings.items() if r >= 4} | s.liked_ids
    langs, genres, counts = set(s.fav_languages), set(s.fav_genres), Counter()
    for m in liked:
        p = engine.pos.get(m)
        if p is None:
            continue
        rec = engine.records[p]
        langs.add(rec["language_code"])
        counts.update(rec["genres"])
    genres |= {g for g, _ in counts.most_common(3)}
    return langs, genres
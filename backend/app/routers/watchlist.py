from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.deps import get_current_user
from backend.app.models import Movie, User, Watchlist, WatchHistory
from backend.app.schemas.user import ActivityItem, ActivityPage, make_page
from backend.app.services.recommender_service import cards_for

router = APIRouter(tags=["Watchlist"])


def _require_movie(db: Session, movie_id: int) -> None:
    if not db.get(Movie, movie_id):
        raise HTTPException(404, "Movie not found")


@router.get("/watchlist", response_model=ActivityPage)
def get_watchlist(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total = db.scalar(select(func.count()).select_from(Watchlist)
                      .where(Watchlist.user_id == user.id)) or 0
    rows = list(db.scalars(
        select(Watchlist).where(Watchlist.user_id == user.id)
        .order_by(Watchlist.added_at.desc(), Watchlist.id.desc())
        .offset((page - 1) * page_size).limit(page_size)))
    cards = cards_for(db, [r.movie_id for r in rows])
    items = [ActivityItem(movie=cards[r.movie_id], at=r.added_at)
             for r in rows if r.movie_id in cards]
    return make_page(items, total, page, page_size)


@router.post("/watchlist/{movie_id}", response_model=ActivityItem)
def add_to_watchlist(movie_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Safe to call twice: adding a movie already on the list changes nothing."""
    _require_movie(db, movie_id)
    row = db.scalar(select(Watchlist).where(
        Watchlist.user_id == user.id, Watchlist.movie_id == movie_id))
    if not row:
        row = Watchlist(user_id=user.id, movie_id=movie_id)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            row = db.scalar(select(Watchlist).where(
                Watchlist.user_id == user.id, Watchlist.movie_id == movie_id))
        else:
            db.refresh(row)
    return ActivityItem(movie=cards_for(db, [movie_id])[movie_id], at=row.added_at)


@router.delete("/watchlist/{movie_id}", status_code=204)
def remove_from_watchlist(movie_id: int, db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    row = db.scalar(select(Watchlist).where(
        Watchlist.user_id == user.id, Watchlist.movie_id == movie_id))
    if not row:
        raise HTTPException(404, "Movie is not on your watchlist")
    db.delete(row)
    db.commit()
    return Response(status_code=204)


@router.post("/watch-history/{movie_id}", response_model=ActivityItem)
def mark_watched(movie_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    _require_movie(db, movie_id)
    row = db.scalar(select(WatchHistory).where(
        WatchHistory.user_id == user.id, WatchHistory.movie_id == movie_id,
        WatchHistory.event_type == "watched"))
    if not row:
        row = WatchHistory(user_id=user.id, movie_id=movie_id, event_type="watched")
        db.add(row)
        db.commit()
        db.refresh(row)
    return ActivityItem(movie=cards_for(db, [movie_id])[movie_id], at=row.occurred_at)


@router.delete("/watch-history/{movie_id}", status_code=204)
def unmark_watched(movie_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    db.execute(delete(WatchHistory).where(
        WatchHistory.user_id == user.id, WatchHistory.movie_id == movie_id,
        WatchHistory.event_type == "watched"))
    db.commit()
    return Response(status_code=204)
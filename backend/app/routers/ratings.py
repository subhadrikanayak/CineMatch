from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.deps import get_current_user
from backend.app.models import Movie, User, UserRating, WatchHistory
from backend.app.schemas.user import ActivityItem, ActivityPage, RatingIn, make_page
from backend.app.services.recommender_service import cards_for

router = APIRouter(tags=["Ratings"])


@router.put("/ratings/{movie_id}", response_model=ActivityItem)
def rate_movie(movie_id: int, body: RatingIn, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    """Create or update your rating (0.5 to 5, steps of 0.5). Also marks the movie as watched."""
    if not db.get(Movie, movie_id):
        raise HTTPException(404, "Movie not found")
    row = db.scalar(select(UserRating).where(
        UserRating.user_id == user.id, UserRating.movie_id == movie_id))
    if row:
        row.rating = body.rating
        row.rated_at = func.now()
    else:
        row = UserRating(user_id=user.id, movie_id=movie_id, rating=body.rating)
        db.add(row)
    watched = db.scalar(select(WatchHistory.id).where(
        WatchHistory.user_id == user.id, WatchHistory.movie_id == movie_id,
        WatchHistory.event_type == "watched"))
    if not watched:
        db.add(WatchHistory(user_id=user.id, movie_id=movie_id, event_type="watched"))
    db.commit()
    db.refresh(row)
    return ActivityItem(movie=cards_for(db, [movie_id])[movie_id], at=row.rated_at, rating=row.rating)


@router.delete("/ratings/{movie_id}", status_code=204)
def delete_rating(movie_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    row = db.scalar(select(UserRating).where(
        UserRating.user_id == user.id, UserRating.movie_id == movie_id))
    if not row:
        raise HTTPException(404, "You have not rated this movie")
    db.delete(row)
    db.commit()
    return Response(status_code=204)


@router.get("/ratings", response_model=ActivityPage)
def my_ratings(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total = db.scalar(select(func.count()).select_from(UserRating)
                      .where(UserRating.user_id == user.id)) or 0
    rows = list(db.scalars(
        select(UserRating).where(UserRating.user_id == user.id)
        .order_by(UserRating.rated_at.desc(), UserRating.id.desc())
        .offset((page - 1) * page_size).limit(page_size)))
    cards = cards_for(db, [r.movie_id for r in rows])
    items = [ActivityItem(movie=cards[r.movie_id], at=r.rated_at, rating=r.rating)
             for r in rows if r.movie_id in cards]
    return make_page(items, total, page, page_size)
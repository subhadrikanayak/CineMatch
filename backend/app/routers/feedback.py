from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.deps import get_current_user
from backend.app.models import Movie, RecommendationFeedback, User
from backend.app.schemas.user import FeedbackIn, FeedbackOut

router = APIRouter(prefix="/feedback", tags=["Feedback"])

REACTIONS = ["like", "dislike"]


@router.post("", response_model=FeedbackOut)
def give_feedback(body: FeedbackIn, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """like / dislike keep ONE current reaction per movie (the newest replaces the old).
    Comments are stored every time."""
    if not db.get(Movie, body.movie_id):
        raise HTTPException(404, "Movie not found")
    if body.feedback_type in REACTIONS:
        db.execute(delete(RecommendationFeedback).where(
            RecommendationFeedback.user_id == user.id,
            RecommendationFeedback.movie_id == body.movie_id,
            RecommendationFeedback.feedback_type.in_(REACTIONS)))
    row = RecommendationFeedback(
        user_id=user.id, movie_id=body.movie_id, feedback_type=body.feedback_type,
        comment=body.comment.strip() if body.comment else None)
    db.add(row)
    db.commit()
    db.refresh(row)
    return FeedbackOut(id=row.id, movie_id=row.movie_id, feedback_type=row.feedback_type,
                       comment=row.comment, created_at=row.created_at)


@router.get("/movie/{movie_id}")
def movie_comments(movie_id: int, limit: int = Query(30, ge=1, le=100),
                   db: Session = Depends(get_db)):
    """Public list of comments on a movie, newest first."""
    rows = db.execute(
        select(RecommendationFeedback, User.username)
        .join(User, User.id == RecommendationFeedback.user_id)
        .where(RecommendationFeedback.movie_id == movie_id,
               RecommendationFeedback.feedback_type == "comment")
        .order_by(RecommendationFeedback.id.desc()).limit(limit)).all()
    return [{"id": f.id, "user_id": f.user_id, "username": name,
             "comment": f.comment, "created_at": f.created_at} for f, name in rows]


@router.delete("/comment/{comment_id}", status_code=204)
def delete_comment(comment_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """You can delete only your own comments."""
    row = db.get(RecommendationFeedback, comment_id)
    if not row or row.feedback_type != "comment" or row.user_id != user.id:
        raise HTTPException(404, "Comment not found")
    db.delete(row)
    db.commit()
    return Response(status_code=204)


@router.delete("/{movie_id}", status_code=204)
def clear_reaction(movie_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Undo a like or dislike."""
    db.execute(delete(RecommendationFeedback).where(
        RecommendationFeedback.user_id == user.id,
        RecommendationFeedback.movie_id == movie_id,
        RecommendationFeedback.feedback_type.in_(REACTIONS)))
    db.commit()
    return Response(status_code=204)


@router.get("/me")
def my_reactions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(RecommendationFeedback.movie_id, RecommendationFeedback.feedback_type)
                      .where(RecommendationFeedback.user_id == user.id,
                             RecommendationFeedback.feedback_type.in_(REACTIONS))).all()
    return {"liked": [m for m, t in rows if t == "like"],
            "disliked": [m for m, t in rows if t == "dislike"]}
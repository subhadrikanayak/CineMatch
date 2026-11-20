from fastapi import APIRouter, Depends, HTTPException, Response
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
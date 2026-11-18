from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.repositories.movie_repository import MovieFilters

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_optional_user(token: str | None = Depends(oauth2), db: Session = Depends(get_db)) -> User | None:
    if not token:
        return None
    user_id = decode_access_token(token)
    if user_id is None:
        return None
    user = db.get(User, user_id)
    return user if user and user.is_active else None


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.name != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


def movie_filters(
    language: list[str] | None = Query(None, description="hi, te, ta, ml, kn"),
    genre: list[str] | None = Query(None),
    genre_match: str = Query("any", pattern="^(any|all)$"),
    with_actor_id: list[int] | None = Query(None),
    director_id: list[int] | None = Query(None),
    min_rating: float | None = Query(None, ge=0, le=10),
    year_min: int | None = Query(None, ge=1900, le=2100),
    year_max: int | None = Query(None, ge=1900, le=2100),
    runtime_min: int | None = Query(None, ge=0),
    runtime_max: int | None = Query(None, ge=0),
    q: str | None = Query(None, max_length=100),
    sort: str = Query("popularity", pattern="^(popularity|rating|year|title)$"),
) -> MovieFilters:
    return MovieFilters(
        languages=language or [], genres=genre or [], genre_match=genre_match,
                actor_ids=with_actor_id or [], director_ids=director_id or [],
        min_rating=min_rating, year_min=year_min, year_max=year_max,
        runtime_min=runtime_min, runtime_max=runtime_max, q=q, sort=sort,
    )
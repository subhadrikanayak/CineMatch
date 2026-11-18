from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db.session import get_db
from backend.app.deps import get_current_user
from backend.app.models import Role, User
from backend.app.schemas.auth import RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, username=u.username,
                   role=u.role.name, created_at=u.created_at)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    taken = db.scalar(select(User).where(or_(User.email == email, User.username == body.username)))
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email or username already registered")
    role = db.scalar(select(Role).where(Role.name == "user"))
    user = User(email=email, username=body.username,
                password_hash=hash_password(body.password), role_id=role.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """The 'username' field accepts either the email or the username."""
    ident = form.username.strip().lower()
    user = db.scalar(select(User).where(or_(User.email == ident, User.username == form.username.strip())))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email/username or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)
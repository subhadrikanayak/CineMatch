from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: str
    created_at: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
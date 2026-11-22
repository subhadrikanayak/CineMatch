import os

# Safe dummy settings so tests run on any machine (a real .env still wins if present).
os.environ.setdefault("MYSQL_USER", "test")
os.environ.setdefault("MYSQL_PASSWORD", "test")
os.environ.setdefault("MYSQL_DATABASE", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only-0123456789")
os.environ["W_CONTENT"] = "0.5"
os.environ["W_COLLAB"] = "0.3"
os.environ["W_POPULARITY"] = "0.2"
os.environ["W_PREFERENCE"] = "0.15"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import models  # noqa: F401
from backend.app.core.security import hash_password
from backend.app.db.session import Base, get_db
from backend.app.main import app
from backend.app.models import Genre, Language, Movie, Role, User


def _seed(db):
    user_role, admin_role = Role(name="user"), Role(name="admin")
    ml, hi = Language(code="ml", name="Malayalam"), Language(code="hi", name="Hindi")
    thriller, drama = Genre(name="Thriller"), Genre(name="Drama")
    db.add_all([user_role, admin_role, ml, hi, thriller, drama])
    db.flush()

    def movie(tmdb_id, title, lang, year, rating, genre):
        m = Movie(tmdb_id=tmdb_id, title=title, original_language_id=lang.id,
                  release_year=year, runtime=120, tmdb_rating=rating, tmdb_votes=500,
                  popularity=50.0, ratings_source="tmdb")
        m.genres.append(genre)
        db.add(m)

    movie(1, "Malayalam Thriller", ml, 2013, 8.2, thriller)
    movie(2, "Malayalam Drama", ml, 2015, 6.0, drama)
    movie(3, "Hindi Thriller", hi, 2018, 7.5, thriller)
    movie(4, "Hindi Drama", hi, 2020, 5.0, drama)
    db.add(User(email="admin@test.com", username="admin",
                password_hash=hash_password("Admin12345"), role_id=admin_role.id))
    db.commit()


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        _seed(s)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)          # no "with": startup (engine load) is skipped
    app.dependency_overrides.clear()
    engine.dispose()


def make_user(client, name="mahi"):
    """Registers a user and returns auth headers."""
    r = client.post("/api/v1/auth/register",
                    json={"email": f"{name}@test.com", "username": name, "password": "Test12345"})
    assert r.status_code == 201, r.text
    return login(client, f"{name}@test.com", "Test12345")


def login(client, ident, password):
    r = client.post("/api/v1/auth/login", data={"username": ident, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
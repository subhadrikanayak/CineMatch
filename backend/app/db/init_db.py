import logging

from sqlalchemy import inspect, select

from backend.app.db.session import Base, SessionLocal, engine
from backend.app import models  # noqa: F401  (registers all tables)
from backend.app.models import Genre, Language, Role

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("init_db")

ROLES = ["user", "admin"]

LANGUAGES = [
    ("hi", "Hindi"),
    ("te", "Telugu"),
    ("ta", "Tamil"),
    ("ml", "Malayalam"),
    ("kn", "Kannada"),
]

# (tmdb_id, name). Rom-Com has no TMDB id: it is derived (Romance + Comedy).
GENRES = [
    (28, "Action"), (35, "Comedy"), (10749, "Romance"), (None, "Rom-Com"),
    (53, "Thriller"), (9648, "Mystery"), (27, "Horror"), (18, "Drama"),
    (878, "Sci-Fi"), (12, "Adventure"), (80, "Crime"), (10751, "Family"),
    (16, "Animation"), (14, "Fantasy"),
]


def seed() -> None:
    with SessionLocal() as db:
        existing_roles = set(db.scalars(select(Role.name)))
        for name in ROLES:
            if name not in existing_roles:
                db.add(Role(name=name))

        existing_langs = set(db.scalars(select(Language.code)))
        for code, name in LANGUAGES:
            if code not in existing_langs:
                db.add(Language(code=code, name=name))

        existing_genres = set(db.scalars(select(Genre.name)))
        for tmdb_id, name in GENRES:
            if name not in existing_genres:
                db.add(Genre(tmdb_id=tmdb_id, name=name))

        db.commit()
    log.info("Seed data ready: %d roles, %d languages, %d genres",
             len(ROLES), len(LANGUAGES), len(GENRES))


def main() -> None:
    Base.metadata.create_all(bind=engine)
    tables = sorted(inspect(engine).get_table_names())
    log.info("Tables in database (%d): %s", len(tables), ", ".join(tables))
    seed()


if __name__ == "__main__":
    main()
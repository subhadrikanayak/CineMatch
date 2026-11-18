from datetime import date, datetime

from sqlalchemy import (
    Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)  # ISO 639-1
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True)  # NULL for derived genres (Rom-Com)
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        Index("ix_movies_lang_year", "original_language_id", "release_year"),
        Index("ix_movies_imdb_rating", "imdb_rating"),
        Index("ft_movies_title_keywords", "title", "keywords_text", mysql_prefix="FULLTEXT"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    imdb_id: Mapped[str | None] = mapped_column(String(15), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(255))
    overview: Mapped[str | None] = mapped_column(Text)
    keywords_text: Mapped[str | None] = mapped_column(Text)

    original_language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), nullable=False)
    dubbed_languages: Mapped[str | None] = mapped_column(String(255))  # only filled when verified

    release_date: Mapped[date | None] = mapped_column(Date)
    release_year: Mapped[int | None] = mapped_column(Integer)
    runtime: Mapped[int | None] = mapped_column(Integer)

    imdb_rating: Mapped[float | None] = mapped_column(Float)
    imdb_votes: Mapped[int | None] = mapped_column(Integer)
    tmdb_rating: Mapped[float | None] = mapped_column(Float)
    tmdb_votes: Mapped[int | None] = mapped_column(Integer)
    popularity: Mapped[float | None] = mapped_column(Float)
    ratings_source: Mapped[str | None] = mapped_column(String(10))  # 'imdb' or 'tmdb'
    ratings_fetched_at: Mapped[datetime | None] = mapped_column(DateTime)

    poster_path: Mapped[str | None] = mapped_column(String(255))
    backdrop_path: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    language: Mapped["Language"] = relationship()
    genres: Mapped[list["Genre"]] = relationship(secondary="movie_genres")
    directors: Mapped[list["Director"]] = relationship(secondary="movie_directors")
    cast: Mapped[list["MovieCast"]] = relationship(
        back_populates="movie", order_by="MovieCast.cast_order"
    )


class MovieGenre(Base):
    __tablename__ = "movie_genres"

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class Actor(Base):
    __tablename__ = "actors"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    gender: Mapped[str] = mapped_column(String(10), default="unknown")  # male/female/other/unknown
    profile_path: Mapped[str | None] = mapped_column(String(255))
    popularity: Mapped[float | None] = mapped_column(Float)


class MovieCast(Base):
    __tablename__ = "movie_cast"
    __table_args__ = (Index("ix_cast_movie_order", "movie_id", "cast_order"),)

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    actor_id: Mapped[int] = mapped_column(
        ForeignKey("actors.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    character_name: Mapped[str | None] = mapped_column(String(255))
    cast_order: Mapped[int | None] = mapped_column(Integer)

    movie: Mapped["Movie"] = relationship(back_populates="cast")
    actor: Mapped["Actor"] = relationship()


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    profile_path: Mapped[str | None] = mapped_column(String(255))


class MovieDirector(Base):
    __tablename__ = "movie_directors"

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    director_id: Mapped[int] = mapped_column(
        ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True, index=True
    )
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


class StreamingProvider(Base):
    __tablename__ = "streaming_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_provider_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    logo_path: Mapped[str | None] = mapped_column(String(255))


class StreamingAvailability(Base):
    """Rows exist only when a provider is returned by the TMDB watch-providers API.
    No row = unknown / not available. Nothing is ever guessed."""

    __tablename__ = "streaming_availability"
    __table_args__ = (
        CheckConstraint("offer_type IN ('flatrate','rent','buy','free','ads')", name="ck_offer_type"),
    )

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("streaming_providers.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    region: Mapped[str] = mapped_column(String(2), primary_key=True, default="IN")
    offer_type: Mapped[str] = mapped_column(String(10), primary_key=True, default="flatrate")
    verified_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
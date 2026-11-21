"""Add real IMDb ratings from OMDb to movies that have an imdb_id.
Run (VPN on if OMDb is blocked):  python -m backend.scripts.enrich_omdb --limit 900
Safe to re-run: movies that already have an IMDb rating are skipped."""
import argparse
import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.models import Movie

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("enrich_omdb")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=900, help="max requests (free tier ~1000/day)")
    a = ap.parse_args()
    if not settings.OMDB_API_KEY:
        raise SystemExit("OMDB_API_KEY is empty. Add it to .env first.")

    updated = skipped = 0
    with SessionLocal() as db, httpx.Client(timeout=30) as client:
        movies = db.scalars(
            select(Movie).where(Movie.imdb_id.is_not(None), Movie.imdb_rating.is_(None))
            .order_by(Movie.tmdb_votes.desc()).limit(a.limit)).all()
        log.info("%d movies to look up", len(movies))
        for m in movies:
            try:
                data = client.get("https://www.omdbapi.com/",
                                  params={"i": m.imdb_id, "apikey": settings.OMDB_API_KEY}).json()
            except (httpx.HTTPError, ValueError) as exc:
                log.warning("Request failed for %s: %s", m.title, exc)
                continue
            if data.get("Response") == "False":
                if "limit" in data.get("Error", "").lower():
                    log.error("Daily limit reached. Run again tomorrow.")
                    break
                skipped += 1
                continue
            try:
                m.imdb_rating = float(data["imdbRating"])
                m.imdb_votes = int(data["imdbVotes"].replace(",", ""))
            except (KeyError, ValueError):          # OMDb returns "N/A" when unknown
                skipped += 1
                continue
            m.ratings_source = "imdb"
            m.ratings_fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            updated += 1
            time.sleep(0.05)
    log.info("Updated %d movies, skipped %d (no IMDb data).", updated, skipped)


if __name__ == "__main__":
    main()
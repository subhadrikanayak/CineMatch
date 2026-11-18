"""Load Indian-language movies from TMDB into MySQL.

Usage (from D:\\CineMatch, venv active):
    python -m backend.scripts.ingest_tmdb --pages 3
"""
import argparse
import logging
import time
from datetime import date, datetime

import httpx
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.models import (
    Actor, Director, Genre, Language, Movie, MovieCast, StreamingAvailability,
    StreamingProvider,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("ingest_tmdb")

BASE = "https://api.themoviedb.org/3"
CAST_LIMIT = 15
OFFER_TYPES = ["flatrate", "rent", "buy", "free", "ads"]
GENDER = {1: "female", 2: "male", 3: "other"}


def api_get(client: httpx.Client, path: str, **params) -> dict | None:
    params["api_key"] = settings.TMDB_API_KEY
    for attempt in range(4):
        try:
            r = client.get(f"{BASE}{path}", params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(2 + attempt * 2)
                continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as exc:
            log.warning("Request failed (%s), retry %d", exc, attempt + 1)
            time.sleep(2)
    return None


def parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def ingest_movie(db, client, tmdb_id, lang, genre_map, caches) -> bool:
    d = api_get(
        client, f"/movie/{tmdb_id}",
        append_to_response="credits,keywords,watch/providers",
    )
    if not d:
        return False

    release = parse_date(d.get("release_date"))
    keywords = [k["name"] for k in d.get("keywords", {}).get("keywords", [])]

    movie = Movie(
        tmdb_id=tmdb_id,
        imdb_id=d.get("imdb_id") or None,
        title=d["title"][:255],
        original_title=(d.get("original_title") or "")[:255] or None,
        overview=d.get("overview") or None,
        keywords_text=", ".join(keywords) or None,
        original_language_id=lang.id,
        release_date=release,
        release_year=release.year if release else None,
        runtime=d.get("runtime") or None,
        tmdb_rating=d.get("vote_average"),
        tmdb_votes=d.get("vote_count"),
        popularity=d.get("popularity"),
        ratings_source="tmdb",
        ratings_fetched_at=datetime.utcnow(),
        poster_path=d.get("poster_path"),
        backdrop_path=d.get("backdrop_path"),
    )

    # genres (+ derived Rom-Com)
    tmdb_genre_ids = {g["id"] for g in d.get("genres", [])}
    for gid in tmdb_genre_ids:
        if gid in genre_map:
            movie.genres.append(genre_map[gid])
    if 10749 in tmdb_genre_ids and 35 in tmdb_genre_ids and "Rom-Com" in genre_map:
        movie.genres.append(genre_map["Rom-Com"])

    credits = d.get("credits", {})

    # directors
    for person in credits.get("crew", []):
        if person.get("job") == "Director":
            director = caches["directors"].get(person["id"]) or db.scalar(
                select(Director).where(Director.tmdb_id == person["id"])
            )
            if not director:
                director = Director(
                    tmdb_id=person["id"], name=person["name"][:150],
                    profile_path=person.get("profile_path"),
                )
                db.add(director)
                db.flush()
            caches["directors"][person["id"]] = director
            if director not in movie.directors:
                movie.directors.append(director)

    db.add(movie)
    db.flush()

    # cast
    for person in credits.get("cast", [])[:CAST_LIMIT]:
        actor = caches["actors"].get(person["id"]) or db.scalar(
            select(Actor).where(Actor.tmdb_id == person["id"])
        )
        if not actor:
            actor = Actor(
                tmdb_id=person["id"], name=person["name"][:150],
                gender=GENDER.get(person.get("gender"), "unknown"),
                profile_path=person.get("profile_path"),
                popularity=person.get("popularity"),
            )
            db.add(actor)
            db.flush()
        caches["actors"][person["id"]] = actor
        db.add(MovieCast(
            movie_id=movie.id, actor_id=actor.id,
            character_name=(person.get("character") or "")[:255] or None,
            cast_order=person.get("order"),
        ))

    # streaming: only what TMDB actually returns for India
    region = d.get("watch/providers", {}).get("results", {}).get("IN", {})
    seen = set()
    for offer in OFFER_TYPES:
        for p in region.get(offer, []):
            provider = caches["providers"].get(p["provider_id"]) or db.scalar(
                select(StreamingProvider).where(
                    StreamingProvider.tmdb_provider_id == p["provider_id"]
                )
            )
            if not provider:
                provider = StreamingProvider(
                    tmdb_provider_id=p["provider_id"],
                    name=p["provider_name"][:100],
                    logo_path=p.get("logo_path"),
                )
                db.add(provider)
                db.flush()
            caches["providers"][p["provider_id"]] = provider
            if (provider.id, offer) in seen:
                continue
            seen.add((provider.id, offer))
            db.add(StreamingAvailability(
                movie_id=movie.id, provider_id=provider.id,
                region="IN", offer_type=offer,
            ))
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=3, help="pages per language (20 movies/page)")
    parser.add_argument("--min-votes", type=int, default=20)
    parser.add_argument("--languages", nargs="+", default=["hi", "te", "ta", "ml", "kn"])
    args = parser.parse_args()

    if not settings.TMDB_API_KEY:
        raise SystemExit("TMDB_API_KEY is empty. Add it to .env first.")

    caches = {"actors": {}, "directors": {}, "providers": {}}
    added = skipped = 0

    with SessionLocal() as db, httpx.Client() as client:
        genre_map = {g.tmdb_id: g for g in db.scalars(select(Genre)) if g.tmdb_id}
        genre_map["Rom-Com"] = db.scalar(select(Genre).where(Genre.name == "Rom-Com"))
        languages = {l.code: l for l in db.scalars(select(Language))}

        for code in args.languages:
            lang = languages[code]
            log.info("=== %s ===", lang.name)
            for page in range(1, args.pages + 1):
                data = api_get(
                    client, "/discover/movie",
                    with_original_language=code, sort_by="vote_count.desc",
                    page=page, include_adult="false",
                    **{"vote_count.gte": args.min_votes},
                )
                if not data or not data.get("results"):
                    break
                for item in data["results"]:
                    if db.scalar(select(Movie.id).where(Movie.tmdb_id == item["id"])):
                        skipped += 1
                        continue
                    try:
                        if ingest_movie(db, client, item["id"], lang, genre_map, caches):
                            db.commit()
                            added += 1
                            log.info("Added: %s", item["title"])
                    except Exception as exc:
                        db.rollback()
                        caches = {"actors": {}, "directors": {}, "providers": {}}
                        log.error("Failed %s: %s", item.get("title"), exc)
                    time.sleep(0.05)

    log.info("Done. Added %d movies, skipped %d existing.", added, skipped)


if __name__ == "__main__":
    main()
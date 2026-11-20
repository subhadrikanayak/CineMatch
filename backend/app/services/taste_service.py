from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import Movie, MovieCast, User
from backend.app.schemas.movie import effective_rating
from backend.app.schemas.user import PersonCount, ShareItem, TasteProfileOut
from backend.app.services.recommender_service import build_signals

NOTE = ("Built only from your real activity: movies you rated 3.5 or higher, movies you "
        "liked, and your watchlist. Percentages are shares of that weighted activity. "
        "Disliked movies never count towards your taste.")


def _shares(counter: Counter, top: int, codes: dict | None = None) -> list[ShareItem]:
    total = sum(counter.values())
    if not total:
        return []
    return [ShareItem(name=n, code=(codes or {}).get(n), percent=round(v / total * 100, 1))
            for n, v in counter.most_common(top)]


def _people(d: dict, top: int = 5) -> list[PersonCount]:
    rows = [(pid, name, n) for pid, (name, n) in d.items() if n >= 2]   # 1 movie is noise
    rows.sort(key=lambda r: (-r[2], r[1]))
    return [PersonCount(id=p, name=n, movies=c) for p, n, c in rows[:top]]


def compute_taste(db: Session, user: User) -> TasteProfileOut:
    s = build_signals(db, user)
    weights: dict[int, float] = {}
    for mid, r in s.ratings.items():
        if r >= 3.5:
            weights[mid] = r - 2.0                      # 3.5 -> 1.5 ... 5 -> 3.0
    for mid in s.liked_ids:
        weights[mid] = max(weights.get(mid, 0.0), 2.0)
    for mid in s.watchlist_ids:
        weights.setdefault(mid, 0.5)
    for mid in s.disliked_ids:
        weights.pop(mid, None)

    avoid_ids = {m for m, r in s.ratings.items() if r <= 2.0} | s.disliked_ids
    ids = set(weights) | avoid_ids
    movies = {}
    if ids:
        stmt = (select(Movie).where(Movie.id.in_(ids)).options(
            selectinload(Movie.language), selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.cast).selectinload(MovieCast.actor)))
        movies = {m.id: m for m in db.scalars(stmt)}

    genres, langs, decades = Counter(), Counter(), Counter()
    codes: dict[str, str] = {}
    actors: dict[int, list] = {}
    directors: dict[int, list] = {}
    rt = [0.0, 0.0]; yr = [0.0, 0.0]; pub = [0.0, 0.0]      # [weighted sum, weight]

    for mid, w in weights.items():
        m = movies.get(mid)
        if not m:
            continue
        for g in m.genres:
            genres[g.name] += w
        langs[m.language.name] += w
        codes[m.language.name] = m.language.code
        if m.release_year:
            decades[f"{m.release_year // 10 * 10}s"] += w
            yr[0] += w * m.release_year; yr[1] += w
        if m.runtime:
            rt[0] += w * m.runtime; rt[1] += w
        rating, _, _ = effective_rating(m)
        if rating:
            pub[0] += w * rating; pub[1] += w
        for c in m.cast[:5]:
            actors.setdefault(c.actor.id, [c.actor.name, 0])[1] += 1
        for d in m.directors:
            directors.setdefault(d.id, [d.name, 0])[1] += 1

    avoided = Counter(g.name for mid in avoid_ids if mid in movies for g in movies[mid].genres)
    own = list(s.ratings.values())

    return TasteProfileOut(
        enough_data=len(weights) >= 3,
        based_on={"ratings": len(s.ratings), "likes": len(s.liked_ids),
                  "dislikes": len(s.disliked_ids), "watchlist": len(s.watchlist_ids),
                  "movies_used_for_taste": len(weights)},
        declared={"languages": sorted(s.fav_languages), "genres": sorted(s.fav_genres)},
        genres=_shares(genres, 8), languages=_shares(langs, 5, codes),
        decades=sorted(_shares(decades, 10), key=lambda x: x.name),
        top_actors=_people(actors), top_directors=_people(directors),
        avg_runtime=round(rt[0] / rt[1]) if rt[1] else None,
        avg_release_year=round(yr[0] / yr[1]) if yr[1] else None,
        avg_public_rating=round(pub[0] / pub[1], 1) if pub[1] else None,
        own_average_rating=round(sum(own) / len(own), 2) if own else None,
        avoided_genres=[g for g, n in avoided.most_common(3) if n >= 2],
        note=NOTE,
    )
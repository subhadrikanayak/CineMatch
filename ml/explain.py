import pandas as pd


def build_reasons(rec, comps, weights, signals, taste_genres, nearest, wr, min_rating=None):
    """Every reason comes from a real signal; nothing is invented."""
    reasons = []

    if rec["language_code"] in signals.fav_languages:
        reasons.append(f"Matches your favourite language ({rec['language']})")

    wanted = set(signals.fav_genres) | set(taste_genres)
    overlap = [g for g in rec["genres"] if g in wanted]
    if overlap:
        reasons.append("Matches your preferred genres: " + ", ".join(overlap[:3]))

    fav_actors = [n for a, n in zip(rec["cast_ids"], rec["cast_names"])
                  if a in signals.fav_actor_ids]
    if fav_actors:
        reasons.append("Features your favourite actor(s): " + ", ".join(fav_actors[:2]))

    if nearest and weights["content"] > 0 and nearest[1] >= 0.15:
        liked, _sim = nearest
        r = signals.ratings.get(liked["id"])
        how = f"which you rated {r:g}/5" if r and r >= 4 else "which you liked"
        reasons.append(f"Similar to {liked['title']}, {how}")

    if weights["collab"] > 0 and comps["collab"] >= 0.7:
        reasons.append("Viewers with tastes similar to yours rated it highly")

    if min_rating is not None and pd.notna(rec["rating"]) and rec["rating"] >= min_rating:
        reasons.append(f"Rated {rec['rating']:.1f} ({rec['rating_source'].upper()}), "
                       f"above your minimum of {min_rating:g}")

    if comps["pop"] >= 0.8:
        reasons.append(f"Among the best rated in this selection (weighted rating {wr:.1f}/10)")

    return reasons[:5] or ["Fits your selected filters"]
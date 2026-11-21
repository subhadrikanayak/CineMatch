import numpy as np
import pandas as pd
import pytest

from ml.collaborative import CollaborativeModel
from ml.content_based import ContentModel
from ml.diversity import mmr
from ml.hidden_gems import find_gems
from ml.hybrid import HybridRecommender, UserSignals
from ml.semantic import parse_query
from ml.utils import minmax

GENRES = [["Thriller", "Mystery"], ["Romance", "Drama"], ["Comedy", "Family"], ["Action", "Crime"]]


def make_df() -> pd.DataFrame:
    rows = []
    for i in range(1, 25):
        g = GENRES[i % 4]                      # i % 4 == 0 -> Thriller (and all those ids are even -> ml)
        rows.append({
            "id": i, "title": f"Movie {i}",
            "language": "Malayalam" if i % 2 == 0 else "Hindi",
            "language_code": "ml" if i % 2 == 0 else "hi",
            "release_year": 2000 + i, "genres": g,
            "director_ids": [i % 3], "cast_ids": [i % 5, 100 + i],
            "cast_names": [f"Actor {i % 5}", f"Extra {i}"],
            "keywords": " ".join(g).lower(),
            "overview": f"A story about {g[0].lower()} and {g[1].lower()} number {i}",
            "rating": 5.0 + (i % 5), "votes": 100 + i * 10, "rating_source": "tmdb",
        })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def engine():
    df = make_df()
    return HybridRecommender(df, ContentModel.fit(df), CollaborativeModel())


# ---------------------------------------------------------------- hybrid
def test_cold_start_uses_preferences(engine):
    recs = engine.recommend(UserSignals(fav_languages={"ml"}, fav_genres={"Thriller"}),
                            k=5, diversify=False)
    top = [engine.records[engine.pos[r.movie_id]] for r in recs[:3]]
    assert all("Thriller" in m["genres"] and m["language_code"] == "ml" for m in top)


def test_hard_filter_candidates_are_never_violated(engine):
    allowed = [1, 3, 5, 7, 9, 11]
    recs = engine.recommend(UserSignals(fav_genres={"Thriller"}), allowed, k=10)
    assert recs and {r.movie_id for r in recs} <= set(allowed)


def test_rated_movies_are_excluded(engine):
    recs = engine.recommend(UserSignals(ratings={4: 5.0}), k=30, diversify=False)
    assert 4 not in {r.movie_id for r in recs}


def test_scores_weights_and_reasons_are_sane(engine):
    recs = engine.recommend(UserSignals(ratings={4: 5.0}), k=5, diversify=False)
    for r in recs:
        assert 0 <= r.match_percent <= 100
        assert r.reasons
    w = recs[0].weights
    assert w["collab"] == 0.0                     # no ratings data -> SVD stays off
    assert abs(sum(w.values()) - 1) < 0.01


def test_liked_movie_drives_content_similarity(engine):
    recs = engine.recommend(UserSignals(ratings={4: 5.0}), k=3, diversify=False)
    seed_genres = set(engine.records[engine.pos[4]]["genres"])
    assert set(engine.records[engine.pos[recs[0].movie_id]]["genres"]) == seed_genres


def test_empty_candidate_list_returns_nothing(engine):
    assert engine.recommend(UserSignals(), [9999], k=5) == []


# ---------------------------------------------------------------- components
def test_collaborative_stays_off_without_enough_ratings():
    ratings = pd.DataFrame({"user_id": [1, 1, 2], "movie_id": [1, 2, 1], "rating": [5, 3, 4]})
    assert CollaborativeModel.fit(ratings, [1, 2, 3]).ready is False


def test_mmr_prefers_diverse_second_pick():
    rel = np.array([1.0, 0.99, 0.5])
    sim = np.array([[1, 1, 0], [1, 1, 0], [0, 0, 1]], dtype=float)
    assert mmr(rel, sim, 2, lam=0.5) == [0, 2]


def test_mmr_returns_unique_indices():
    rel = np.random.default_rng(0).random(10)
    picked = mmr(rel, np.eye(10), 5)
    assert len(set(picked)) == 5


def test_minmax():
    assert minmax([1, 2, 3]).tolist() == [0.0, 0.5, 1.0]
    assert minmax([4, 4]).tolist() == [0.5, 0.5]


def test_hidden_gems_never_include_low_vote_movies():
    rows = [{"id": i, "title": f"M{i}", "rating": 6 + (i % 10) * 0.3, "votes": 100 + i * 50,
             "rating_source": "tmdb"} for i in range(1, 41)]
    rows.append({"id": 999, "title": "Few votes", "rating": 9.9, "votes": 3, "rating_source": "tmdb"})
    pop = {i: 100 - i for i in range(1, 41)}
    pop[999] = 1
    gems, th = find_gems(pd.DataFrame(rows), pop)
    assert 999 not in {int(g["id"]) for g in gems}
    assert all(g["votes"] >= th["min_votes"] for g in gems)


# ---------------------------------------------------------------- query parsing
def test_parse_query_extracts_hard_filters():
    p = parse_query("Suggest a Malayalam psychological thriller with an unexpected ending")
    assert p.languages == ["ml"] and p.genres == ["Thriller"]
    assert "psychological" in p.text and "malayalam" not in p.text


def test_parse_query_year_and_rating():
    p = parse_query("Tamil action movies after 2015 rated above 7")
    assert p.languages == ["ta"] and p.genres == ["Action"]
    assert p.year_min == 2015 and p.min_rating == 7
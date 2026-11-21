from backend.tests.conftest import login, make_user

API = "/api/v1"


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ---------------------------------------------------------------- auth
def test_register_login_me(client):
    h = make_user(client)
    me = client.get(f"{API}/auth/me", headers=h).json()
    assert me["username"] == "mahi" and me["role"] == "user"


def test_login_by_username_works(client):
    make_user(client)
    assert login(client, "mahi", "Test12345")


def test_duplicate_register_rejected(client):
    make_user(client)
    r = client.post(f"{API}/auth/register",
                    json={"email": "mahi@test.com", "username": "other", "password": "Test12345"})
    assert r.status_code == 409


def test_wrong_password_rejected(client):
    make_user(client)
    r = client.post(f"{API}/auth/login", data={"username": "mahi", "password": "nope-nope"})
    assert r.status_code == 401


def test_short_password_rejected(client):
    r = client.post(f"{API}/auth/register",
                    json={"email": "a@b.com", "username": "abc", "password": "short"})
    assert r.status_code == 422


def test_protected_route_needs_token(client):
    assert client.get(f"{API}/auth/me").status_code == 401


# ---------------------------------------------------------------- movies and hard filters
def test_language_and_rating_filters_are_hard(client):
    r = client.get(f"{API}/movies", params={"language": "ml", "min_rating": 7}).json()
    assert r["total"] == 1
    assert r["items"][0]["title"] == "Malayalam Thriller"


def test_genre_filter(client):
    r = client.get(f"{API}/movies", params={"genre": "Thriller"}).json()
    assert {m["title"] for m in r["items"]} == {"Malayalam Thriller", "Hindi Thriller"}


def test_year_filter(client):
    r = client.get(f"{API}/movies", params={"year_min": 2018}).json()
    assert {m["release_year"] for m in r["items"]} == {2018, 2020}


def test_rating_carries_its_source_label(client):
    item = client.get(f"{API}/movies").json()["items"][0]
    assert item["rating_source"] == "tmdb"


def test_movie_detail_and_404(client):
    first = client.get(f"{API}/movies").json()["items"][0]["id"]
    d = client.get(f"{API}/movies/{first}").json()
    assert d["streaming"] == []          # nothing is invented
    assert client.get(f"{API}/movies/9999").status_code == 404


def test_recommendations_fail_gracefully_without_engine(client):
    assert client.post(f"{API}/recommendations", json={}).status_code == 503


# ---------------------------------------------------------------- ratings, watchlist
def test_rating_flow(client):
    h = make_user(client)
    assert client.put(f"{API}/ratings/1", json={"rating": 4}, headers=h).status_code == 200
    r = client.put(f"{API}/ratings/1", json={"rating": 5}, headers=h)   # update, not duplicate
    assert r.json()["rating"] == 5
    assert client.get(f"{API}/ratings", headers=h).json()["total"] == 1
    assert client.put(f"{API}/ratings/1", json={"rating": 3.3}, headers=h).status_code == 422
    assert client.delete(f"{API}/ratings/1", headers=h).status_code == 204
    assert client.delete(f"{API}/ratings/1", headers=h).status_code == 404


def test_watchlist_is_idempotent(client):
    h = make_user(client)
    assert client.post(f"{API}/watchlist/1", headers=h).status_code == 200
    assert client.post(f"{API}/watchlist/1", headers=h).status_code == 200
    assert client.get(f"{API}/watchlist", headers=h).json()["total"] == 1
    assert client.delete(f"{API}/watchlist/1", headers=h).status_code == 204
    assert client.delete(f"{API}/watchlist/1", headers=h).status_code == 404


def test_users_cannot_see_each_others_lists(client):
    a = make_user(client, "alice")
    b = make_user(client, "bobby")
    client.post(f"{API}/watchlist/1", headers=a)
    assert client.get(f"{API}/watchlist", headers=b).json()["total"] == 0


def test_preferences_round_trip_and_validation(client):
    h = make_user(client)
    body = {"languages": ["ml"], "genres": ["Thriller"], "actor_ids": []}
    saved = client.put(f"{API}/users/me/preferences", json=body, headers=h).json()
    assert saved["languages"][0]["code"] == "ml" and saved["genres"] == ["Thriller"]
    assert client.put(f"{API}/users/me/preferences", headers=h,
                      json={"languages": ["xx"], "genres": [], "actor_ids": []}).status_code == 422
    assert client.put(f"{API}/users/me/preferences", headers=h,
                      json={"languages": [], "genres": ["Nope"], "actor_ids": []}).status_code == 400


# ---------------------------------------------------------------- admin lock
def test_admin_requires_admin_role(client):
    assert client.get(f"{API}/admin/stats").status_code == 401
    h = make_user(client)
    assert client.get(f"{API}/admin/stats", headers=h).status_code == 403


def test_admin_can_read_stats(client):
    h = login(client, "admin@test.com", "Admin12345")
    r = client.get(f"{API}/admin/stats", headers=h)
    assert r.status_code == 200
    assert r.json()["movies"] == 4
    assert r.json()["engine"]["collaborative_ready"] is False
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.routers import (
    admin, auth, compare, feedback, mood, movies, people, ratings, recommendations,
    search, similar, users, watchlist,
)
from backend.app.services.recommender_service import load_engine

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_engine()          # loads TF-IDF / SVD artifacts once at startup
    yield


app = FastAPI(title="CineMatch API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
for r in (auth.router, movies.router, people.router, recommendations.router,
          mood.router, similar.router, search.router, compare.router,
          ratings.router, watchlist.router, feedback.router, users.router, admin.router):
    app.include_router(r, prefix=API)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.routers import auth, movies, people

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="CineMatch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
app.include_router(auth.router, prefix=API)
app.include_router(movies.router, prefix=API)
app.include_router(people.router, prefix=API)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}
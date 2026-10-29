import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import run_logs, run_manager
from app.core.download_router import router as download_router
from app.db import init_db
from app.scrapers.ppra import filters as ppra_filters
from app.scrapers.ppra.router import router as ppra_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="PK-Hub API", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    run_logs.install()
    try:
        init_db()
        logger.info("Database tables ready")
    except Exception:
        logger.exception("Could not initialize database — check DATABASE_URL in .env")
    run_manager.load_persisted_runs()
    # Fill the in-process filter cache now so the first page load doesn't pay for the DB read.
    try:
        ppra_filters.get_filter_options()
    except Exception:  # noqa: BLE001 — the first request retries; boot must not fail on this
        logger.exception("could not warm the PPRA filter cache")


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ppra_router)
app.include_router(download_router)


@app.get("/")
def health() -> dict:
    return {
        "status": "ok",
        "service": "pk-hub",
        "scrapers": ["ppra"],
    }

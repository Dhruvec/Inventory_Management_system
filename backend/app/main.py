"""FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload
Interactive API docs are then available at /docs (Swagger UI) and /redoc.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import alerts, auth, invoices, orders, products

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inventory")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup (fine for this project's scope)."""
    logger.info("Initialising database at %s", settings.database_url)
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "REST API for small-business inventory, order and billing management. "
        "Covers products & stock, orders, invoicing with partial payments, and "
        "low-stock alerts."
    ),
    lifespan=lifespan,
)

# CORS: allowed origins are configurable via the CORS_ORIGINS env var
# (comma-separated). Defaults cover the Vite dev server and the nginx build.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(invoices.router)
app.include_router(alerts.router)


@app.get("/api/health", tags=["health"])
def health_check() -> dict:
    """Liveness probe used by Docker / CI."""
    return {"status": "ok", "app": settings.app_name, "version": app.version}


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"message": "Inventory & Order Management API", "docs": "/docs"}

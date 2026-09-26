"""Shared pytest fixtures.

Each test runs against an isolated in-memory SQLite database, so the suite is
fast and has no external dependencies.
"""
from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, schemas
from app.crud import products as products_crud
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Provide a transactional-free but isolated in-memory database session."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """A TestClient wired to the isolated DB session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def owner_token(client: TestClient) -> str:
    """Register the first user (auto-owner) and return a bearer token."""
    client.post(
        "/api/auth/register",
        json={"username": "owner", "password": "owner123", "is_owner": True},
    )
    resp = client.post(
        "/api/auth/token",
        data={"username": "owner", "password": "owner123"},
    )
    return resp.json()["access_token"]


@pytest.fixture()
def auth_headers(owner_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture()
def sample_product(db_session: Session) -> models.Product:
    return products_crud.create_product(
        db_session,
        schemas.ProductCreate(
            sku="TEST-001",
            name="Test Widget",
            unit_price=100.0,
            cost_price=60.0,
            quantity_in_stock=50,
            low_stock_threshold=10,
        ),
    )

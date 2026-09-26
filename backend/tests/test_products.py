"""Unit tests for product CRUD and stock-adjustment logic."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import products as crud


def test_create_product_records_opening_stock(db_session: Session):
    product = crud.create_product(
        db_session,
        schemas.ProductCreate(
            sku="P-1", name="Widget", unit_price=10, cost_price=5, quantity_in_stock=7
        ),
    )
    assert product.id is not None
    movements = crud.list_movements(db_session, product.id)
    assert len(movements) == 1
    assert movements[0].change == 7
    assert movements[0].reason == models.MovementReason.PURCHASE


def test_low_stock_flag(sample_product: models.Product):
    assert sample_product.is_low_stock is False
    sample_product.quantity_in_stock = 10
    assert sample_product.is_low_stock is True


def test_adjust_stock_add_and_remove(db_session: Session, sample_product):
    crud.adjust_stock(
        db_session,
        sample_product,
        schemas.StockAdjustment(change=-5, note="damaged"),
    )
    db_session.refresh(sample_product)
    assert sample_product.quantity_in_stock == 45

    crud.adjust_stock(
        db_session,
        sample_product,
        schemas.StockAdjustment(change=20, reason=models.MovementReason.PURCHASE),
    )
    db_session.refresh(sample_product)
    assert sample_product.quantity_in_stock == 65


def test_adjust_stock_rejects_negative_inventory(db_session: Session, sample_product):
    try:
        crud.adjust_stock(
            db_session, sample_product, schemas.StockAdjustment(change=-100)
        )
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "negative" in str(exc).lower()
    db_session.refresh(sample_product)
    assert sample_product.quantity_in_stock == 50


def test_soft_delete_keeps_record(db_session: Session, sample_product):
    crud.delete_product(db_session, sample_product)
    db_session.refresh(sample_product)
    assert sample_product.is_active is False
    assert crud.get_product(db_session, sample_product.id) is not None


def test_low_stock_listing(db_session: Session):
    crud.create_product(
        db_session,
        schemas.ProductCreate(sku="LOW", name="Low", quantity_in_stock=2, low_stock_threshold=10),
    )
    crud.create_product(
        db_session,
        schemas.ProductCreate(sku="OK", name="Ok", quantity_in_stock=100, low_stock_threshold=10),
    )
    low = crud.low_stock_products(db_session)
    assert [p.sku for p in low] == ["LOW"]

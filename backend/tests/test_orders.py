"""Unit tests for the order lifecycle and stock deduction."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app import schemas
from app.crud import orders as crud
from app.crud import products as products_crud
from app.models import MovementReason, OrderStatus


def _make_product(db: Session, sku: str, qty: int, price: float = 100.0):
    return products_crud.create_product(
        db,
        schemas.ProductCreate(
            sku=sku, name=f"Product {sku}", unit_price=price, quantity_in_stock=qty
        ),
    )


def test_confirmed_order_deducts_stock_and_creates_invoice(db_session: Session):
    product = _make_product(db_session, "O-1", qty=50)
    order = crud.create_order(
        db_session,
        schemas.OrderCreate(items=[schemas.OrderItemCreate(product_id=product.id, quantity=5)]),
    )
    db_session.refresh(product)
    assert product.quantity_in_stock == 45
    assert order.status == OrderStatus.CONFIRMED
    assert order.invoice is not None
    assert float(order.invoice.total_amount) == 500.0


def test_draft_order_does_not_touch_stock(db_session: Session):
    product = _make_product(db_session, "O-2", qty=30)
    order = crud.create_order(
        db_session,
        schemas.OrderCreate(
            items=[schemas.OrderItemCreate(product_id=product.id, quantity=4)],
            confirm=False,
        ),
    )
    db_session.refresh(product)
    assert product.quantity_in_stock == 30
    assert order.status == OrderStatus.DRAFT
    assert order.invoice is None


def test_confirm_draft_order(db_session: Session):
    product = _make_product(db_session, "O-3", qty=10)
    order = crud.create_order(
        db_session,
        schemas.OrderCreate(
            items=[schemas.OrderItemCreate(product_id=product.id, quantity=3)],
            confirm=False,
        ),
    )
    crud.confirm_order(db_session, order)
    db_session.refresh(product)
    assert product.quantity_in_stock == 7
    assert order.invoice is not None


def test_insufficient_stock_raises_and_rolls_back(db_session: Session):
    product = _make_product(db_session, "O-4", qty=2)
    with pytest.raises(crud.OrderError):
        crud.create_order(
            db_session,
            schemas.OrderCreate(
                items=[schemas.OrderItemCreate(product_id=product.id, quantity=5)]
            ),
        )
    db_session.refresh(product)
    assert product.quantity_in_stock == 2


def test_duplicate_lines_are_merged_for_stock_check(db_session: Session):
    product = _make_product(db_session, "O-5", qty=10, price=50.0)
    order = crud.create_order(
        db_session,
        schemas.OrderCreate(
            items=[
                schemas.OrderItemCreate(product_id=product.id, quantity=4),
                schemas.OrderItemCreate(product_id=product.id, quantity=3),
            ]
        ),
    )
    db_session.refresh(product)
    assert product.quantity_in_stock == 3
    assert len(order.items) == 1
    assert order.items[0].quantity == 7
    assert float(order.total_amount) == 350.0


def test_cancelling_confirmed_order_restocks(db_session: Session):
    product = _make_product(db_session, "O-6", qty=20)
    order = crud.create_order(
        db_session,
        schemas.OrderCreate(
            items=[schemas.OrderItemCreate(product_id=product.id, quantity=8)]
        ),
    )
    db_session.refresh(product)
    assert product.quantity_in_stock == 12

    crud.cancel_order(db_session, order)
    db_session.refresh(product)
    assert product.quantity_in_stock == 20
    assert order.status == OrderStatus.CANCELLED
    assert order.invoice.status.value == "cancelled"

    movements = products_crud.list_movements(db_session, product.id)
    returns = [m for m in movements if m.reason == MovementReason.RETURN]
    assert len(returns) == 1
    assert returns[0].change == 8


def test_cannot_confirm_twice(db_session: Session):
    product = _make_product(db_session, "O-7", qty=10)
    order = crud.create_order(
        db_session,
        schemas.OrderCreate(
            items=[schemas.OrderItemCreate(product_id=product.id, quantity=1)]
        ),
    )
    with pytest.raises(crud.OrderError):
        crud.confirm_order(db_session, order)


def test_empty_order_rejected(db_session: Session):
    with pytest.raises(crud.OrderError):
        crud.create_order(db_session, schemas.OrderCreate(items=[], confirm=True))

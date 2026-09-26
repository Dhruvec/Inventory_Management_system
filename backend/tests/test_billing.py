"""Unit tests for invoicing and partial-payment handling."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app import schemas
from app.crud import billing as crud
from app.crud import orders as orders_crud
from app.crud import products as products_crud
from app.models import InvoiceStatus, PaymentMethod


def _confirmed_invoice(db: Session):
    product = products_crud.create_product(
        db,
        schemas.ProductCreate(
            sku="B-1", name="Billing Item", unit_price=200.0, quantity_in_stock=100
        ),
    )
    order = orders_crud.create_order(
        db,
        schemas.OrderCreate(
            items=[schemas.OrderItemCreate(product_id=product.id, quantity=5)]
        ),
    )
    return order.invoice


def test_invoice_created_unpaid(db_session: Session):
    invoice = _confirmed_invoice(db_session)
    assert invoice.status == InvoiceStatus.UNPAID
    assert float(invoice.total_amount) == 1000.0
    assert invoice.balance_due == 1000.0


def test_partial_payment_marks_partially_paid(db_session: Session):
    invoice = _confirmed_invoice(db_session)
    crud.record_payment(
        db_session, invoice, schemas.PaymentCreate(amount=400.0, method=PaymentMethod.CASH)
    )
    db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.PARTIALLY_PAID
    assert float(invoice.amount_paid) == 400.0
    assert invoice.balance_due == 600.0


def test_second_payment_settles_invoice(db_session: Session):
    invoice = _confirmed_invoice(db_session)
    crud.record_payment(db_session, invoice, schemas.PaymentCreate(amount=400.0))
    crud.record_payment(db_session, invoice, schemas.PaymentCreate(amount=600.0))
    db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.PAID
    assert invoice.balance_due == 0.0
    assert len(invoice.payments) == 2


def test_overpayment_rejected(db_session: Session):
    invoice = _confirmed_invoice(db_session)
    with pytest.raises(crud.BillingError):
        crud.record_payment(db_session, invoice, schemas.PaymentCreate(amount=1500.0))
    db_session.refresh(invoice)
    assert float(invoice.amount_paid) == 0.0


def test_cannot_pay_cancelled_invoice(db_session: Session):
    product = products_crud.create_product(
        db_session,
        schemas.ProductCreate(sku="B-2", name="Item", unit_price=50.0, quantity_in_stock=10),
    )
    order = orders_crud.create_order(
        db_session,
        schemas.OrderCreate(items=[schemas.OrderItemCreate(product_id=product.id, quantity=2)]),
    )
    orders_crud.cancel_order(db_session, order)
    db_session.refresh(order.invoice)
    with pytest.raises(crud.BillingError):
        crud.record_payment(db_session, order.invoice, schemas.PaymentCreate(amount=10.0))

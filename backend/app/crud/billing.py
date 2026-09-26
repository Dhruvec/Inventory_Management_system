"""Invoice and payment operations, including partial-payment handling."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas


class BillingError(Exception):
    """Raised for invalid billing operations (overpayment, etc.)."""


def get_invoice(db: Session, invoice_id: int) -> models.Invoice | None:
    return db.get(models.Invoice, invoice_id)


def get_invoice_by_order(db: Session, order_id: int) -> models.Invoice | None:
    return db.scalar(select(models.Invoice).where(models.Invoice.order_id == order_id))


def list_invoices(
    db: Session,
    *,
    status: models.InvoiceStatus | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[models.Invoice]:
    stmt = select(models.Invoice)
    if status:
        stmt = stmt.where(models.Invoice.status == status)
    stmt = stmt.order_by(models.Invoice.issued_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def record_payment(
    db: Session, invoice: models.Invoice, payload: schemas.PaymentCreate
) -> models.Payment:
    """Record a (possibly partial) payment and recompute the invoice status.

    Guards against:
    * paying a cancelled invoice
    * overpaying beyond the outstanding balance
    """
    if invoice.status == models.InvoiceStatus.CANCELLED:
        raise BillingError("Cannot pay a cancelled invoice")

    amount = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    if amount <= 0:
        raise BillingError("Payment amount must be positive")

    balance = Decimal(str(invoice.total_amount)) - Decimal(str(invoice.amount_paid))
    if amount > balance:
        raise BillingError(
            f"Payment exceeds outstanding balance of {balance:.2f}"
        )

    payment = models.Payment(
        invoice_id=invoice.id,
        amount=amount,
        method=payload.method,
        reference=payload.reference,
    )
    db.add(payment)

    invoice.amount_paid = (Decimal(str(invoice.amount_paid)) + amount).quantize(
        Decimal("0.01")
    )
    _refresh_status(invoice)
    db.commit()
    db.refresh(invoice)
    return payment


def _refresh_status(invoice: models.Invoice) -> None:
    """Derive invoice status from the paid amount."""
    total = Decimal(str(invoice.total_amount))
    paid = Decimal(str(invoice.amount_paid))
    if paid <= 0:
        invoice.status = models.InvoiceStatus.UNPAID
    elif paid < total:
        invoice.status = models.InvoiceStatus.PARTIALLY_PAID
    else:
        invoice.status = models.InvoiceStatus.PAID

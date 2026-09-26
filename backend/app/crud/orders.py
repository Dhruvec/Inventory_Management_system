"""Order lifecycle: creation, stock deduction, cancellation and invoicing.

This module holds the most business-critical logic in the system. Invariants:

* Only ``CONFIRMED`` orders have deducted stock.
* Confirming an order deducts stock atomically and generates an invoice.
* Cancelling a confirmed order (a "return") restocks every line item and
  cancels the linked invoice.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import products as products_crud


class OrderError(Exception):
    """Raised for domain-rule violations (e.g. insufficient stock)."""


def _next_reference(db: Session, prefix: str) -> str:
    """Generate a human-friendly, sequential reference like ``ORD-000007``."""
    count = db.scalar(select(func.count()).select_from(models.Order)) or 0
    return f"{prefix}-{count + 1:06d}"


def _next_invoice_number(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(models.Invoice)) or 0
    year = datetime.now(timezone.utc).year
    return f"INV-{year}-{count + 1:06d}"


def create_order(
    db: Session, payload: schemas.OrderCreate, user: models.User | None = None
) -> models.Order:
    """Create an order from line items.

    When ``confirm`` is true the stock is deducted immediately and an invoice is
    generated; otherwise the order stays in ``DRAFT`` with no stock movement.
    """
    if not payload.items:
        raise OrderError("An order must contain at least one item")

    order = models.Order(
        reference=_next_reference(db, "ORD"),
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        status=models.OrderStatus.DRAFT,
        created_by_id=user.id if user else None,
    )
    db.add(order)
    db.flush()  # assign order.id

    # Merge duplicate lines for the same product so stock checks are accurate.
    merged: dict[int, int] = {}
    for item in payload.items:
        merged[item.product_id] = merged.get(item.product_id, 0) + item.quantity

    total = Decimal("0")
    for product_id, quantity in merged.items():
        product = products_crud.get_product(db, product_id)
        if product is None or not product.is_active:
            raise OrderError(f"Product {product_id} not found or inactive")

        if payload.confirm and product.quantity_in_stock < quantity:
            raise OrderError(
                f"Insufficient stock for '{product.name}': "
                f"requested {quantity}, available {product.quantity_in_stock}"
            )

        unit_price = Decimal(str(product.unit_price))
        line_total = (unit_price * quantity).quantize(Decimal("0.01"))
        total += line_total

        order.items.append(
            models.OrderItem(
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    order.total_amount = total
    db.flush()

    if payload.confirm:
        confirm_order(db, order)
    else:
        db.commit()

    db.refresh(order)
    return order


def confirm_order(db: Session, order: models.Order) -> models.Order:
    """Deduct stock for every line item and issue the invoice."""
    if order.status == models.OrderStatus.CONFIRMED:
        raise OrderError("Order is already confirmed")
    if order.status == models.OrderStatus.CANCELLED:
        raise OrderError("Cannot confirm a cancelled order")

    # Validate all stock first so we fail atomically (no partial deduction).
    for item in order.items:
        product = item.product
        if product is None or not product.is_active:
            raise OrderError(f"Product {item.product_id} is unavailable")
        if product.quantity_in_stock < item.quantity:
            raise OrderError(
                f"Insufficient stock for '{product.name}': "
                f"requested {item.quantity}, available {product.quantity_in_stock}"
            )

    for item in order.items:
        products_crud._record_movement(
            db,
            item.product,
            -item.quantity,
            models.MovementReason.SALE,
            reference=order.reference,
        )

    order.status = models.OrderStatus.CONFIRMED
    db.flush()
    _generate_invoice(db, order)
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order: models.Order, restock: bool = True) -> models.Order:
    """Cancel an order. If it was confirmed, restock the items (a return)."""
    if order.status == models.OrderStatus.CANCELLED:
        raise OrderError("Order is already cancelled")

    if order.status == models.OrderStatus.CONFIRMED and restock:
        for item in order.items:
            product = item.product
            if product is not None:
                products_crud._record_movement(
                    db,
                    product,
                    item.quantity,
                    models.MovementReason.RETURN,
                    reference=order.reference,
                    note="Order cancelled / returned",
                )

    order.status = models.OrderStatus.CANCELLED
    if order.invoice is not None:
        order.invoice.status = models.InvoiceStatus.CANCELLED
    db.commit()
    db.refresh(order)
    return order


def _generate_invoice(db: Session, order: models.Order) -> models.Invoice:
    """Create the invoice for a confirmed order (called within a transaction)."""
    if order.invoice is not None:
        return order.invoice

    subtotal = sum(
        (Decimal(str(item.line_total)) for item in order.items), Decimal("0")
    ).quantize(Decimal("0.01"))

    invoice = models.Invoice(
        number=_next_invoice_number(db),
        order_id=order.id,
        status=models.InvoiceStatus.UNPAID,
        subtotal=subtotal,
        tax_amount=Decimal("0"),
        total_amount=subtotal,
        amount_paid=Decimal("0"),
    )
    db.add(invoice)
    db.flush()
    return invoice


def get_order(db: Session, order_id: int) -> models.Order | None:
    return db.get(models.Order, order_id)


def list_orders(
    db: Session,
    *,
    status: models.OrderStatus | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[models.Order]:
    stmt = select(models.Order)
    if status:
        stmt = stmt.where(models.Order.status == status)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            models.Order.reference.ilike(like) | models.Order.customer_name.ilike(like)
        )
    stmt = stmt.order_by(models.Order.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))

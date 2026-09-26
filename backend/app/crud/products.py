"""Product catalogue CRUD and stock-level operations."""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import models, schemas


def _record_movement(
    db: Session,
    product: models.Product,
    change: int,
    reason: models.MovementReason,
    reference: str | None = None,
    note: str | None = None,
) -> models.StockMovement:
    """Apply a stock delta to a product and log the movement."""
    product.quantity_in_stock += change
    movement = models.StockMovement(
        product_id=product.id,
        change=change,
        quantity_after=product.quantity_in_stock,
        reason=reason,
        reference=reference,
        note=note,
    )
    db.add(movement)
    return movement


def create_product(db: Session, payload: schemas.ProductCreate) -> models.Product:
    """Create a product and record its opening stock exactly once.

    The product row starts at zero so that the opening quantity flows through
    :func:`_record_movement` (which applies the delta and writes the audit row),
    avoiding double-counting the quantity carried on the request payload.
    """
    data = payload.model_dump()
    opening_stock = data.pop("quantity_in_stock", 0)

    product = models.Product(**data, quantity_in_stock=0)
    db.add(product)
    db.flush()  # assign product.id

    if opening_stock:
        _record_movement(
            db,
            product,
            opening_stock,
            models.MovementReason.PURCHASE,
            note="Opening stock",
        )

    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: int) -> models.Product | None:
    return db.get(models.Product, product_id)


def get_product_by_sku(db: Session, sku: str) -> models.Product | None:
    return db.scalar(select(models.Product).where(models.Product.sku == sku))


def list_products(
    db: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    active_only: bool = False,
    low_stock_only: bool = False,
    offset: int = 0,
    limit: int = 100,
) -> list[models.Product]:
    stmt = select(models.Product)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(models.Product.name.ilike(like), models.Product.sku.ilike(like))
        )
    if category:
        stmt = stmt.where(models.Product.category == category)
    if active_only:
        stmt = stmt.where(models.Product.is_active.is_(True))
    if low_stock_only:
        stmt = stmt.where(
            models.Product.quantity_in_stock <= models.Product.low_stock_threshold
        )
    stmt = stmt.order_by(models.Product.name).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def update_product(
    db: Session, product: models.Product, payload: schemas.ProductUpdate
) -> models.Product:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: models.Product) -> None:
    """Soft-delete: keeps historical order/invoice references intact."""
    product.is_active = False
    db.commit()


def adjust_stock(
    db: Session, product: models.Product, payload: schemas.StockAdjustment
) -> models.Product:
    """Manually add/remove stock, guarding against negative inventory."""
    if product.quantity_in_stock + payload.change < 0:
        raise ValueError("Adjustment would result in negative stock")
    _record_movement(
        db, product, payload.change, payload.reason, note=payload.note
    )
    db.commit()
    db.refresh(product)
    return product


def list_movements(
    db: Session, product_id: int, limit: int = 100
) -> list[models.StockMovement]:
    stmt = (
        select(models.StockMovement)
        .where(models.StockMovement.product_id == product_id)
        .order_by(models.StockMovement.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def low_stock_products(db: Session) -> list[models.Product]:
    stmt = (
        select(models.Product)
        .where(
            models.Product.is_active.is_(True),
            models.Product.quantity_in_stock <= models.Product.low_stock_threshold,
        )
        .order_by(models.Product.quantity_in_stock)
    )
    return list(db.scalars(stmt))

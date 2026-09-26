"""Aggregated metrics for the dashboard."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas


def summary(db: Session) -> schemas.DashboardSummary:
    total_products = db.scalar(select(func.count()).select_from(models.Product)) or 0
    active_products = (
        db.scalar(
            select(func.count())
            .select_from(models.Product)
            .where(models.Product.is_active.is_(True))
        )
        or 0
    )
    low_stock_count = (
        db.scalar(
            select(func.count())
            .select_from(models.Product)
            .where(
                models.Product.is_active.is_(True),
                models.Product.quantity_in_stock <= models.Product.low_stock_threshold,
            )
        )
        or 0
    )
    out_of_stock_count = (
        db.scalar(
            select(func.count())
            .select_from(models.Product)
            .where(models.Product.quantity_in_stock == 0)
        )
        or 0
    )

    total_orders = db.scalar(select(func.count()).select_from(models.Order)) or 0
    confirmed_orders = (
        db.scalar(
            select(func.count())
            .select_from(models.Order)
            .where(models.Order.status == models.OrderStatus.CONFIRMED)
        )
        or 0
    )
    cancelled_orders = (
        db.scalar(
            select(func.count())
            .select_from(models.Order)
            .where(models.Order.status == models.OrderStatus.CANCELLED)
        )
        or 0
    )

    total_revenue = db.scalar(
        select(func.coalesce(func.sum(models.Order.total_amount), 0)).where(
            models.Order.status == models.OrderStatus.CONFIRMED
        )
    ) or 0

    outstanding = db.scalar(
        select(
            func.coalesce(
                func.sum(models.Invoice.total_amount - models.Invoice.amount_paid), 0
            )
        ).where(models.Invoice.status != models.InvoiceStatus.CANCELLED)
    ) or 0

    inventory_value = db.scalar(
        select(
            func.coalesce(
                func.sum(models.Product.quantity_in_stock * models.Product.cost_price), 0
            )
        ).where(models.Product.is_active.is_(True))
    ) or 0

    return schemas.DashboardSummary(
        total_products=int(total_products),
        active_products=int(active_products),
        low_stock_count=int(low_stock_count),
        out_of_stock_count=int(out_of_stock_count),
        total_orders=int(total_orders),
        confirmed_orders=int(confirmed_orders),
        cancelled_orders=int(cancelled_orders),
        total_revenue=float(Decimal(str(total_revenue))),
        outstanding_balance=float(Decimal(str(outstanding))),
        inventory_value=float(Decimal(str(inventory_value))),
    )


def low_stock_alerts(db: Session) -> list[schemas.LowStockAlert]:
    products = db.scalars(
        select(models.Product)
        .where(
            models.Product.is_active.is_(True),
            models.Product.quantity_in_stock <= models.Product.low_stock_threshold,
        )
        .order_by(models.Product.quantity_in_stock)
    )
    return [
        schemas.LowStockAlert(
            product_id=p.id,
            sku=p.sku,
            name=p.name,
            quantity_in_stock=p.quantity_in_stock,
            low_stock_threshold=p.low_stock_threshold,
            deficit=max(p.low_stock_threshold - p.quantity_in_stock, 0),
        )
        for p in products
    ]

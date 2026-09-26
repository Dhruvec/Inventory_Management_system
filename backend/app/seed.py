"""Seed the database with demo data.

Usage:
    python -m app.seed

Creates an owner account (owner/owner123), a handful of products, one confirmed
order with a partial payment, and one draft order so the dashboard and alerts
have something to show.
"""
from __future__ import annotations

import logging

from app import schemas
from app.crud import billing as billing_crud
from app.crud import orders as orders_crud
from app.crud import products as products_crud
from app.database import SessionLocal, init_db
from app.models import PaymentMethod, User
from app.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

DEMO_PRODUCTS = [
    ("SKU-1001", "Paracetamol 500mg (strip)", "Pharmacy", 25.0, 15.0, 120, 30),
    ("SKU-1002", "Hand Sanitiser 500ml", "Pharmacy", 150.0, 95.0, 8, 20),
    ("SKU-1003", "A4 Paper Ream", "Stationery", 320.0, 250.0, 40, 10),
    ("SKU-1004", "Blue Ballpoint Pen", "Stationery", 10.0, 5.0, 500, 50),
    ("SKU-1005", "Cold Coffee 250ml", "Beverages", 60.0, 38.0, 5, 15),
    ("SKU-1006", "Bottled Water 1L", "Beverages", 20.0, 12.0, 200, 40),
    ("SKU-1007", "Notebook 200pg", "Stationery", 75.0, 50.0, 0, 12),
]


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).first() is None:
            db.add(
                User(
                    username="owner",
                    full_name="Shop Owner",
                    hashed_password=hash_password("owner123"),
                    is_owner=True,
                )
            )
            db.commit()
            logger.info("Created owner account (owner / owner123)")

        if not products_crud.list_products(db, limit=1):
            for sku, name, category, price, cost, qty, threshold in DEMO_PRODUCTS:
                products_crud.create_product(
                    db,
                    schemas.ProductCreate(
                        sku=sku,
                        name=name,
                        category=category,
                        unit_price=price,
                        cost_price=cost,
                        quantity_in_stock=qty,
                        low_stock_threshold=threshold,
                    ),
                )
            logger.info("Seeded %d products", len(DEMO_PRODUCTS))

        # Demo confirmed order with stock deduction + invoice.
        if not orders_crud.list_orders(db, limit=1):
            order = orders_crud.create_order(
                db,
                schemas.OrderCreate(
                    customer_name="Walk-in Customer",
                    items=[
                        schemas.OrderItemCreate(product_id=1, quantity=2),
                        schemas.OrderItemCreate(product_id=6, quantity=3),
                    ],
                    confirm=True,
                ),
            )
            invoice = billing_crud.get_invoice_by_order(db, order.id)
            if invoice:
                billing_crud.record_payment(
                    db,
                    invoice,
                    schemas.PaymentCreate(
                        amount=float(invoice.total_amount) / 2,
                        method=PaymentMethod.UPI,
                        reference="UPI-DEMO",
                    ),
                )
            # A draft order to exercise the confirm flow in the UI.
            orders_crud.create_order(
                db,
                schemas.OrderCreate(
                    customer_name="A. Sharma",
                    items=[schemas.OrderItemCreate(product_id=4, quantity=10)],
                    confirm=False,
                ),
            )
            logger.info("Seeded demo orders and a partial payment")

        logger.info("Seeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()

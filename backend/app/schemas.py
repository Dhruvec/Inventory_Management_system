"""Pydantic v2 schemas (request/response DTOs) for the API layer."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    InvoiceStatus,
    MovementReason,
    OrderStatus,
    PaymentMethod,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class Token(ORMModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = None
    is_owner: bool = False


class UserRead(ORMModel):
    id: int
    username: str
    full_name: str | None
    is_active: bool
    is_owner: bool
    created_at: datetime


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #
class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    unit_price: float = Field(ge=0, default=0)
    cost_price: float = Field(ge=0, default=0)
    quantity_in_stock: int = Field(ge=0, default=0)
    low_stock_threshold: int = Field(ge=0, default=10)
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    category: str | None = None
    unit_price: float | None = Field(default=None, ge=0)
    cost_price: float | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductRead(ORMModel):
    id: int
    sku: str
    name: str
    description: str | None
    category: str | None
    unit_price: float
    cost_price: float
    quantity_in_stock: int
    low_stock_threshold: int
    is_active: bool
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime


class StockAdjustment(BaseModel):
    """Manual stock change (restock, shrinkage, correction)."""

    change: int = Field(description="Positive to add stock, negative to remove")
    reason: MovementReason = MovementReason.ADJUSTMENT
    note: str | None = None


class StockMovementRead(ORMModel):
    id: int
    product_id: int
    change: int
    quantity_after: int
    reason: MovementReason
    reference: str | None
    note: str | None
    created_at: datetime


# --------------------------------------------------------------------------- #
# Orders
# --------------------------------------------------------------------------- #
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderItemRead(ORMModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    line_total: float


class OrderCreate(BaseModel):
    customer_name: str | None = None
    customer_phone: str | None = None
    # An empty cart is allowed at the schema layer so the service-level guard in
    # crud.orders.create_order() is the single source of truth for the rule.
    items: list[OrderItemCreate] = Field(default_factory=list)
    confirm: bool = Field(
        default=True,
        description="Confirm immediately (deducts stock) vs. keep as draft",
    )


class OrderRead(ORMModel):
    id: int
    reference: str
    customer_name: str | None
    customer_phone: str | None
    status: OrderStatus
    total_amount: float
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead] = []


# --------------------------------------------------------------------------- #
# Invoices & Payments
# --------------------------------------------------------------------------- #
class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    method: PaymentMethod = PaymentMethod.CASH
    reference: str | None = None


class PaymentRead(ORMModel):
    id: int
    invoice_id: int
    amount: float
    method: PaymentMethod
    reference: str | None
    paid_at: datetime


class InvoiceRead(ORMModel):
    id: int
    number: str
    order_id: int
    status: InvoiceStatus
    subtotal: float
    tax_amount: float
    total_amount: float
    amount_paid: float
    balance_due: float
    issued_at: datetime
    payments: list[PaymentRead] = []


# --------------------------------------------------------------------------- #
# Dashboard / misc
# --------------------------------------------------------------------------- #
class LowStockAlert(BaseModel):
    product_id: int
    sku: str
    name: str
    quantity_in_stock: int
    low_stock_threshold: int
    deficit: int


class DashboardSummary(BaseModel):
    total_products: int
    active_products: int
    low_stock_count: int
    out_of_stock_count: int
    total_orders: int
    confirmed_orders: int
    cancelled_orders: int
    total_revenue: float
    outstanding_balance: float
    inventory_value: float

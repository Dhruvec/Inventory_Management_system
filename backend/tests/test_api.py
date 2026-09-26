"""Integration tests exercising the HTTP API end to end."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_auth_required_for_product_creation(client: TestClient):
    resp = client.post(
        "/api/products",
        json={"sku": "X-1", "name": "No auth", "unit_price": 1},
    )
    assert resp.status_code == 401


def test_full_order_and_payment_flow(client: TestClient, auth_headers: dict):
    # 1. Create a product (authenticated).
    create = client.post(
        "/api/products",
        headers=auth_headers,
        json={
            "sku": "API-1",
            "name": "API Widget",
            "unit_price": 250.0,
            "cost_price": 150.0,
            "quantity_in_stock": 20,
            "low_stock_threshold": 5,
        },
    )
    assert create.status_code == 201, create.text
    product_id = create.json()["id"]

    # 2. Place a confirmed order.
    order = client.post(
        "/api/orders",
        headers=auth_headers,
        json={
            "customer_name": "Test Buyer",
            "items": [{"product_id": product_id, "quantity": 4}],
            "confirm": True,
        },
    )
    assert order.status_code == 201, order.text
    order_body = order.json()
    assert order_body["status"] == "confirmed"
    assert order_body["total_amount"] == 1000.0

    # 3. Stock was deducted.
    product = client.get(f"/api/products/{product_id}").json()
    assert product["quantity_in_stock"] == 16

    # 4. Invoice generated and payable.
    invoice = client.get(f"/api/invoices/by-order/{order_body['id']}")
    assert invoice.status_code == 200
    invoice_body = invoice.json()
    assert invoice_body["status"] == "unpaid"

    pay = client.post(
        f"/api/invoices/{invoice_body['id']}/payments",
        headers=auth_headers,
        json={"amount": 400.0, "method": "cash"},
    )
    assert pay.status_code == 201, pay.text
    assert pay.json()["status"] == "partially_paid"
    assert pay.json()["balance_due"] == 600.0


def test_low_stock_alert_endpoint(client: TestClient, auth_headers: dict):
    client.post(
        "/api/products",
        headers=auth_headers,
        json={
            "sku": "LOW-API",
            "name": "Nearly Gone",
            "unit_price": 10,
            "quantity_in_stock": 1,
            "low_stock_threshold": 5,
        },
    )
    alerts = client.get("/api/alerts/low-stock")
    assert alerts.status_code == 200
    skus = [a["sku"] for a in alerts.json()]
    assert "LOW-API" in skus


def test_dashboard_summary(client: TestClient, auth_headers: dict):
    client.post(
        "/api/products",
        headers=auth_headers,
        json={
            "sku": "DASH-1",
            "name": "Dash",
            "unit_price": 100,
            "cost_price": 50,
            "quantity_in_stock": 10,
        },
    )
    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_products"] >= 1
    assert "inventory_value" in body


def test_duplicate_sku_rejected(client: TestClient, auth_headers: dict):
    payload = {"sku": "DUP-1", "name": "Dup", "unit_price": 5}
    first = client.post("/api/products", headers=auth_headers, json=payload)
    assert first.status_code == 201
    second = client.post("/api/products", headers=auth_headers, json=payload)
    assert second.status_code == 400

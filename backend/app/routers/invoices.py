"""Invoice and payment endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import billing as crud
from app.database import get_db
from app.dependencies import get_current_user
from app.models import InvoiceStatus

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("", response_model=list[schemas.InvoiceRead])
def list_invoices(
    status: InvoiceStatus | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.list_invoices(db, status=status, offset=offset, limit=limit)


@router.get("/{invoice_id}", response_model=schemas.InvoiceRead)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/by-order/{order_id}", response_model=schemas.InvoiceRead)
def get_invoice_by_order(order_id: int, db: Session = Depends(get_db)):
    invoice = crud.get_invoice_by_order(db, order_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found for order")
    return invoice


@router.post("/{invoice_id}/payments", response_model=schemas.InvoiceRead, status_code=201)
def add_payment(
    invoice_id: int,
    payload: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    invoice = crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        crud.record_payment(db, invoice, payload)
    except crud.BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(invoice)
    return invoice

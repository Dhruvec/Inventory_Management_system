"""Order endpoints: create, list, confirm, cancel (return)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import orders as crud
from app.database import get_db
from app.dependencies import get_current_user
from app.models import OrderStatus

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=list[schemas.OrderRead])
def list_orders(
    status: OrderStatus | None = None,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.list_orders(db, status=status, search=search, offset=offset, limit=limit)


@router.post("", response_model=schemas.OrderRead, status_code=201)
def create_order(
    payload: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        return crud.create_order(db, payload, user=current_user)
    except crud.OrderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{order_id}", response_model=schemas.OrderRead)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/confirm", response_model=schemas.OrderRead)
def confirm_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    try:
        return crud.confirm_order(db, order)
    except crud.OrderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{order_id}/cancel", response_model=schemas.OrderRead)
def cancel_order(
    order_id: int,
    restock: bool = True,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    try:
        return crud.cancel_order(db, order, restock=restock)
    except crud.OrderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

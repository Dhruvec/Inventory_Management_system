"""Product catalogue and stock-management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import products as crud
from app.database import get_db
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[schemas.ProductRead])
def list_products(
    search: str | None = None,
    category: str | None = None,
    active_only: bool = False,
    low_stock_only: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.list_products(
        db,
        search=search,
        category=category,
        active_only=active_only,
        low_stock_only=low_stock_only,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=schemas.ProductRead, status_code=201)
def create_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    if crud.get_product_by_sku(db, payload.sku):
        raise HTTPException(status_code=400, detail="SKU already exists")
    return crud.create_product(db, payload)


@router.get("/{product_id}", response_model=schemas.ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=schemas.ProductRead)
def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud.update_product(db, product, payload)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    crud.delete_product(db, product)


@router.post("/{product_id}/stock", response_model=schemas.ProductRead)
def adjust_stock(
    product_id: int,
    payload: schemas.StockAdjustment,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        return crud.adjust_stock(db, product, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{product_id}/movements", response_model=list[schemas.StockMovementRead])
def list_movements(product_id: int, db: Session = Depends(get_db)):
    return crud.list_movements(db, product_id)

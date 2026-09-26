"""Low-stock alerts and dashboard summary endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.crud import reports as crud
from app.database import get_db

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/alerts/low-stock", response_model=list[schemas.LowStockAlert])
def low_stock_alerts(db: Session = Depends(get_db)):
    return crud.low_stock_alerts(db)


@router.get("/dashboard/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    return crud.summary(db)

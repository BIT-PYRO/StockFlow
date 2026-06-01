from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DashboardResponse
import app.crud as crud

router = APIRouter()


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """
    Business analytics dashboard.

    Returns aggregate KPIs for products, customers, orders (broken down by
    status), total completed-order revenue, and a list of products below the
    low-stock threshold (stock_quantity < 10) ordered by stock level ascending.
    """
    return crud.get_dashboard_stats(db)

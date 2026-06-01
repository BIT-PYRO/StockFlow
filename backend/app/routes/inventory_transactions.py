from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TransactionType
from app.schemas import InventoryTransactionListResponse
import app.crud as crud

router = APIRouter()


@router.get("", response_model=InventoryTransactionListResponse)
def list_inventory_transactions(
    product_id: int | None = Query(
        default=None,
        ge=1,
        description="Filter by product ID",
    ),
    transaction_type: TransactionType | None = Query(
        default=None,
        description="Filter by transaction type: IN, OUT, or ADJUSTMENT",
    ),
    start_date: date | None = Query(
        default=None,
        description="Include transactions on or after this date (YYYY-MM-DD)",
    ),
    end_date: date | None = Query(
        default=None,
        description="Include transactions on or before this date (YYYY-MM-DD)",
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (1-based)",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=200,
        description="Number of records per page (max 200)",
    ),
    db: Session = Depends(get_db),
):
    """
    List all inventory stock movements with optional filtering and pagination.

    - **product_id** — show movements for a single product
    - **transaction_type** — `IN` (restock/return), `OUT` (sale/deduction), `ADJUSTMENT`
    - **start_date / end_date** — inclusive date range filter (YYYY-MM-DD)
    - **page / page_size** — pagination; results ordered newest first

    `previous_stock` and `new_stock` are derived from the cumulative history of
    movements for each product and reflect the stock level immediately before and
    after each transaction.
    """
    return crud.get_inventory_transactions(
        db=db,
        product_id=product_id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardStats
from app.services.dashboard_service import DashboardService
from app.auth.rbac import require_manager_or_above
from app.models.user import User

router = APIRouter()


@router.get("", response_model=DashboardStats)
def get_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """Aggregate KPIs and stats for the dashboard. Manager and Admin only."""
    return DashboardService(db).get_stats()

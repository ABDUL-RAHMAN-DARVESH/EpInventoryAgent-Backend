from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.dashboard import DashboardSummary, WeeklyExportSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardSummary)
async def get_dashboard(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_dashboard_summary(db, current_user.id)


@router.get("/weekly-export/previous", response_model=WeeklyExportSummary)
async def get_previous_week_export(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await dashboard_service.get_previous_week_export(db, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Last week's export has expired.")
    return result

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.payment import PaymentFeedItem
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[PaymentFeedItem])
async def list_recent_payments(
    skip: int = 0,
    limit: int = Query(50, le=2000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unified feed of customer + manufacturer payments, newest first."""
    return await payment_service.list_recent_payments(db, current_user.id, skip=skip, limit=limit)

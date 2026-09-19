import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.payment import ManufacturerPaymentCreate, ManufacturerPaymentRead, ManufacturerPaymentUpdate
from app.schemas.purchase import PurchaseCreate, PurchaseRead, PurchaseUpdate
from app.services import payment_service, purchase_service

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.post("", response_model=PurchaseRead, status_code=201)
async def create_purchase(
    data: PurchaseCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await purchase_service.create_purchase(db, current_user.id, data)


@router.get("", response_model=list[PurchaseRead])
async def list_purchases(
    manufacturer_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await purchase_service.list_purchases(db, current_user.id, manufacturer_id=manufacturer_id, skip=skip, limit=limit)


@router.get("/{purchase_id}", response_model=PurchaseRead)
async def get_purchase(
    purchase_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await purchase_service.get_purchase(db, current_user.id, purchase_id)


@router.patch("/{purchase_id}", response_model=PurchaseRead)
async def update_purchase(
    purchase_id: uuid.UUID,
    data: PurchaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await purchase_service.update_purchase(db, current_user.id, purchase_id, data)


@router.delete("/{purchase_id}", status_code=204)
async def delete_purchase(
    purchase_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await purchase_service.delete_purchase(db, current_user.id, purchase_id)


@router.post("/{purchase_id}/payments", response_model=ManufacturerPaymentRead, status_code=201)
async def record_purchase_payment(
    purchase_id: uuid.UUID,
    data: ManufacturerPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await payment_service.record_manufacturer_payment(db, current_user.id, purchase_id, data)


@router.get("/{purchase_id}/payments", response_model=list[ManufacturerPaymentRead])
async def list_purchase_payments(
    purchase_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await payment_service.list_manufacturer_payments_by_purchase(db, current_user.id, purchase_id)


@router.patch("/{purchase_id}/payments/{payment_id}", response_model=ManufacturerPaymentRead)
async def update_purchase_payment(
    purchase_id: uuid.UUID,
    payment_id: uuid.UUID,
    data: ManufacturerPaymentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await payment_service.update_manufacturer_payment(db, current_user.id, purchase_id, payment_id, data)


@router.delete("/{purchase_id}/payments/{payment_id}", status_code=204)
async def delete_purchase_payment(
    purchase_id: uuid.UUID,
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await payment_service.delete_manufacturer_payment(db, current_user.id, purchase_id, payment_id)

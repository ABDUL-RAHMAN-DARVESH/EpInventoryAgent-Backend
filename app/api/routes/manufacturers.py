import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.manufacturer import ManufacturerCreate, ManufacturerRead, ManufacturerUpdate
from app.schemas.payment import ManufacturerPaymentRead
from app.schemas.purchase import PurchaseCreate, PurchaseRead
from app.services import manufacturer_service, payment_service, purchase_service

router = APIRouter(prefix="/manufacturers", tags=["manufacturers"])


@router.post("", response_model=ManufacturerRead, status_code=201)
async def create_manufacturer(
    data: ManufacturerCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await manufacturer_service.create_manufacturer(db, current_user.id, data)


@router.get("", response_model=list[ManufacturerRead])
async def list_manufacturers(
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await manufacturer_service.list_manufacturers(db, current_user.id, is_active=is_active, skip=skip, limit=limit)


@router.get("/{manufacturer_id}", response_model=ManufacturerRead)
async def get_manufacturer(
    manufacturer_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await manufacturer_service.get_manufacturer(db, current_user.id, manufacturer_id)


@router.patch("/{manufacturer_id}", response_model=ManufacturerRead)
async def update_manufacturer(
    manufacturer_id: uuid.UUID,
    data: ManufacturerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await manufacturer_service.update_manufacturer(db, current_user.id, manufacturer_id, data)


@router.delete("/{manufacturer_id}", response_model=ManufacturerRead)
async def deactivate_manufacturer(
    manufacturer_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Soft-deletes (deactivates) the manufacturer. Manufacturers with financial history are never hard-deleted."""
    return await manufacturer_service.deactivate_manufacturer(db, current_user.id, manufacturer_id)


@router.post("/{manufacturer_id}/image", response_model=ManufacturerRead)
async def upload_manufacturer_image(
    manufacturer_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    return await manufacturer_service.upload_manufacturer_image(
        db, current_user.id, manufacturer_id, file_bytes, file.content_type
    )


@router.post("/{manufacturer_id}/purchases", response_model=PurchaseRead, status_code=201)
async def create_purchase_for_manufacturer(
    manufacturer_id: uuid.UUID,
    data: PurchaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await manufacturer_service.get_manufacturer(db, current_user.id, manufacturer_id)
    data = data.model_copy(update={"manufacturer_id": manufacturer_id})
    return await purchase_service.create_purchase(db, current_user.id, data)


@router.get("/{manufacturer_id}/purchases", response_model=list[PurchaseRead])
async def list_manufacturer_purchases(
    manufacturer_id: uuid.UUID,
    skip: int = 0,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await manufacturer_service.get_manufacturer(db, current_user.id, manufacturer_id)
    return await purchase_service.list_purchases(db, current_user.id, manufacturer_id=manufacturer_id, skip=skip, limit=limit)


@router.get("/{manufacturer_id}/payments", response_model=list[ManufacturerPaymentRead])
async def list_manufacturer_payments(
    manufacturer_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await manufacturer_service.get_manufacturer(db, current_user.id, manufacturer_id)
    return await payment_service.list_manufacturer_payments_by_manufacturer(db, current_user.id, manufacturer_id)

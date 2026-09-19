import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.payment import CustomerPaymentCreate, CustomerPaymentRead, CustomerPaymentUpdate
from app.schemas.sale import SaleCreate, SaleRead, SaleUpdate
from app.services import payment_service, sale_service

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("", response_model=SaleRead, status_code=201)
async def create_sale(
    data: SaleCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await sale_service.create_sale(db, current_user.id, data)


@router.get("", response_model=list[SaleRead])
async def list_sales(
    customer_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await sale_service.list_sales(db, current_user.id, customer_id=customer_id, skip=skip, limit=limit)


@router.get("/{sale_id}", response_model=SaleRead)
async def get_sale(sale_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await sale_service.get_sale(db, current_user.id, sale_id)


@router.patch("/{sale_id}", response_model=SaleRead)
async def update_sale(
    sale_id: uuid.UUID,
    data: SaleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await sale_service.update_sale(db, current_user.id, sale_id, data)


@router.delete("/{sale_id}", status_code=204)
async def delete_sale(sale_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await sale_service.delete_sale(db, current_user.id, sale_id)


@router.post("/{sale_id}/payments", response_model=CustomerPaymentRead, status_code=201)
async def record_sale_payment(
    sale_id: uuid.UUID,
    data: CustomerPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await payment_service.record_customer_payment(db, current_user.id, sale_id, data)


@router.get("/{sale_id}/payments", response_model=list[CustomerPaymentRead])
async def list_sale_payments(
    sale_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await payment_service.list_customer_payments_by_sale(db, current_user.id, sale_id)


@router.patch("/{sale_id}/payments/{payment_id}", response_model=CustomerPaymentRead)
async def update_sale_payment(
    sale_id: uuid.UUID,
    payment_id: uuid.UUID,
    data: CustomerPaymentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await payment_service.update_customer_payment(db, current_user.id, sale_id, payment_id, data)


@router.delete("/{sale_id}/payments/{payment_id}", status_code=204)
async def delete_sale_payment(
    sale_id: uuid.UUID,
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await payment_service.delete_customer_payment(db, current_user.id, sale_id, payment_id)

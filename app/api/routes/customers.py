import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.schemas.payment import CustomerPaymentRead
from app.schemas.sale import SaleCreate, SaleRead
from app.services import customer_service, payment_service, sale_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=201)
async def create_customer(
    data: CustomerCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await customer_service.create_customer(db, current_user.id, data)


@router.get("", response_model=list[CustomerRead])
async def list_customers(
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await customer_service.list_customers(db, current_user.id, is_active=is_active, skip=skip, limit=limit)


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await customer_service.get_customer(db, current_user.id, customer_id)


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await customer_service.update_customer(db, current_user.id, customer_id, data)


@router.delete("/{customer_id}", response_model=CustomerRead)
async def deactivate_customer(
    customer_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Soft-deletes (deactivates) the customer. Customers with financial history are never hard-deleted."""
    return await customer_service.deactivate_customer(db, current_user.id, customer_id)


@router.post("/{customer_id}/sales", response_model=SaleRead, status_code=201)
async def create_sale_for_customer(
    customer_id: uuid.UUID,
    data: SaleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await customer_service.get_customer(db, current_user.id, customer_id)  # 404s if not owned by this user
    data = data.model_copy(update={"customer_id": customer_id})
    return await sale_service.create_sale(db, current_user.id, data)


@router.get("/{customer_id}/sales", response_model=list[SaleRead])
async def list_customer_sales(
    customer_id: uuid.UUID,
    skip: int = 0,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await customer_service.get_customer(db, current_user.id, customer_id)
    return await sale_service.list_sales(db, current_user.id, customer_id=customer_id, skip=skip, limit=limit)


@router.get("/{customer_id}/payments", response_model=list[CustomerPaymentRead])
async def list_customer_payments(
    customer_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await customer_service.get_customer(db, current_user.id, customer_id)
    return await payment_service.list_customer_payments_by_customer(db, current_user.id, customer_id)

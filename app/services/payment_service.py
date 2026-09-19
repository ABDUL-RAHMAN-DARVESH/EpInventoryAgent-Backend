import uuid
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.payment import CustomerPayment, ManufacturerPayment
from app.repositories import payment as payment_repo
from app.repositories import purchase as purchase_repo
from app.repositories import sale as sale_repo
from app.schemas.payment import (
    CustomerPaymentCreate,
    CustomerPaymentUpdate,
    ManufacturerPaymentCreate,
    ManufacturerPaymentUpdate,
    PaymentFeedItem,
)
from app.utils.status import compute_payment_status


def _today() -> date:
    return datetime.now(timezone.utc).date()


async def record_customer_payment(
    db: AsyncSession, owner_id: uuid.UUID, sale_id: uuid.UUID, data: CustomerPaymentCreate
) -> CustomerPayment:
    # Row lock on the sale keeps the balance check + update atomic under concurrent payments.
    sale = await sale_repo.get_for_update(db, owner_id, sale_id)
    if sale is None:
        raise NotFoundError(f"Sale {sale_id} not found")

    if data.amount > sale.balance_due:
        raise ValidationAppError(
            f"Payment amount {data.amount} exceeds outstanding balance {sale.balance_due}"
        )

    payment = CustomerPayment(
        owner_id=owner_id,
        customer_id=sale.customer_id,
        sale_id=sale.id,
        amount=data.amount,
        payment_date=data.payment_date or _today(),
        method=data.method,
        reference_number=data.reference_number,
        notes=data.notes,
    )
    await payment_repo.create_customer_payment(db, payment)

    sale.amount_paid = sale.amount_paid + data.amount
    sale.balance_due = sale.total_amount - sale.amount_paid
    sale.payment_status = compute_payment_status(sale.total_amount, sale.amount_paid, sale.due_date, _today())

    await db.commit()
    await db.refresh(payment)
    return payment


async def update_customer_payment(
    db: AsyncSession, owner_id: uuid.UUID, sale_id: uuid.UUID, payment_id: uuid.UUID, data: CustomerPaymentUpdate
) -> CustomerPayment:
    # Row lock on the sale keeps the balance recalculation atomic under concurrent payments.
    sale = await sale_repo.get_for_update(db, owner_id, sale_id)
    if sale is None:
        raise NotFoundError(f"Sale {sale_id} not found")

    payment = await payment_repo.get_customer_payment(db, owner_id, payment_id)
    if payment is None or payment.sale_id != sale_id:
        raise NotFoundError(f"Payment {payment_id} not found for sale {sale_id}")

    updates = data.model_dump(exclude_unset=True)
    new_amount = updates.get("amount", payment.amount)
    if new_amount != payment.amount:
        recalculated_paid = sale.amount_paid - payment.amount + new_amount
        if recalculated_paid > sale.total_amount:
            raise ValidationAppError(
                f"Updated amount would bring total paid to {recalculated_paid}, "
                f"exceeding the sale total of {sale.total_amount}"
            )
        if recalculated_paid < 0:
            raise ValidationAppError("Updated amount cannot bring total paid below zero")
        sale.amount_paid = recalculated_paid
        sale.balance_due = sale.total_amount - sale.amount_paid
        sale.payment_status = compute_payment_status(sale.total_amount, sale.amount_paid, sale.due_date, _today())

    for field, value in updates.items():
        setattr(payment, field, value)

    await db.commit()
    await db.refresh(payment)
    return payment


async def delete_customer_payment(db: AsyncSession, owner_id: uuid.UUID, sale_id: uuid.UUID, payment_id: uuid.UUID) -> None:
    sale = await sale_repo.get_for_update(db, owner_id, sale_id)
    if sale is None:
        raise NotFoundError(f"Sale {sale_id} not found")

    payment = await payment_repo.get_customer_payment(db, owner_id, payment_id)
    if payment is None or payment.sale_id != sale_id:
        raise NotFoundError(f"Payment {payment_id} not found for sale {sale_id}")

    sale.amount_paid = sale.amount_paid - payment.amount
    sale.balance_due = sale.total_amount - sale.amount_paid
    sale.payment_status = compute_payment_status(sale.total_amount, sale.amount_paid, sale.due_date, _today())

    await payment_repo.delete_customer_payment(db, payment)
    await db.commit()


async def list_customer_payments_by_sale(db: AsyncSession, owner_id: uuid.UUID, sale_id: uuid.UUID) -> list[CustomerPayment]:
    sale = await sale_repo.get(db, owner_id, sale_id)
    if sale is None:
        raise NotFoundError(f"Sale {sale_id} not found")
    return await payment_repo.list_customer_payments_by_sale(db, owner_id, sale_id)


async def list_customer_payments_by_customer(
    db: AsyncSession, owner_id: uuid.UUID, customer_id: uuid.UUID
) -> list[CustomerPayment]:
    return await payment_repo.list_customer_payments_by_customer(db, owner_id, customer_id)


async def record_manufacturer_payment(
    db: AsyncSession, owner_id: uuid.UUID, purchase_id: uuid.UUID, data: ManufacturerPaymentCreate
) -> ManufacturerPayment:
    purchase = await purchase_repo.get_for_update(db, owner_id, purchase_id)
    if purchase is None:
        raise NotFoundError(f"Purchase {purchase_id} not found")

    if data.amount > purchase.balance_due:
        raise ValidationAppError(
            f"Payment amount {data.amount} exceeds outstanding balance {purchase.balance_due}"
        )

    payment = ManufacturerPayment(
        owner_id=owner_id,
        manufacturer_id=purchase.manufacturer_id,
        purchase_id=purchase.id,
        amount=data.amount,
        payment_date=data.payment_date or _today(),
        method=data.method,
        reference_number=data.reference_number,
        notes=data.notes,
    )
    await payment_repo.create_manufacturer_payment(db, payment)

    purchase.amount_paid = purchase.amount_paid + data.amount
    purchase.balance_due = purchase.total_amount - purchase.amount_paid
    purchase.payment_status = compute_payment_status(
        purchase.total_amount, purchase.amount_paid, purchase.due_date, _today()
    )

    await db.commit()
    await db.refresh(payment)
    return payment


async def update_manufacturer_payment(
    db: AsyncSession, owner_id: uuid.UUID, purchase_id: uuid.UUID, payment_id: uuid.UUID, data: ManufacturerPaymentUpdate
) -> ManufacturerPayment:
    purchase = await purchase_repo.get_for_update(db, owner_id, purchase_id)
    if purchase is None:
        raise NotFoundError(f"Purchase {purchase_id} not found")

    payment = await payment_repo.get_manufacturer_payment(db, owner_id, payment_id)
    if payment is None or payment.purchase_id != purchase_id:
        raise NotFoundError(f"Payment {payment_id} not found for purchase {purchase_id}")

    updates = data.model_dump(exclude_unset=True)
    new_amount = updates.get("amount", payment.amount)
    if new_amount != payment.amount:
        recalculated_paid = purchase.amount_paid - payment.amount + new_amount
        if recalculated_paid > purchase.total_amount:
            raise ValidationAppError(
                f"Updated amount would bring total paid to {recalculated_paid}, "
                f"exceeding the purchase total of {purchase.total_amount}"
            )
        if recalculated_paid < 0:
            raise ValidationAppError("Updated amount cannot bring total paid below zero")
        purchase.amount_paid = recalculated_paid
        purchase.balance_due = purchase.total_amount - purchase.amount_paid
        purchase.payment_status = compute_payment_status(
            purchase.total_amount, purchase.amount_paid, purchase.due_date, _today()
        )

    for field, value in updates.items():
        setattr(payment, field, value)

    await db.commit()
    await db.refresh(payment)
    return payment


async def delete_manufacturer_payment(
    db: AsyncSession, owner_id: uuid.UUID, purchase_id: uuid.UUID, payment_id: uuid.UUID
) -> None:
    purchase = await purchase_repo.get_for_update(db, owner_id, purchase_id)
    if purchase is None:
        raise NotFoundError(f"Purchase {purchase_id} not found")

    payment = await payment_repo.get_manufacturer_payment(db, owner_id, payment_id)
    if payment is None or payment.purchase_id != purchase_id:
        raise NotFoundError(f"Payment {payment_id} not found for purchase {purchase_id}")

    purchase.amount_paid = purchase.amount_paid - payment.amount
    purchase.balance_due = purchase.total_amount - purchase.amount_paid
    purchase.payment_status = compute_payment_status(
        purchase.total_amount, purchase.amount_paid, purchase.due_date, _today()
    )

    await payment_repo.delete_manufacturer_payment(db, payment)
    await db.commit()


async def list_manufacturer_payments_by_purchase(
    db: AsyncSession, owner_id: uuid.UUID, purchase_id: uuid.UUID
) -> list[ManufacturerPayment]:
    purchase = await purchase_repo.get(db, owner_id, purchase_id)
    if purchase is None:
        raise NotFoundError(f"Purchase {purchase_id} not found")
    return await payment_repo.list_manufacturer_payments_by_purchase(db, owner_id, purchase_id)


async def list_manufacturer_payments_by_manufacturer(
    db: AsyncSession, owner_id: uuid.UUID, manufacturer_id: uuid.UUID
) -> list[ManufacturerPayment]:
    return await payment_repo.list_manufacturer_payments_by_manufacturer(db, owner_id, manufacturer_id)


async def list_recent_payments(db: AsyncSession, owner_id: uuid.UUID, *, skip: int = 0, limit: int = 50) -> list[PaymentFeedItem]:
    """Unified customer+manufacturer payment feed, newest first.

    Pulls (skip + limit) rows from each side (sufficient to guarantee correctness of any
    page within that bound), merges, re-sorts, then slices -- avoids a cross-table SQL UNION
    over two differently-shaped tables for what is expected to stay a small dataset.
    """
    fetch_n = skip + limit
    customer_rows = await payment_repo.list_recent_customer_payments(db, owner_id, fetch_n)
    manufacturer_rows = await payment_repo.list_recent_manufacturer_payments(db, owner_id, fetch_n)

    items = [
        PaymentFeedItem(
            id=payment.id,
            type="CUSTOMER",
            party_id=payment.customer_id,
            party_name=name,
            reference_id=payment.sale_id,
            amount=payment.amount,
            payment_date=payment.payment_date,
            method=payment.method,
            reference_number=payment.reference_number,
            notes=payment.notes,
            created_at=payment.created_at,
        )
        for payment, name in customer_rows
    ] + [
        PaymentFeedItem(
            id=payment.id,
            type="MANUFACTURER",
            party_id=payment.manufacturer_id,
            party_name=name,
            reference_id=payment.purchase_id,
            amount=payment.amount,
            payment_date=payment.payment_date,
            method=payment.method,
            reference_number=payment.reference_number,
            notes=payment.notes,
            created_at=payment.created_at,
        )
        for payment, name in manufacturer_rows
    ]

    items.sort(key=lambda item: (item.payment_date, item.created_at), reverse=True)
    return items[skip : skip + limit]

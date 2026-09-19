import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.payment import ManufacturerPayment
from app.models.purchase import Purchase, PurchaseItem
from app.repositories import manufacturer as manufacturer_repo
from app.repositories import payment as payment_repo
from app.repositories import product as product_repo
from app.repositories import purchase as purchase_repo
from app.schemas.purchase import PurchaseCreate, PurchaseUpdate
from app.utils.status import compute_payment_status


def _today() -> date:
    return datetime.now(timezone.utc).date()


async def create_purchase(db: AsyncSession, owner_id: uuid.UUID, data: PurchaseCreate) -> Purchase:
    manufacturer = await manufacturer_repo.get(db, owner_id, data.manufacturer_id)
    if manufacturer is None:
        raise NotFoundError(f"Manufacturer {data.manufacturer_id} not found")

    purchase_date = data.purchase_date or _today()

    items: list[PurchaseItem] = []
    total_amount = Decimal("0")
    for item_data in data.items:
        product = await product_repo.get(db, owner_id, item_data.product_id)
        if product is None:
            raise NotFoundError(f"Product {item_data.product_id} not found")

        if item_data.line_total is not None:
            line_total = item_data.line_total
        elif item_data.unit_price is not None:
            line_total = (item_data.unit_price * item_data.quantity).quantize(Decimal("0.01"))
        else:
            raise ValidationAppError("Each purchase item requires either unit_price or line_total")

        total_amount += line_total
        items.append(
            PurchaseItem(
                product_id=product.id,
                product_name=product.name,
                unit_price=item_data.unit_price,
                quantity=item_data.quantity,
                line_total=line_total,
            )
        )

    if data.initial_payment and data.initial_payment.amount > total_amount:
        raise ValidationAppError("Initial payment cannot exceed the purchase total")

    purchase = Purchase(
        owner_id=owner_id,
        manufacturer_id=manufacturer.id,
        purchase_date=purchase_date,
        due_date=data.due_date,
        total_amount=total_amount,
        amount_paid=Decimal("0"),
        balance_due=total_amount,
        payment_status=compute_payment_status(total_amount, Decimal("0"), data.due_date, _today()),
        notes=data.notes,
        items=items,
    )
    purchase = await purchase_repo.create(db, purchase)

    if data.initial_payment:
        payment = ManufacturerPayment(
            owner_id=owner_id,
            manufacturer_id=manufacturer.id,
            purchase_id=purchase.id,
            amount=data.initial_payment.amount,
            payment_date=data.initial_payment.payment_date or purchase_date,
            method=data.initial_payment.method,
            reference_number=data.initial_payment.reference_number,
            notes=data.initial_payment.notes,
        )
        db.add(payment)
        purchase.amount_paid = data.initial_payment.amount
        purchase.balance_due = total_amount - purchase.amount_paid
        purchase.payment_status = compute_payment_status(total_amount, purchase.amount_paid, data.due_date, _today())

    await db.commit()
    purchase = await purchase_repo.get(db, owner_id, purchase.id)
    return purchase


async def update_purchase(db: AsyncSession, owner_id: uuid.UUID, purchase_id: uuid.UUID, data: PurchaseUpdate) -> Purchase:
    # Row lock: an items replacement changes total_amount, which must stay
    # consistent with amount_paid under concurrent payment recording/editing.
    purchase = await purchase_repo.get_for_update(db, owner_id, purchase_id)
    if purchase is None:
        raise NotFoundError(f"Purchase {purchase_id} not found")

    updates = data.model_dump(exclude_unset=True, exclude={"items"})
    for field, value in updates.items():
        setattr(purchase, field, value)

    if data.items is not None:
        new_items: list[PurchaseItem] = []
        total_amount = Decimal("0")
        for item_data in data.items:
            product = await product_repo.get(db, owner_id, item_data.product_id)
            if product is None:
                raise NotFoundError(f"Product {item_data.product_id} not found")

            if item_data.line_total is not None:
                line_total = item_data.line_total
            elif item_data.unit_price is not None:
                line_total = (item_data.unit_price * item_data.quantity).quantize(Decimal("0.01"))
            else:
                raise ValidationAppError("Each purchase item requires either unit_price or line_total")

            total_amount += line_total
            new_items.append(
                PurchaseItem(
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=item_data.unit_price,
                    quantity=item_data.quantity,
                    line_total=line_total,
                )
            )
        if purchase.amount_paid > total_amount:
            raise ValidationAppError(
                f"Cannot reduce the purchase total to {total_amount}: {purchase.amount_paid} has already been paid. "
                "Edit or delete the existing payments first."
            )
        purchase.items = new_items  # cascade="all, delete-orphan" removes the old rows
        purchase.total_amount = total_amount
        purchase.balance_due = total_amount - purchase.amount_paid

    if "due_date" in updates or data.items is not None:
        purchase.payment_status = compute_payment_status(
            purchase.total_amount, purchase.amount_paid, purchase.due_date, _today()
        )

    await db.commit()
    return await get_purchase(db, owner_id, purchase.id)


async def delete_purchase(db: AsyncSession, owner_id: uuid.UUID, purchase_id: uuid.UUID) -> None:
    purchase = await purchase_repo.get_for_update(db, owner_id, purchase_id)
    if purchase is None:
        raise NotFoundError(f"Purchase {purchase_id} not found")

    # manufacturer_payments.purchase_id is ON DELETE RESTRICT, so its payment
    # history must be cleared before the purchase itself can be deleted.
    payments = await payment_repo.list_manufacturer_payments_by_purchase(db, owner_id, purchase_id)
    for payment in payments:
        await payment_repo.delete_manufacturer_payment(db, payment)

    await purchase_repo.delete(db, purchase)
    await db.commit()


async def get_purchase(db: AsyncSession, owner_id: uuid.UUID, purchase_id: uuid.UUID) -> Purchase:
    purchase = await purchase_repo.get(db, owner_id, purchase_id)
    if purchase is None:
        raise NotFoundError(f"Purchase {purchase_id} not found")
    return refresh_overdue_status(purchase)


async def list_purchases(
    db: AsyncSession, owner_id: uuid.UUID, *, manufacturer_id: uuid.UUID | None = None, skip: int = 0, limit: int = 100
) -> list[Purchase]:
    purchases = await purchase_repo.list_all(db, owner_id=owner_id, manufacturer_id=manufacturer_id, skip=skip, limit=limit)
    return [refresh_overdue_status(purchase) for purchase in purchases]


def refresh_overdue_status(purchase: Purchase) -> Purchase:
    purchase.payment_status = compute_payment_status(
        purchase.total_amount, purchase.amount_paid, purchase.due_date, _today()
    )
    return purchase

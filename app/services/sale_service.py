import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.payment import CustomerPayment
from app.models.sale import Sale, SaleItem
from app.repositories import customer as customer_repo
from app.repositories import payment as payment_repo
from app.repositories import product as product_repo
from app.repositories import sale as sale_repo
from app.schemas.sale import SaleCreate, SaleUpdate
from app.utils.status import compute_payment_status


def _today() -> date:
    return datetime.now(timezone.utc).date()


async def create_sale(db: AsyncSession, owner_id: uuid.UUID, data: SaleCreate) -> Sale:
    customer = await customer_repo.get(db, owner_id, data.customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {data.customer_id} not found")

    sale_date = data.sale_date or _today()

    items: list[SaleItem] = []
    total_amount = Decimal("0")
    for item_data in data.items:
        product = await product_repo.get(db, owner_id, item_data.product_id)
        if product is None:
            raise NotFoundError(f"Product {item_data.product_id} not found")
        line_total = (item_data.unit_price * item_data.quantity).quantize(Decimal("0.01"))
        total_amount += line_total
        items.append(
            SaleItem(
                product_id=product.id,
                product_name=product.name,
                unit_price=item_data.unit_price,
                quantity=item_data.quantity,
                line_total=line_total,
            )
        )

    if data.initial_payment and data.initial_payment.amount > total_amount:
        raise ValidationAppError("Initial payment cannot exceed the sale total")

    sale = Sale(
        owner_id=owner_id,
        customer_id=customer.id,
        sale_date=sale_date,
        due_date=data.due_date,
        total_amount=total_amount,
        amount_paid=Decimal("0"),
        balance_due=total_amount,
        payment_status=compute_payment_status(total_amount, Decimal("0"), data.due_date, _today()),
        notes=data.notes,
        items=items,
    )
    sale = await sale_repo.create(db, sale)

    if data.initial_payment:
        payment = CustomerPayment(
            owner_id=owner_id,
            customer_id=customer.id,
            sale_id=sale.id,
            amount=data.initial_payment.amount,
            payment_date=data.initial_payment.payment_date or sale_date,
            method=data.initial_payment.method,
            reference_number=data.initial_payment.reference_number,
            notes=data.initial_payment.notes,
        )
        db.add(payment)
        sale.amount_paid = data.initial_payment.amount
        sale.balance_due = total_amount - sale.amount_paid
        sale.payment_status = compute_payment_status(total_amount, sale.amount_paid, data.due_date, _today())

    await db.commit()
    sale = await sale_repo.get(db, owner_id, sale.id)
    return sale


async def update_sale(db: AsyncSession, owner_id: uuid.UUID, sale_id: uuid.UUID, data: SaleUpdate) -> Sale:
    # Row lock: an items replacement changes total_amount, which must stay
    # consistent with amount_paid under concurrent payment recording/editing.
    sale = await sale_repo.get_for_update(db, owner_id, sale_id)
    if sale is None:
        raise NotFoundError(f"Sale {sale_id} not found")

    updates = data.model_dump(exclude_unset=True, exclude={"items"})
    for field, value in updates.items():
        setattr(sale, field, value)

    if data.items is not None:
        new_items: list[SaleItem] = []
        total_amount = Decimal("0")
        for item_data in data.items:
            product = await product_repo.get(db, owner_id, item_data.product_id)
            if product is None:
                raise NotFoundError(f"Product {item_data.product_id} not found")
            line_total = (item_data.unit_price * item_data.quantity).quantize(Decimal("0.01"))
            total_amount += line_total
            new_items.append(
                SaleItem(
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=item_data.unit_price,
                    quantity=item_data.quantity,
                    line_total=line_total,
                )
            )
        if sale.amount_paid > total_amount:
            raise ValidationAppError(
                f"Cannot reduce the sale total to {total_amount}: {sale.amount_paid} has already been paid. "
                "Edit or delete the existing payments first."
            )
        sale.items = new_items  # cascade="all, delete-orphan" removes the old rows
        sale.total_amount = total_amount
        sale.balance_due = total_amount - sale.amount_paid

    if "due_date" in updates or data.items is not None:
        # OVERDUE (due_date) and PAID/PARTIALLY_PAID (total_amount) both depend on fields that may have just changed.
        sale.payment_status = compute_payment_status(sale.total_amount, sale.amount_paid, sale.due_date, _today())

    await db.commit()
    return await get_sale(db, owner_id, sale.id)


async def delete_sale(db: AsyncSession, owner_id: uuid.UUID, sale_id: uuid.UUID) -> None:
    sale = await sale_repo.get_for_update(db, owner_id, sale_id)
    if sale is None:
        raise NotFoundError(f"Sale {sale_id} not found")

    # customer_payments.sale_id is ON DELETE RESTRICT, so its payment history
    # must be cleared before the sale itself can be deleted.
    payments = await payment_repo.list_customer_payments_by_sale(db, owner_id, sale_id)
    for payment in payments:
        await payment_repo.delete_customer_payment(db, payment)

    await sale_repo.delete(db, sale)
    await db.commit()


async def get_sale(db: AsyncSession, owner_id: uuid.UUID, sale_id: uuid.UUID) -> Sale:
    sale = await sale_repo.get(db, owner_id, sale_id)
    if sale is None:
        raise NotFoundError(f"Sale {sale_id} not found")
    return refresh_overdue_status(sale)


async def list_sales(
    db: AsyncSession, owner_id: uuid.UUID, *, customer_id: uuid.UUID | None = None, skip: int = 0, limit: int = 100
) -> list[Sale]:
    sales = await sale_repo.list_all(db, owner_id=owner_id, customer_id=customer_id, skip=skip, limit=limit)
    return [refresh_overdue_status(sale) for sale in sales]


def refresh_overdue_status(sale: Sale) -> Sale:
    """Recomputes the read-time OVERDUE view without persisting, since it depends on today's date."""
    sale.payment_status = compute_payment_status(sale.total_amount, sale.amount_paid, sale.due_date, _today())
    return sale

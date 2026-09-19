import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.manufacturer import Manufacturer
from app.models.payment import CustomerPayment, ManufacturerPayment
from app.models.purchase import Purchase
from app.models.sale import Sale
from app.schemas.dashboard import (
    DashboardSummary,
    LatestCustomerPaymentActivity,
    LatestCustomerPaymentRow,
    LatestSaleRow,
    LatestSalesActivity,
    PreviousWeekExport,
    WeeklyExportPurchaseRow,
    WeeklyExportSaleRow,
    WeeklyExportSummary,
)
from app.schemas.payment import CustomerPaymentRead
from app.schemas.purchase import PurchaseRead
from app.schemas.sale import SaleRead

# The export offered for a just-completed week stays available for this many
# days after the week ends (Saturday + Sunday), then it's gone.
EXPORT_GRACE_DAYS = 2


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _area_filter(column, area: str | None):
    return column.is_(None) if area is None else column == area


def _week_bounds(reference_date: date) -> tuple[date, date]:
    """The Saturday-to-Friday business week containing `reference_date`.
    Python's date.weekday() has Saturday=5, so this walks back to the most
    recent Saturday (0 days back if `reference_date` is itself a Saturday)."""
    days_since_saturday = (reference_date.weekday() - 5) % 7
    week_start = reference_date - timedelta(days=days_since_saturday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


async def _weekly_financials(
    db: AsyncSession, owner_id: uuid.UUID, week_start: date, week_end: date, *, pending_all_time: bool = False
) -> dict:
    """Net position/receivables/payables for one Saturday-to-Friday week --
    scoped to *actual money that changed hands* (payments dated within the
    window), not the amount customers/manufacturers were expected to pay.
    `pending_receivables`/`pending_payables` carry the old "expected but not
    yet paid" view (still scoped to sales/purchases dated this week) as a
    secondary figure. This is what makes each new week start fresh.

    With `pending_all_time`, the pending totals and the "N customers/
    manufacturers still owing" counts ignore the week entirely and cover every
    sale/purchase up to today -- that's what the live Dashboard shows, since
    who still owes (or is still owed) doesn't reset on Saturday. Only the
    completed-week export keeps the weekly scoping, as a snapshot of that week."""
    total_receivables = await db.scalar(
        select(func.coalesce(func.sum(CustomerPayment.amount), 0)).where(
            CustomerPayment.owner_id == owner_id,
            CustomerPayment.payment_date >= week_start,
            CustomerPayment.payment_date <= week_end,
        )
    ) or Decimal("0")
    total_payables = await db.scalar(
        select(func.coalesce(func.sum(ManufacturerPayment.amount), 0)).where(
            ManufacturerPayment.owner_id == owner_id,
            ManufacturerPayment.payment_date >= week_start,
            ManufacturerPayment.payment_date <= week_end,
        )
    ) or Decimal("0")

    sale_scope = [Sale.owner_id == owner_id]
    purchase_scope = [Purchase.owner_id == owner_id]
    if not pending_all_time:
        sale_scope += [Sale.sale_date >= week_start, Sale.sale_date <= week_end]
        purchase_scope += [Purchase.purchase_date >= week_start, Purchase.purchase_date <= week_end]

    pending_receivables = await db.scalar(select(func.coalesce(func.sum(Sale.balance_due), 0)).where(*sale_scope)) or Decimal("0")
    customers_with_outstanding_balance = await db.scalar(
        select(func.count(func.distinct(Sale.customer_id))).where(*sale_scope, Sale.balance_due > 0)
    ) or 0

    pending_payables = await db.scalar(
        select(func.coalesce(func.sum(Purchase.balance_due), 0)).where(*purchase_scope)
    ) or Decimal("0")
    manufacturers_with_outstanding_balance = await db.scalar(
        select(func.count(func.distinct(Purchase.manufacturer_id))).where(*purchase_scope, Purchase.balance_due > 0)
    ) or 0

    return {
        "total_receivables": total_receivables,
        "total_payables": total_payables,
        "net_position": total_receivables - total_payables,
        "pending_receivables": pending_receivables,
        "pending_payables": pending_payables,
        "customers_with_outstanding_balance": customers_with_outstanding_balance,
        "manufacturers_with_outstanding_balance": manufacturers_with_outstanding_balance,
    }


async def _latest_sales_activity(db: AsyncSession, owner_id: uuid.UUID) -> LatestSalesActivity | None:
    """The most recent sales "visit": every sale sharing the same area and
    sale_date as the most recently recorded sale (matches the real workflow --
    a week-wise visit to one area, selling to many customers in one go)."""
    latest_stmt = (
        select(Sale.sale_date, Customer.area)
        .join(Customer, Customer.id == Sale.customer_id)
        .where(Sale.owner_id == owner_id)
        .order_by(Sale.created_at.desc())
        .limit(1)
    )
    latest_row = (await db.execute(latest_stmt)).first()
    if latest_row is None:
        return None
    batch_date, area = latest_row

    stmt = (
        select(Sale, Customer.name)
        .join(Customer, Customer.id == Sale.customer_id)
        .where(Sale.owner_id == owner_id, Sale.sale_date == batch_date, _area_filter(Customer.area, area))
        .options(selectinload(Sale.items))
        .order_by(Sale.created_at.asc())
    )
    rows = (await db.execute(stmt)).all()

    # A Sale only ever carries its own advance/paid/pending -- Customer
    # Payment collection history is a separate activity on a separate visit,
    # so this activity (and its export) deliberately excludes it.
    sales = [row[0] for row in rows]
    sale_rows = []
    for sale, customer_name in rows:
        data = SaleRead.model_validate(sale).model_dump()
        data["customer_name"] = customer_name
        sale_rows.append(LatestSaleRow(**data))

    fully_paid = [s for s in sales if s.balance_due <= 0]
    created_ats = [s.created_at for s in sales]

    return LatestSalesActivity(
        area=area,
        batch_date=batch_date,
        sales_count=len(sales),
        customers_count=len({s.customer_id for s in sales}),
        total_sales_amount=sum((s.total_amount for s in sales), Decimal("0")),
        total_advance_received=sum((s.amount_paid for s in sales), Decimal("0")),
        total_fully_paid_amount=sum((s.total_amount for s in fully_paid), Decimal("0")),
        fully_paid_count=len(fully_paid),
        fully_paid_customers_count=len({s.customer_id for s in fully_paid}),
        total_pending_amount=sum((s.balance_due for s in sales), Decimal("0")),
        pending_count=len(sales) - len(fully_paid),
        last_recorded_at=max(created_ats) if created_ats else None,
        sales=sale_rows,
    )


async def _latest_customer_payment_activity(db: AsyncSession, owner_id: uuid.UUID) -> LatestCustomerPaymentActivity | None:
    """The most recent payment *collection round*: every payment sharing the
    same area and payment_date as the most recently recorded payment (matches
    the real workflow -- a day's collection round through one area).

    Deliberately excludes `is_initial_payment` rows -- an advance/full amount
    paid at the moment of sale is part of that sale (see Latest Sales), not a
    later collection visit, and must never masquerade as one just because it
    happens to be the most recently-created CustomerPayment row."""
    latest_stmt = (
        select(CustomerPayment.payment_date, Customer.area)
        .join(Customer, Customer.id == CustomerPayment.customer_id)
        .where(CustomerPayment.owner_id == owner_id, CustomerPayment.is_initial_payment.is_(False))
        .order_by(CustomerPayment.created_at.desc())
        .limit(1)
    )
    latest_row = (await db.execute(latest_stmt)).first()
    if latest_row is None:
        return None
    batch_date, area = latest_row

    stmt = (
        select(CustomerPayment, Customer.name)
        .join(Customer, Customer.id == CustomerPayment.customer_id)
        .where(
            CustomerPayment.owner_id == owner_id,
            CustomerPayment.is_initial_payment.is_(False),
            CustomerPayment.payment_date == batch_date,
            _area_filter(Customer.area, area),
        )
        .order_by(CustomerPayment.created_at.asc())
    )
    rows = (await db.execute(stmt)).all()

    payments = [row[0] for row in rows]
    payment_rows = []
    for payment, customer_name in rows:
        data = CustomerPaymentRead.model_validate(payment).model_dump()
        data["customer_name"] = customer_name
        payment_rows.append(LatestCustomerPaymentRow(**data))

    created_ats = [p.created_at for p in payments]

    total_customers_in_area = await db.scalar(
        select(func.count(Customer.id)).where(Customer.owner_id == owner_id, _area_filter(Customer.area, area))
    ) or 0
    customers_pending_in_area = await db.scalar(
        select(func.count(func.distinct(Sale.customer_id)))
        .join(Customer, Customer.id == Sale.customer_id)
        .where(Sale.owner_id == owner_id, _area_filter(Customer.area, area), Sale.balance_due > 0)
    ) or 0

    return LatestCustomerPaymentActivity(
        area=area,
        batch_date=batch_date,
        payments_count=len(payments),
        customers_count=len({p.customer_id for p in payments}),
        sales_touched_count=len({p.sale_id for p in payments}),
        total_collected=sum((p.amount for p in payments), Decimal("0")),
        total_customers_in_area=total_customers_in_area,
        customers_pending_in_area=customers_pending_in_area,
        first_recorded_at=min(created_ats) if created_ats else None,
        last_recorded_at=max(created_ats) if created_ats else None,
        payments=payment_rows,
    )


def _previous_week_window(today: date) -> tuple[date, date, int]:
    week_start, _ = _week_bounds(today)
    prev_week_end = week_start - timedelta(days=1)
    prev_week_start = prev_week_end - timedelta(days=6)
    days_since_prev_week_end = (today - prev_week_end).days
    return prev_week_start, prev_week_end, days_since_prev_week_end


async def get_dashboard_summary(db: AsyncSession, owner_id: uuid.UUID) -> DashboardSummary:
    today = _today()
    week_start, week_end = _week_bounds(today)
    financials = await _weekly_financials(db, owner_id, week_start, week_end, pending_all_time=True)

    prev_week_start, prev_week_end, days_since_prev_week_end = _previous_week_window(today)
    export_available = 1 <= days_since_prev_week_end <= EXPORT_GRACE_DAYS

    latest_sales = await _latest_sales_activity(db, owner_id)
    latest_customer_payments = await _latest_customer_payment_activity(db, owner_id)

    return DashboardSummary(
        week_start=week_start,
        week_end=week_end,
        latest_sales=latest_sales,
        latest_customer_payments=latest_customer_payments,
        previous_week_export=PreviousWeekExport(
            week_start=prev_week_start,
            week_end=prev_week_end,
            available=export_available,
            expires_on=prev_week_end + timedelta(days=EXPORT_GRACE_DAYS),
        ),
        **financials,
    )


async def get_previous_week_export(db: AsyncSession, owner_id: uuid.UUID) -> WeeklyExportSummary | None:
    """Full detail (summary totals + every sale/purchase) for the week that
    just ended, or None once it's past its EXPORT_GRACE_DAYS window -- the
    route turns that into a 404 rather than silently serving stale data
    forever."""
    today = _today()
    prev_week_start, prev_week_end, days_since_prev_week_end = _previous_week_window(today)
    if not (1 <= days_since_prev_week_end <= EXPORT_GRACE_DAYS):
        return None

    financials = await _weekly_financials(db, owner_id, prev_week_start, prev_week_end)

    sale_rows = (
        await db.execute(
            select(Sale, Customer.name)
            .join(Customer, Customer.id == Sale.customer_id)
            .where(Sale.owner_id == owner_id, Sale.sale_date >= prev_week_start, Sale.sale_date <= prev_week_end)
            .options(selectinload(Sale.items))
            .order_by(Sale.created_at.asc())
        )
    ).all()
    sales = []
    for sale, customer_name in sale_rows:
        data = SaleRead.model_validate(sale).model_dump()
        data["customer_name"] = customer_name
        sales.append(WeeklyExportSaleRow(**data))

    purchase_rows = (
        await db.execute(
            select(Purchase, Manufacturer.name)
            .join(Manufacturer, Manufacturer.id == Purchase.manufacturer_id)
            .where(
                Purchase.owner_id == owner_id,
                Purchase.purchase_date >= prev_week_start,
                Purchase.purchase_date <= prev_week_end,
            )
            .options(selectinload(Purchase.items))
            .order_by(Purchase.created_at.asc())
        )
    ).all()
    purchases = []
    for purchase, manufacturer_name in purchase_rows:
        data = PurchaseRead.model_validate(purchase).model_dump()
        data["manufacturer_name"] = manufacturer_name
        purchases.append(WeeklyExportPurchaseRow(**data))

    return WeeklyExportSummary(
        week_start=prev_week_start,
        week_end=prev_week_end,
        sales=sales,
        purchases=purchases,
        **financials,
    )

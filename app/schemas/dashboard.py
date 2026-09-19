from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.payment import CustomerPaymentRead
from app.schemas.purchase import PurchaseRead
from app.schemas.sale import SaleRead


class LatestSaleRow(SaleRead):
    customer_name: str


class LatestCustomerPaymentRow(CustomerPaymentRead):
    customer_name: str


class LatestSalesActivity(BaseModel):
    """Aggregates the most recent sales visit -- the batch of sales sharing
    the same area and sale_date as the most recently recorded sale."""

    area: str | None
    batch_date: date
    sales_count: int
    customers_count: int
    total_sales_amount: Decimal
    total_advance_received: Decimal
    total_fully_paid_amount: Decimal
    fully_paid_count: int
    fully_paid_customers_count: int
    total_pending_amount: Decimal
    pending_count: int
    last_recorded_at: datetime | None
    sales: list[LatestSaleRow]


class LatestCustomerPaymentActivity(BaseModel):
    """Aggregates the most recent payment collection round -- the batch of
    payments sharing the same area and payment_date as the most recently
    recorded payment."""

    area: str | None
    batch_date: date
    payments_count: int
    customers_count: int
    sales_touched_count: int
    total_collected: Decimal
    total_customers_in_area: int
    customers_pending_in_area: int
    first_recorded_at: datetime | None
    last_recorded_at: datetime | None
    payments: list[LatestCustomerPaymentRow]


class PreviousWeekExport(BaseModel):
    """Tells the client whether last week's summary can still be pulled --
    the export is only ever offered for the 2 days right after a week ends,
    then it's gone (see EXPORT_GRACE_DAYS in dashboard_service.py)."""

    week_start: date
    week_end: date
    available: bool
    expires_on: date


class DashboardSummary(BaseModel):
    # The business week runs Saturday -> Friday (see dashboard_service._week_bounds).
    # Every money/count figure below is scoped to sales/purchases/payments
    # dated within [week_start, week_end] -- it resets fresh every Saturday,
    # it is not a lifetime running total.
    week_start: date
    week_end: date

    # Actual money that changed hands this week (all CustomerPayment /
    # ManufacturerPayment rows dated within the week, including advance
    # payments taken at sale time) -- NOT the amount customers/manufacturers
    # were merely expected to pay.
    total_receivables: Decimal
    total_payables: Decimal
    net_position: Decimal

    # The "expected but not yet paid" view, still scoped to sales/purchases
    # dated this week -- what total_receivables/total_payables used to mean.
    pending_receivables: Decimal
    pending_payables: Decimal

    customers_with_outstanding_balance: int
    manufacturers_with_outstanding_balance: int

    latest_sales: LatestSalesActivity | None = None
    latest_customer_payments: LatestCustomerPaymentActivity | None = None

    previous_week_export: PreviousWeekExport


class WeeklyExportSaleRow(SaleRead):
    customer_name: str


class WeeklyExportPurchaseRow(PurchaseRead):
    manufacturer_name: str


class WeeklyExportSummary(BaseModel):
    """The full detail behind a completed week's summary -- the totals plus
    every underlying sale/purchase -- returned only while the export is
    still within its 2-day grace window (see dashboard_service.py)."""

    week_start: date
    week_end: date

    total_receivables: Decimal
    total_payables: Decimal
    net_position: Decimal

    pending_receivables: Decimal
    pending_payables: Decimal

    customers_with_outstanding_balance: int
    manufacturers_with_outstanding_balance: int

    sales: list[WeeklyExportSaleRow]
    purchases: list[WeeklyExportPurchaseRow]

from datetime import date
from decimal import Decimal

from app.models.enums import PaymentStatus


def compute_payment_status(
    total_amount: Decimal, amount_paid: Decimal, due_date: date | None, today: date
) -> PaymentStatus:
    if amount_paid >= total_amount:
        return PaymentStatus.PAID
    if due_date is not None and due_date < today:
        return PaymentStatus.OVERDUE
    if amount_paid > 0:
        return PaymentStatus.PARTIALLY_PAID
    return PaymentStatus.PENDING

import enum


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    UPI = "UPI"
    CARD = "CARD"
    CHEQUE = "CHEQUE"
    OTHER = "OTHER"

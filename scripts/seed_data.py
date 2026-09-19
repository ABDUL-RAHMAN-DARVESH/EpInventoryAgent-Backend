"""
Wipes all app data and seeds realistic test data:
50 Home Appliances products (some with brand/size variants), 10 areas,
200 customers (20 per area) with real names, and multiple sales per customer
with varied payment states (paid / partially paid / pending / overdue).

Run from the EP-Backend root: python scripts/seed_data.py
"""
import asyncio
import random
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.customer import Customer
from app.models.enums import PaymentMethod
from app.models.payment import CustomerPayment
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.models.user import User, UserRole
from app.repositories import user as user_repo
from app.utils.status import compute_payment_status

DEMO_USER_EMAIL = "demo@example.com"
DEMO_USER_PASSWORD = "Demo1234!"

random.seed(42)

# ---------------------------------------------------------------------------
# Products: 50 total in "Home Appliances". A few base products repeat with
# different brand/size combos (variants); the rest are single SKUs.
# (sku, name, brand, size)
# ---------------------------------------------------------------------------
VARIANT_PRODUCTS = [
    ("HA-001", "Mixer Grinder 500W", "Philips", Decimal("2499.00")),
    ("HA-002", "Mixer Grinder 750W", "Bajaj", Decimal("3299.00")),
    ("HA-003", "Mixer Grinder 1000W", "Preethi", Decimal("4199.00")),
    ("HA-004", "Ceiling Fan 1200mm", "Havells", Decimal("1899.00")),
    ("HA-005", "Ceiling Fan 1200mm", "Crompton", Decimal("1699.00")),
    ("HA-006", "Ceiling Fan 1400mm", "Orient", Decimal("2199.00")),
    ("HA-007", "Pressure Cooker 3L", "Prestige", Decimal("1299.00")),
    ("HA-008", "Pressure Cooker 5L", "Hawkins", Decimal("1799.00")),
    ("HA-009", "Pressure Cooker 7.5L", "Prestige", Decimal("2499.00")),
    ("HA-010", "Table Fan 400mm", "Bajaj", Decimal("1499.00")),
    ("HA-011", "Table Fan 300mm", "Usha", Decimal("1199.00")),
    ("HA-012", "Pedestal Fan 450mm", "Crompton", Decimal("2299.00")),
    ("HA-013", "Pedestal Fan 450mm", "Havells", Decimal("2499.00")),
]

SINGLE_PRODUCTS = [
    ("HA-014", "Tower Fan", "Bajaj", Decimal("3499.00")),
    ("HA-015", "Steel Plate Set (6 pcs)", "Generic", Decimal("899.00")),
    ("HA-016", "Steel Rack 4-Tier", "Generic", Decimal("2199.00")),
    ("HA-017", "Steel Fruit Strainer", "Generic", Decimal("299.00")),
    ("HA-018", "Steel Glasses Set (6 pcs)", "Generic", Decimal("499.00")),
    ("HA-019", "TV Stand", "Generic", Decimal("3999.00")),
    ("HA-020", "Electric Kettle 1.5L", "Bajaj", Decimal("899.00")),
    ("HA-021", "Induction Cooktop", "Prestige", Decimal("2199.00")),
    ("HA-022", "Toaster 2-Slice", "Philips", Decimal("1399.00")),
    ("HA-023", "Rice Cooker 1.8L", "Panasonic", Decimal("1999.00")),
    ("HA-024", "Iron Box (Dry)", "Bajaj", Decimal("799.00")),
    ("HA-025", "Iron Box (Steam)", "Philips", Decimal("1599.00")),
    ("HA-026", "Water Purifier", "Kent", Decimal("8999.00")),
    ("HA-027", "Air Cooler", "Symphony", Decimal("6999.00")),
    ("HA-028", "Room Heater", "Bajaj", Decimal("1899.00")),
    ("HA-029", "Wall Clock", "Generic", Decimal("399.00")),
    ("HA-030", "Steel Bucket", "Generic", Decimal("349.00")),
    ("HA-031", "Steel Tiffin Box 3-Tier", "Generic", Decimal("599.00")),
    ("HA-032", "Non-stick Tawa", "Prestige", Decimal("549.00")),
    ("HA-033", "Non-stick Kadai", "Prestige", Decimal("699.00")),
    ("HA-034", "Pressure Pan 3L", "Hawkins", Decimal("1199.00")),
    ("HA-035", "Storage Container Set", "Tupperware", Decimal("1299.00")),
    ("HA-036", "Study Table Lamp", "Generic", Decimal("699.00")),
    ("HA-037", "LED Bulb 9W (Pack of 4)", "Philips", Decimal("399.00")),
    ("HA-038", "Extension Cord 4-Socket", "Havells", Decimal("599.00")),
    ("HA-039", "Wall Mount Fan 16\"", "Usha", Decimal("1799.00")),
    ("HA-040", "Exhaust Fan 8\"", "Havells", Decimal("899.00")),
    ("HA-041", "Kitchen Chimney 60cm", "Faber", Decimal("7499.00")),
    ("HA-042", "Gas Stove 2 Burner", "Sunflame", Decimal("2499.00")),
    ("HA-043", "Gas Stove 3 Burner", "Prestige", Decimal("3799.00")),
    ("HA-044", "Steel Almirah Small", "Godrej", Decimal("5499.00")),
    ("HA-045", "Plastic Chair Set (4 pcs)", "Nilkamal", Decimal("2399.00")),
    ("HA-046", "Foldable Table", "Nilkamal", Decimal("1899.00")),
    ("HA-047", "Steel Trolley 3-Tier", "Generic", Decimal("1999.00")),
    ("HA-048", "Hand Blender", "Philips", Decimal("1199.00")),
    ("HA-049", "Juicer Mixer Grinder", "Bajaj", Decimal("3999.00")),
    ("HA-050", "Sandwich Maker", "Prestige", Decimal("1099.00")),
]

ALL_PRODUCTS = VARIANT_PRODUCTS + SINGLE_PRODUCTS
assert len(ALL_PRODUCTS) == 50, len(ALL_PRODUCTS)

AREAS = [
    "Koramangala",
    "Indiranagar",
    "Whitefield",
    "Jayanagar",
    "HSR Layout",
    "Andheri West",
    "Bandra West",
    "Powai",
    "T Nagar",
    "Anna Nagar",
]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Krishna", "Ishaan",
    "Rohan", "Karthik", "Suresh", "Ramesh", "Manoj", "Deepak", "Sanjay", "Rajesh",
    "Vikram", "Anil", "Sunil", "Ajay", "Priya", "Ananya", "Diya", "Saanvi",
    "Aadhya", "Kavya", "Pooja", "Neha", "Sneha", "Divya", "Meera", "Lakshmi",
    "Anjali", "Swathi", "Kiran", "Ravi", "Prakash", "Gopal", "Mahesh", "Naveen",
    "Arun", "Vinod", "Ashok", "Sathish", "Balaji", "Ganesh", "Harish", "Vijay",
    "Nikhil", "Rahul", "Amit", "Rakesh", "Sandeep", "Pankaj", "Vishal", "Gaurav",
    "Nisha", "Radha", "Sunita", "Geeta", "Usha", "Shalini", "Preethi", "Deepa",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Iyer", "Nair", "Menon", "Pillai", "Rao",
    "Reddy", "Naidu", "Chowdary", "Kumar", "Singh", "Yadav", "Mishra", "Pandey",
    "Joshi", "Patil", "Deshmukh", "Kulkarni", "Shetty", "Kamath", "Hegde", "Bhat",
    "Krishnan", "Subramaniam", "Raman", "Murthy", "Chandran", "Pillai", "Varma", "Chauhan",
]


def unique_names(count: int) -> list[str]:
    combos = {f"{f} {l}" for f in FIRST_NAMES for l in LAST_NAMES}
    return random.sample(sorted(combos), count)


def random_phone() -> str:
    return f"+91-9{random.randint(100000000, 999999999)}"


async def wipe_all(session):
    # Only ever wipes business data -- users/features/app_version_configs are
    # left untouched so login and admin config survive a re-seed.
    await session.execute(
        text(
            "TRUNCATE TABLE "
            "customer_payments, sale_items, sales, "
            "manufacturer_payments, purchase_items, purchases, "
            "customers, manufacturers, products "
            "RESTART IDENTITY CASCADE"
        )
    )
    await session.commit()


async def get_or_create_demo_user(session) -> User:
    """All seeded data is scoped to this one demo account rather than the
    bootstrap admin, so the admin's own account stays empty/clean."""
    user = await user_repo.get_by_email(session, DEMO_USER_EMAIL)
    if user is not None:
        return user
    user = User(
        email=DEMO_USER_EMAIL,
        hashed_password=hash_password(DEMO_USER_PASSWORD),
        full_name="Demo User",
        role=UserRole.STAFF,
    )
    session.add(user)
    await session.flush()
    return user


async def seed():
    async with AsyncSessionLocal() as session:
        demo_user = await get_or_create_demo_user(session)
        await session.commit()
        owner_id = demo_user.id

        print("Wiping existing business data...")
        await wipe_all(session)

        print("Creating 50 products...")
        products = [
            Product(owner_id=owner_id, sku=sku, name=name, brand=brand, category="Home Appliances")
            for sku, name, brand, _price in ALL_PRODUCTS
        ]
        session.add_all(products)
        await session.flush()
        price_by_sku = {sku: price for sku, _name, _brand, price in ALL_PRODUCTS}

        print("Creating 10 areas x 20 customers = 200 customers...")
        names = unique_names(200)
        customers = []
        idx = 0
        for area in AREAS:
            for _ in range(20):
                customers.append(Customer(owner_id=owner_id, name=names[idx], area=area, phone=random_phone()))
                idx += 1
        session.add_all(customers)
        await session.flush()

        print("Creating sales with varied payment states...")
        today = date.today()
        for customer in customers:
            num_sales = random.randint(1, 4)
            for _ in range(num_sales):
                num_items = random.randint(1, 4)
                chosen = random.sample(products, num_items)
                sale_date = today - timedelta(days=random.randint(0, 180))

                items = []
                total = Decimal("0")
                for product in chosen:
                    unit_price = price_by_sku[product.sku]
                    quantity = random.randint(1, 3)
                    line_total = (unit_price * quantity).quantize(Decimal("0.01"))
                    total += line_total
                    items.append(
                        SaleItem(
                            product_id=product.id,
                            product_name=product.name,
                            unit_price=unit_price,
                            quantity=quantity,
                            line_total=line_total,
                        )
                    )

                # Payment state mix: ~40% fully paid, ~30% partially paid,
                # ~20% pending (no payment), ~10% overdue (past due date, unpaid/partial)
                roll = random.random()
                due_date = None
                if roll < 0.10:
                    # Overdue: due date in the past, not fully paid
                    due_date = sale_date + timedelta(days=random.randint(7, 20))
                    if due_date >= today:
                        due_date = today - timedelta(days=random.randint(1, 30))
                    paid_fraction = random.choice([Decimal("0"), Decimal("0.4"), Decimal("0.7")])
                elif roll < 0.40:
                    paid_fraction = Decimal("0")
                elif roll < 0.70:
                    paid_fraction = random.choice([Decimal("0.3"), Decimal("0.5"), Decimal("0.75")])
                    if random.random() < 0.5:
                        due_date = sale_date + timedelta(days=random.randint(10, 45))
                else:
                    paid_fraction = Decimal("1.0")

                amount_paid = (total * paid_fraction).quantize(Decimal("0.01"))

                sale = Sale(
                    owner_id=owner_id,
                    customer_id=customer.id,
                    sale_date=sale_date,
                    due_date=due_date,
                    total_amount=total,
                    amount_paid=Decimal("0"),
                    balance_due=total,
                    payment_status=compute_payment_status(total, Decimal("0"), due_date, today),
                    items=items,
                )
                session.add(sale)
                await session.flush()

                if amount_paid > 0:
                    # Split into 1-2 payment installments for realistic history
                    num_payments = 1 if amount_paid < total * Decimal("0.5") else random.choice([1, 2])
                    remaining = amount_paid
                    for i in range(num_payments):
                        chunk = remaining if i == num_payments - 1 else (remaining / 2).quantize(Decimal("0.01"))
                        remaining -= chunk
                        payment_date = sale_date + timedelta(days=random.randint(0, 15) * (i + 1))
                        if payment_date > today:
                            payment_date = today
                        session.add(
                            CustomerPayment(
                                owner_id=owner_id,
                                customer_id=customer.id,
                                sale_id=sale.id,
                                amount=chunk,
                                payment_date=payment_date,
                                method=random.choice(list(PaymentMethod)),
                            )
                        )

                sale.amount_paid = amount_paid
                sale.balance_due = total - amount_paid
                sale.payment_status = compute_payment_status(total, amount_paid, due_date, today)

        await session.commit()
        print(f"Done. Seeded {len(products)} products, {len(customers)} customers.")
        print(f"Log in as {DEMO_USER_EMAIL} / {DEMO_USER_PASSWORD} to see this data.")


async def main():
    await seed()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

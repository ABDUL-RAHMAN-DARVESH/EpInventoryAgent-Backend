# PayBook — Backend

Standalone backend for tracking **customer sales & receivables** and **manufacturer purchases & payables**,
built to validate payment-tracking ideas before they're folded into the Orchestrator.

This is **not** a stock/inventory quantity system — no stock levels, warehouses, or stock movements are tracked.

## Tech stack

- Python 3.12, FastAPI
- SQLAlchemy 2.0 (async, `psycopg` v3 driver) + Alembic migrations
- PostgreSQL
- Pydantic v2

## Project structure

```
app/
  main.py              FastAPI app, CORS, exception handling
  core/                settings (env vars) and app-level exceptions
  db/                  SQLAlchemy Base + async session/engine
  models/               ORM models (one file per entity)
  schemas/             Pydantic request/response models
  repositories/        Plain data-access functions (no business logic)
  services/            Business logic: validation, balance math, status transitions
  api/routes/          FastAPI routers, one per resource
migrations/            Alembic migration scripts
tests/                 pytest end-to-end HTTP flow tests
```

Layering: **routes** parse/validate the HTTP request and call a **service**; services own business
rules (balance checks, status computation, transactions) and call **repositories** for plain DB access.
Models never contain business logic.

## Setup

### 1. Create a virtualenv and install dependencies

```powershell
py -3.12 -m venv venv
venv\Scripts\pip install -r requirements.txt
```

### 2. Configure the database

Create a Postgres role + database (adjust to your local setup):

```sql
CREATE USER inventory_agent WITH PASSWORD 'inventory_agent';
CREATE DATABASE inventory_agent OWNER inventory_agent;
```

Copy `.env.example` to `.env` and fill in real credentials:

```
DATABASE_URL=postgresql+psycopg://inventory_agent:inventory_agent@localhost:5432/inventory_agent
```

The same URL is used both by the app (async) and by Alembic (sync) — `psycopg` v3 supports both.

### 3. Run migrations

```powershell
venv\Scripts\alembic revision --autogenerate -m "init schema"
venv\Scripts\alembic upgrade head
```

### 4. Start the server

```powershell
venv\Scripts\python run.py
```

`run.py` sets the Windows `SelectorEventLoop` policy before uvicorn starts — required because
`psycopg`'s async driver cannot run on Windows' default `ProactorEventLoop`, and that policy has to be
set before uvicorn creates its event loop (setting it inside the app is too late). On macOS/Linux this
is a no-op and `uvicorn app.main:app --reload` works directly too.

### 5. (Optional) Seed realistic test data

```powershell
venv\Scripts\python scripts\seed_data.py
```

**Wipes all existing data** and seeds 50 Home Appliances products (some with brand/size variants),
10 real-sounding areas, 200 customers (20 per area), and 1-4 sales per customer with a realistic mix
of paid/partially-paid/pending/overdue payment states — useful for exercising the mobile app's lists,
filters, dashboard, and exports against real-looking data instead of an empty database.

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## Running tests

Tests exercise the full FastAPI HTTP stack (routing, validation, serialization) against the
database configured in `.env`, so migrations must be applied first.

```powershell
venv\Scripts\pytest -v
```

## Environment variables

| Variable       | Description                                              | Default |
|----------------|-----------------------------------------------------------|---------|
| `APP_NAME`     | Displayed as the API title in Swagger                     | `PayBook` |
| `APP_ENV`      | Free-text environment label                                | `local` |
| `DEBUG`        | Enables SQL echo logging                                   | `true` |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:port/db`               | — |
| `CORS_ORIGINS` | Comma-separated allowed origins, or `*`                     | `*` |

## Data model

```
customers ──< sales ──< sale_items
   │            │  (product_id → products)
   │            └──< customer_payments
   └──< customer_payment_schedules ──> sales

manufacturers ──< purchases ──< purchase_items
   │                 │  (product_id → products)
   │                 └──< manufacturer_payments
   └──< manufacturer_payment_schedules ──> purchases

products (master data only — no stock quantity)
```

- **Transaction** tables (`sales`, `purchases`) represent the original obligation. Their `total_amount`
  is the immutable sum of line items computed at creation time.
- **Payment** tables (`customer_payments`, `manufacturer_payments`) represent actual money movement —
  the only source of truth for `amount_paid`.
- **Schedule** tables (`customer_payment_schedules`, `manufacturer_payment_schedules`) represent an
  *expected* future payment plan. Creating or updating a schedule never touches `amount_paid` — it is
  purely informational until a real payment is recorded against the sale/purchase.
- `amount_paid` / `balance_due` / `payment_status` are denormalized onto the sale/purchase header
  (for fast dashboard aggregation) but are only ever mutated by the payment-recording service inside
  the same DB transaction as the payment insert, under a row lock (`SELECT ... FOR UPDATE`) — so
  concurrent payments against the same sale can't race past the outstanding balance.

### Payment status

Stored as one of `PENDING` / `PARTIALLY_PAID` / `PAID`, computed from amounts alone. `OVERDUE` is
derived at read time (not stored) from `balance_due > 0 AND due_date < today`, so it always reflects
"today" rather than the last time a payment was recorded.

## Business rules enforced

- All money fields are `NUMERIC(14,2)` / `Decimal` end-to-end — never `float`.
- Sale/purchase quantities must be `> 0`; unit prices and payment amounts must be `> 0`.
- A payment can never exceed the current outstanding balance (`422` if it would) — no overpayment/credit
  mechanism is implemented, per spec.
- Referenced customer/manufacturer/product/sale/purchase must exist (`404` otherwise).
- Deleting a customer/manufacturer is always a **soft delete** (`is_active = false`) via `DELETE`, so
  existing financial history is never destroyed; `sales.customer_id` / `purchases.manufacturer_id` /
  `sale_items.product_id` / `purchase_items.product_id` use `ON DELETE RESTRICT` as a hard backstop.
- A `SaleItem`'s `line_total` is always server-computed as `unit_price * quantity` (client-supplied
  totals are ignored) to keep totals trustworthy.
- A `PurchaseItem` accepts either `unit_price` (server computes `line_total`) or a direct `line_total`
  (matching the spec's purchase example, which gives only a lump total, not a per-unit price) — at
  least one is required.
- An optional `initial_payment` block on sale/purchase creation atomically creates the header row and
  its first payment row in one transaction — it is never a separate money field on the header, to keep
  "transaction" and "payment" concepts strictly separate as the spec requires.

## API overview

All routes are under `/api/v1`.

```
POST   /customers
GET    /customers
GET    /customers/{customer_id}
PATCH  /customers/{customer_id}
DELETE /customers/{customer_id}                 soft delete (deactivate)
POST   /customers/{customer_id}/sales           create a sale for this customer
GET    /customers/{customer_id}/sales
GET    /customers/{customer_id}/payments         all payments across this customer's sales

POST   /sales                                   create a sale (customer_id in body)
GET    /sales                                   ?customer_id= filter
GET    /sales/{sale_id}
POST   /sales/{sale_id}/payments                record a payment against this sale
GET    /sales/{sale_id}/payments

POST   /customer-payment-schedules
GET    /customer-payment-schedules              ?customer_id=&is_active= filters
GET    /customer-payment-schedules/{schedule_id}
PATCH  /customer-payment-schedules/{schedule_id}

POST   /manufacturers
GET    /manufacturers
GET    /manufacturers/{manufacturer_id}
PATCH  /manufacturers/{manufacturer_id}
DELETE /manufacturers/{manufacturer_id}         soft delete (deactivate)
POST   /manufacturers/{manufacturer_id}/purchases
GET    /manufacturers/{manufacturer_id}/purchases
GET    /manufacturers/{manufacturer_id}/payments

POST   /purchases
GET    /purchases                               ?manufacturer_id= filter
GET    /purchases/{purchase_id}
POST   /purchases/{purchase_id}/payments
GET    /purchases/{purchase_id}/payments

POST   /manufacturer-payment-schedules
GET    /manufacturer-payment-schedules          ?manufacturer_id=&is_active= filters
GET    /manufacturer-payment-schedules/{schedule_id}
PATCH  /manufacturer-payment-schedules/{schedule_id}

POST   /products
GET    /products
GET    /products/{product_id}
PATCH  /products/{product_id}
DELETE /products/{product_id}                   soft delete (deactivate)

GET    /payments                                unified customer+manufacturer feed, newest first
                                                 (?skip=&limit= paging) — powers the mobile app's Payments tab

GET    /dashboard
```

## Example requests

### Create a customer

```http
POST /api/v1/customers
{
  "name": "ABC Traders",
  "area": "Downtown",
  "phone": "+91-9000000000"
}
```

### Create a product

```http
POST /api/v1/products
{ "sku": "TV-001", "name": "Samsung TV", "brand": "Samsung" }
```

### Create a sale (₹1,00,000 = 2 × ₹50,000), with a ₹20,000 advance recorded at creation

```http
POST /api/v1/sales
{
  "customer_id": "<customer-id>",
  "items": [{ "product_id": "<product-id>", "unit_price": "50000.00", "quantity": 2 }],
  "initial_payment": { "amount": "20000.00", "method": "CASH" }
}
```

Response includes `total_amount: 100000.00`, `amount_paid: 20000.00`, `balance_due: 80000.00`,
`payment_status: "PARTIALLY_PAID"`.

### Record a further payment

```http
POST /api/v1/sales/<sale-id>/payments
{ "amount": "10000.00", "method": "UPI", "reference_number": "UPI123456" }
```

### Create a weekly ₹5,000 customer payment schedule

```http
POST /api/v1/customer-payment-schedules
{
  "customer_id": "<customer-id>",
  "sale_id": "<sale-id>",
  "frequency": "WEEKLY",
  "expected_amount": "5000.00",
  "start_date": "2026-09-15"
}
```

This only records an *expectation* — it never marks money as received.

### Dashboard

```http
GET /api/v1/dashboard
```

```json
{
  "total_receivables": "550000.00",
  "total_payables": "320000.00",
  "net_position": "230000.00",
  "total_collected_from_customers": "...",
  "total_paid_to_manufacturers": "...",
  "customers_with_outstanding_balance": 12,
  "manufacturers_with_outstanding_balance": 4,
  "overdue_customer_balance": "...",
  "overdue_manufacturer_balance": "...",
  "overdue_customer_count": 3,
  "overdue_manufacturer_count": 1
}
```

## Design notes / assumptions

- A sale/purchase can contain multiple line items (`sale_items` / `purchase_items`), even though the
  spec's worked examples only show one product per transaction — this matches the normalized schema
  the spec itself lists in section 12.
- `due_date` is optional on sales/purchases; it's the only thing that drives the `OVERDUE` status. If
  you never set it, a balance simply stays `PENDING`/`PARTIALLY_PAID` indefinitely instead of going
  overdue — there's no implicit "overdue after N days" rule.
- `customer_payment_schedules` / `manufacturer_payment_schedules` require both a customer/manufacturer
  **and** a specific sale/purchase, per the field list in the spec. They do not advance
  `next_expected_date` automatically — that's left for the automation experiments this app exists to
  support.

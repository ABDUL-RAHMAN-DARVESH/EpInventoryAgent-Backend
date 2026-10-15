"""make customer and manufacturer numbers sequential per owner

Revision ID: d8f2a1c6b903
Revises: c4a6d9e2f7b1
Create Date: 2026-10-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8f2a1c6b903"
down_revision: Union[str, None] = "c4a6d9e2f7b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _renumber(table: str, column: str) -> None:
    op.execute(sa.text(f"""
        WITH numbered AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY owner_id ORDER BY created_at, id) AS n
            FROM {table}
        )
        UPDATE {table} AS records SET {column} = numbered.n
        FROM numbered WHERE records.id = numbered.id
    """))


def upgrade() -> None:
    op.drop_constraint("uq_customers_customer_number", "customers", type_="unique")
    op.drop_constraint("uq_manufacturers_manufacturer_number", "manufacturers", type_="unique")
    op.alter_column("customers", "customer_number", server_default=None)
    op.alter_column("manufacturers", "manufacturer_number", server_default=None)
    _renumber("customers", "customer_number")
    _renumber("manufacturers", "manufacturer_number")
    op.create_unique_constraint("uq_customers_owner_number", "customers", ["owner_id", "customer_number"])
    op.create_unique_constraint("uq_manufacturers_owner_number", "manufacturers", ["owner_id", "manufacturer_number"])

    op.create_table(
        "party_number_counters",
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("party_type", sa.String(length=20), nullable=False),
        sa.Column("last_number", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("party_type IN ('customer', 'manufacturer')", name="ck_party_number_type"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("owner_id", "party_type"),
    )
    op.execute(sa.text("""
        INSERT INTO party_number_counters (owner_id, party_type, last_number)
        SELECT owner_id, 'customer', MAX(customer_number) FROM customers GROUP BY owner_id
        UNION ALL
        SELECT owner_id, 'manufacturer', MAX(manufacturer_number) FROM manufacturers GROUP BY owner_id
    """))
    op.execute(sa.text("DROP SEQUENCE customer_number_seq"))
    op.execute(sa.text("DROP SEQUENCE manufacturer_number_seq"))


def downgrade() -> None:
    op.drop_table("party_number_counters")
    op.drop_constraint("uq_customers_owner_number", "customers", type_="unique")
    op.drop_constraint("uq_manufacturers_owner_number", "manufacturers", type_="unique")
    for table, column, sequence, constraint in (
        ("customers", "customer_number", "customer_number_seq", "uq_customers_customer_number"),
        ("manufacturers", "manufacturer_number", "manufacturer_number_seq", "uq_manufacturers_manufacturer_number"),
    ):
        op.execute(sa.text(f"CREATE SEQUENCE {sequence} START WITH 1"))
        op.execute(sa.text(f"""
            WITH numbered AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, id) AS n FROM {table}
            )
            UPDATE {table} AS records SET {column} = numbered.n
            FROM numbered WHERE records.id = numbered.id
        """))
        op.execute(sa.text(f"SELECT setval('{sequence}', COALESCE(MAX({column}), 1), MAX({column}) IS NOT NULL) FROM {table}"))
        op.alter_column(table, column, server_default=sa.text(f"nextval('{sequence}'::regclass)"))
        op.create_unique_constraint(constraint, table, [column])

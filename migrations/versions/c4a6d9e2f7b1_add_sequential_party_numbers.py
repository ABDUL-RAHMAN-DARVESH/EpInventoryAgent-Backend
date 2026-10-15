"""add sequential customer and manufacturer numbers

Revision ID: c4a6d9e2f7b1
Revises: b7f4e1a9c2d5
Create Date: 2026-10-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4a6d9e2f7b1"
down_revision: Union[str, None] = "b7f4e1a9c2d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_number_column(table: str, column: str, sequence: str) -> None:
    op.execute(sa.text(f"CREATE SEQUENCE {sequence} START WITH 1"))
    op.add_column(table, sa.Column(column, sa.BigInteger(), nullable=True))
    op.execute(
        sa.text(
            f"""
            WITH numbered AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, id) AS assigned_number
                FROM {table}
            )
            UPDATE {table} AS records
            SET {column} = numbered.assigned_number
            FROM numbered
            WHERE records.id = numbered.id
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            SELECT setval(
                '{sequence}',
                COALESCE(MAX({column}), 1),
                MAX({column}) IS NOT NULL
            )
            FROM {table}
            """
        )
    )
    op.alter_column(
        table,
        column,
        existing_type=sa.BigInteger(),
        nullable=False,
        server_default=sa.text(f"nextval('{sequence}'::regclass)"),
    )
    op.create_unique_constraint(f"uq_{table}_{column}", table, [column])


def upgrade() -> None:
    _add_number_column("customers", "customer_number", "customer_number_seq")
    _add_number_column("manufacturers", "manufacturer_number", "manufacturer_number_seq")


def downgrade() -> None:
    op.drop_constraint("uq_manufacturers_manufacturer_number", "manufacturers", type_="unique")
    op.drop_column("manufacturers", "manufacturer_number")
    op.execute(sa.text("DROP SEQUENCE manufacturer_number_seq"))

    op.drop_constraint("uq_customers_customer_number", "customers", type_="unique")
    op.drop_column("customers", "customer_number")
    op.execute(sa.text("DROP SEQUENCE customer_number_seq"))

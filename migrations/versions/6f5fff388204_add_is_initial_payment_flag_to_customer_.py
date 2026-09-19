"""add is initial payment flag to customer payments

Revision ID: 6f5fff388204
Revises: 33ff5bfe74d2
Create Date: 2026-09-16 08:35:08.244970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f5fff388204'
down_revision: Union[str, None] = '33ff5bfe74d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'customer_payments',
        sa.Column('is_initial_payment', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Backfill existing rows: a sale and its initial payment are created and
    # committed together in the same DB transaction (sale_service.create_sale),
    # and both columns use server_default=now() -- Postgres's now() returns the
    # *transaction* start time, so it's identical for every row written in
    # that transaction. A genuine later Customer Payment is always a separate
    # transaction, so its created_at can never coincide with its sale's. This
    # makes an exact timestamp match a reliable signal for backfill.
    op.execute(
        """
        UPDATE customer_payments cp
        SET is_initial_payment = true
        FROM sales s
        WHERE cp.sale_id = s.id AND cp.created_at = s.created_at
        """
    )


def downgrade() -> None:
    op.drop_column('customer_payments', 'is_initial_payment')

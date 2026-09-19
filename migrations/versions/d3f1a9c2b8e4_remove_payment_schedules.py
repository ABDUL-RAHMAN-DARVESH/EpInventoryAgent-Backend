"""remove payment schedules

Revision ID: d3f1a9c2b8e4
Revises: 479e8626518b
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f1a9c2b8e4'
down_revision: Union[str, None] = '479e8626518b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f('ix_manufacturer_payment_schedules_purchase_id'), table_name='manufacturer_payment_schedules')
    op.drop_index(op.f('ix_manufacturer_payment_schedules_manufacturer_id'), table_name='manufacturer_payment_schedules')
    op.drop_table('manufacturer_payment_schedules')

    op.drop_index(op.f('ix_customer_payment_schedules_sale_id'), table_name='customer_payment_schedules')
    op.drop_index(op.f('ix_customer_payment_schedules_customer_id'), table_name='customer_payment_schedules')
    op.drop_table('customer_payment_schedules')

    sa.Enum(name='schedule_frequency_enum').drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    schedule_frequency_enum = sa.Enum('DAILY', 'WEEKLY', 'MONTHLY', name='schedule_frequency_enum')
    schedule_frequency_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'customer_payment_schedules',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sale_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('frequency', schedule_frequency_enum, nullable=False),
        sa.Column('expected_amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('next_expected_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_customer_payment_schedules_customer_id'), 'customer_payment_schedules', ['customer_id'], unique=False)
    op.create_index(op.f('ix_customer_payment_schedules_sale_id'), 'customer_payment_schedules', ['sale_id'], unique=False)

    op.create_table(
        'manufacturer_payment_schedules',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('manufacturer_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('purchase_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('frequency', schedule_frequency_enum, nullable=False),
        sa.Column('expected_amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('next_expected_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['manufacturer_id'], ['manufacturers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['purchase_id'], ['purchases.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_manufacturer_payment_schedules_manufacturer_id'), 'manufacturer_payment_schedules', ['manufacturer_id'], unique=False)
    op.create_index(op.f('ix_manufacturer_payment_schedules_purchase_id'), 'manufacturer_payment_schedules', ['purchase_id'], unique=False)

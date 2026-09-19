"""remove product sku

Revision ID: f297324dedba
Revises: 6f5fff388204
Create Date: 2026-09-16 09:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f297324dedba'
down_revision: Union[str, None] = '6f5fff388204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uq_products_owner_sku', 'products', type_='unique')
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.drop_column('products', 'sku')


def downgrade() -> None:
    # Structural rollback only -- the original SKU values are gone for good.
    op.add_column('products', sa.Column('sku', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=False)
    op.create_unique_constraint('uq_products_owner_sku', 'products', ['owner_id', 'sku'])

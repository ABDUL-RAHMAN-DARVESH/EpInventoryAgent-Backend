"""add images and shop profile

Revision ID: a1c2d9e6f0b3
Revises: f297324dedba
Create Date: 2026-09-17 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c2d9e6f0b3'
down_revision: Union[str, None] = 'f297324dedba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('customers', sa.Column('image_url', sa.String(length=500), nullable=True))
    op.add_column('manufacturers', sa.Column('image_url', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('shop_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('shop_address', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('shop_logo_url', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('shop_image_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'shop_image_url')
    op.drop_column('users', 'shop_logo_url')
    op.drop_column('users', 'shop_address')
    op.drop_column('users', 'shop_name')
    op.drop_column('manufacturers', 'image_url')
    op.drop_column('customers', 'image_url')

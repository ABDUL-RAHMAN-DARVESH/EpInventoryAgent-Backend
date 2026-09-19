"""add shop phone

Revision ID: b7f4e1a9c2d5
Revises: a1c2d9e6f0b3
Create Date: 2026-09-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7f4e1a9c2d5'
down_revision: Union[str, None] = 'a1c2d9e6f0b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('shop_phone', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'shop_phone')

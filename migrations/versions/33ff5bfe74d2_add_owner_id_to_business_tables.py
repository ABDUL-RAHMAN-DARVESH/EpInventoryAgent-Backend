"""add owner id to business tables

Revision ID: 33ff5bfe74d2
Revises: 1e0ba68952fe
Create Date: 2026-09-15 15:13:04.817593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33ff5bfe74d2'
down_revision: Union[str, None] = '1e0ba68952fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BOOTSTRAP_ADMIN_EMAIL = "admin@example.com"

# owner_id is denormalized onto every business table (rather than inferred via
# joins) to match this codebase's existing query style -- lots of direct
# aggregate `select(...).where(...)` calls, especially in dashboard_service.py.
TABLES = ['customers', 'manufacturers', 'products', 'sales', 'purchases', 'customer_payments', 'manufacturer_payments']


def upgrade() -> None:
    connection = op.get_bind()
    bootstrap_admin_id = connection.execute(
        sa.text("SELECT id FROM users WHERE email = :email"), {"email": BOOTSTRAP_ADMIN_EMAIL}
    ).scalar()
    if bootstrap_admin_id is None:
        raise RuntimeError(
            f"Bootstrap admin ({BOOTSTRAP_ADMIN_EMAIL}) not found -- did the previous migration run?"
        )

    for table in TABLES:
        op.add_column(table, sa.Column('owner_id', sa.UUID(), nullable=True))
        connection.execute(
            sa.text(f"UPDATE {table} SET owner_id = :owner_id WHERE owner_id IS NULL"),
            {"owner_id": bootstrap_admin_id},
        )
        op.alter_column(table, 'owner_id', nullable=False)
        op.create_foreign_key(
            f'fk_{table}_owner_id_users', table, 'users', ['owner_id'], ['id'], ondelete='RESTRICT'
        )
        op.create_index(op.f(f'ix_{table}_owner_id'), table, ['owner_id'], unique=False)

    # SKUs move from a globally-unique index to a per-tenant unique
    # constraint -- two different users' catalogs may legitimately both use
    # "HA-001". Keep a plain (non-unique) index on sku alone for lookups that
    # don't have owner_id as a composite-index prefix.
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=False)
    op.create_unique_constraint('uq_products_owner_sku', 'products', ['owner_id', 'sku'])


def downgrade() -> None:
    op.drop_constraint('uq_products_owner_sku', 'products', type_='unique')
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)

    for table in TABLES:
        op.drop_index(op.f(f'ix_{table}_owner_id'), table_name=table)
        op.drop_constraint(f'fk_{table}_owner_id_users', table, type_='foreignkey')
        op.drop_column(table, 'owner_id')

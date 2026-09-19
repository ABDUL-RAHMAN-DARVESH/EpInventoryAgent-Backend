"""add users licensing features

Revision ID: 1e0ba68952fe
Revises: d3f1a9c2b8e4
Create Date: 2026-09-15 15:13:02.721403

"""
import secrets
import uuid
from typing import Sequence, Union

import bcrypt
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e0ba68952fe'
down_revision: Union[str, None] = 'd3f1a9c2b8e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Bootstrap admin -- the only account that exists until someone logs in and
# creates real users via the admin API. The password is generated fresh each
# time this migration runs against a new database and printed once below --
# it is never stored in source, so capture it from the migration/deploy log
# and change it via the admin dashboard immediately after first login.
BOOTSTRAP_ADMIN_ID = uuid.uuid4()
BOOTSTRAP_ADMIN_EMAIL = "admin@example.com"
BOOTSTRAP_ADMIN_PASSWORD = secrets.token_urlsafe(12)


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('ADMIN', 'STAFF', name='user_role_enum'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table(
        'features',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_features_key'), 'features', ['key'], unique=True)

    op.create_table(
        'user_features',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('feature_id', sa.UUID(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['feature_id'], ['features.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'feature_id', name='uq_user_features_user_feature'),
    )
    op.create_index(op.f('ix_user_features_user_id'), 'user_features', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_features_feature_id'), 'user_features', ['feature_id'], unique=False)

    op.create_table(
        'app_version_configs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('platform', sa.String(length=30), nullable=False),
        sa.Column('latest_version', sa.String(length=30), nullable=False),
        sa.Column('minimum_version', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_app_version_configs_platform'), 'app_version_configs', ['platform'], unique=True)

    # Bootstrap admin account + a starting Android version policy that matches
    # the app's current app.json version, so /version/check never blocks by
    # accident before anyone's configured it via the admin API.
    hashed = bcrypt.hashpw(BOOTSTRAP_ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    users_table = sa.table(
        'users',
        sa.column('id', sa.UUID()),
        sa.column('email', sa.String()),
        sa.column('hashed_password', sa.String()),
        sa.column('full_name', sa.String()),
        sa.column('role', sa.Enum('ADMIN', 'STAFF', name='user_role_enum')),
        sa.column('is_active', sa.Boolean()),
    )
    op.bulk_insert(
        users_table,
        [
            {
                'id': BOOTSTRAP_ADMIN_ID,
                'email': BOOTSTRAP_ADMIN_EMAIL,
                'hashed_password': hashed,
                'full_name': 'Bootstrap Admin',
                'role': 'ADMIN',
                'is_active': True,
            }
        ],
    )
    print("=" * 70)
    print(f"Bootstrap admin created: {BOOTSTRAP_ADMIN_EMAIL} / {BOOTSTRAP_ADMIN_PASSWORD}")
    print("Log in and change this password immediately -- it will not be shown again.")
    print("=" * 70)

    app_version_table = sa.table(
        'app_version_configs',
        sa.column('id', sa.UUID()),
        sa.column('platform', sa.String()),
        sa.column('latest_version', sa.String()),
        sa.column('minimum_version', sa.String()),
    )
    op.bulk_insert(
        app_version_table,
        [
            {
                'id': uuid.uuid4(),
                'platform': 'android',
                'latest_version': '1.0.0',
                'minimum_version': '1.0.0',
            }
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_app_version_configs_platform'), table_name='app_version_configs')
    op.drop_table('app_version_configs')
    op.drop_index(op.f('ix_user_features_feature_id'), table_name='user_features')
    op.drop_index(op.f('ix_user_features_user_id'), table_name='user_features')
    op.drop_table('user_features')
    op.drop_index(op.f('ix_features_key'), table_name='features')
    op.drop_table('features')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS user_role_enum')

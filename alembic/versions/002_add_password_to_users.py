"""add hashed_password to users

Revision ID: 002
Revises: 001
Create Date: 2026-04-25

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('hashed_password', sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'hashed_password')

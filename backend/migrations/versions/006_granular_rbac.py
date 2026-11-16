"""Add granular RBAC support and custom_permissions column to project_members

Revision ID: 006_granular_rbac
Revises: 005_advanced_contradiction_detection
Create Date: 2026-11-15 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_granular_rbac'
down_revision: Union[str, None] = '005_advanced_contradiction_detection'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add custom_permissions JSON column to project_members table
    op.add_column(
        'project_members',
        sa.Column('custom_permissions', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    # Remove custom_permissions column
    op.drop_column('project_members', 'custom_permissions')

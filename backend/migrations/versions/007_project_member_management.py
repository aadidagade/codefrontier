"""Add status, invitation_status, invited_by, and invited_at to project_members

Revision ID: 007_project_member_management
Revises: 006_granular_rbac
Create Date: 2026-11-15 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_project_member_management'
down_revision: Union[str, None] = '006_granular_rbac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'project_members',
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'active'")),
    )
    op.add_column(
        'project_members',
        sa.Column('invitation_status', sa.String(length=50), nullable=False, server_default=sa.text("'accepted'")),
    )
    op.add_column(
        'project_members',
        sa.Column('invited_by', sa.Uuid(), nullable=True),
    )
    op.add_column(
        'project_members',
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_project_members_invited_by',
        'project_members', 'users',
        ['invited_by'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_project_members_status',
        'project_members',
        ['status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_project_members_status', table_name='project_members')
    op.drop_constraint('fk_project_members_invited_by', 'project_members', type_='foreignkey')
    op.drop_column('project_members', 'invited_at')
    op.drop_column('project_members', 'invited_by')
    op.drop_column('project_members', 'invitation_status')
    op.drop_column('project_members', 'status')

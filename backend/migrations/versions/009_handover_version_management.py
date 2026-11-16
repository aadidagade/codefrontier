"""Implement Handover Version Management system

Revision ID: 009_handover_version_management
Revises: 008_audit_trail_system
Create Date: 2026-11-16 02:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '009_handover_version_management'
down_revision: Union[str, None] = '008_audit_trail_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to handover_versions table
    op.add_column('handover_versions', sa.Column('version_description', sa.Text(), nullable=True))
    op.add_column('handover_versions', sa.Column('approval_status', sa.String(length=50), nullable=False, server_default='DRAFT'))
    op.add_column('handover_versions', sa.Column('parent_version_id', sa.Uuid(), nullable=True))
    op.add_column('handover_versions', sa.Column('is_latest', sa.Boolean(), nullable=False, server_default='false'))

    # Add foreign key and indexes
    op.create_foreign_key(
        'fk_handover_versions_parent_version_id',
        'handover_versions',
        'handover_versions',
        ['parent_version_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_handover_versions_parent_version_id', 'handover_versions', ['parent_version_id'], unique=False)
    op.create_index('ix_handover_versions_approval_status', 'handover_versions', ['approval_status'], unique=False)
    op.create_index('ix_handover_versions_is_latest', 'handover_versions', ['is_latest'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_handover_versions_is_latest', table_name='handover_versions')
    op.drop_index('ix_handover_versions_approval_status', table_name='handover_versions')
    op.drop_index('ix_handover_versions_parent_version_id', table_name='handover_versions')
    op.drop_constraint('fk_handover_versions_parent_version_id', 'handover_versions', type_='foreignkey')
    op.drop_column('handover_versions', 'is_latest')
    op.drop_column('handover_versions', 'parent_version_id')
    op.drop_column('handover_versions', 'approval_status')
    op.drop_column('handover_versions', 'version_description')

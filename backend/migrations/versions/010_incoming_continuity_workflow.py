"""Implement Incoming Member Continuity Workflow

Revision ID: 010_incoming_continuity_workflow
Revises: 009_handover_version_management
Create Date: 2026-11-16 02:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '010_incoming_continuity_workflow'
down_revision: Union[str, None] = '009_handover_version_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add continuity and acknowledgement columns to handovers table
    op.add_column('handovers', sa.Column('transition_status', sa.String(length=50), nullable=False, server_default='Awaiting Acknowledgement'))
    op.add_column('handovers', sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('handovers', sa.Column('acknowledged_by', sa.Uuid(), nullable=True))
    op.add_column('handovers', sa.Column('acknowledgement_notes', sa.Text(), nullable=True))
    op.add_column('handovers', sa.Column('checklist_confirmed', sa.Boolean(), nullable=False, server_default='false'))

    op.create_foreign_key(
        'fk_handovers_acknowledged_by_users',
        'handovers',
        'users',
        ['acknowledged_by'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_handovers_transition_status', 'handovers', ['transition_status'], unique=False)
    op.create_index('ix_handovers_acknowledged_by', 'handovers', ['acknowledged_by'], unique=False)

    # Create task_progress_updates table
    op.create_table(
        'task_progress_updates',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('task_id', sa.Uuid(), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('update_text', sa.Text(), nullable=False),
        sa.Column('status_before', sa.String(length=50), nullable=True),
        sa.Column('status_after', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_task_progress_updates_task_id', 'task_progress_updates', ['task_id'], unique=False)
    op.create_index('ix_task_progress_updates_user_id', 'task_progress_updates', ['user_id'], unique=False)
    op.create_index('ix_task_progress_updates_created_at', 'task_progress_updates', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('task_progress_updates')
    op.drop_index('ix_handovers_acknowledged_by', table_name='handovers')
    op.drop_index('ix_handovers_transition_status', table_name='handovers')
    op.drop_constraint('fk_handovers_acknowledged_by_users', 'handovers', type_='foreignkey')
    op.drop_column('handovers', 'checklist_confirmed')
    op.drop_column('handovers', 'acknowledgement_notes')
    op.drop_column('handovers', 'acknowledged_by')
    op.drop_column('handovers', 'acknowledged_at')
    op.drop_column('handovers', 'transition_status')

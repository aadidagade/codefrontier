"""Add advanced contradiction detection columns to conflicts

Revision ID: 005_advanced_contradiction_detection
Revises: 004_advanced_evidence_verification
Create Date: 2026-11-15 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005_advanced_contradiction_detection'
down_revision: Union[str, None] = '004_advanced_evidence_verification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add explicit columns for the 9 required conflict fields
    op.add_column('conflicts', sa.Column('conflict_category', sa.String(length=100), nullable=True))
    op.add_column('conflicts', sa.Column('statement_a', sa.Text(), nullable=True))
    op.add_column('conflicts', sa.Column('statement_b', sa.Text(), nullable=True))
    op.add_column('conflicts', sa.Column('source_document_a_id', sa.Uuid(), nullable=True))
    op.add_column('conflicts', sa.Column('source_document_a_name', sa.String(length=255), nullable=True))
    op.add_column('conflicts', sa.Column('source_document_b_id', sa.Uuid(), nullable=True))
    op.add_column('conflicts', sa.Column('source_document_b_name', sa.String(length=255), nullable=True))
    op.add_column('conflicts', sa.Column('source_excerpt_a', sa.Text(), nullable=True))
    op.add_column('conflicts', sa.Column('source_excerpt_b', sa.Text(), nullable=True))
    op.add_column(
        'conflicts',
        sa.Column('detection_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        'conflicts',
        sa.Column('resolution_status', sa.String(length=50), nullable=False, server_default=sa.text("'Unresolved'")),
    )

    op.create_foreign_key(
        'fk_conflicts_doc_a',
        'conflicts', 'documents',
        ['source_document_a_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_conflicts_doc_b',
        'conflicts', 'documents',
        ['source_document_b_id'], ['id'],
        ondelete='SET NULL',
    )

    op.create_index('ix_conflicts_conflict_category', 'conflicts', ['conflict_category'], unique=False)
    op.create_index('ix_conflicts_doc_a', 'conflicts', ['source_document_a_id'], unique=False)
    op.create_index('ix_conflicts_doc_b', 'conflicts', ['source_document_b_id'], unique=False)
    op.create_index('ix_conflicts_resolution_status', 'conflicts', ['resolution_status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_conflicts_resolution_status', table_name='conflicts')
    op.drop_index('ix_conflicts_doc_b', table_name='conflicts')
    op.drop_index('ix_conflicts_doc_a', table_name='conflicts')
    op.drop_index('ix_conflicts_conflict_category', table_name='conflicts')

    op.drop_constraint('fk_conflicts_doc_b', 'conflicts', type_='foreignkey')
    op.drop_constraint('fk_conflicts_doc_a', 'conflicts', type_='foreignkey')

    op.drop_column('conflicts', 'resolution_status')
    op.drop_column('conflicts', 'detection_timestamp')
    op.drop_column('conflicts', 'source_excerpt_b')
    op.drop_column('conflicts', 'source_excerpt_a')
    op.drop_column('conflicts', 'source_document_b_name')
    op.drop_column('conflicts', 'source_document_b_id')
    op.drop_column('conflicts', 'source_document_a_name')
    op.drop_column('conflicts', 'source_document_a_id')
    op.drop_column('conflicts', 'statement_b')
    op.drop_column('conflicts', 'statement_a')
    op.drop_column('conflicts', 'conflict_category')

"""Add Advanced Evidence Verification schema and claim_verifications table

Revision ID: 004_advanced_evidence_verification
Revises: 003_add_fts_index
Create Date: 2026-11-15 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_advanced_evidence_verification'
down_revision: Union[str, None] = '003_add_fts_index'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update evidence_references to support optional document_id and rich claim metadata
    op.alter_column(
        'evidence_references',
        'document_id',
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.add_column('evidence_references', sa.Column('claim_id', sa.String(length=255), nullable=True))
    op.add_column('evidence_references', sa.Column('claim_text', sa.Text(), nullable=True))
    op.add_column('evidence_references', sa.Column('supporting_text_excerpt', sa.Text(), nullable=True))
    op.add_column('evidence_references', sa.Column('source_filename', sa.String(length=255), nullable=True))
    op.add_column('evidence_references', sa.Column('section_reference', sa.String(length=255), nullable=True))
    op.add_column('evidence_references', sa.Column('reasoning', sa.Text(), nullable=True))
    op.add_column(
        'evidence_references',
        sa.Column('verification_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_evidence_references_claim_id', 'evidence_references', ['claim_id'], unique=False)

    # 2. Create claim_verifications table for rigorous factual audit persistence
    op.create_table(
        'claim_verifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('handover_id', sa.Uuid(), nullable=False),
        sa.Column('handover_section_id', sa.Uuid(), nullable=True),
        sa.Column('claim_id', sa.String(length=255), nullable=False),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False),
        sa.Column('supporting_document_id', sa.Uuid(), nullable=True),
        sa.Column('document_chunk_id', sa.Uuid(), nullable=True),
        sa.Column('source_filename', sa.String(length=255), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('section_reference', sa.String(length=255), nullable=True),
        sa.Column('supporting_text_excerpt', sa.Text(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('alignment_score', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('verification_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['handover_id'], ['handovers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['handover_section_id'], ['handover_sections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supporting_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_chunk_id'], ['document_chunks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_claim_verifications_id', 'claim_verifications', ['id'], unique=False)
    op.create_index('ix_claim_verifications_handover_id', 'claim_verifications', ['handover_id'], unique=False)
    op.create_index('ix_claim_verifications_section_id', 'claim_verifications', ['handover_section_id'], unique=False)
    op.create_index('ix_claim_verifications_claim_id', 'claim_verifications', ['claim_id'], unique=False)
    op.create_index('ix_claim_verifications_status', 'claim_verifications', ['verification_status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_claim_verifications_status', table_name='claim_verifications')
    op.drop_index('ix_claim_verifications_claim_id', table_name='claim_verifications')
    op.drop_index('ix_claim_verifications_section_id', table_name='claim_verifications')
    op.drop_index('ix_claim_verifications_handover_id', table_name='claim_verifications')
    op.drop_index('ix_claim_verifications_id', table_name='claim_verifications')
    op.drop_table('claim_verifications')

    op.drop_index('ix_evidence_references_claim_id', table_name='evidence_references')
    op.drop_column('evidence_references', 'verification_timestamp')
    op.drop_column('evidence_references', 'reasoning')
    op.drop_column('evidence_references', 'section_reference')
    op.drop_column('evidence_references', 'source_filename')
    op.drop_column('evidence_references', 'supporting_text_excerpt')
    op.drop_column('evidence_references', 'claim_text')
    op.drop_column('evidence_references', 'claim_id')
    op.alter_column(
        'evidence_references',
        'document_id',
        existing_type=sa.Uuid(),
        nullable=False,
    )

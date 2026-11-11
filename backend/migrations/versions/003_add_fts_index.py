"""Add GIN index for document chunk full-text search

Revision ID: 003_add_fts_index
Revises: 002_add_vector_index
Create Date: 2026-11-10 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_add_fts_index'
down_revision = '002_add_vector_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use GIN index on to_tsvector('english', content) for fast keyword full text retrieval
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_content_fts "
        "ON document_chunks USING gin (to_tsvector('english', content));"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_fts;")

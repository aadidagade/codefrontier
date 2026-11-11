"""Add HNSW index for document chunk embeddings

Revision ID: 002_add_vector_index
Revises: 001_initial_schema
Create Date: 2026-11-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_vector_index'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use HNSW index on document_chunks (embedding vector_cosine_ops)
    # HNSW provides fast approximate nearest neighbor search with cosine distance
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw;")

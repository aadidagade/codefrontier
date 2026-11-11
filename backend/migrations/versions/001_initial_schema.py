"""Initial schema with 15 models and pgvector extension

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-10 12:00:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Table: users
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('profile_image', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 3. Table: refresh_tokens
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refresh_tokens_id', 'refresh_tokens', ['id'], unique=False)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)

    # 4. Table: projects
    op.create_table(
        'projects',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('organization_name', sa.String(length=255), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'active'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_projects_id', 'projects', ['id'], unique=False)
    op.create_index('ix_projects_name', 'projects', ['name'], unique=False)
    op.create_index('ix_projects_created_by', 'projects', ['created_by'], unique=False)
    op.create_index('ix_projects_status', 'projects', ['status'], unique=False)

    # 5. Table: project_members
    op.create_table(
        'project_members',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_project_member'),
    )
    op.create_index('ix_project_members_id', 'project_members', ['id'], unique=False)
    op.create_index('ix_project_members_project_id', 'project_members', ['project_id'], unique=False)
    op.create_index('ix_project_members_user_id', 'project_members', ['user_id'], unique=False)

    # 6. Table: documents
    op.create_table(
        'documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('processing_status', sa.String(length=50), nullable=False, server_default=sa.text("'uploaded'")),
        sa.Column('extraction_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stored_filename', name='uq_documents_stored_filename'),
    )
    op.create_index('ix_documents_id', 'documents', ['id'], unique=False)
    op.create_index('ix_documents_project_id', 'documents', ['project_id'], unique=False)
    op.create_index('ix_documents_uploaded_by', 'documents', ['uploaded_by'], unique=False)
    op.create_index('ix_documents_status', 'documents', ['processing_status'], unique=False)

    # 7. Table: document_chunks (pgvector 768)
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('section_title', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_document_chunks_id', 'document_chunks', ['id'], unique=False)
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'], unique=False)
    op.create_index('ix_document_chunks_project_id', 'document_chunks', ['project_id'], unique=False)
    op.create_index('ix_chunks_project_doc', 'document_chunks', ['project_id', 'document_id'], unique=False)
    op.create_index('ix_chunks_doc_index', 'document_chunks', ['document_id', 'chunk_index'], unique=False)

    # 8. Table: handovers
    op.create_table(
        'handovers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('assigned_to', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'draft'")),
        sa.Column('version', sa.String(length=50), nullable=False, server_default=sa.text("'v1.0'")),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('shared_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_handovers_id', 'handovers', ['id'], unique=False)
    op.create_index('ix_handovers_project_id', 'handovers', ['project_id'], unique=False)
    op.create_index('ix_handovers_created_by', 'handovers', ['created_by'], unique=False)
    op.create_index('ix_handovers_assigned_to', 'handovers', ['assigned_to'], unique=False)
    op.create_index('ix_handovers_status', 'handovers', ['status'], unique=False)

    # 9. Table: handover_sections
    op.create_table(
        'handover_sections',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('handover_id', sa.Uuid(), nullable=False),
        sa.Column('section_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default=sa.text('1.0')),
        sa.Column('review_status', sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['handover_id'], ['handovers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_handover_sections_id', 'handover_sections', ['id'], unique=False)
    op.create_index('ix_handover_sections_handover_id', 'handover_sections', ['handover_id'], unique=False)
    op.create_index('ix_handover_section_sort', 'handover_sections', ['handover_id', 'sort_order'], unique=False)

    # 10. Table: handover_versions
    op.create_table(
        'handover_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('handover_id', sa.Uuid(), nullable=False),
        sa.Column('version_number', sa.String(length=50), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['handover_id'], ['handovers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_handover_versions_id', 'handover_versions', ['id'], unique=False)
    op.create_index('ix_handover_versions_handover_id', 'handover_versions', ['handover_id'], unique=False)

    # 11. Table: handover_audit_logs
    op.create_table(
        'handover_audit_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('handover_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['handover_id'], ['handovers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_handover_audit_logs_id', 'handover_audit_logs', ['id'], unique=False)
    op.create_index('ix_handover_audit_logs_handover_id', 'handover_audit_logs', ['handover_id'], unique=False)
    op.create_index('ix_handover_audit_logs_user_id', 'handover_audit_logs', ['user_id'], unique=False)

    # 12. Table: evidence_references
    op.create_table(
        'evidence_references',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('handover_section_id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('document_chunk_id', sa.Uuid(), nullable=True),
        sa.Column('quoted_text', sa.Text(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=False, server_default=sa.text('1.0')),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default=sa.text("'supported'")),
        sa.ForeignKeyConstraint(['handover_section_id'], ['handover_sections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_chunk_id'], ['document_chunks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evidence_references_id', 'evidence_references', ['id'], unique=False)
    op.create_index('ix_evidence_references_section_id', 'evidence_references', ['handover_section_id'], unique=False)
    op.create_index('ix_evidence_references_doc_id', 'evidence_references', ['document_id'], unique=False)
    op.create_index('ix_evidence_references_chunk_id', 'evidence_references', ['document_chunk_id'], unique=False)

    # 13. Table: conflicts
    op.create_table(
        'conflicts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('handover_id', sa.Uuid(), nullable=True),
        sa.Column('conflict_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('source_a', sa.JSON(), nullable=False),
        sa.Column('source_b', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'unresolved'")),
        sa.Column('resolution', sa.JSON(), nullable=True),
        sa.Column('resolved_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['handover_id'], ['handovers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_conflicts_id', 'conflicts', ['id'], unique=False)
    op.create_index('ix_conflicts_project_id', 'conflicts', ['project_id'], unique=False)
    op.create_index('ix_conflicts_handover_id', 'conflicts', ['handover_id'], unique=False)
    op.create_index('ix_conflicts_status', 'conflicts', ['status'], unique=False)

    # 14. Table: tasks
    op.create_table(
        'tasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('handover_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assigned_to', sa.Uuid(), nullable=True),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default=sa.text("'medium'")),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['handover_id'], ['handovers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tasks_id', 'tasks', ['id'], unique=False)
    op.create_index('ix_tasks_project_id', 'tasks', ['project_id'], unique=False)
    op.create_index('ix_tasks_handover_id', 'tasks', ['handover_id'], unique=False)
    op.create_index('ix_tasks_assigned_to', 'tasks', ['assigned_to'], unique=False)
    op.create_index('ix_tasks_status', 'tasks', ['status'], unique=False)

    # 15. Table: task_dependencies
    op.create_table(
        'task_dependencies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('depends_on_task_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['depends_on_task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('task_id != depends_on_task_id', name='ck_no_self_task_dependency'),
        sa.UniqueConstraint('task_id', 'depends_on_task_id', name='uq_task_dependency_pair'),
    )
    op.create_index('ix_task_dependencies_id', 'task_dependencies', ['id'], unique=False)
    op.create_index('ix_task_dependencies_task_id', 'task_dependencies', ['task_id'], unique=False)
    op.create_index('ix_task_dependencies_depends_on', 'task_dependencies', ['depends_on_task_id'], unique=False)

    # 16. Table: notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_id', 'notifications', ['id'], unique=False)
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)
    op.create_index('ix_notifications_project_id', 'notifications', ['project_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order of foreign key dependencies
    op.drop_table('notifications')
    op.drop_table('task_dependencies')
    op.drop_table('tasks')
    op.drop_table('conflicts')
    op.drop_table('evidence_references')
    op.drop_table('handover_audit_logs')
    op.drop_table('handover_versions')
    op.drop_table('handover_sections')
    op.drop_table('handovers')
    op.drop_table('document_chunks')
    op.drop_table('documents')
    op.drop_table('project_members')
    op.drop_table('projects')
    op.drop_table('refresh_tokens')
    op.drop_table('users')

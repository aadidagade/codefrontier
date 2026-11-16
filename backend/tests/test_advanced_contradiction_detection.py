"""
Comprehensive Test Suite for Advanced Contradiction Detection Engine.

Validates:
1. Extraction of important factual statements from document chunks.
2. Grouping of statements referring to the same project entity or topic.
3. Gemini and deterministic evaluation of whether statements genuinely contradict each other.
4. Strictly avoids flagging simple wording differences as contradictions.
5. Identification of both source documents and their respective passages/quotes.
6. Storage of detected conflicts in the database containing all 9 mandated fields:
   - Conflict ID
   - Conflict category
   - Conflicting statement A
   - Conflicting statement B
   - Source document A
   - Source document B
   - Relevant source excerpts
   - Detection timestamp
   - Resolution status
7. Implementation of conflict resolution statuses:
   - Unresolved
   - Under Review
   - Resolved
   - Dismissed
8. System NEVER automatically selects one statement as correct (resolution=None on detection).
9. Human reviewer must decide which information is authoritative.
10. Comprehensive coverage for all prompt examples:
    - Different project deadlines
    - Different technology stacks
    - Conflicting task completion statuses
    - Different team member responsibilities
    - Outdated decisions conflicting with newer decisions
"""

import json
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import Settings
from app.models.conflict import Conflict
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.schemas.conflict import (
    ConflictCategory,
    ConflictResolutionStatus,
    ConflictResponse,
    ConflictResolveRequest,
    ConflictUpdateRequest,
    FactualStatement,
    normalize_conflict_status,
)
from app.services.contradiction_service import ContradictionDetectionService


@pytest.mark.asyncio
async def test_extract_factual_statements():
    """Requirement 1: Extracts important factual statements from document chunks."""
    mock_db = AsyncMock()
    service = ContradictionDetectionService(mock_db)

    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, original_filename="architecture_v1.md")
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        content=(
            "The hard release deadline for Version 1.0 is set for November 15, 2026. "
            "The backend primary database utilizes PostgreSQL 16 with pgvector. "
            "Alice is the lead backend engineer on this project. "
            "The OAuth2 authentication integration is completed and verified."
        ),
        page_number=1,
    )

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        statements = await service.extract_factual_statements([(chunk, doc)])

    assert len(statements) >= 3
    categories = {s.category for s in statements}
    assert ConflictCategory.DEADLINE.value in categories
    assert ConflictCategory.TECHNOLOGY_STACK.value in categories

    for s in statements:
        assert s.document_id == doc_id
        assert s.document_name == "architecture_v1.md"
        assert s.chunk_id == chunk.id
        assert s.page_number == 1
        assert len(s.statement) > 0
        assert len(s.excerpt) > 0


def test_group_statements_by_entity_or_topic():
    """Requirement 2: Groups statements referring to the same project entity or topic."""
    mock_db = AsyncMock()
    service = ContradictionDetectionService(mock_db)

    doc1_id = uuid.uuid4()
    doc2_id = uuid.uuid4()

    s1 = FactualStatement(
        statement="Release deadline is November 15, 2026.",
        entity_or_topic="Project Deadline",
        category="deadline",
        document_id=doc1_id,
        document_name="doc_a.md",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="Release deadline is November 15, 2026.",
    )
    s2 = FactualStatement(
        statement="Target launch deadline pushed to December 1, 2026.",
        entity_or_topic="Project Deadline",
        category="deadline",
        document_id=doc2_id,
        document_name="doc_b.md",
        chunk_id=uuid.uuid4(),
        page_number=2,
        excerpt="Target launch deadline pushed to December 1, 2026.",
    )
    s3 = FactualStatement(
        statement="Database engine is PostgreSQL 16.",
        entity_or_topic="Database Technology",
        category="technology_stack",
        document_id=doc1_id,
        document_name="doc_a.md",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="Database engine is PostgreSQL 16.",
    )

    groups = service.group_statements_by_entity_or_topic([s1, s2, s3])
    assert len(groups) >= 2

    # Verify deadline group contains both statements s1 and s2
    deadline_group_keys = [k for k in groups if "deadline" in k]
    assert len(deadline_group_keys) >= 1
    deadline_stmts = groups[deadline_group_keys[0]]
    assert s1 in deadline_stmts
    assert s2 in deadline_stmts


@pytest.mark.asyncio
async def test_gemini_contradiction_evaluation_structured():
    """Requirement 3: Use Gemini to evaluate whether statements genuinely contradict each other."""
    mock_db = AsyncMock()
    service = ContradictionDetectionService(mock_db)

    stmt_a = FactualStatement(
        statement="All microservices communicate via synchronous REST API calls.",
        entity_or_topic="Architecture Decision",
        category="decision",
        document_id=uuid.uuid4(),
        document_name="legacy_specs.md",
        chunk_id=uuid.uuid4(),
        page_number=3,
        excerpt="All microservices communicate via synchronous REST API calls.",
    )
    stmt_b = FactualStatement(
        statement="Architecture decision: all inter-service communication is event-driven via Kafka.",
        entity_or_topic="Architecture Decision",
        category="decision",
        document_id=uuid.uuid4(),
        document_name="new_adr.md",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="Architecture decision: all inter-service communication is event-driven via Kafka.",
    )

    mock_gemini_json = {
        "is_contradiction": True,
        "confidence": 0.96,
        "conflict_category": "decision",
        "description": "Conflicting architecture decisions: synchronous REST vs asynchronous Kafka events.",
        "statement_a": stmt_a.statement,
        "statement_b": stmt_b.statement,
        "excerpt_a": stmt_a.excerpt,
        "excerpt_b": stmt_b.excerpt,
        "reasoning": "Synchronous HTTP REST is fundamentally incompatible with mandatory asynchronous Kafka events.",
    }

    with patch.object(Settings, "is_gemini_configured", return_value=True), \
         patch("app.services.contradiction_service.gemini_service.generate_structured_json", return_value=mock_gemini_json):
        evaluation = await service.evaluate_contradiction(stmt_a, stmt_b)

    assert evaluation is not None
    assert evaluation.is_contradiction is True
    assert evaluation.conflict_category == "decision"
    assert "REST vs asynchronous Kafka" in evaluation.description
    assert evaluation.confidence >= 0.90


@pytest.mark.asyncio
async def test_avoid_flagging_simple_wording_differences_as_contradictions():
    """Requirement 4: Avoid flagging simple wording differences as contradictions."""
    mock_db = AsyncMock()
    service = ContradictionDetectionService(mock_db)

    # Example 1: Framework wording difference
    stmt_wording_1 = FactualStatement(
        statement="The backend service is built using FastAPI framework.",
        entity_or_topic="Core Technology Stack",
        category="technology_stack",
        document_id=uuid.uuid4(),
        document_name="readme.md",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="The backend service is built using FastAPI framework.",
    )
    stmt_wording_2 = FactualStatement(
        statement="The backend application uses Python FastAPI for its REST APIs.",
        entity_or_topic="Core Technology Stack",
        category="technology_stack",
        document_id=uuid.uuid4(),
        document_name="architecture.md",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="The backend application uses Python FastAPI for its REST APIs.",
    )

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        evaluation = await service.evaluate_contradiction(stmt_wording_1, stmt_wording_2)
    assert evaluation is None, "Simple wording variations must NOT be flagged as contradictions"

    # Example 2: Postgres wording difference
    stmt_db_1 = FactualStatement(
        statement="Primary relational data storage is PostgreSQL.",
        entity_or_topic="Database Technology",
        category="technology_stack",
        document_id=uuid.uuid4(),
        document_name="overview.md",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="Primary relational data storage is PostgreSQL.",
    )
    stmt_db_2 = FactualStatement(
        statement="The persistent database engine is Postgres 16.",
        entity_or_topic="Database Technology",
        category="technology_stack",
        document_id=uuid.uuid4(),
        document_name="db_runbook.md",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="The persistent database engine is Postgres 16.",
    )

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        eval_db = await service.evaluate_contradiction(stmt_db_1, stmt_db_2)
    assert eval_db is None, "Postgres vs PostgreSQL wording must NOT be flagged as contradiction"


@pytest.mark.asyncio
async def test_detect_conflicting_deadlines_cross_document():
    """Example 1: Different project deadlines in different documents."""
    mock_db = AsyncMock()
    service = ContradictionDetectionService(mock_db)

    stmt_a = FactualStatement(
        statement="Final hard release deadline is November 15, 2026.",
        entity_or_topic="Project Deadline",
        category="deadline",
        document_id=uuid.uuid4(),
        document_name="project_roadmap_q4.md",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="Final hard release deadline is November 15, 2026.",
    )
    stmt_b = FactualStatement(
        statement="The approved launch deadline is December 1, 2026.",
        entity_or_topic="Project Deadline",
        category="deadline",
        document_id=uuid.uuid4(),
        document_name="sprint_retro_minutes.docx",
        chunk_id=uuid.uuid4(),
        page_number=4,
        excerpt="The approved launch deadline is December 1, 2026.",
    )

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        eval_result = await service.evaluate_contradiction(stmt_a, stmt_b)

    assert eval_result is not None
    assert eval_result.is_contradiction is True
    assert eval_result.conflict_category == ConflictCategory.DEADLINE.value
    assert "project_roadmap_q4.md" in eval_result.description
    assert "sprint_retro_minutes.docx" in eval_result.description


@pytest.mark.asyncio
async def test_detect_conflicting_tech_stacks_cross_document():
    """Example 2: Different technology stacks mentioned in project documentation."""
    mock_db = AsyncMock()
    service = ContradictionDetectionService(mock_db)

    stmt_a = FactualStatement(
        statement="The core application stores all user data in PostgreSQL 16.",
        entity_or_topic="Database Technology",
        category="technology_stack",
        document_id=uuid.uuid4(),
        document_name="system_design.pdf",
        chunk_id=uuid.uuid4(),
        page_number=2,
        excerpt="The core application stores all user data in PostgreSQL 16.",
    )
    stmt_b = FactualStatement(
        statement="The database persistence layer is implemented with MongoDB Atlas.",
        entity_or_topic="Database Technology",
        category="technology_stack",
        document_id=uuid.uuid4(),
        document_name="devops_setup_guide.md",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="The database persistence layer is implemented with MongoDB Atlas.",
    )

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        eval_result = await service.evaluate_contradiction(stmt_a, stmt_b)

    assert eval_result is not None
    assert eval_result.is_contradiction is True
    assert eval_result.conflict_category == ConflictCategory.TECHNOLOGY_STACK.value
    assert "postgresql" in eval_result.description.lower()
    assert "mongodb" in eval_result.description.lower()


@pytest.mark.asyncio
async def test_detect_conflicting_task_completion_statuses():
    """Example 3: Conflicting task completion statuses across documents."""
    mock_db = AsyncMock()
    service = ContradictionDetectionService(mock_db)

    stmt_a = FactualStatement(
        statement="The OAuth2 single-sign-on integration is completed and verified in production.",
        entity_or_topic="Task Completion Status",
        category="task_status",
        document_id=uuid.uuid4(),
        document_name="handover_checklist.md",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="The OAuth2 single-sign-on integration is completed and verified in production.",
    )
    stmt_b = FactualStatement(
        statement="OAuth2 SSO authentication is currently in progress and pending security sign-off.",
        entity_or_topic="Task Completion Status",
        category="task_status",
        document_id=uuid.uuid4(),
        document_name="pending_backlog.md",
        chunk_id=uuid.uuid4(),
        page_number=3,
        excerpt="OAuth2 SSO authentication is currently in progress and pending security sign-off.",
    )

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        eval_result = await service.evaluate_contradiction(stmt_a, stmt_b)

    assert eval_result is not None
    assert eval_result.is_contradiction is True
    assert eval_result.conflict_category == ConflictCategory.TASK_STATUS.value


@pytest.mark.asyncio
async def test_detect_conflicting_team_responsibilities():
    """Example 4: Different team member responsibilities."""
    mock_db = AsyncMock()
    service = ContradictionDetectionService(mock_db)

    stmt_a = FactualStatement(
        statement="Alice is the lead engineer for the backend API and database architecture.",
        entity_or_topic="Team Responsibility",
        category="team_responsibility",
        document_id=uuid.uuid4(),
        document_name="team_charter.docx",
        chunk_id=uuid.uuid4(),
        page_number=1,
        excerpt="Alice is the lead engineer for the backend API and database architecture.",
    )
    stmt_b = FactualStatement(
        statement="Bob is the lead engineer overseeing backend API services.",
        entity_or_topic="Team Responsibility",
        category="team_responsibility",
        document_id=uuid.uuid4(),
        document_name="onboarding_guide.md",
        chunk_id=uuid.uuid4(),
        page_number=2,
        excerpt="Bob is the lead engineer overseeing backend API services.",
    )

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        eval_result = await service.evaluate_contradiction(stmt_a, stmt_b)

    assert eval_result is not None
    assert eval_result.is_contradiction is True
    assert eval_result.conflict_category == ConflictCategory.TEAM_RESPONSIBILITY.value
    assert "Alice" in eval_result.description
    assert "Bob" in eval_result.description


@pytest.mark.asyncio
async def test_conflict_model_contains_all_9_required_fields():
    """Requirement 6: Stored conflict contains all 9 mandated fields and leaves resolution unarbitrated."""
    mock_db = AsyncMock()
    service = ContradictionDetectionService(mock_db)

    doc_a_id = uuid.uuid4()
    doc_b_id = uuid.uuid4()
    project_id = uuid.uuid4()

    doc_a = Document(id=doc_a_id, original_filename="doc_release_v1.md", processing_status="READY")
    doc_b = Document(id=doc_b_id, original_filename="doc_roadmap_update.md", processing_status="READY")

    chunk_a = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_a_id,
        project_id=project_id,
        content="Final hard release deadline is November 15, 2026.",
        page_number=1,
    )
    chunk_b = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_b_id,
        project_id=project_id,
        content="The approved launch deadline is December 1, 2026.",
        page_number=2,
    )

    mock_db.execute.return_value.all.return_value = [
        (chunk_a, doc_a),
        (chunk_b, doc_b),
    ]

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        report = await service.detect_project_conflicts(project_id=project_id)

    assert report.contradictions_detected >= 1
    conflict_resp = report.conflicts[0]

    # Verify all 9 required fields
    assert conflict_resp.conflict_id is not None or conflict_resp.id is not None
    assert conflict_resp.conflict_category in ("deadline", "technology_stack", "task_status", "team_responsibility", "decision", "architecture")
    assert conflict_resp.statement_a is not None
    assert conflict_resp.statement_b is not None
    assert conflict_resp.source_document_a == "doc_release_v1.md"
    assert conflict_resp.source_document_b == "doc_roadmap_update.md"
    assert "November 15, 2026" in conflict_resp.source_excerpt_a
    assert "December 1, 2026" in conflict_resp.source_excerpt_b
    assert conflict_resp.detection_timestamp is not None
    assert conflict_resp.resolution_status in (
        ConflictResolutionStatus.UNRESOLVED.value,
        "OPEN",
    )

    # Requirement 8: Do not automatically select one statement as correct
    assert conflict_resp.resolution is None
    assert conflict_resp.resolved_by is None


@pytest.mark.asyncio
async def test_conflict_resolution_statuses_and_human_reviewer_workflow():
    """
    Requirements 7, 8, & 9:
    - Statuses: Unresolved, Under Review, Resolved, Dismissed
    - Never auto-selects statement
    - Human reviewer decides authoritative information
    """
    mock_db = AsyncMock()
    service = ContradictionDetectionService(mock_db)

    conflict_id = uuid.uuid4()
    reviewer_user = User(id=uuid.uuid4(), full_name="Lead Reviewer", email="lead@example.com")

    # Initial detected conflict is Unresolved with no auto-resolution
    conflict = Conflict(
        id=conflict_id,
        project_id=uuid.uuid4(),
        conflict_category="deadline",
        description="Release date mismatch: Nov 15 vs Dec 1.",
        statement_a="Release date is November 15, 2026.",
        statement_b="Target release pushed to December 1, 2026.",
        source_document_a_name="plan_v1.md",
        source_document_b_name="plan_v2.md",
        source_excerpt_a="Release date is November 15, 2026.",
        source_excerpt_b="Target release pushed to December 1, 2026.",
        status=ConflictResolutionStatus.UNRESOLVED.value,
        resolution_status=ConflictResolutionStatus.UNRESOLVED.value,
        resolution=None,
        resolved_by=None,
    )

    assert conflict.resolution_status == "Unresolved"
    assert conflict.resolution is None

    # Status transition to 'Under Review'
    mock_db.execute.return_value.scalars.return_value.first.return_value = conflict
    updated_conflict = await service.update_conflict_status(
        conflict_id=conflict_id,
        new_status=ConflictResolutionStatus.UNDER_REVIEW.value,
        notes="Reviewing with product management.",
        current_user=reviewer_user,
    )
    assert updated_conflict.resolution_status == "Under Review"

    # Human Reviewer decides authoritative information
    mock_db.execute.return_value.scalars.return_value.first.return_value = conflict
    resolved_conflict = await service.resolve_conflict(
        conflict_id=conflict_id,
        payload=ConflictResolveRequest(
            chosen_source="source_b",
            authoritative_value="December 1, 2026",
            resolution_notes="December 1 release was confirmed in sprint planning notes.",
            status="Resolved",
        ),
        current_user=reviewer_user,
    )

    assert resolved_conflict.resolution_status == "Resolved"
    assert resolved_conflict.resolved_by == reviewer_user.id
    assert resolved_conflict.resolution["chosen_source"] == "source_b"
    assert resolved_conflict.resolution["authoritative_value"] == "December 1, 2026"
    assert "confirmed in sprint planning" in resolved_conflict.resolution["resolution_explanation"]
    assert resolved_conflict.resolution["resolved_by_name"] == "Lead Reviewer"


def test_normalize_conflict_status_helper():
    """Validates robust normalization across upper snake case, lowercase, and title case."""
    assert normalize_conflict_status("OPEN") == ConflictResolutionStatus.UNRESOLVED.value
    assert normalize_conflict_status("unresolved") == ConflictResolutionStatus.UNRESOLVED.value
    assert normalize_conflict_status("Unresolved") == ConflictResolutionStatus.UNRESOLVED.value

    assert normalize_conflict_status("UNDER_REVIEW") == ConflictResolutionStatus.UNDER_REVIEW.value
    assert normalize_conflict_status("under review") == ConflictResolutionStatus.UNDER_REVIEW.value
    assert normalize_conflict_status("Under Review") == ConflictResolutionStatus.UNDER_REVIEW.value

    assert normalize_conflict_status("RESOLVED") == ConflictResolutionStatus.RESOLVED.value
    assert normalize_conflict_status("resolved") == ConflictResolutionStatus.RESOLVED.value
    assert normalize_conflict_status("Resolved") == ConflictResolutionStatus.RESOLVED.value

    assert normalize_conflict_status("DISMISSED") == ConflictResolutionStatus.DISMISSED.value
    assert normalize_conflict_status("dismissed") == ConflictResolutionStatus.DISMISSED.value
    assert normalize_conflict_status("Dismissed") == ConflictResolutionStatus.DISMISSED.value

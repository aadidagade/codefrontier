import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.handover import Handover, HandoverVersion
from app.models.user import User
from app.schemas.handover import (
    ContentChangeType,
    SectionDiff,
    TaskDiff,
    ResponsibilityDiff,
    ComparisonSummary,
    VersionDiffResponse,
)
from app.services.version_service import (
    HandoverVersionService,
    extract_section_text,
    resolve_canonical_category,
    CANONICAL_CATEGORIES,
)
from app.api.v1.endpoints.handovers import (
    compare_handover_versions,
    compare_handover_versions_query,
)


# =============================================================================
# 1. CANONICAL CATEGORY RESOLUTION & TEXT EXTRACTION TESTS
# =============================================================================

def test_resolve_canonical_categories():
    """
    Verifies that all 8 required categories are correctly resolved from various
    section types and titles:
    - Project overview
    - Technical architecture
    - Key decisions
    - Pending tasks
    - Risks and blockers
    - Dependencies
    - Team responsibilities
    - Recommendations
    """
    assert resolve_canonical_category("project_overview") == "project_overview"
    assert resolve_canonical_category("overview", "1. Project Overview") == "project_overview"

    assert resolve_canonical_category("technical_architecture") == "technical_architecture"
    assert resolve_canonical_category("architecture", "System Architecture") == "technical_architecture"

    assert resolve_canonical_category("important_decisions") == "key_decisions"
    assert resolve_canonical_category("key_decisions", "Key Architectural Decisions") == "key_decisions"

    assert resolve_canonical_category("pending_tasks") == "pending_tasks"
    assert resolve_canonical_category("tasks", "Action Items & Roadmap") == "pending_tasks"

    assert resolve_canonical_category("risks_and_blockers") == "risks_and_blockers"
    assert resolve_canonical_category("risks", "Project Risks") == "risks_and_blockers"

    assert resolve_canonical_category("setup_and_installation") == "dependencies"
    assert resolve_canonical_category("dependencies", "System Dependencies") == "dependencies"

    assert resolve_canonical_category("team_responsibilities") == "team_responsibilities"
    assert resolve_canonical_category("roles", "Team Roles and Responsibilities") == "team_responsibilities"

    assert resolve_canonical_category("recommended_next_actions") == "recommendations"
    assert resolve_canonical_category("recommendations", "Long-term Recommendations") == "recommendations"


def test_extract_section_text_formats():
    """Verifies text extraction across plain strings, markdown objects, and structured dictionaries."""
    assert extract_section_text(None) == ""
    assert extract_section_text({}) == ""
    assert extract_section_text({"content": "Plain text content"}) == "Plain text content"
    assert extract_section_text({"content": {"markdown": "# Heading\nParagraph text"}}) == "# Heading\nParagraph text"
    assert "Executive Summary" in extract_section_text({"content": {"summary": "Executive Summary", "structured_data": {"port": 5432}}})


# =============================================================================
# 2. COMPARISON ENGINE: ALL 8 CHAPTERS COMPARED USING STORED VERSIONS
# =============================================================================

@pytest.mark.asyncio
async def test_compare_all_eight_core_chapters():
    """
    Validates that the comparison engine compares all 8 explicit categories:
    1. Project overview
    2. Technical architecture
    3. Key decisions
    4. Pending tasks
    5. Risks and blockers
    6. Dependencies
    7. Team responsibilities
    8. Recommendations
    and correctly marks modified, added, removed, and unchanged categories.
    """
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()

    # Stored Version 1 (Baseline)
    v1_snapshot = {
        "title": "Cloud Platform Handover v1",
        "assigned_to": "alice-lead-uuid",
        "sections": [
            {"section_type": "project_overview", "title": "1. Project Overview", "content": "Payment platform handling 1k tps."},
            {"section_type": "technical_architecture", "title": "2. Technical Architecture", "content": "FastAPI + Postgres 15."},
            {"section_type": "important_decisions", "title": "4. Important Decisions", "content": "ADR 1: Use gRPC for inter-service."},
            {"section_type": "pending_tasks", "title": "5. Pending Tasks", "content": "Task list in section content."},
            {"section_type": "risks_and_blockers", "title": "7. Risks and Blockers", "content": "Risk 1: Redis cache single point of failure."},
            {"section_type": "setup_and_installation", "title": "3. Setup and Installation", "content": "Docker compose up -d."},
            {"section_type": "team_responsibilities", "title": "Team Responsibilities", "content": "Alice: Backend, Bob: DevOps."},
            {"section_type": "recommended_next_actions", "title": "10. Recommended Next Actions", "content": "Migrate to Kubernetes."},
        ],
        "tasks": [
            {"id": "task-1", "title": "Setup Redis Sentinel", "status": "pending", "assigned_to": "alice-lead-uuid"},
            {"id": "task-2", "title": "Load Test Gateway", "status": "pending", "assigned_to": "bob-devops-uuid"},
        ],
    }

    # Stored Version 2 (Revised)
    v2_snapshot = {
        "title": "Cloud Platform Handover v2",
        "assigned_to": "bob-devops-uuid",  # Changed handover assignee!
        "sections": [
            {"section_type": "project_overview", "title": "1. Project Overview", "content": "Payment platform handling 50k tps."},  # MODIFIED
            {"section_type": "technical_architecture", "title": "2. Technical Architecture", "content": "FastAPI + Postgres 16 + Redis Cluster."},  # MODIFIED
            {"section_type": "important_decisions", "title": "4. Important Decisions", "content": "ADR 1: Use gRPC for inter-service.\nADR 2: Adopt Kafka."},  # MODIFIED
            {"section_type": "pending_tasks", "title": "5. Pending Tasks", "content": "Task list updated."},  # MODIFIED
            {"section_type": "risks_and_blockers", "title": "7. Risks and Blockers", "content": "Risk 1: Redis cache single point of failure."},  # UNCHANGED
            {"section_type": "setup_and_installation", "title": "3. Setup and Installation", "content": "Docker compose up -d."},  # UNCHANGED
            {"section_type": "team_responsibilities", "title": "Team Responsibilities", "content": "Bob: Lead Architect, Charlie: Backend."},  # MODIFIED
            {"section_type": "recommended_next_actions", "title": "10. Recommended Next Actions", "content": "Migrate to EKS in Q2."},  # MODIFIED
        ],
        "tasks": [
            {"id": "task-1", "title": "Setup Redis Sentinel", "status": "completed", "assigned_to": "alice-lead-uuid"},  # STATUS CHANGED!
            {"id": "task-2", "title": "Load Test Gateway", "status": "in_progress", "assigned_to": "charlie-dev-uuid"},  # REASSIGNED & STATUS!
            {"id": "task-3", "title": "Configure Prometheus", "status": "pending", "assigned_to": "bob-devops-uuid"},  # NEW TASK!
        ],
    }

    v1 = HandoverVersion(id=v1_id, handover_id=handover_id, version_number="v1.0", snapshot=v1_snapshot)
    v2 = HandoverVersion(id=v2_id, handover_id=handover_id, version_number="v2.0", snapshot=v2_snapshot)

    service = HandoverVersionService(mock_db)
    with patch.object(service, "get_version", side_effect=[v1, v2]):
        diff = await service.compare_versions(handover_id, v1_id, v2_id)

    # 1. Basic Metadata
    assert diff.from_version_number == "v1.0"
    assert diff.to_version_number == "v2.0"
    assert len(diff.section_diffs) == 8

    # 2. Canonical Category Status Mapping
    cat_status = diff.summary.category_status
    assert cat_status["project_overview"] == "MODIFIED"
    assert cat_status["technical_architecture"] == "MODIFIED"
    assert cat_status["key_decisions"] == "MODIFIED"
    assert cat_status["pending_tasks"] == "MODIFIED"
    assert cat_status["risks_and_blockers"] == "UNCHANGED"
    assert cat_status["dependencies"] == "UNCHANGED"
    assert cat_status["team_responsibilities"] == "MODIFIED"
    assert cat_status["recommendations"] == "MODIFIED"

    # 3. Summary Counters
    assert diff.summary.total_sections_compared == 8
    assert diff.summary.modified_sections_count == 6
    assert diff.summary.unchanged_sections_count == 2
    assert diff.summary.has_differences is True


# =============================================================================
# 3. IDENTIFY ADDED, REMOVED, AND MODIFIED CONTENT
# =============================================================================

@pytest.mark.asyncio
async def test_identify_added_and_removed_chapters():
    """Verifies detection of entirely added or removed chapters between stored snapshots."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()

    v1_snapshot = {
        "sections": [
            {"section_type": "architecture", "title": "Architecture", "content": "Microservices"},
            {"section_type": "legacy_notes", "title": "Legacy Notes", "content": "Old system notes that should be deleted."},
        ]
    }

    v2_snapshot = {
        "sections": [
            {"section_type": "architecture", "title": "Architecture", "content": "Microservices"},
            {"section_type": "security_guidelines", "title": "Security Guidelines", "content": "New chapter: OAuth2 & TLS 1.3 enforced."},
        ]
    }

    v1 = HandoverVersion(id=v1_id, handover_id=handover_id, version_number="v1.0", snapshot=v1_snapshot)
    v2 = HandoverVersion(id=v2_id, handover_id=handover_id, version_number="v1.1", snapshot=v2_snapshot)

    service = HandoverVersionService(mock_db)
    with patch.object(service, "get_version", side_effect=[v1, v2]):
        diff = await service.compare_versions(handover_id, v1_id, v2_id)

    # Legacy notes was removed
    rem_diff = next(d for d in diff.section_diffs if d.section_type == "legacy_notes")
    assert rem_diff.change_type == ContentChangeType.REMOVED.value
    assert rem_diff.has_changed is True
    assert rem_diff.new_content is None
    assert "Old system notes" in rem_diff.old_content

    # Security guidelines was added
    add_diff = next(d for d in diff.section_diffs if d.section_type == "security_guidelines")
    assert add_diff.change_type == ContentChangeType.ADDED.value
    assert add_diff.has_changed is True
    assert add_diff.old_content is None
    assert "OAuth2 & TLS 1.3" in add_diff.new_content

    # Architecture unchanged
    arch_diff = next(d for d in diff.section_diffs if d.section_type == "architecture")
    assert arch_diff.change_type == ContentChangeType.UNCHANGED.value
    assert arch_diff.has_changed is False

    assert diff.summary.added_sections_count == 1
    assert diff.summary.removed_sections_count == 1
    assert diff.summary.unchanged_sections_count == 1


@pytest.mark.asyncio
async def test_identify_modified_content_line_level_diff():
    """Verifies detailed line-level diff capturing added and removed lines within a chapter."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()

    old_text = "Step 1: Clone repo\nStep 2: Run npm start\nStep 3: Connect to MySQL"
    new_text = "Step 1: Clone repo\nStep 2: Run docker compose up\nStep 3: Connect to PostgreSQL\nStep 4: Verify metrics"

    v1_snapshot = {"sections": [{"section_type": "setup", "title": "Setup", "content": old_text}]}
    v2_snapshot = {"sections": [{"section_type": "setup", "title": "Setup", "content": new_text}]}

    v1 = HandoverVersion(id=v1_id, handover_id=handover_id, version_number="v1.0", snapshot=v1_snapshot)
    v2 = HandoverVersion(id=v2_id, handover_id=handover_id, version_number="v1.1", snapshot=v2_snapshot)

    service = HandoverVersionService(mock_db)
    with patch.object(service, "get_version", side_effect=[v1, v2]):
        diff = await service.compare_versions(handover_id, v1_id, v2_id)

    setup_diff = diff.section_diffs[0]
    assert setup_diff.change_type == ContentChangeType.MODIFIED.value
    assert setup_diff.has_changed is True
    assert "Step 2: Run docker compose up" in setup_diff.added_lines
    assert "Step 4: Verify metrics" in setup_diff.added_lines
    assert "Step 2: Run npm start" in setup_diff.removed_lines
    assert "Step 3: Connect to MySQL" in setup_diff.removed_lines
    assert "lines added" in setup_diff.diff_summary


# =============================================================================
# 4. IDENTIFY CHANGED TASK STATUSES & CHANGED RESPONSIBILITIES
# =============================================================================

@pytest.mark.asyncio
async def test_identify_changed_task_statuses():
    """Verifies identification of task status transitions (e.g. pending -> completed)."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()

    v1_snapshot = {
        "sections": [],
        "tasks": [
            {"id": "t1", "title": "Implement RBAC", "status": "pending", "assigned_to": "user-1"},
            {"id": "t2", "title": "Database Migration", "status": "in_progress", "assigned_to": "user-2"},
        ],
    }

    v2_snapshot = {
        "sections": [],
        "tasks": [
            {"id": "t1", "title": "Implement RBAC", "status": "completed", "assigned_to": "user-1"},  # Completed!
            {"id": "t2", "title": "Database Migration", "status": "in_progress", "assigned_to": "user-2"},  # Unchanged
        ],
    }

    v1 = HandoverVersion(id=v1_id, handover_id=handover_id, version_number="v1.0", snapshot=v1_snapshot)
    v2 = HandoverVersion(id=v2_id, handover_id=handover_id, version_number="v1.1", snapshot=v2_snapshot)

    service = HandoverVersionService(mock_db)
    with patch.object(service, "get_version", side_effect=[v1, v2]):
        diff = await service.compare_versions(handover_id, v1_id, v2_id)

    t1_diff = next(t for t in diff.task_diffs if t.task_id == "t1")
    assert t1_diff.status_changed is True
    assert t1_diff.old_status == "pending"
    assert t1_diff.new_status == "completed"
    assert t1_diff.change_type == ContentChangeType.MODIFIED.value

    t2_diff = next(t for t in diff.task_diffs if t.task_id == "t2")
    assert t2_diff.status_changed is False
    assert t2_diff.change_type == ContentChangeType.UNCHANGED.value

    assert diff.summary.task_status_changes_count == 1


@pytest.mark.asyncio
async def test_identify_changed_responsibilities():
    """
    Verifies detection of changed responsibilities:
    - Task reassigned from User A to User B
    - New task assigned to User C
    - Overall handover lead transfer
    """
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()

    v1_snapshot = {
        "assigned_to": "outgoing-lead-uuid",
        "sections": [],
        "tasks": [
            {"id": "task-auth", "title": "Auth Setup", "status": "pending", "assigned_to": "outgoing-lead-uuid"},
            {"id": "task-docs", "title": "Documentation", "status": "pending", "assigned_to": "charlie-uuid"},
        ],
    }

    v2_snapshot = {
        "assigned_to": "incoming-lead-uuid",  # Handover lead transferred!
        "sections": [],
        "tasks": [
            {"id": "task-auth", "title": "Auth Setup", "status": "pending", "assigned_to": "incoming-lead-uuid"},  # Reassigned!
            # task-docs was removed (unassigned)!
            {"id": "task-infra", "title": "Infra Provisioning", "status": "pending", "assigned_to": "devops-uuid"},  # Newly assigned!
        ],
    }

    v1 = HandoverVersion(id=v1_id, handover_id=handover_id, version_number="v1.0", snapshot=v1_snapshot)
    v2 = HandoverVersion(id=v2_id, handover_id=handover_id, version_number="v1.1", snapshot=v2_snapshot)

    service = HandoverVersionService(mock_db)
    with patch.object(service, "get_version", side_effect=[v1, v2]):
        diff = await service.compare_versions(handover_id, v1_id, v2_id)

    # 1. Task responsibility changes
    resp_diffs = diff.responsibility_diffs
    assert len(resp_diffs) >= 3

    auth_resp = next(r for r in resp_diffs if r.entity_name == "Auth Setup")
    assert auth_resp.change_type == "REASSIGNED"
    assert auth_resp.old_assignee == "outgoing-lead-uuid"
    assert auth_resp.new_assignee == "incoming-lead-uuid"

    infra_resp = next(r for r in resp_diffs if r.entity_name == "Infra Provisioning")
    assert infra_resp.change_type == "ASSIGNED"
    assert infra_resp.new_assignee == "devops-uuid"

    # 2. Handover overall assignee transfer
    handover_resp = next(r for r in resp_diffs if r.entity_type == "handover")
    assert handover_resp.change_type == "REASSIGNED"
    assert handover_resp.old_assignee == "outgoing-lead-uuid"
    assert handover_resp.new_assignee == "incoming-lead-uuid"


# =============================================================================
# 5. IMMUTABLE STORED VERSIONS GUARANTEE (NO AI REGENERATION)
# =============================================================================

@pytest.mark.asyncio
async def test_comparison_uses_stored_snapshots_without_ai():
    """
    Requirement:
    Ensure comparison uses actual stored versions rather than regenerated AI content.
    No calls to GeminiService, RAGService, or external APIs are made.
    """
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()

    stored_v1 = HandoverVersion(
        id=v1_id,
        handover_id=handover_id,
        version_number="v1.0",
        snapshot={"sections": [{"section_type": "overview", "title": "Overview", "content": "Frozen v1 Snapshot"}]},
    )
    stored_v2 = HandoverVersion(
        id=v2_id,
        handover_id=handover_id,
        version_number="v1.1",
        snapshot={"sections": [{"section_type": "overview", "title": "Overview", "content": "Frozen v2 Snapshot"}]},
    )

    service = HandoverVersionService(mock_db)

    with patch("app.services.rag_service.RAGService") as mock_rag, \
         patch("app.services.gemini_service.GeminiService") as mock_gemini, \
         patch.object(service, "get_version", side_effect=[stored_v1, stored_v2]):

        diff = await service.compare_versions(handover_id, v1_id, v2_id)

        # Verify AI services were NEVER called
        assert mock_rag.call_count == 0
        assert mock_gemini.call_count == 0

    assert diff.from_version_number == "v1.0"
    assert diff.to_version_number == "v1.1"
    assert diff.section_diffs[0].old_content == "Frozen v1 Snapshot"
    assert diff.section_diffs[0].new_content == "Frozen v2 Snapshot"


# =============================================================================
# 6. VERSION COMPARISON BY VERSION NUMBER STRING
# =============================================================================

@pytest.mark.asyncio
async def test_compare_by_version_numbers_string():
    """Verifies compare_versions resolves version number strings (e.g. 'v1.0' and 'v1.1')."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()

    v1 = HandoverVersion(id=uuid.uuid4(), handover_id=handover_id, version_number="v1.0", snapshot={"sections": []})
    v2 = HandoverVersion(id=uuid.uuid4(), handover_id=handover_id, version_number="v1.1", snapshot={"sections": []})

    service = HandoverVersionService(mock_db)
    with patch.object(service, "get_version_by_number", side_effect=[v1, v2]):
        diff = await service.compare_versions(handover_id, "v1.0", "v1.1")

    assert diff.from_version_number == "v1.0"
    assert diff.to_version_number == "v1.1"


# =============================================================================
# 7. PERMISSION & API ENDPOINT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_compare_versions_endpoint_path_based():
    """Verifies path-based comparison endpoint returns ApiResponse[VersionDiffResponse]."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()
    handover = Handover(id=handover_id, project_id=uuid.uuid4())
    user = User(id=uuid.uuid4(), email="lead@company.com")

    v1 = HandoverVersion(id=v1_id, handover_id=handover_id, version_number="v1.0", snapshot={"sections": []})
    v2 = HandoverVersion(id=v2_id, handover_id=handover_id, version_number="v1.1", snapshot={"sections": []})

    with patch.object(HandoverVersionService, "get_version", side_effect=[v1, v2]):
        res = await compare_handover_versions(
            handover_id=handover_id,
            from_version_id=v1_id,
            to_version_id=v2_id,
            handover=handover,
            current_user=user,
            db=mock_db,
        )

    assert res.data.from_version_number == "v1.0"
    assert res.data.to_version_number == "v1.1"
    assert "Successfully compared" in res.message


@pytest.mark.asyncio
async def test_compare_versions_endpoint_query_based():
    """Verifies query-based comparison endpoint (e.g. ?from_version=v1.0&to_version=v1.1)."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    handover = Handover(id=handover_id, project_id=uuid.uuid4())
    user = User(id=uuid.uuid4(), email="lead@company.com")

    v1 = HandoverVersion(id=uuid.uuid4(), handover_id=handover_id, version_number="v1.0", snapshot={"sections": []})
    v2 = HandoverVersion(id=uuid.uuid4(), handover_id=handover_id, version_number="v1.1", snapshot={"sections": []})

    with patch.object(HandoverVersionService, "get_version_by_number", side_effect=[v1, v2]):
        res = await compare_handover_versions_query(
            handover_id=handover_id,
            from_version="v1.0",
            to_version="v1.1",
            handover=handover,
            current_user=user,
            db=mock_db,
        )

    assert res.data.from_version_number == "v1.0"
    assert res.data.to_version_number == "v1.1"


@pytest.mark.asyncio
async def test_compare_versions_non_existent_version_raises_404():
    """Verifies attempting to compare with a non-existent version raises NotFoundException."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v_missing_id = uuid.uuid4()

    v1 = HandoverVersion(id=v1_id, handover_id=handover_id, version_number="v1.0", snapshot={"sections": []})

    service = HandoverVersionService(mock_db)
    with patch.object(service, "get_version", side_effect=[v1, NotFoundException("HandoverVersion", v_missing_id)]):
        with pytest.raises(NotFoundException):
            await service.compare_versions(handover_id, v1_id, v_missing_id)

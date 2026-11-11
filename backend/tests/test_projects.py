import uuid
import pytest
from app.models.project import ProjectMemberRole
from app.schemas.project import ProjectCreate, ProjectUpdate, MemberAdd, MemberUpdateRole


def test_project_create_schema_validation():
    """Verifies that project create schema enforces minimum name length."""
    valid = ProjectCreate(name="Core Payment Engine", description="Gateway")
    assert valid.name == "Core Payment Engine"
    assert valid.description == "Gateway"

    with pytest.raises(Exception):
        ProjectCreate(name="")


def test_member_role_assignment_schemas():
    """Verifies member addition and update schemas."""
    add_req = MemberAdd(email="engineer@company.internal", role=ProjectMemberRole.OUTGOING)
    assert add_req.role == ProjectMemberRole.OUTGOING
    assert add_req.email == "engineer@company.internal"

    update_req = MemberUpdateRole(role=ProjectMemberRole.LEAD)
    assert update_req.role == ProjectMemberRole.LEAD


def test_project_overview_schema_defaults():
    """Validates structure of ProjectOverviewResponse."""
    from app.schemas.project import ProjectOverviewResponse, ProjectResponse

    proj_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now_dt = pytest.importorskip("datetime").datetime.now(pytest.importorskip("datetime").timezone.utc)

    proj = ProjectResponse(
        id=proj_id,
        name="Test Project",
        status="active",
        created_by=user_id,
        created_at=now_dt,
        updated_at=now_dt,
    )

    overview = ProjectOverviewResponse(
        project=proj,
        members=[],
        total_members=0,
        total_documents=5,
        processed_documents=3,
        total_handovers=1,
        pending_reviews=1,
        open_conflicts=2,
        pending_tasks=4,
        overall_handover_status="in_review",
    )

    assert overview.total_documents == 5
    assert overview.processed_documents == 3
    assert overview.pending_reviews == 1
    assert overview.open_conflicts == 2
    assert overview.overall_handover_status == "in_review"

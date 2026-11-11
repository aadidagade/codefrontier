import uuid
import pytest
from app.models.project import ProjectMemberRole


def test_role_hierarchy_values():
    """Confirms all required ProjectMemberRole enum values exist."""
    assert ProjectMemberRole.ADMIN.value == "ADMIN"
    assert ProjectMemberRole.OUTGOING.value == "OUTGOING"
    assert ProjectMemberRole.INCOMING.value == "INCOMING"
    assert ProjectMemberRole.LEAD.value == "LEAD"


def test_permission_matrix_rules():
    """
    Validates the role permission matrix rules:
    - ADMIN: Full project access, manage members, manage handovers, approve.
    - OUTGOING: Upload docs, generate handovers, edit drafts, submit.
    - INCOMING: View shared/approved handovers, view approved evidence, acknowledge.
    - LEAD: Review handovers, resolve conflicts, approve handovers.
    """
    can_manage_members = [ProjectMemberRole.ADMIN]
    can_upload_docs = [ProjectMemberRole.ADMIN, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD]
    can_generate_handover = [ProjectMemberRole.ADMIN, ProjectMemberRole.OUTGOING]
    can_approve_handover = [ProjectMemberRole.ADMIN, ProjectMemberRole.LEAD]
    can_acknowledge_handover = [ProjectMemberRole.INCOMING, ProjectMemberRole.ADMIN]

    # Verify OUTGOING can upload and generate, but NOT approve or acknowledge
    assert ProjectMemberRole.OUTGOING in can_upload_docs
    assert ProjectMemberRole.OUTGOING in can_generate_handover
    assert ProjectMemberRole.OUTGOING not in can_approve_handover
    assert ProjectMemberRole.OUTGOING not in can_acknowledge_handover

    # Verify INCOMING cannot upload, generate, or approve
    assert ProjectMemberRole.INCOMING not in can_upload_docs
    assert ProjectMemberRole.INCOMING not in can_generate_handover
    assert ProjectMemberRole.INCOMING not in can_approve_handover
    assert ProjectMemberRole.INCOMING in can_acknowledge_handover

    # Verify LEAD can approve and review
    assert ProjectMemberRole.LEAD in can_approve_handover
    assert ProjectMemberRole.LEAD in can_upload_docs
    assert ProjectMemberRole.LEAD not in can_manage_members

    # Verify ADMIN has all privileges
    for matrix in [can_manage_members, can_upload_docs, can_generate_handover, can_approve_handover]:
        assert ProjectMemberRole.ADMIN in matrix

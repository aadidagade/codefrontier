import uuid
import pytest
from app.models.user import User, RefreshToken
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.document import Document, DocumentChunk
from app.models.handover import Handover, HandoverSection, HandoverVersion, HandoverAuditLog
from app.models.evidence import EvidenceReference
from app.models.conflict import Conflict
from app.models.task import Task, TaskDependency
from app.models.notification import Notification


def test_user_model_attributes():
    user = User(
        full_name="Elena Rostova",
        email="elena@company.internal",
        password_hash="argon2_hashed_secret",
    )
    assert user.full_name == "Elena Rostova"
    assert user.email == "elena@company.internal"
    assert user.is_active is True


def test_project_member_role_values():
    assert ProjectMemberRole.ADMIN.value == "ADMIN"
    assert ProjectMemberRole.OUTGOING.value == "OUTGOING"
    assert ProjectMemberRole.INCOMING.value == "INCOMING"
    assert ProjectMemberRole.LEAD.value == "LEAD"


def test_document_and_chunk_structure():
    doc_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        project_id=proj_id,
        original_filename="Architecture_Spec.pdf",
        stored_filename=f"{doc_id}.pdf",
        file_type="pdf",
        file_size=1048576,
        storage_path=f"storage/uploads/{doc_id}.pdf",
        processing_status="ready",
    )
    chunk = DocumentChunk(
        document_id=doc_id,
        project_id=proj_id,
        chunk_index=0,
        content="Payment router failover architecture chunk.",
        page_number=1,
    )
    assert doc.original_filename == "Architecture_Spec.pdf"
    assert chunk.chunk_index == 0


def test_handover_and_evidence_models():
    handover_id = uuid.uuid4()
    section_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    section = HandoverSection(
        id=section_id,
        handover_id=handover_id,
        section_type="decisions",
        title="Key Architectural Decisions",
        content={"decisions": ["Kafka settlement retention"]},
        confidence=0.98,
        review_status="approved",
    )
    evidence = EvidenceReference(
        handover_section_id=section_id,
        document_id=doc_id,
        quoted_text="Kafka retention policy 14 days",
        relevance_score=0.95,
        verification_status="supported",
    )
    assert section.section_type == "decisions"
    assert evidence.verification_status == "supported"


def test_task_dependency_constraint_model():
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()
    dep = TaskDependency(task_id=t1, depends_on_task_id=t2)
    assert dep.task_id != dep.depends_on_task_id

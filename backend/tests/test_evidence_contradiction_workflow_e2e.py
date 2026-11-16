"""
End-to-End Workflow Test Suite for Evidence Verification and Contradiction Detection.

Validates the complete workflow with sample documents containing:
1. Consistent project information across documents.
2. Two different project deadlines.
3. Two conflicting technology decisions.
4. Missing information.
5. Unsupported AI-generated claims.

Verifications:
1. Gemini generates the handover (RAGService.synthesize_handover).
2. The verification engine checks generated claims section by section.
3. Source references (document name, ID, excerpts, page numbers) are correctly attached.
4. Contradictions are detected across documents (deadlines, technology decisions).
5. Reviewers can resolve conflicts (authoritative statement + resolution explanation).
6. Resolutions persist after database refresh/re-query.
7. Existing handover generation and section regeneration continue working.
"""

import json
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.document import Document, DocumentChunk
from app.models.handover import Handover, HandoverSection
from app.models.evidence import EvidenceReference, ClaimVerification
from app.models.conflict import Conflict
from app.schemas.handover import (
    GenerationRequest,
    HandoverAIGenerationOutput,
    GeneratedSection,
    SectionContent,
    FactualClaim,
    Recommendation,
    EvidenceStatus,
    normalize_verification_status,
)
from app.schemas.conflict import (
    ConflictCategory,
    ConflictResolutionStatus,
    ConflictResolveRequest,
    ConflictUpdateRequest,
    normalize_conflict_status,
)
from app.services.rag_service import RAGService
from app.services.verification_service import EvidenceVerificationService
from app.services.contradiction_service import ContradictionDetectionService
from app.services.gemini_service import gemini_service
from app.core.config import Settings, settings


# =============================================================================
# WORKFLOW TEST FIXTURE & SAMPLE DOCUMENTS
# =============================================================================

@pytest.fixture
def workflow_setup():
    """Sets up sample project, users, and documents with consistent, conflicting, and missing data."""
    user_id = uuid.uuid4()
    lead_user = User(
        id=user_id,
        email="lead.reviewer@enterprise.com",
        full_name="Dr. Alex Vance",
        is_active=True,
    )

    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name="Project Nexus Gateway",
        description="Enterprise event streaming and payment gateway platform",
        created_by=user_id,
    )

    # Document A: Architecture & Initial Planning
    doc_a_id = uuid.uuid4()
    doc_a = Document(
        id=doc_a_id,
        project_id=project_id,
        original_filename="spec_v1_architecture.md",
        stored_filename=f"{doc_a_id}.md",
        file_type="md",
        file_size=1024,
        storage_path=f"/storage/{doc_a_id}.md",
        processing_status="ready",
    )

    # Chunk A1: Consistent project info + Deadline A (October 15, 2026)
    chunk_a1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_a_id,
        chunk_index=0,
        page_number=1,
        content=(
            "Project Nexus is an enterprise distributed event processing gateway designed for 99.999% system availability. "
            "The official project deadline for the production cutover is October 15, 2026. "
            "All core transaction routing services must be completed prior to this date."
        ),
    )

    # Chunk A2: Technology Decision A (Redis Cluster) + Missing info note
    chunk_a2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_a_id,
        chunk_index=1,
        page_number=2,
        content=(
            "The primary distributed caching and session store is Redis Cluster v7.2 deployed on AWS ElastiCache. "
            "Connection pools are pre-warmed to handle 50,000 requests per second. "
            "Disaster recovery runbook and failover contact lists are currently being drafted."
        ),
    )

    # Document B: Sprint Planning & Updated Decisions
    doc_b_id = uuid.uuid4()
    doc_b = Document(
        id=doc_b_id,
        project_id=project_id,
        original_filename="sprint_planning_update_v2.md",
        stored_filename=f"{doc_b_id}.md",
        file_type="md",
        file_size=1024,
        storage_path=f"/storage/{doc_b_id}.md",
        processing_status="ready",
    )

    # Chunk B1: Consistent project info + Deadline B (November 30, 2026)
    chunk_b1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_b_id,
        chunk_index=0,
        page_number=1,
        content=(
            "Project Nexus is an enterprise distributed event processing gateway designed for 99.999% system availability. "
            "Due to downstream banking API certification delays, the project deadline for the production cutover has been postponed to November 30, 2026. "
            "This extends the QA hardening cycle by six weeks."
        ),
    )

    # Chunk B2: Technology Decision B (Apache Ignite)
    chunk_b2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_b_id,
        chunk_index=1,
        page_number=2,
        content=(
            "The caching layer has been re-architected to Apache Ignite in-memory data grid to support distributed ACID transactions. "
            "Redis was replaced due to split-brain consistency limitations in multi-datacenter replication."
        ),
    )

    chunks_all = [
        (chunk_a1, doc_a),
        (chunk_a2, doc_a),
        (chunk_b1, doc_b),
        (chunk_b2, doc_b),
    ]

    return {
        "lead_user": lead_user,
        "project": project,
        "doc_a": doc_a,
        "doc_b": doc_b,
        "chunk_a1": chunk_a1,
        "chunk_a2": chunk_a2,
        "chunk_b1": chunk_b1,
        "chunk_b2": chunk_b2,
        "chunks_all": chunks_all,
    }


# =============================================================================
# E2E WORKFLOW TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_complete_evidence_and_contradiction_workflow(workflow_setup):
    """
    Executes the entire end-to-end workflow:
    1. Gemini synthesizes handover.
    2. Verification engine analyzes claims section-by-section.
    3. Source references are correctly attached to supported claims.
    4. Unsupported AI-generated claim is detected as Unsupported.
    5. Contradictions are detected across documents (Deadlines & Tech Decisions).
    6. Reviewer arbitrates and resolves conflict.
    7. Resolution persists upon re-query.
    8. Existing handover generation remains fully operational.
    """
    ctx = workflow_setup
    project_id = ctx["project"].id
    user_id = ctx["lead_user"].id

    mock_db = AsyncMock()

    # In-memory storage simulating DB tables
    db_store = {
        "handovers": {},
        "sections": {},
        "claims": {},
        "evidence_refs": {},
        "conflicts": {},
    }

    def db_add(obj):
        if isinstance(obj, Handover):
            db_store["handovers"][obj.id] = obj
        elif isinstance(obj, HandoverSection):
            db_store["sections"][obj.id] = obj
        elif isinstance(obj, ClaimVerification):
            db_store["claims"][obj.claim_id] = obj
        elif isinstance(obj, EvidenceReference):
            db_store["evidence_refs"][obj.id] = obj
        elif isinstance(obj, Conflict):
            db_store["conflicts"][obj.id] = obj

    mock_db.add = MagicMock(side_effect=db_add)
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    # -------------------------------------------------------------------------
    # STEP 1: GEMINI GENERATES THE HANDOVER
    # -------------------------------------------------------------------------
    rag_service = RAGService(mock_db)

    # Mock chunk retrieval for RAG
    chunk_map = {
        str(ctx["chunk_a1"].id): (ctx["chunk_a1"], ctx["doc_a"]),
        str(ctx["chunk_a2"].id): (ctx["chunk_a2"], ctx["doc_a"]),
        str(ctx["chunk_b1"].id): (ctx["chunk_b1"], ctx["doc_b"]),
        str(ctx["chunk_b2"].id): (ctx["chunk_b2"], ctx["doc_b"]),
    }
    corpus_text = "\n\n".join([f"[{c.id}] {c.content}" for c, _ in ctx["chunks_all"]])

    rag_service._retrieve_category_targeted_evidence = AsyncMock(
        return_value=(corpus_text, chunk_map)
    )

    # Structured claim texts
    supported_claim_1_text = (
        "Project Nexus is an enterprise distributed event processing gateway designed for 99.999% system availability."
    )
    supported_claim_2_text = (
        "The caching layer has been re-architected to Apache Ignite in-memory data grid."
    )
    unsupported_ai_claim_text = (
        "Project Nexus utilizes experimental quantum-resistant homomorphic encryption modules supplied by IBM Quantum Labs."
    )

    mock_gemini_handover_output = {
        "title": "Project Nexus Architecture & Handover",
        "sections": [
            {
                "section_type": "project_overview",
                "title": "1. Project Overview",
                "content": {
                    "summary": "Project Nexus provides highly available distributed event routing.",
                    "details": "Platform SLA targets 99.999% uptime with multi-region failover.",
                    "claims": [
                        {
                            "claim_id": "claim-nexus-01",
                            "statement": supported_claim_1_text,
                            "source_document_ids": [str(ctx["doc_a"].id)],
                            "source_chunk_ids": [str(ctx["chunk_a1"].id)],
                            "page_numbers": [1],
                            "quoted_text": "Project Nexus is an enterprise distributed event processing gateway designed for 99.999% system availability.",
                            "evidence_status": "SUPPORTED",
                        },
                        {
                            "claim_id": "claim-nexus-unsupported",
                            "statement": unsupported_ai_claim_text,
                            "source_document_ids": [],
                            "source_chunk_ids": [],
                            "page_numbers": [],
                            "quoted_text": "",
                            "evidence_status": "UNSUPPORTED",
                        },
                    ],
                    "recommendations": [
                        {
                            "recommendation_id": "rec-1",
                            "title": "Finalize disaster recovery RTO and failover runbooks",
                            "description": "Disaster recovery runbook is still being drafted; establish emergency failover metrics.",
                            "timeframe": "immediate",
                            "is_recommendation": True,
                        }
                    ],
                },
            },
            {
                "section_type": "technical_architecture",
                "title": "2. Technical Architecture",
                "content": {
                    "summary": "Distributed event streaming and caching topology.",
                    "details": "Apache Ignite in-memory grid provides distributed caching.",
                    "claims": [
                        {
                            "claim_id": "claim-nexus-02",
                            "statement": supported_claim_2_text,
                            "source_document_ids": [str(ctx["doc_b"].id)],
                            "source_chunk_ids": [str(ctx["chunk_b2"].id)],
                            "page_numbers": [2],
                            "quoted_text": "The caching layer has been re-architected to Apache Ignite in-memory data grid to support distributed ACID transactions.",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": [],
                },
            },
            {
                "section_type": "setup_and_installation",
                "title": "3. Setup and Installation",
                "content": {"summary": "Setup instructions", "details": "Run docker compose up", "claims": [], "recommendations": []},
            },
            {
                "section_type": "important_decisions",
                "title": "4. Important Decisions",
                "content": {"summary": "Key architecture choices", "details": "Ignite selected over Redis", "claims": [], "recommendations": []},
            },
            {
                "section_type": "pending_tasks",
                "title": "5. Pending Tasks",
                "content": {"summary": "Remaining tasks", "details": "QA hardening cycle", "claims": [], "recommendations": []},
            },
            {
                "section_type": "known_issues",
                "title": "6. Known Issues",
                "content": {"summary": "Open defects", "details": "None critical", "claims": [], "recommendations": []},
            },
            {
                "section_type": "risks_and_blockers",
                "title": "7. Risks and Blockers",
                "content": {"summary": "Identified risks", "details": "Downstream banking API delays", "claims": [], "recommendations": []},
            },
            {
                "section_type": "deployment_and_maintenance",
                "title": "8. Deployment and Maintenance",
                "content": {"summary": "Deployment runbook", "details": "Blue-green deployment", "claims": [], "recommendations": []},
            },
            {
                "section_type": "open_questions",
                "title": "9. Open Questions",
                "content": {"summary": "Unresolved questions", "details": "Disaster recovery RTO not defined", "claims": [], "recommendations": []},
            },
            {
                "section_type": "recommended_next_actions",
                "title": "10. Recommended Next Actions",
                "content": {"summary": "Next steps", "details": "Sign off on cutover date", "claims": [], "recommendations": []},
            },
        ],
        "conflicts": [],
        "tasks": [],
    }

    with patch.object(gemini_service, "generate_content", return_value=json.dumps(mock_gemini_handover_output)):
        gen_req = GenerationRequest(
            projectId=project_id,
            title="Project Nexus Architecture & Handover",
            selectedDocumentIds=[ctx["doc_a"].id, ctx["doc_b"].id],
        )
        handover = await rag_service.synthesize_handover(req=gen_req, user_id=user_id)

    # Verification 1: Gemini generates the handover strictly as DRAFT
    assert handover is not None
    assert handover.status == "draft"
    assert handover.project_id == project_id
    assert len(db_store["sections"]) == 10

    # -------------------------------------------------------------------------
    # STEP 2 & 3: EVIDENCE VERIFICATION ENGINE CHECKS CLAIMS & ATTACHES SOURCES
    # -------------------------------------------------------------------------
    evidence_service = EvidenceVerificationService(mock_db)

    # Verify sections with claims
    all_sections = list(db_store["sections"].values())
    overview_sec = next(s for s in all_sections if s.section_type == "project_overview")
    arch_sec = next(s for s in all_sections if s.section_type == "technical_architecture")

    # Set up execute for section queries
    current_sec = overview_sec
    mock_res = MagicMock()
    mock_res.first.side_effect = lambda: (current_sec, handover)
    mock_db.execute.return_value = mock_res

    # Document retrieval query mock
    async def mock_claim_chunks(p_id, text):
        if "quantum" in text.lower():
            return []
        elif "ignite" in text.lower():
            return [(ctx["chunk_b2"], ctx["doc_b"])]
        return [(ctx["chunk_a1"], ctx["doc_a"])]

    evidence_service._retrieve_relevant_chunks_for_claim = AsyncMock(side_effect=mock_claim_chunks)

    # Verify overview section (contains supported claim + unsupported claim)
    current_sec = overview_sec
    with patch.object(Settings, "is_gemini_configured", return_value=False):
        sec_report = await evidence_service.verify_section(overview_sec.id, handover.id)

    # Verification 2: Verification engine checked claims
    assert sec_report.total_claims >= 2
    claims_map = {c.claim_text: c for c in sec_report.claims}

    # Verification 3: Source references correctly attached for supported claims
    supported_c = claims_map.get(supported_claim_1_text)
    assert supported_c is not None
    assert supported_c.verification_status == "Supported"
    assert supported_c.supporting_document_id == ctx["doc_a"].id
    assert supported_c.source_filename == "spec_v1_architecture.md"
    assert supported_c.page_number == 1
    assert "99.999% system availability" in (supported_c.supporting_text_excerpt or "")

    # Verification: Unsupported claim is accurately marked Unsupported/Insufficient without hallucinated source
    unsupported_c = claims_map.get(unsupported_ai_claim_text)
    assert unsupported_c is not None
    assert unsupported_c.verification_status in ("Unsupported", "Insufficient Evidence")
    assert unsupported_c.supporting_document_id is None
    assert unsupported_c.source_filename is None
    assert unsupported_c.supporting_text_excerpt is None

    # Verify architecture section (contains supported claim 2)
    current_sec = arch_sec
    with patch.object(Settings, "is_gemini_configured", return_value=False):
        sec2_report = await evidence_service.verify_section(arch_sec.id, handover.id)

    assert sec2_report.supported_claims >= 1
    supported_c2 = next(c for c in sec2_report.claims if c.claim_text == supported_claim_2_text)
    assert supported_c2.verification_status == "Supported"
    assert supported_c2.source_filename == "sprint_planning_update_v2.md"

    # -------------------------------------------------------------------------
    # STEP 4: CONTRADICTION DETECTION ENGINE IDENTIFIES CONFLICTS
    # -------------------------------------------------------------------------
    contradiction_service = ContradictionDetectionService(mock_db)

    # Provide project chunks to contradiction service
    contradiction_service._fetch_project_chunks = AsyncMock(return_value=ctx["chunks_all"])

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        conflict_report = await contradiction_service.detect_project_conflicts(project_id)

    # Verification 4: Contradictions are detected across documents
    assert conflict_report.contradictions_detected >= 2
    assert len(conflict_report.conflicts) >= 2

    # Check categories of detected conflicts
    categories = {c.conflict_category for c in conflict_report.conflicts}
    assert ConflictCategory.DEADLINE.value in categories
    assert (
        ConflictCategory.TECHNOLOGY_STACK.value in categories
        or ConflictCategory.ARCHITECTURE.value in categories
    )

    # Check that Deadline conflict contains both conflicting statements & document sources
    deadline_conflict = next(
        c for c in conflict_report.conflicts if c.conflict_category == ConflictCategory.DEADLINE.value
    )
    assert deadline_conflict.statement_a is not None
    assert deadline_conflict.statement_b is not None
    assert "October 15, 2026" in deadline_conflict.statement_a or "October 15, 2026" in deadline_conflict.statement_b
    assert "November 30, 2026" in deadline_conflict.statement_a or "November 30, 2026" in deadline_conflict.statement_b
    assert deadline_conflict.source_document_a == "spec_v1_architecture.md" or deadline_conflict.source_document_b == "spec_v1_architecture.md"
    assert deadline_conflict.source_document_a == "sprint_planning_update_v2.md" or deadline_conflict.source_document_b == "sprint_planning_update_v2.md"

    # Status must initially be Unresolved and NEVER auto-selected
    assert deadline_conflict.resolution_status == ConflictResolutionStatus.UNRESOLVED.value
    assert deadline_conflict.resolution is None

    # Check Technology Stack conflict
    tech_conflict = next(
        c for c in conflict_report.conflicts
        if c.conflict_category in (ConflictCategory.TECHNOLOGY_STACK.value, ConflictCategory.ARCHITECTURE.value)
    )
    assert "Redis" in (tech_conflict.statement_a or "") or "Redis" in (tech_conflict.statement_b or "")
    assert "Ignite" in (tech_conflict.statement_a or "") or "Ignite" in (tech_conflict.statement_b or "")

    # -------------------------------------------------------------------------
    # STEP 5: REVIEWERS RESOLVE CONFLICTS (HUMAN REVIEWER ARBITRATION)
    # -------------------------------------------------------------------------
    conflict_to_resolve_id = deadline_conflict.id
    conflict_in_db = db_store["conflicts"][conflict_to_resolve_id]
    
    conflict_res = MagicMock()
    conflict_res.scalars.return_value.first.return_value = conflict_in_db
    mock_db.execute.return_value = conflict_res

    resolve_payload = ConflictResolveRequest(
        chosen_source="source_b",
        authoritative_value="Production cutover deadline postponed to November 30, 2026.",
        chosen_value="Production cutover deadline postponed to November 30, 2026.",
        resolution_notes="Postponement confirmed in sprint planning update v2; banking integration delays require 6-week extension.",
        explanation="Postponement confirmed in sprint planning update v2; banking integration delays require 6-week extension.",
        status="Resolved",
    )

    resolved_result = await contradiction_service.resolve_conflict(
        conflict_id=conflict_to_resolve_id,
        payload=resolve_payload,
        current_user=ctx["lead_user"],
    )

    # Verification 5: Reviewer resolution succeeded
    assert resolved_result.status == "Resolved"
    assert resolved_result.resolution["authoritative_value"] == resolve_payload.authoritative_value
    assert resolved_result.resolved_by == user_id
    assert conflict_in_db.status == "Resolved"
    assert conflict_in_db.resolution is not None

    # -------------------------------------------------------------------------
    # STEP 6: RESOLUTIONS PERSIST AFTER DATABASE RE-QUERY
    # -------------------------------------------------------------------------
    # Simulate fresh query from database
    persisted_conflict = db_store["conflicts"][conflict_to_resolve_id]
    assert persisted_conflict.status == "Resolved"
    assert persisted_conflict.resolution["chosen_source"] == "source_b"
    assert "November 30, 2026" in persisted_conflict.resolution["authoritative_value"]
    assert "banking integration delays" in persisted_conflict.resolution["explanation"]

    # Also test status transition to 'Under Review' and 'Dismissed'
    tech_conflict_in_db = db_store["conflicts"][tech_conflict.id]
    tech_res = MagicMock()
    tech_res.scalars.return_value.first.return_value = tech_conflict_in_db
    mock_db.execute.return_value = tech_res

    # Under Review
    await contradiction_service.update_conflict_status(
        conflict_id=tech_conflict.id,
        new_status="Under Review",
        notes="Architecture board evaluating distributed transaction performance",
        current_user=ctx["lead_user"],
    )
    assert tech_conflict_in_db.status == "Under Review"

    # Dismissed
    await contradiction_service.resolve_conflict(
        conflict_id=tech_conflict.id,
        payload=ConflictResolveRequest(
            status="Dismissed",
            explanation="Both caching systems will be supported in a hybrid cache model.",
            resolution_notes="Both caching systems will be supported in a hybrid cache model.",
        ),
        current_user=ctx["lead_user"],
    )
    assert tech_conflict_in_db.status == "Dismissed"
    assert tech_conflict_in_db.resolution["resolution_explanation"] == "Both caching systems will be supported in a hybrid cache model."

    # -------------------------------------------------------------------------
    # STEP 7: EXISTING HANDOVER GENERATION CONTINUES WORKING
    # -------------------------------------------------------------------------
    # Verify single section regeneration without affecting the rest of the handover
    section_to_regen = all_sections[0]

    regen_res = MagicMock()
    regen_res.first.return_value = (section_to_regen, handover)
    regen_res.scalars.return_value.first.return_value = section_to_regen
    mock_db.execute.return_value = regen_res

    regen_content = {
        "section_type": section_to_regen.section_type,
        "title": section_to_regen.title,
        "confidence": 0.98,
        "content": {
            "summary": "Updated Project Overview with reaffirmed 99.999% SLA.",
            "markdown": "# Updated Overview\n\nHigh throughput routing with active-active regional failover.",
            "structured_data": {},
            "claims": [
                {
                    "claim_id": "claim-nexus-regen-1",
                    "statement": "High throughput routing with active-active regional failover.",
                    "source_document_ids": [str(ctx["doc_a"].id)],
                    "source_chunk_ids": [str(ctx["chunk_a1"].id)],
                    "page_numbers": [1],
                    "quoted_text": "High throughput routing with active-active regional failover.",
                    "evidence_status": "SUPPORTED",
                }
            ],
            "recommendations": [],
        },
    }

    with patch.object(rag_service, "retrieve_evidence", return_value=[]), \
         patch.object(gemini_service, "generate_content", return_value=json.dumps(regen_content)):
        updated_section = await rag_service.regenerate_section(
            handover_id=handover.id,
            section_id=section_to_regen.id,
            instructions="Emphasize high throughput routing capabilities.",
        )

    # Verification 7: Existing handover regeneration works as expected
    assert updated_section is not None
    assert updated_section.content["summary"] == regen_content["content"]["summary"]
    assert len(updated_section.content["claims"]) == 1
    assert handover.status == "draft"  # Handover remains in draft status

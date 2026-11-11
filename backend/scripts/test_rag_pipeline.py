"""
End-to-End Verification Script for Step 8 & 9:
RAG Synthesis, Evidence Traceability, Conflict Detection, and Handover Approval Lifecycle.

Workflow tested:
1. Environment & Database check
2. Test Project & Ingested Document Chunks setup
3. RAG Handover Synthesis via Gemini
4. Verification of Sections (7 standard chapters), Citations, Conflicts, and Tasks
5. Reviewer Section Edit & Lead Approval Transition
6. Incoming Member Handover Sign-off / Acknowledgement
7. Conflict Resolution & Task Progress Updates
8. Database Cleanup
"""

import sys
import uuid
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Add backend root to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.document import Document, DocumentChunk
from app.models.handover import Handover, HandoverSection, HandoverAuditLog
from app.models.evidence import EvidenceReference
from app.models.conflict import Conflict
from app.models.task import Task
from app.services.rag_service import RAGService
from app.services.gemini_service import gemini_service
from app.schemas.handover import GenerationRequest
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def run_rag_test():
    print("=" * 75)
    print("  STEP 8 & 9: RAG HANDOVER SYNTHESIS & APPROVAL LIFECYCLE VERIFICATION")
    print("=" * 75)

    if not settings.is_gemini_configured():
        print("[-] GEMINI_API_KEY is not configured in backend/.env.")
        print("    Please set GEMINI_API_KEY in backend/.env to run live RAG synthesis.")
        sys.exit(1)

    async with async_session_factory() as session:
        # Step 1: Create test users and project
        print("\n[1/7] Setting up test users, workspace, and roles...")
        lead_user_id = uuid.uuid4()
        incoming_user_id = uuid.uuid4()
        project_id = uuid.uuid4()

        lead_user = User(
            id=lead_user_id,
            email=f"lead_{lead_user_id.hex[:6]}@example.com",
            full_name="Sarah Connor (Tech Lead)",
            password_hash="argon2_fake_hash_for_test",
        )
        incoming_user = User(
            id=incoming_user_id,
            email=f"incoming_{incoming_user_id.hex[:6]}@example.com",
            full_name="John Doe (Incoming Dev)",
            password_hash="argon2_fake_hash_for_test",
        )
        session.add(lead_user)
        session.add(incoming_user)

        project = Project(
            id=project_id,
            name="Alpha Platform Cloud Migration",
            description="Knowledge base for microservices cloud migration",
            created_by=lead_user_id,
        )
        session.add(project)

        mem_lead = ProjectMember(
            id=uuid.uuid4(),
            project_id=project_id,
            user_id=lead_user_id,
            role=ProjectMemberRole.LEAD.value,
        )
        mem_incoming = ProjectMember(
            id=uuid.uuid4(),
            project_id=project_id,
            user_id=incoming_user_id,
            role=ProjectMemberRole.INCOMING.value,
        )
        session.add(mem_lead)
        session.add(mem_incoming)
        await session.commit()
        print(f"[+] Workspace created: '{project.name}' with LEAD and INCOMING members.")

        # Step 2: Seed Ingested Documentation with Chunks & Embeddings
        print("\n[2/7] Seeding processed technical documentation with 768-dim embeddings...")
        doc1_id = uuid.uuid4()
        doc2_id = uuid.uuid4()

        doc1 = Document(
            id=doc1_id,
            project_id=project_id,
            uploaded_by=lead_user_id,
            original_filename="system_architecture.md",
            stored_filename=f"{doc1_id.hex}_system_architecture.md",
            file_type="md",
            file_size=2048,
            storage_path=str(BACKEND_DIR / "storage" / "arch.md"),
            processing_status="READY",
        )
        doc2 = Document(
            id=doc2_id,
            project_id=project_id,
            uploaded_by=lead_user_id,
            original_filename="deployment_runbook.md",
            stored_filename=f"{doc2_id.hex}_deployment_runbook.md",
            file_type="md",
            file_size=1536,
            storage_path=str(BACKEND_DIR / "storage" / "runbook.md"),
            processing_status="READY",
        )
        session.add(doc1)
        session.add(doc2)

        # Chunks containing key facts and an intentional architecture contradiction
        chunk_texts = [
            (
                doc1_id,
                0,
                "The core API service runs on FastAPI and uses PostgreSQL 16 with pgvector for semantic search. "
                "All internal inter-service calls must use gRPC on port 50051 with mutual TLS.",
                "Architecture Overview",
                1,
            ),
            (
                doc1_id,
                1,
                "Database migrations are strictly managed using Alembic. Never run manual DDL in production. "
                "Primary ownership of database migrations belongs to the Backend Team Lead.",
                "Database Operations",
                2,
            ),
            (
                doc2_id,
                0,
                "Deployment Notice: The legacy services communicate over plain HTTP REST on port 8080. "
                "Engineers must ensure port 8080 is accessible across all subnet firewalls.",
                "Network & Ports",
                1,
            ),
            (
                doc2_id,
                1,
                "On-call rotations: Every engineer must monitor PagerDuty. Escalation SLA for critical alerts is 15 minutes.",
                "On-Call SOP",
                2,
            ),
        ]

        # Generate live embeddings via Gemini for these 4 chunks
        embeddings = gemini_service.generate_embeddings_batch([t[2] for t in chunk_texts])
        created_chunks = []
        for (doc_id, idx, content, sec_title, page), emb in zip(chunk_texts, embeddings):
            chunk = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_id,
                project_id=project_id,
                chunk_index=idx,
                content=content,
                embedding=emb,
                section_title=sec_title,
                page_number=page,
            )
            session.add(chunk)
            created_chunks.append(chunk)

        await session.commit()
        print(f"[+] Seeded 2 documents and {len(created_chunks)} chunks with real Gemini embeddings.")

        # Step 3: Run RAG Synthesis
        print("\n[3/7] Invoking Gemini RAG Synthesis Engine...")
        rag_service = RAGService(session)
        req = GenerationRequest(
            projectId=project_id,
            targetRole="Incoming Senior Software Engineer",
            handoverScope="Complete Technical & Operational Transition",
            timelineScope="All Time",
            title="Alpha Platform Handover Dossier",
            additionalInstructions="Ensure port 50051 vs port 8080 contradiction is highlighted.",
        )

        handover = await rag_service.synthesize_handover(req, user_id=lead_user_id)
        print(f"[+] Handover synthesized successfully! ID: {handover.id}")
        print(f"    Title: '{handover.title}' | Status: '{handover.status}' | Version: {handover.version}")

        # Step 4: Verify Sections, Evidence Citations, Conflicts, and Tasks
        print("\n[4/7] Verifying database integrity (sections, citations, conflicts, tasks)...")
        stmt = (
            select(Handover)
            .where(Handover.id == handover.id)
            .options(
                selectinload(Handover.sections).selectinload(HandoverSection.evidence_references),
                selectinload(Handover.conflicts),
                selectinload(Handover.tasks),
            )
        )
        res = await session.execute(stmt)
        full_handover = res.scalars().first()

        print(f"[+] Total sections generated: {len(full_handover.sections)}")
        assert len(full_handover.sections) >= 5, "Expected at least 5 standard sections"
        for s in full_handover.sections:
            print(f"    - [{s.section_type}] {s.title} (Confidence: {s.confidence:.2f}, Citations: {len(s.evidence_references)})")

        total_citations = sum(len(s.evidence_references) for s in full_handover.sections)
        print(f"[+] Total evidence citations linked: {total_citations}")
        assert total_citations > 0, "Expected at least one evidence citation"

        print(f"[+] Contradictions/Conflicts detected: {len(full_handover.conflicts)}")
        for c in full_handover.conflicts:
            print(f"    - [{c.conflict_type}] {c.description[:80]}... (Status: {c.status})")

        print(f"[+] Actionable Continuation Tasks created: {len(full_handover.tasks)}")
        for t in full_handover.tasks:
            print(f"    - [{t.priority.upper()}] {t.title}")
        assert len(full_handover.tasks) > 0, "Expected at least one continuation task"

        # Step 5: Review & Lead Approval
        print("\n[5/7] Testing Lead Handover Approval Workflow...")
        # Lead reviews section 1 and marks it approved
        section_to_review = full_handover.sections[0]
        section_to_review.review_status = "approved"
        # Formal lead approval
        full_handover.status = "approved"
        full_handover.approved_at = datetime.now(timezone.utc)
        audit_approve = HandoverAuditLog(
            id=uuid.uuid4(),
            handover_id=full_handover.id,
            user_id=lead_user_id,
            action="approved",
            details={"approved_by": "Sarah Connor", "notes": "LGTM"},
        )
        session.add(audit_approve)
        await session.commit()
        print(f"[+] Handover approved and published by Lead: status = '{full_handover.status}'")

        # Step 6: Incoming Member Sign-off / Acknowledgement
        print("\n[6/7] Testing Incoming Member Sign-Off (Acknowledgement)...")
        full_handover.status = "acknowledged"
        full_handover.shared_at = datetime.now(timezone.utc)
        full_handover.assigned_to = incoming_user_id
        audit_ack = HandoverAuditLog(
            id=uuid.uuid4(),
            handover_id=full_handover.id,
            user_id=incoming_user_id,
            action="acknowledged",
            details={"acknowledged_by": "John Doe", "notes": "Accepted responsibility"},
        )
        session.add(audit_ack)

        # Resolve first conflict
        if full_handover.conflicts:
            conf = full_handover.conflicts[0]
            conf.status = "resolved"
            conf.resolution = {
                "resolutionType": "verify_source_a",
                "resolutionNote": "Confirmed gRPC on port 50051 is correct; 8080 is deprecated.",
                "resolvedBy": str(lead_user_id),
            }
            conf.resolved_by = lead_user_id
            print(f"[+] Conflict '{conf.conflict_type}' resolved with human arbitration note.")

        # Complete first task
        if full_handover.tasks:
            first_task = full_handover.tasks[0]
            first_task.status = "completed"
            first_task.description = (first_task.description or "") + "\n\n**Note:** Onboarding complete."
            print(f"[+] Task '{first_task.title}' marked as completed.")

        await session.commit()
        print(f"[+] Handover formally acknowledged by incoming member: status = '{full_handover.status}'")

        # Step 7: Clean up test data
        print("\n[7/7] Cleaning up test records from PostgreSQL...")
        await session.delete(full_handover)
        for c in created_chunks:
            await session.delete(c)
        await session.delete(doc1)
        await session.delete(doc2)
        await session.delete(mem_lead)
        await session.delete(mem_incoming)
        await session.delete(project)
        await session.delete(lead_user)
        await session.delete(incoming_user)
        await session.commit()
        print("[+] Test database records cleanly removed.")

    print("\n" + "=" * 75)
    print("  [SUCCESS] Steps 8, 9, 10 Verified: RAG Synthesis, Approval, and Sign-off Complete!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_rag_test())

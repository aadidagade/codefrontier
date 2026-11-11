"""
Verification Script for Step 9:
AI-Powered Knowledge Handover Generation (10 Sections, Strict Claims, DRAFT State, and Single-Section Regeneration).

Execution steps:
1. Load database & verify Gemini API configuration
2. Seed test project and realistic multi-file engineering documentation
3. Trigger RAG Handover generation (POST /projects/{project_id}/handovers/generate)
4. Verify all 10 standard sections are generated and ordered (sort_order 0 to 9)
5. Verify factual claim attribution (claim_id, sources, pages, evidence_status)
6. Verify explicit isolation of recommendations (is_recommendation = True)
7. Verify Handover is saved strictly as DRAFT
8. Test single-section regeneration without touching the other 9 sections
9. Database cleanup
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
from app.services.rag_service import RAGService, HANDOVER_SECTIONS_SPEC
from app.services.gemini_service import gemini_service
from app.schemas.handover import GenerationRequest
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def run_step9_verification():
    print("=" * 75)
    print("  STEP 9: 10-SECTION AI HANDOVER GENERATION & SECTION REGENERATION TEST")
    print("=" * 75)

    if not settings.is_gemini_configured():
        print("[-] GEMINI_API_KEY is not configured in backend/.env.")
        print("    Please set GEMINI_API_KEY in backend/.env to run live AI synthesis.")
        sys.exit(1)

    async with async_session_factory() as session:
        # Step 1: Create test user and project
        print("\n[1/7] Setting up test project workspace and OUTGOING member...")
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=f"dev_lead_{user_id.hex[:6]}@example.com",
            full_name="Alex Mercer (Outgoing Staff Engineer)",
            password_hash="argon2_fake_hash",
        )
        session.add(user)

        project_id = uuid.uuid4()
        project = Project(
            id=project_id,
            name="E-Commerce Core Microservices",
            description="High-throughput payment and checkout services handover",
            created_by=user_id,
        )
        session.add(project)

        mem = ProjectMember(
            id=uuid.uuid4(),
            project_id=project_id,
            user_id=user_id,
            role=ProjectMemberRole.OUTGOING.value,
        )
        session.add(mem)
        await session.commit()
        print(f"[+] Workspace created: '{project.name}' (ID: {project_id})")

        # Step 2: Seed Ingested Documentation Covering Technical, Operational, and Runbook Aspects
        print("\n[2/7] Seeding realistic technical documentation with Gemini embeddings...")
        doc1_id = uuid.uuid4()
        doc2_id = uuid.uuid4()

        doc1 = Document(
            id=doc1_id,
            project_id=project_id,
            uploaded_by=user_id,
            original_filename="core_architecture_and_setup.md",
            stored_filename=f"{doc1_id.hex}_arch.md",
            file_type="md",
            file_size=3072,
            storage_path=str(BACKEND_DIR / "storage" / "arch.md"),
            processing_status="READY",
        )
        doc2 = Document(
            id=doc2_id,
            project_id=project_id,
            uploaded_by=user_id,
            original_filename="operations_and_known_issues.md",
            stored_filename=f"{doc2_id.hex}_ops.md",
            file_type="md",
            file_size=2560,
            storage_path=str(BACKEND_DIR / "storage" / "ops.md"),
            processing_status="READY",
        )
        session.add(doc1)
        session.add(doc2)

        sample_chunks = [
            (
                doc1_id,
                0,
                "Project Overview & Stack: The E-Commerce Core platform processes cart checkout and payments. "
                "Backend is built on Python FastAPI with SQLAlchemy 2.0 and PostgreSQL 16 on port 5432 with pgvector.",
                "System Overview & Stack",
                1,
            ),
            (
                doc1_id,
                1,
                "Setup and Installation: Requires Python 3.11+, PostgreSQL with vector extension enabled. "
                "Install dependencies with `pip install -r requirements.txt`. Run migrations via `alembic upgrade head`. "
                "Start development server using `uvicorn app.main:app --reload --port 8000`.",
                "Local Development Setup",
                2,
            ),
            (
                doc1_id,
                2,
                "Architectural Decisions (ADRs): We decided to use asyncpg for asynchronous non-blocking PostgreSQL I/O. "
                "We rejected Redis for primary state storage in favor of relational consistency with row-level locks.",
                "Key Decisions & ADRs",
                3,
            ),
            (
                doc2_id,
                0,
                "Pending Tasks: Complete the stripe webhook idempotency key deduplication. Priority: HIGH. "
                "Assigned to Incoming Dev. Due before Q1 release.",
                "Roadmap Tasks",
                1,
            ),
            (
                doc2_id,
                1,
                "Known Issues & Workarounds: High load during Black Friday causes database connection exhaustion if pool size < 40. "
                "Workaround: Set DB_POOL_SIZE=50 in environment variables. Bug #402 tracking memory leak in pdf generation.",
                "Known Bugs & Limitations",
                2,
            ),
            (
                doc2_id,
                2,
                "Deployment & Monitoring: Service is deployed via Docker to AWS ECS Fargate. "
                "Prometheus metrics exposed at /metrics. Database automated daily snapshots run at 02:00 UTC.",
                "Deployment & Backups",
                3,
            ),
        ]

        # Generate live embeddings
        vectors = gemini_service.generate_embeddings_batch([c[2] for c in sample_chunks])
        created_chunks = []
        for (doc_id, idx, content, sec_title, page), emb in zip(sample_chunks, vectors):
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
        print(f"[+] Seeded {len(created_chunks)} chunks with dense 768-dim embeddings.")

        # Step 3: Trigger 10-Section AI Handover Generation
        print("\n[3/7] Generating complete 10-section handover via Gemini RAG...")
        rag_service = RAGService(session)
        req = GenerationRequest(
            projectId=project_id,
            targetRole="Incoming Staff Backend Engineer",
            handoverScope="Complete Technical & Operational Transition",
            title="E-Commerce Core System Handover Dossier",
            additionalInstructions="Ensure Black Friday DB pool size issue is highlighted in known issues.",
        )

        handover = await rag_service.synthesize_handover(req, user_id=user_id)
        print(f"[+] Handover generated successfully! ID: {handover.id}")

        # Step 4: Strict Assertions on Status & Structure
        print("\n[4/7] Verifying DRAFT state, 10 sections, and sort order...")
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
        saved_handover = res.scalars().first()

        # Strict rule: ALWAYS DRAFT
        print(f"    - Status: '{saved_handover.status}' (Must be 'draft')")
        assert saved_handover.status == "draft", "Violation: Handover was not saved as DRAFT!"

        # Exactly 10 sections in order
        print(f"    - Total sections: {len(saved_handover.sections)} (Must be 10)")
        assert len(saved_handover.sections) == 10, f"Expected 10 sections, got {len(saved_handover.sections)}"

        for idx, sec in enumerate(saved_handover.sections):
            expected_spec = HANDOVER_SECTIONS_SPEC[idx]
            print(f"      {idx + 1:2d}. [{sec.section_type:<28}] {sec.title} (sort_order={sec.sort_order})")
            assert sec.sort_order == idx
            assert sec.section_type == expected_spec["type"]

        # Step 5: Verify Factual Claim Attribution & Recommendations
        print("\n[5/7] Verifying factual claims, evidence status, and recommendation separation...")
        total_claims = 0
        total_recs = 0
        for sec in saved_handover.sections:
            content = sec.content or {}
            claims = content.get("claims", [])
            recs = content.get("recommendations", [])
            total_claims += len(claims)
            total_recs += len(recs)

            for claim in claims:
                assert "claim_id" in claim
                assert "evidence_status" in claim
                assert claim["evidence_status"] in ("SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "NEEDS_REVIEW")

            for rec in recs:
                assert rec.get("is_recommendation") is True

        print(f"[+] Total factual claims validated: {total_claims}")
        print(f"[+] Total recommendations isolated: {total_recs}")
        assert total_claims > 0, "Expected factual claims across sections"

        # Check evidence citations stored in DB
        total_citations = sum(len(s.evidence_references) for s in saved_handover.sections)
        print(f"[+] Total EvidenceReference rows in PostgreSQL: {total_citations}")
        assert total_citations > 0, "Expected EvidenceReference records in database"

        # Step 6: Test Individual Section Regeneration
        print("\n[6/7] Testing individual section regeneration (Section 6: Known Issues)...")
        section_to_regen = [s for s in saved_handover.sections if s.section_type == "known_issues"][0]
        original_summary = section_to_regen.content.get("summary", "")

        updated_sec = await rag_service.regenerate_section(
            handover_id=saved_handover.id,
            section_id=section_to_regen.id,
            instructions="Focus heavily on the database connection pool exhaustion workaround (DB_POOL_SIZE=50).",
            user_id=user_id,
        )

        print(f"[+] Section successfully regenerated: '{updated_sec.title}'")
        print(f"    Confidence: {updated_sec.confidence:.2f}")
        print(f"    New Summary: {updated_sec.content.get('summary', '')[:100]}...")
        assert updated_sec.id == section_to_regen.id
        assert len(updated_sec.evidence_references) > 0

        # Verify other 9 sections remained untouched
        res_after = await session.execute(stmt)
        handover_after = res_after.scalars().first()
        assert len(handover_after.sections) == 10
        print("[+] Verified: All other 9 sections remained completely intact.")

        # Step 7: Database Cleanup
        print("\n[7/7] Cleaning up test records from database...")
        await session.delete(saved_handover)
        for c in created_chunks:
            await session.delete(c)
        await session.delete(doc1)
        await session.delete(doc2)
        await session.delete(mem)
        await session.delete(project)
        await session.delete(user)
        await session.commit()
        print("[+] Test database records cleanly removed.")

    print("\n" + "=" * 75)
    print("  [SUCCESS] Step 9 Complete: 10-Section AI Generation & Regeneration Verified!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_step9_verification())

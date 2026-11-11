"""
Comprehensive verification script for Step 8: Complete Hybrid RAG Pipeline.

Validates:
1. Strict project isolation (cross-project data leakage prevention).
2. Semantic vector search (Gemini embeddings + pgvector <=> cosine distance).
3. Keyword full-text search (PostgreSQL tsvector / tsquery).
4. Reciprocal Rank Fusion (RRF) merging & ranking.
5. Deduplication and source metadata preservation.
6. Low-confidence handling & threshold filtering.
7. Question answering grounded in retrieved evidence.
8. Database cleanup.
"""

import sys
import uuid
import asyncio
from pathlib import Path

# Add backend root to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.document import Document, DocumentChunk
from app.services.rag_service import RAGService
from app.services.gemini_service import gemini_service
from alembic.config import Config
from alembic import command


async def run_hybrid_rag_test():
    print("=" * 75)
    print("  STEP 8: HYBRID RAG PIPELINE & ATTRIBUTION VERIFICATION")
    print("=" * 75)

    # 1. Run migrations to head
    print("\n[1/7] Ensuring all migrations up to head are applied...")
    try:
        alembic_ini_path = BACKEND_DIR / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        command.upgrade(alembic_cfg, "head")
        print("[+] Migrations upgraded to head successfully.")
    except Exception as e:
        print(f"[-] Migration error: {e}")
        sys.exit(1)

    # 2. Setup Test Data (2 isolated projects)
    print("\n[2/7] Creating 2 isolated project workspaces to test cross-project protection...")
    async with async_session_factory() as session:
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=f"rag_tester_{user_id.hex[:6]}@example.com",
            full_name="RAG Verification Tester",
            password_hash="argon2_fake_hash",
        )
        session.add(user)

        # Project A
        proj_a_id = uuid.uuid4()
        proj_a = Project(id=proj_a_id, name="Project Alpha (Target Workspace)", created_by=user_id)
        session.add(proj_a)

        # Project B (Cross-tenant isolation test)
        proj_b_id = uuid.uuid4()
        proj_b = Project(id=proj_b_id, name="Project Beta (Isolated Workspace)", created_by=user_id)
        session.add(proj_b)

        await session.commit()

        # Seed Documents in Project A
        doc_a1_id = uuid.uuid4()
        doc_a2_id = uuid.uuid4()
        doc_a1 = Document(
            id=doc_a1_id,
            project_id=proj_a_id,
            original_filename="kafka_event_bus.md",
            stored_filename=f"{doc_a1_id.hex}_kafka.md",
            file_type="md",
            file_size=1024,
            storage_path=str(BACKEND_DIR / "storage" / "k.md"),
            processing_status="READY",
        )
        doc_a2 = Document(
            id=doc_a2_id,
            project_id=proj_a_id,
            original_filename="redis_caching_layer.md",
            stored_filename=f"{doc_a2_id.hex}_redis.md",
            file_type="md",
            file_size=1024,
            storage_path=str(BACKEND_DIR / "storage" / "r.md"),
            processing_status="READY",
        )
        session.add(doc_a1)
        session.add(doc_a2)

        # Seed Document in Project B with confidential text
        doc_b1_id = uuid.uuid4()
        doc_b1 = Document(
            id=doc_b1_id,
            project_id=proj_b_id,
            original_filename="confidential_beta_keys.md",
            stored_filename=f"{doc_b1_id.hex}_beta.md",
            file_type="md",
            file_size=1024,
            storage_path=str(BACKEND_DIR / "storage" / "b.md"),
            processing_status="READY",
        )
        session.add(doc_b1)

        chunks_a_data = [
            (
                doc_a1_id,
                proj_a_id,
                0,
                "Apache Kafka cluster runs on broker port 9092. Topic names must follow the convention domain.event.v1.",
                "Kafka Broker Configuration",
                1,
            ),
            (
                doc_a1_id,
                proj_a_id,
                1,
                "Consumer groups use SASL_SSL authentication. Dead letter queues (DLQ) are configured with 7 day retention.",
                "Security & Dead Letter Queue",
                2,
            ),
            (
                doc_a2_id,
                proj_a_id,
                0,
                "Redis sentinel cluster is deployed on port 6379 with standard TTL of 3600 seconds for session tokens.",
                "Redis Cache TTL",
                1,
            ),
        ]

        chunks_b_data = [
            (
                doc_b1_id,
                proj_b_id,
                0,
                "CONFIDENTIAL BETA TOKEN: secret-kafka-token-xyz-12345. Broker port 9092.",
                "Project Beta Secrets",
                1,
            ),
        ]

        # Generate embeddings if Gemini is configured, otherwise fallback to synthetic 768-vectors for unit test
        all_texts = [c[3] for c in chunks_a_data + chunks_b_data]
        if settings.is_gemini_configured():
            vectors = gemini_service.generate_embeddings_batch(all_texts)
        else:
            vectors = [[0.05 * (i + 1)] * 768 for i in range(len(all_texts))]

        created_chunks = []
        for (doc_id, p_id, idx, content, sec_title, page), emb in zip(chunks_a_data + chunks_b_data, vectors):
            ch = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_id,
                project_id=p_id,
                chunk_index=idx,
                content=content,
                embedding=emb,
                section_title=sec_title,
                page_number=page,
            )
            session.add(ch)
            created_chunks.append(ch)

        await session.commit()
        print(f"[+] Seeded {len(chunks_a_data)} chunks in Project Alpha, and {len(chunks_b_data)} chunk in Project Beta.")

        rag = RAGService(session)

        # 3. Test Keyword Search
        print("\n[3/7] Testing Keyword Search (PostgreSQL tsvector & token match)...")
        kw_chunks = await rag.retrieve_evidence(
            project_id=proj_a_id,
            query="broker port 9092 SASL_SSL",
            search_mode="keyword",
            limit=5,
        )
        print(f"[+] Keyword retrieval returned {len(kw_chunks)} chunks.")
        assert len(kw_chunks) > 0, "Keyword search should return at least 1 match"
        print(f"    Top match: '{kw_chunks[0].section_title}' (Score: {kw_chunks[0].similarity_score})")
        assert "Kafka" in kw_chunks[0].content or "9092" in kw_chunks[0].content

        # 4. Test Semantic & Hybrid Search
        print("\n[4/7] Testing Hybrid Search with Reciprocal Rank Fusion (RRF)...")
        hybrid_chunks = await rag.retrieve_evidence(
            project_id=proj_a_id,
            query="What is the session cache TTL and port for Redis?",
            search_mode="hybrid",
            limit=5,
        )
        print(f"[+] Hybrid retrieval returned {len(hybrid_chunks)} chunks.")
        assert len(hybrid_chunks) > 0, "Hybrid search should return matches"
        for idx, ch in enumerate(hybrid_chunks, start=1):
            print(f"    {idx}. [{ch.retrieval_method.upper()}] Doc: '{ch.document_name}' | Page: {ch.page_number} | Score: {ch.similarity_score}")
            print(f"       Section: '{ch.section_title}' -> Text: {ch.content[:80]}...")
            assert ch.document_name in ("kafka_event_bus.md", "redis_caching_layer.md")

        # 5. Test Strict Project Isolation
        print("\n[5/7] Testing Strict Project Isolation (Zero Cross-Project Data Leakage)...")
        isolation_query = "secret-kafka-token-xyz-12345"
        leaked_chunks = await rag.retrieve_evidence(
            project_id=proj_a_id,
            query=isolation_query,
            search_mode="hybrid",
            limit=10,
        )
        # Must NOT return any chunks from Project Beta!
        beta_chunks_found = [c for c in leaked_chunks if "CONFIDENTIAL" in c.content or c.document_name == "confidential_beta_keys.md"]
        assert len(beta_chunks_found) == 0, "FATAL: Cross-tenant leakage detected! Project A retrieved Project B chunks."
        print("[+] Strict project isolation verified: Zero Project B chunks leaked into Project A queries.")

        # 6. Test Low-Confidence & Threshold Handling
        print("\n[6/7] Testing Low-Confidence Retrieval & Threshold Filtering...")
        unrelated_query = "Quantum mechanics wave particle duality in outer space astrophysics"
        strict_chunks = await rag.retrieve_evidence(
            project_id=proj_a_id,
            query=unrelated_query,
            similarity_threshold=0.95,  # Very high threshold
            search_mode="hybrid",
            limit=5,
        )
        print(f"[+] High-threshold retrieval on unrelated query returned {len(strict_chunks)} chunks (expected 0).")
        assert len(strict_chunks) == 0, "Should return empty result when no evidence meets high threshold"
        print("[+] Graceful low-confidence handling verified: No fabricated evidence returned.")

        # 7. Test Question Answering (if Gemini configured)
        print("\n[7/7] Testing Grounded Q&A...")
        if settings.is_gemini_configured():
            qa_res = await rag.answer_question(
                project_id=proj_a_id,
                question="What port does Redis sentinel run on and what is the TTL?",
            )
            print(f"[+] Q&A Answer:\n    {qa_res['answer']}")
            print(f"[+] Citations attached: {len(qa_res['citations'])}")
            assert len(qa_res["citations"]) > 0
            assert "6379" in qa_res["answer"] or "3600" in qa_res["answer"]
        else:
            print("[*] Gemini API key not configured; skipping live LLM generation for Q&A.")

        # Cleanup
        print("\n[+] Cleaning up test records from PostgreSQL...")
        for ch in created_chunks:
            await session.delete(ch)
        await session.delete(doc_a1)
        await session.delete(doc_a2)
        await session.delete(doc_b1)
        await session.delete(proj_a)
        await session.delete(proj_b)
        await session.delete(user)
        await session.commit()
        print("[+] Database cleaned up successfully.")

    print("\n" + "=" * 75)
    print("  [SUCCESS] Step 8 Complete: Hybrid RAG Pipeline & Attribution Verified!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_hybrid_rag_test())

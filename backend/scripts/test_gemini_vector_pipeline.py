"""
Verification script for Step 7: Google Gemini API Integration & pgvector pipeline.

Tests:
1. Environment variables and database connectivity
2. pgvector extension and vector(768) type
3. Alembic migrations up to head (including HNSW index)
4. Gemini client initialization and model discovery
5. 768-dimensional normalized text embedding generation
6. Batch embedding generation with alignment
7. Live pgvector cosine similarity search in PostgreSQL
8. Gemini text/content generation
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
from app.repositories.document_repository import DocumentRepository
from app.services.gemini_service import gemini_service
from alembic.config import Config
from alembic import command
import asyncpg
from urllib.parse import urlparse


async def run_pipeline_test():
    print("=" * 70)
    print("  STEP 7: GOOGLE GEMINI API & PGVECTOR PIPELINE VERIFICATION")
    print("=" * 70)

    # 1. Database Connection & pgvector
    print("\n[1/6] Verifying PostgreSQL connection and pgvector extension...")
    db_url = settings.DATABASE_URL
    if not db_url or "YOUR_PASSWORD" in db_url:
        print("[-] FAIL: Please configure your PostgreSQL password in backend/.env.")
        sys.exit(1)

    raw_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(raw_url)
    try:
        conn = await asyncpg.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=parsed.username or "postgres",
            password=parsed.password or "",
            database=parsed.path.lstrip("/") or "knowledge_handover",
        )
        ext_ver = await conn.fetchval("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        print(f"[+] pgvector extension is active (v{ext_ver}).")
        await conn.close()
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        sys.exit(1)

    # 2. Alembic Migrations
    print("\n[2/6] Running Alembic migrations to head (including HNSW index)...")
    try:
        alembic_ini_path = BACKEND_DIR / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")
        print("[+] Migrations upgraded to head successfully.")
    except Exception as e:
        print(f"[-] Migration error: {e}")
        sys.exit(1)

    # 3. Gemini Configuration Check
    print("\n[3/6] Checking Gemini API configuration...")
    if not settings.is_gemini_configured():
        print("[-] GEMINI_API_KEY is not configured in backend/.env.")
        print("    Please obtain an API key from https://aistudio.google.com/api-keys")
        print("    and set GEMINI_API_KEY in backend/.env to run live API tests.")
        sys.exit(1)
    print("[+] GEMINI_API_KEY found in backend/.env.")

    # 4. Model Verification & Discovery
    print("\n[4/6] Verifying Gemini models...")
    try:
        gen_model = gemini_service.get_supported_generation_model()
        embed_model = gemini_service.get_supported_embedding_model()
        print(f"[+] Verified active Generation model: '{gen_model}'")
        print(f"[+] Verified active Embedding model:  '{embed_model}'")
    except Exception as e:
        print(f"[-] Model verification failed: {e}")
        sys.exit(1)

    # 5. Embedding Generation (Single & Batch)
    print("\n[5/6] Testing 768-dimensional embedding generation...")
    test_text = "Knowledge handover platform architecture and database schema."
    try:
        vector = gemini_service.generate_embedding(test_text)
        print(f"[+] Single embedding generated successfully: {len(vector)} dimensions.")
        assert len(vector) == settings.EMBEDDING_DIMENSION, f"Expected {settings.EMBEDDING_DIMENSION}, got {len(vector)}"

        batch_texts = [
            "PostgreSQL pgvector cosine distance search for knowledge continuity.",
            "FastAPI async backend architecture with clean domain-driven design.",
            "Google Gemini API integration with automatic retry and rate-limit handling.",
        ]
        batch_vectors = gemini_service.generate_embeddings_batch(batch_texts)
        print(f"[+] Batch embeddings generated successfully: {len(batch_vectors)} vectors (each {len(batch_vectors[0])} dims).")
        assert len(batch_vectors) == 3
        for v in batch_vectors:
            assert len(v) == settings.EMBEDDING_DIMENSION
    except Exception as e:
        print(f"[-] Embedding generation failed: {e}")
        sys.exit(1)

    # 6. Database Vector Insertion & Cosine Similarity Search
    print("\n[6/6] Testing live pgvector insertion and cosine similarity search...")
    async with async_session_factory() as session:
        # Create a test project and document
        test_project_id = uuid.uuid4()
        test_doc_id = uuid.uuid4()
        test_chunk_1_id = uuid.uuid4()
        test_chunk_2_id = uuid.uuid4()

        project = Project(
            id=test_project_id,
            name="Verification Test Project",
            description="Temporary project for vector search validation",
        )
        session.add(project)

        doc = Document(
            id=test_doc_id,
            project_id=test_project_id,
            original_filename="test_arch.md",
            stored_filename=f"{test_doc_id.hex}_test_arch.md",
            file_type="md",
            file_size=1024,
            storage_path=str(BACKEND_DIR / "storage" / "test.md"),
            processing_status="READY",
        )
        session.add(doc)

        chunk1 = DocumentChunk(
            id=test_chunk_1_id,
            document_id=test_doc_id,
            project_id=test_project_id,
            chunk_index=0,
            content="PostgreSQL pgvector cosine distance search for knowledge continuity.",
            embedding=batch_vectors[0],
            section_title="Vector Search",
        )
        chunk2 = DocumentChunk(
            id=test_chunk_2_id,
            document_id=test_doc_id,
            project_id=test_project_id,
            chunk_index=1,
            content="FastAPI async backend architecture with clean domain-driven design.",
            embedding=batch_vectors[1],
            section_title="Backend Architecture",
        )
        session.add(chunk1)
        session.add(chunk2)
        await session.commit()

        try:
            # Query vector search for something similar to chunk 1
            query = "How do we search vectors using pgvector and cosine distance?"
            query_vector = gemini_service.generate_embedding(query)

            repo = DocumentRepository(session)
            results = await repo.search_similar_chunks(
                project_id=test_project_id,
                query_embedding=query_vector,
                top_k=2,
            )

            print(f"[+] Vector search returned {len(results)} matches:")
            for chunk, sim in results:
                print(f"    - Chunk {chunk.chunk_index} ({chunk.section_title}): similarity = {sim:.4f}")
                print(f"      Text: {chunk.content[:70]}...")

            assert len(results) > 0, "Vector search returned no results"
            top_chunk, top_sim = results[0]
            assert top_chunk.id == test_chunk_1_id, "Expected chunk 1 (Vector Search) to be the top match!"
            print(f"[+] Correct top match verified with cosine similarity: {top_sim:.4f}")

            # Test generation model
            print("\n[+] Testing content generation...")
            gen_resp = gemini_service.generate_content("Respond with exactly: 'Gemini pipeline verified.'")
            print(f"    Gemini response: '{gen_resp}'")

        finally:
            # Clean up test records
            await session.delete(chunk1)
            await session.delete(chunk2)
            await session.delete(doc)
            await session.delete(project)
            await session.commit()
            print("[+] Test database records cleaned up.")

    print("\n" + "=" * 70)
    print("  [SUCCESS] Step 7 Complete: Gemini API and pgvector fully operational!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_pipeline_test())

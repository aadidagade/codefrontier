"""
Unit tests for Step 8: Hybrid RAG Pipeline, Reciprocal Rank Fusion, Attribution, and Search Endpoint.
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.rag_service import RAGService
from app.repositories.document_repository import DocumentRepository
from app.models.document import Document, DocumentChunk
from app.schemas.search import RetrievedChunk, ProjectSearchRequest, ProjectSearchResponse


def create_dummy_chunk(content: str, doc_name: str = "test.md", chunk_idx: int = 0) -> tuple:
    doc_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    doc = Document(id=doc_id, original_filename=doc_name)
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        project_id=proj_id,
        chunk_index=chunk_idx,
        content=content,
        page_number=1,
        section_title="Architecture",
    )
    return chunk, doc_name


@pytest.mark.asyncio
async def test_hybrid_search_rrf_merging():
    """Validates that RRF merges ranks, dedupes chunks, and labels method as 'hybrid'."""
    mock_db = AsyncMock()
    repo = DocumentRepository(mock_db)

    chunk1, doc1 = create_dummy_chunk("FastAPI backend with pgvector cosine search", "arch.md", 0)
    chunk2, doc2 = create_dummy_chunk("Alembic database migrations runner", "db.md", 1)
    chunk3, doc3 = create_dummy_chunk("Redis caching layer on port 6379", "cache.md", 2)

    # Chunk 1 is top in semantic (rank 1), and second in keyword (rank 2)
    # Chunk 2 is in semantic only
    # Chunk 3 is in keyword only
    semantic_matches = [
        (chunk1, doc1, 0.92),
        (chunk2, doc2, 0.75),
    ]
    keyword_matches = [
        (chunk3, doc3, 0.88),
        (chunk1, doc1, 0.80),
    ]

    with patch.object(repo, "search_similar_chunks", return_value=semantic_matches), \
         patch.object(repo, "search_keyword_chunks", return_value=keyword_matches):

        results = await repo.hybrid_search(
            project_id=uuid.uuid4(),
            query_text="search query",
            query_embedding=[0.1] * 768,
            top_k=5,
            search_mode="hybrid",
        )

        assert len(results) == 3
        # Deduplication: chunk1 appeared in both lists, but only 1 entry in results
        chunk_ids = [c.chunk_id for c in results]
        assert len(chunk_ids) == len(set(chunk_ids))

        # Chunk 1 was present in both, so its RRF score should be highest
        assert results[0].chunk_id == chunk1.id
        assert results[0].retrieval_method == "hybrid"
        assert results[0].document_name == "arch.md"
        assert results[0].page_number == 1
        assert results[0].section_title == "Architecture"


@pytest.mark.asyncio
async def test_empty_query_returns_empty_list():
    mock_db = AsyncMock()
    rag = RAGService(mock_db)
    res = await rag.retrieve_evidence(project_id=uuid.uuid4(), query="   \t\n  ")
    assert res == []


@pytest.mark.asyncio
async def test_threshold_filtering_excludes_low_confidence():
    mock_db = AsyncMock()
    repo = DocumentRepository(mock_db)
    chunk1, doc1 = create_dummy_chunk("Some moderately relevant content", "notes.md")

    # Similarity score is 0.45
    semantic_matches = [(chunk1, doc1, 0.45)]

    with patch.object(repo, "search_similar_chunks", return_value=semantic_matches), \
         patch.object(repo, "search_keyword_chunks", return_value=[]):

        results = await repo.hybrid_search(
            project_id=uuid.uuid4(),
            query_text="test",
            query_embedding=[0.1] * 768,
            top_k=5,
            similarity_threshold=0.70,  # Higher than 0.45
        )

        # Must be filtered out
        assert len(results) == 0


@pytest.mark.asyncio
async def test_answer_question_no_evidence():
    """Validates that Q&A does not hallucinate when no evidence exists."""
    mock_db = AsyncMock()
    rag = RAGService(mock_db)

    with patch.object(rag, "retrieve_evidence", return_value=[]):
        res = await rag.answer_question(
            project_id=uuid.uuid4(),
            question="What is the nuclear launch code?",
        )
        assert "No relevant documentation found" in res["answer"]
        assert res["confidence"] == 0.0
        assert res["citations"] == []


@pytest.mark.asyncio
async def test_answer_question_with_evidence():
    mock_db = AsyncMock()
    rag = RAGService(mock_db)

    chunk_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    evidence = [
        RetrievedChunk(
            chunk_id=chunk_id,
            document_id=doc_id,
            document_name="architecture.md",
            chunk_index=0,
            page_number=2,
            section_title="Database",
            content="PostgreSQL runs on port 5432 with pgvector.",
            similarity_score=0.95,
            retrieval_method="hybrid",
        )
    ]

    with patch.object(rag, "retrieve_evidence", return_value=evidence), \
         patch("app.services.rag_service.gemini_service.generate_content", return_value="PostgreSQL runs on port 5432 [1]."):
        res = await rag.answer_question(
            project_id=uuid.uuid4(),
            question="Which port does PostgreSQL run on?",
        )

        assert "5432" in res["answer"]
        assert len(res["citations"]) == 1
        assert res["citations"][0]["chunk_id"] == str(chunk_id)
        assert res["citations"][0]["document_name"] == "architecture.md"
        assert res["citations"][0]["page_number"] == 2

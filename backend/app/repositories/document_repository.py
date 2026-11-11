import uuid
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from app.models.document import Document, DocumentChunk
from app.schemas.search import RetrievedChunk


class DocumentRepository:
    """
    Project-scoped Document and Vector Chunk repository ensuring strict cross-project data isolation.
    Provides semantic vector search, full-text keyword search, and reciprocal rank fusion hybrid retrieval.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_project(self, project_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Document]:
        """Strictly fetches documents belonging to the specified project workspace."""
        stmt = (
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_project_document(self, project_id: uuid.UUID, document_id: uuid.UUID) -> Optional[Document]:
        """Project-scoped single document lookup preventing cross-project document leakage."""
        stmt = select(Document).where(
            Document.id == document_id,
            Document.project_id == project_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def search_similar_chunks(
        self,
        project_id: uuid.UUID,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_threshold: Optional[float] = None,
        document_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Tuple[DocumentChunk, str, float]]:
        """
        Executes a project-isolated semantic vector similarity search via pgvector.
        Uses cosine distance (<=>) restricted to the project workspace.
        Returns a list of tuples: (DocumentChunk, document_name, similarity_score).
        """
        cosine_dist = DocumentChunk.embedding.cosine_distance(query_embedding)
        similarity_expr = (1.0 - cosine_dist).label("similarity")

        conditions = [
            DocumentChunk.project_id == project_id,
            DocumentChunk.embedding.is_not(None),
        ]

        if document_ids:
            conditions.append(DocumentChunk.document_id.in_(document_ids))

        if similarity_threshold is not None:
            # Cosine distance <= (1.0 - similarity_threshold) corresponds to similarity >= similarity_threshold
            conditions.append(cosine_dist <= (1.0 - similarity_threshold))

        stmt = (
            select(DocumentChunk, Document.original_filename, similarity_expr)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(*conditions)
            .order_by(cosine_dist.asc())
            .limit(top_k)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [(row[0], row[1], float(row[2]) if row[2] is not None else 0.0) for row in rows]

    async def search_keyword_chunks(
        self,
        project_id: uuid.UUID,
        query_text: str,
        top_k: int = 10,
        document_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Tuple[DocumentChunk, str, float]]:
        """
        Executes a project-isolated keyword search using PostgreSQL full-text search (tsvector)
        and token matching. Returns (DocumentChunk, document_name, rank_score).
        """
        clean_query = query_text.strip()
        if not clean_query:
            return []

        ts_vec = func.to_tsvector("english", DocumentChunk.content)
        ts_query = func.plainto_tsquery("english", clean_query)
        ts_rank = func.ts_rank(ts_vec, ts_query).label("rank")

        # Also support token matching for specific codes, numbers, or terms
        terms = [t for t in clean_query.split() if len(t) >= 2]
        ilike_clauses = [DocumentChunk.content.ilike(f"%{t}%") for t in terms[:4]]

        match_clause = ts_vec.op("@@")(ts_query)
        if ilike_clauses:
            match_clause = or_(match_clause, *ilike_clauses)

        conditions = [
            DocumentChunk.project_id == project_id,
            match_clause,
        ]

        if document_ids:
            conditions.append(DocumentChunk.document_id.in_(document_ids))

        stmt = (
            select(DocumentChunk, Document.original_filename, ts_rank)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(*conditions)
            .order_by(ts_rank.desc())
            .limit(top_k)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [(row[0], row[1], float(row[2]) if row[2] is not None else 0.5) for row in rows]

    async def hybrid_search(
        self,
        project_id: uuid.UUID,
        query_text: str,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 10,
        similarity_threshold: Optional[float] = None,
        document_ids: Optional[List[uuid.UUID]] = None,
        search_mode: str = "hybrid",
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        rrf_k: int = 60,
    ) -> List[RetrievedChunk]:
        """
        Executes hybrid retrieval combining semantic embeddings (pgvector) and keyword full-text search.
        Merges results using Reciprocal Rank Fusion (RRF), removes duplicates, and preserves full attribution.
        """
        search_mode = (search_mode or "hybrid").lower()

        semantic_results: List[Tuple[DocumentChunk, str, float]] = []
        keyword_results: List[Tuple[DocumentChunk, str, float]] = []

        # 1. Semantic Search
        if search_mode in ("hybrid", "semantic") and query_embedding is not None:
            semantic_results = await self.search_similar_chunks(
                project_id=project_id,
                query_embedding=query_embedding,
                top_k=top_k * 2,
                similarity_threshold=similarity_threshold,
                document_ids=document_ids,
            )

        # 2. Keyword Search
        if search_mode in ("hybrid", "keyword"):
            keyword_results = await self.search_keyword_chunks(
                project_id=project_id,
                query_text=query_text,
                top_k=top_k * 2,
                document_ids=document_ids,
            )

        # If keyword only
        if search_mode == "keyword" or (not semantic_results and keyword_results):
            out = []
            for chunk, doc_name, score in keyword_results[:top_k]:
                out.append(
                    RetrievedChunk(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        document_name=doc_name,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        section_title=chunk.section_title,
                        content=chunk.content,
                        similarity_score=round(min(1.0, score + 0.3), 4),
                        retrieval_method="keyword",
                    )
                )
            return out

        # If semantic only
        if search_mode == "semantic" or (not keyword_results and semantic_results):
            out = []
            for chunk, doc_name, score in semantic_results[:top_k]:
                out.append(
                    RetrievedChunk(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        document_name=doc_name,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        section_title=chunk.section_title,
                        content=chunk.content,
                        similarity_score=round(score, 4),
                        retrieval_method="semantic",
                    )
                )
            return out

        # 3. Reciprocal Rank Fusion (RRF) for Hybrid Search
        # chunk_id -> dict with chunk info, rrf_score, methods
        fused: Dict[uuid.UUID, Dict] = {}

        # Process semantic ranks
        for rank, (chunk, doc_name, sim_score) in enumerate(semantic_results, start=1):
            rrf_sem = semantic_weight / (rrf_k + rank)
            fused[chunk.id] = {
                "chunk": chunk,
                "doc_name": doc_name,
                "sim_score": sim_score,
                "rrf_score": rrf_sem,
                "methods": {"semantic"},
            }

        # Process keyword ranks
        for rank, (chunk, doc_name, kw_score) in enumerate(keyword_results, start=1):
            rrf_kw = keyword_weight / (rrf_k + rank)
            if chunk.id in fused:
                fused[chunk.id]["rrf_score"] += rrf_kw
                fused[chunk.id]["methods"].add("keyword")
                # Boost similarity score when confirmed by both
                fused[chunk.id]["sim_score"] = min(1.0, fused[chunk.id]["sim_score"] * 1.05)
            else:
                fused[chunk.id] = {
                    "chunk": chunk,
                    "doc_name": doc_name,
                    "sim_score": min(0.85, kw_score + 0.3),
                    "rrf_score": rrf_kw,
                    "methods": {"keyword"},
                }

        # Sort by RRF fused score descending
        sorted_fused = sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)

        results: List[RetrievedChunk] = []
        for item in sorted_fused:
            chunk = item["chunk"]
            sim_score = item["sim_score"]

            if similarity_threshold is not None and sim_score < similarity_threshold:
                continue

            methods = item["methods"]
            method_label = "hybrid" if len(methods) > 1 else list(methods)[0]

            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_name=item["doc_name"],
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    content=chunk.content,
                    similarity_score=round(sim_score, 4),
                    retrieval_method=method_label,
                )
            )

            if len(results) >= top_k:
                break

        return results

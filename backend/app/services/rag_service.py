import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import ValidationException, AiServiceException, NotFoundException
from app.models.document import Document, DocumentChunk
from app.models.handover import Handover, HandoverSection, HandoverAuditLog
from app.models.evidence import EvidenceReference
from app.models.conflict import Conflict
from app.models.task import Task
from app.repositories.document_repository import DocumentRepository
from app.services.gemini_service import gemini_service
from app.schemas.handover import (
    GenerationRequest,
    HandoverAIGenerationOutput,
    GeneratedSection,
    SectionContent,
    FactualClaim,
    Recommendation,
    EvidenceStatus,
)
from app.schemas.search import RetrievedChunk

logger = logging.getLogger("app.services.rag")

# =============================================================================
# THE 10 REQUIRED HANDOVER SECTIONS SPECIFICATION
# =============================================================================

HANDOVER_SECTIONS_SPEC = [
    {
        "type": "project_overview",
        "title": "1. Project Overview",
        "query": "project purpose business objective main functionality core problem current project state overview",
        "topics": [
            "Project purpose",
            "Business objective",
            "Main functionality",
            "Current project state",
        ],
    },
    {
        "type": "technical_architecture",
        "title": "2. Technical Architecture",
        "query": "technology stack backend architecture frontend architecture database structure schema external integrations deployment architecture",
        "topics": [
            "Technology stack",
            "Backend architecture",
            "Frontend architecture",
            "Database structure",
            "External integrations",
            "Deployment architecture",
        ],
    },
    {
        "type": "setup_and_installation",
        "title": "3. Setup and Installation",
        "query": "development environment setup installation instructions dependencies environment configuration run instructions local run",
        "topics": [
            "Development environment",
            "Dependencies",
            "Environment configuration",
            "Installation instructions",
            "Run instructions",
        ],
    },
    {
        "type": "important_decisions",
        "title": "4. Important Decisions",
        "query": "technical decisions architectural decisions ADR business decisions tradeoff rationale reasons behind decisions",
        "topics": [
            "Technical decisions",
            "Architectural decisions",
            "Business decisions",
            "Reasons behind decisions",
        ],
    },
    {
        "type": "pending_tasks",
        "title": "5. Pending Tasks",
        "query": "pending tasks todo roadmap work in progress assigned owner due date dependencies unfinished work",
        "topics": [
            "Task description",
            "Priority",
            "Assigned person if known",
            "Due date if known",
            "Dependencies",
        ],
    },
    {
        "type": "known_issues",
        "title": "6. Known Issues",
        "query": "known bugs current issues technical limitations workarounds unresolved problems edge cases failure modes",
        "topics": [
            "Current bugs",
            "Technical limitations",
            "Workarounds",
            "Unresolved problems",
        ],
    },
    {
        "type": "risks_and_blockers",
        "title": "7. Risks and Blockers",
        "query": "technical risks operational risks project blockers external dependencies single point of failure failure modes",
        "topics": [
            "Technical risks",
            "Operational risks",
            "Dependencies",
            "External blockers",
        ],
    },
    {
        "type": "deployment_and_maintenance",
        "title": "8. Deployment and Maintenance",
        "query": "hosting cloud infrastructure deployment steps pipeline database maintenance backup information monitoring logging alerts",
        "topics": [
            "Hosting details",
            "Deployment steps",
            "Database maintenance",
            "Backup information",
            "Monitoring",
        ],
    },
    {
        "type": "open_questions",
        "title": "9. Open Questions",
        "query": "missing documentation unclear decisions unverified information questions for outgoing team member gaps ambiguities",
        "topics": [
            "Missing documentation",
            "Unclear decisions",
            "Unverified information",
            "Questions for the outgoing member",
        ],
    },
    {
        "type": "recommended_next_actions",
        "title": "10. Recommended Next Actions",
        "query": "recommended next actions immediate priorities short term improvements onboarding checklist long term recommendations",
        "topics": [
            "Immediate priorities",
            "Short-term improvements",
            "Long-term recommendations",
        ],
    },
]


class RAGService:
    """
    Industrial-grade Retrieval-Augmented Generation (RAG) Service.
    
    Provides:
    1. Hybrid evidence search with Reciprocal Rank Fusion (`retrieve_evidence`)
    2. Grounded technical question answering (`answer_question`)
    3. Cross-document contradiction / conflict detection (`detect_conflicts`)
    4. 10-chapter structured handover synthesis (`synthesize_handover`)
    5. Single-section regeneration without touching the rest of the handover (`regenerate_section`)

    Strict Rules Enforced:
    - Only states factual claims supported by retrieved evidence.
    - Marks undocumented or missing topics as UNKNOWN or NEEDS_REVIEW with UNSUPPORTED status.
    - Never hallucinates credentials, URLs, names, deadlines, or technical configurations.
    - Explicitly isolates recommendations in `recommendations` with `is_recommendation = True`.
    - Saves all generated handovers as DRAFT (never auto-publishes).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)

    # =========================================================================
    # 1. HYBRID RETRIEVAL PIPELINE
    # =========================================================================

    async def retrieve_evidence(
        self,
        project_id: uuid.UUID,
        query: str,
        limit: int = 10,
        document_ids: Optional[List[uuid.UUID]] = None,
        similarity_threshold: Optional[float] = None,
        search_mode: str = "hybrid",
    ) -> List[RetrievedChunk]:
        """
        Executes production hybrid retrieval (semantic vector + keyword full-text search)
        with Reciprocal Rank Fusion, deduplication, and source attribution preservation.
        Strictly project-isolated. Never fabricates evidence.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        search_mode = (search_mode or "hybrid").lower()
        query_embedding: Optional[List[float]] = None

        if search_mode in ("hybrid", "semantic") and settings.is_gemini_configured():
            try:
                query_embedding = gemini_service.generate_embedding(clean_query)
            except Exception as exc:
                logger.warning(f"Failed to generate query embedding: {exc}. Falling back to keyword search.")
                search_mode = "keyword"

        chunks = await self.repo.hybrid_search(
            project_id=project_id,
            query_text=clean_query,
            query_embedding=query_embedding,
            top_k=limit,
            similarity_threshold=similarity_threshold,
            document_ids=document_ids,
            search_mode=search_mode,
        )

        logger.info(
            f"Retrieved {len(chunks)} chunks for project {project_id} (mode={search_mode}, limit={limit})"
        )
        return chunks

    # =========================================================================
    # 2. QUESTION ANSWERING
    # =========================================================================

    async def answer_question(
        self,
        project_id: uuid.UUID,
        question: str,
        limit: int = 5,
        document_ids: Optional[List[uuid.UUID]] = None,
    ) -> Dict[str, Any]:
        """
        Answers a technical question grounded strictly in retrieved project documents.
        Handles low-confidence retrieval cleanly and attaches evidence citations.
        """
        evidence_chunks = await self.retrieve_evidence(
            project_id=project_id,
            query=question,
            limit=limit,
            document_ids=document_ids,
            similarity_threshold=0.25,
            search_mode="hybrid",
        )

        if not evidence_chunks:
            return {
                "question": question,
                "answer": "No relevant documentation found in this project to answer your question.",
                "confidence": 0.0,
                "citations": [],
            }

        context_lines = []
        for idx, ch in enumerate(evidence_chunks, start=1):
            context_lines.append(
                f"[{idx}] (Doc: '{ch.document_name}', Doc ID: {ch.document_id}, Chunk ID: {ch.chunk_id}, Page: {ch.page_number or 'N/A'})\n"
                f"{ch.content}\n"
            )

        prompt = f"""
Answer the following technical question based strictly on the retrieved source documentation excerpts below.
If the excerpts do not contain sufficient evidence to answer, state clearly that the documentation is insufficient.
Do NOT fabricate facts or make assumptions not supported by the excerpts.
Cite sources using [1], [2], etc. matching the excerpt numbers.

QUESTION:
{question}

RETRIEVED EXCERPTS:
{"---".join(context_lines)}

RESPONSE:
Provide a clear, direct answer with citations.
"""
        system_instruction = (
            "You are a technical documentation assistant. You answer questions strictly based on provided context. "
            "Never invent facts."
        )

        answer_text = gemini_service.generate_content(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.1,
        )

        citations = [
            {
                "chunk_id": str(ch.chunk_id),
                "document_id": str(ch.document_id),
                "document_name": ch.document_name,
                "page_number": ch.page_number,
                "section_title": ch.section_title,
                "similarity_score": ch.similarity_score,
                "excerpt": ch.content[:200],
            }
            for ch in evidence_chunks
        ]

        return {
            "question": question,
            "answer": answer_text,
            "confidence": round(sum(ch.similarity_score for ch in evidence_chunks) / len(evidence_chunks), 2),
            "citations": citations,
        }

    # =========================================================================
    # 3. CONFLICT & CONTRADICTION DETECTION
    # =========================================================================

    async def detect_conflicts(
        self,
        project_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scans project documentation chunks to detect contradictory statements across sources.
        """
        chunks_with_docs = await self._fetch_project_chunks(project_id, document_ids, max_chunks=100)
        if len(chunks_with_docs) < 2:
            return []

        corpus_parts = []
        for chunk, doc in chunks_with_docs:
            header = f"[CHUNK_ID: {chunk.id} | DOC: {doc.original_filename} | PAGE: {chunk.page_number or 1}]"
            corpus_parts.append(f"{header}\n{chunk.content}\n")

        joined_corpus = "---\n".join(corpus_parts)

        prompt = f"""
Analyze the following source document chunks from the same project repository.
Identify any contradictory facts, mismatched configurations, conflicting ownerships, differing dates, or conflicting architecture decisions.

SOURCE CORPUS:
----------------------------------------
{joined_corpus}
----------------------------------------

OUTPUT:
Respond with ONLY valid JSON:
{{
  "conflicts": [
    {{
      "conflict_type": "architecture | owner | date | process | security",
      "description": "Explanation of discrepancy",
      "source_a_chunk_id": "<UUID>",
      "source_a_quote": "...",
      "source_b_chunk_id": "<UUID>",
      "source_b_quote": "..."
    }}
  ]
}}
If no contradictions are found, return {{"conflicts": []}}.
"""
        raw = gemini_service.generate_content(prompt=prompt, temperature=0.1)
        cleaned = self._clean_json_response(raw)
        return cleaned.get("conflicts", [])

    # =========================================================================
    # 4. STRUCTURED 10-SECTION HANDOVER SYNTHESIS
    # =========================================================================

    async def _fetch_project_chunks(
        self,
        project_id: uuid.UUID,
        selected_document_ids: Optional[List[uuid.UUID]] = None,
        max_chunks: int = 150,
    ) -> List[Tuple[DocumentChunk, Document]]:
        """Retrieves all project chunks joined with their parent document metadata."""
        stmt = (
            select(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.project_id == project_id,
                Document.processing_status.in_(["READY", "INDEXING"]),
            )
        )

        if selected_document_ids:
            stmt = stmt.where(DocumentChunk.document_id.in_(selected_document_ids))

        stmt = stmt.order_by(Document.created_at.asc(), DocumentChunk.chunk_index.asc()).limit(max_chunks)
        result = await self.db.execute(stmt)
        return list(result.all())

    @staticmethod
    def _clean_json_response(raw_text: str) -> Dict[str, Any]:
        """Strips markdown code fences and parses JSON payload."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    pass
            logger.error(f"Failed to parse Gemini JSON output: {cleaned[:300]}")
            raise AiServiceException(f"Failed to parse AI synthesis JSON response: {str(exc)}")

    async def _retrieve_category_targeted_evidence(
        self,
        project_id: uuid.UUID,
        selected_document_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[str, Dict[str, Tuple[DocumentChunk, Document]]]:
        """
        Retrieves targeted evidence chunks for each of the 10 handover categories,
        ensuring every section has rich, domain-relevant context.
        """
        all_chunks_with_docs = await self._fetch_project_chunks(project_id, selected_document_ids)
        if not all_chunks_with_docs:
            return "", {}

        chunk_map: Dict[str, Tuple[DocumentChunk, Document]] = {
            str(c.id): (c, d) for c, d in all_chunks_with_docs
        }

        # Build categorized corpus block
        category_blocks = []
        for spec in HANDOVER_SECTIONS_SPEC:
            cat_query = spec["query"]
            cat_chunks = await self.retrieve_evidence(
                project_id=project_id,
                query=cat_query,
                limit=4,
                document_ids=selected_document_ids,
                search_mode="hybrid",
            )

            chunk_lines = []
            for ch in cat_chunks:
                header = f"[CHUNK_ID: {ch.chunk_id} | DOC_ID: {ch.document_id} | DOC: {ch.document_name} | PAGE: {ch.page_number or 1} | SECTION: {ch.section_title or 'N/A'}]"
                chunk_lines.append(f"{header}\n{ch.content}\n")

            if chunk_lines:
                category_blocks.append(f"### SECTION EVIDENCE FOR: {spec['title']}\n" + "\n".join(chunk_lines))

        # Also append general corpus summary
        general_parts = []
        for chunk, doc in all_chunks_with_docs[:40]:
            h = f"[CHUNK_ID: {chunk.id} | DOC_ID: {doc.id} | DOC: {doc.original_filename} | PAGE: {chunk.page_number or 1}]"
            general_parts.append(f"{h}\n{chunk.content}\n")

        full_corpus = "\n========================================\n".join(category_blocks)
        if not category_blocks:
            full_corpus = "\n---\n".join(general_parts)

        return full_corpus, chunk_map

    def _build_10_sections_prompt(
        self,
        corpus_text: str,
        req: GenerationRequest,
    ) -> str:
        """Constructs the prompt instructing Gemini on all 10 sections and strict AI rules."""
        sections_guide = "\n".join(
            f"{i+1}. '{s['type']}' - {s['title']}\n   Must address: {', '.join(s['topics'])}"
            for i, s in enumerate(HANDOVER_SECTIONS_SPEC)
        )

        user_instructions = f"\nAdditional User Instructions: {req.additionalInstructions}" if req.additionalInstructions else ""

        prompt = f"""
You are synthesizing a comprehensive, production-grade Knowledge Handover dossier for an incoming engineer.
Target Recipient: {req.targetRole or 'Incoming Senior Software Engineer'}
Handover Scope: {req.handoverScope or 'Comprehensive'}
Timeline Scope: {req.timelineScope or 'All Time'}
{user_instructions}

SOURCE DOCUMENT CORPUS:
----------------------------------------
{corpus_text}
----------------------------------------

STRICT GENERATION RULES:
1. ONLY state factual claims directly supported by the supplied source evidence chunks.
2. If information for any required subsection is absent or incomplete in the documentation, mark the claim statement as "UNKNOWN: [explanation]" or "NEEDS_REVIEW: [explanation]" with evidence_status = "UNSUPPORTED" or "NEEDS_REVIEW". Do NOT fabricate or hallucinate.
3. NEVER invent credentials, passwords, secrets, API tokens, internal URLs, person names, deadlines, or technical configurations not present in the sources.
4. Clearly distinguish documented facts from AI recommendations: recommendations must be placed strictly in the "recommendations" array with is_recommendation = true.
5. Every factual claim must include:
   - claim_id (e.g. "claim_1", "claim_2")
   - statement
   - source_document_ids (list of Document UUIDs from the chunk headers)
   - source_chunk_ids (list of Chunk UUIDs from the chunk headers)
   - page_numbers (list of integers from the chunk headers)
   - quoted_text (exact short excerpt from the chunk)
   - evidence_status ("SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "NEEDS_REVIEW")
6. Identify any conflicting evidence across documents and record them in the "conflicts" array.
7. Preserve all technical details, versions, ports, and configuration parameters.

YOU MUST GENERATE ALL 10 OF THE FOLLOWING SECTIONS IN ORDER:
{sections_guide}

OUTPUT FORMAT:
Respond with ONLY valid JSON adhering strictly to this schema:
{{
  "title": "{req.title or 'Comprehensive Engineering Knowledge Handover'}",
  "sections": [
    {{
      "section_type": "project_overview",
      "title": "1. Project Overview",
      "confidence": 0.95,
      "content": {{
        "summary": "Brief executive summary...",
        "markdown": "# 1. Project Overview\\n\\n### Project Purpose\\n...\\n\\n### Business Objective\\n...",
        "structured_data": {{
          "purpose": "...",
          "business_objective": "...",
          "main_functionality": ["..."],
          "current_state": "..."
        }},
        "claims": [
          {{
            "claim_id": "claim_overview_1",
            "statement": "...",
            "source_document_ids": ["<DOC_ID>"],
            "source_chunk_ids": ["<CHUNK_ID>"],
            "page_numbers": [1],
            "quoted_text": "...",
            "evidence_status": "SUPPORTED"
          }}
        ],
        "recommendations": [
          {{
            "recommendation_id": "rec_overview_1",
            "title": "...",
            "description": "...",
            "timeframe": "immediate",
            "is_recommendation": true,
            "rationale": "..."
          }}
        ]
      }}
    }}
    // ... all 10 required sections
  ],
  "conflicts": [
    {{
      "conflict_type": "architecture",
      "description": "Document A states X whereas Document B states Y",
      "source_a_chunk_id": "<UUID>",
      "source_a_quote": "...",
      "source_b_chunk_id": "<UUID>",
      "source_b_quote": "..."
    }}
  ],
  "tasks": [
    {{
      "title": "Set up development environment and verify database connection",
      "description": "Follow instructions in section 3.",
      "priority": "high",
      "assigned_to_name": null,
      "due_date_hint": null
    }}
  ]
}}
"""
        return prompt

    async def synthesize_handover(
        self,
        req: GenerationRequest,
        user_id: uuid.UUID,
    ) -> Handover:
        """
        Executes end-to-end RAG synthesis for all 10 required handover sections:
        1. Gathers category-targeted evidence chunks.
        2. Prompts Gemini with strict evidence and validation rules.
        3. Validates output using Pydantic (HandoverAIGenerationOutput).
        4. Saves Handover as DRAFT, along with sections, claims/citations, conflicts, and tasks.
        """
        corpus_text, chunk_map = await self._retrieve_category_targeted_evidence(
            project_id=req.projectId,
            selected_document_ids=req.selectedDocumentIds,
        )

        if not chunk_map:
            raise ValidationException(
                "Cannot generate handover: No processed documents or chunks found in this project. "
                "Please upload and process project documents first."
            )

        prompt = self._build_10_sections_prompt(corpus_text, req)
        system_instruction = (
            "You are a Principal Software Engineer and Enterprise Technical Lead generating a rigorous, "
            "evidence-backed knowledge handover. Only state factual claims supported by supplied evidence. "
            "Never invent facts, URLs, names, or credentials. Distinguish facts from recommendations."
        )

        logger.info(f"Synthesizing 10-section handover for project {req.projectId}...")
        raw_response = gemini_service.generate_content(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.15,
        )

        parsed_json = self._clean_json_response(raw_response)

        # Validate with Pydantic
        try:
            validated_output = HandoverAIGenerationOutput.model_validate(parsed_json)
        except Exception as pydantic_err:
            logger.warning(f"Pydantic validation issue on raw output: {pydantic_err}. Attempting schema repair.")
            # Ensure sections array exists
            if "sections" not in parsed_json or not isinstance(parsed_json["sections"], list):
                parsed_json["sections"] = []
            validated_output = HandoverAIGenerationOutput.model_validate(parsed_json)

        # Create Handover in PostgreSQL (ALWAYS as DRAFT)
        handover_title = validated_output.title or req.title or "Engineering Knowledge Handover"
        handover = Handover(
            id=uuid.uuid4(),
            project_id=req.projectId,
            created_by=user_id,
            title=handover_title,
            status="DRAFT",  # STRICT: Always saved as DRAFT
            version="v1.0",
            generated_at=datetime.now(timezone.utc),
        )
        self.db.add(handover)
        await self.db.flush()

        # Build map of generated sections by type
        gen_sections_by_type = {s.section_type: s for s in validated_output.sections}

        # Ensure all 10 required sections exist in order
        all_created_sections = []
        for sort_idx, spec in enumerate(HANDOVER_SECTIONS_SPEC):
            sec_type = spec["type"]
            sec_title = spec["title"]

            if sec_type in gen_sections_by_type:
                gen_sec = gen_sections_by_type[sec_type]
                sec_content_dict = gen_sec.content.model_dump()
                sec_confidence = gen_sec.confidence
                claims_list = gen_sec.content.claims
            else:
                # Fallback for missing section: mark as UNKNOWN
                sec_confidence = 0.5
                sec_content_dict = {
                    "summary": f"No documentation provided for {sec_title}.",
                    "markdown": f"# {sec_title}\n\n*UNKNOWN: No documentation provided for this section in the project repository.*",
                    "structured_data": {},
                    "claims": [
                        {
                            "claim_id": f"claim_{sec_type}_unknown",
                            "statement": f"UNKNOWN: Information for {sec_title} was not found in uploaded documents.",
                            "source_document_ids": [],
                            "source_chunk_ids": [],
                            "page_numbers": [],
                            "evidence_status": "UNSUPPORTED",
                        }
                    ],
                    "recommendations": [],
                }
                claims_list = [
                    FactualClaim(
                        claim_id=f"claim_{sec_type}_unknown",
                        statement=f"UNKNOWN: Information for {sec_title} was not found in uploaded documents.",
                        evidence_status=EvidenceStatus.UNSUPPORTED,
                    )
                ]

            sec_id = uuid.uuid4()
            section_record = HandoverSection(
                id=sec_id,
                handover_id=handover.id,
                section_type=sec_type,
                title=sec_title,
                content=sec_content_dict,
                confidence=sec_confidence,
                review_status="pending",
                sort_order=sort_idx,
            )
            self.db.add(section_record)
            all_created_sections.append(section_record)

            # Link Evidence References for claims
            for claim in claims_list:
                for chunk_id_str in claim.source_chunk_ids:
                    chunk_id_clean = str(chunk_id_str).strip()
                    if chunk_id_clean in chunk_map:
                        matched_chunk, matched_doc = chunk_map[chunk_id_clean]
                        ev = EvidenceReference(
                            id=uuid.uuid4(),
                            handover_section_id=sec_id,
                            document_id=matched_doc.id,
                            document_chunk_id=matched_chunk.id,
                            quoted_text=claim.quoted_text or claim.statement or matched_chunk.content[:200],
                            page_number=matched_chunk.page_number,
                            relevance_score=0.95 if claim.evidence_status == EvidenceStatus.SUPPORTED else 0.70,
                            verification_status=claim.evidence_status.value if hasattr(claim.evidence_status, "value") else str(claim.evidence_status),
                        )
                        self.db.add(ev)

        # Store Conflicts
        for conf in validated_output.conflicts:
            c_type = conf.conflict_type or "architecture"
            c_desc = conf.description
            ca_id = str(conf.source_a_chunk_id or "")
            cb_id = str(conf.source_b_chunk_id or "")

            src_a = {"text": conf.source_a_quote or ""}
            if ca_id in chunk_map:
                ca, da = chunk_map[ca_id]
                src_a.update({"document_id": str(da.id), "chunk_id": str(ca.id), "document_name": da.original_filename, "page": ca.page_number})

            src_b = {"text": conf.source_b_quote or ""}
            if cb_id in chunk_map:
                cb, db = chunk_map[cb_id]
                src_b.update({"document_id": str(db.id), "chunk_id": str(cb.id), "document_name": db.original_filename, "page": cb.page_number})

            conflict_rec = Conflict(
                id=uuid.uuid4(),
                project_id=req.projectId,
                handover_id=handover.id,
                conflict_type=c_type,
                description=c_desc,
                source_a=src_a,
                source_b=src_b,
                status="unresolved",
            )
            self.db.add(conflict_rec)

        # Store Continuation Tasks
        for t in validated_output.tasks:
            task = Task(
                id=uuid.uuid4(),
                project_id=req.projectId,
                handover_id=handover.id,
                title=t.title,
                description=t.description or "",
                priority=(t.priority or "medium").lower(),
                status="pending",
            )
            self.db.add(task)

        # Audit Log
        audit = HandoverAuditLog(
            id=uuid.uuid4(),
            handover_id=handover.id,
            user_id=user_id,
            action="generated",
            details={
                "sections_count": len(all_created_sections),
                "conflicts_count": len(validated_output.conflicts),
                "tasks_count": len(validated_output.tasks),
                "status": "DRAFT",
            },
        )
        self.db.add(audit)

        # Dispatch notification to user
        if user_id:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.notify_handover_generated(
                user_id=user_id,
                project_id=handover.project_id,
                handover_title=handover.title,
            )

        await self.db.commit()
        await self.db.refresh(handover)
        logger.info(f"Synthesized Handover {handover.id} with {len(all_created_sections)} sections as DRAFT.")
        return handover

    # =========================================================================
    # 5. INDIVIDUAL SECTION REGENERATION
    # =========================================================================

    async def regenerate_section(
        self,
        handover_id: uuid.UUID,
        section_id: uuid.UUID,
        instructions: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> HandoverSection:
        """
        Regenerates a single handover section without modifying the rest of the handover.
        Gathers targeted evidence for that specific section category, calls Gemini,
        validates the schema, updates the section, and refreshes evidence references.
        """
        # Fetch section and parent handover
        stmt = (
            select(HandoverSection, Handover)
            .join(Handover, HandoverSection.handover_id == Handover.id)
            .where(
                HandoverSection.id == section_id,
                HandoverSection.handover_id == handover_id,
            )
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            raise NotFoundException("HandoverSection", section_id)

        section, handover = row

        # Find matching spec
        matched_spec = None
        for spec in HANDOVER_SECTIONS_SPEC:
            if spec["type"] == section.section_type:
                matched_spec = spec
                break

        if not matched_spec:
            matched_spec = {
                "type": section.section_type,
                "title": section.title,
                "query": f"{section.title} {instructions or ''}",
                "topics": ["Overview", "Details", "Action Items"],
            }

        # Retrieve targeted evidence chunks for this single section
        cat_query = f"{matched_spec['query']} {instructions or ''}".strip()
        evidence_chunks = await self.retrieve_evidence(
            project_id=handover.project_id,
            query=cat_query,
            limit=6,
            search_mode="hybrid",
        )

        chunk_lines = []
        for ch in evidence_chunks:
            h = f"[CHUNK_ID: {ch.chunk_id} | DOC_ID: {ch.document_id} | DOC: {ch.document_name} | PAGE: {ch.page_number or 1} | SECTION: {ch.section_title or 'N/A'}]"
            chunk_lines.append(f"{h}\n{ch.content}\n")

        evidence_block = "\n---\n".join(chunk_lines)
        custom_inst = f"\nCustom User Instructions for Regeneration: {instructions}" if instructions else ""

        prompt = f"""
You are regenerating ONLY the following single section of an engineering handover:
SECTION: {matched_spec['title']} (type: '{matched_spec['type']}')
Required Topics: {', '.join(matched_spec['topics'])}
{custom_inst}

SOURCE DOCUMENT CHUNKS:
----------------------------------------
{evidence_block}
----------------------------------------

STRICT RULES:
1. ONLY state factual claims supported by the evidence above.
2. Mark missing/unverified info as UNKNOWN or NEEDS_REVIEW.
3. Recommendations must be placed in the "recommendations" array with is_recommendation = true.
4. Output ONLY valid JSON for this single section matching:
{{
  "section_type": "{matched_spec['type']}",
  "title": "{matched_spec['title']}",
  "confidence": 0.95,
  "content": {{
    "summary": "...",
    "markdown": "# {matched_spec['title']}\\n\\n...",
    "structured_data": {{}},
    "claims": [
      {{
        "claim_id": "claim_regen_1",
        "statement": "...",
        "source_document_ids": ["<DOC_ID>"],
        "source_chunk_ids": ["<CHUNK_ID>"],
        "page_numbers": [1],
        "quoted_text": "...",
        "evidence_status": "SUPPORTED"
      }}
    ],
    "recommendations": [
      {{
        "recommendation_id": "rec_regen_1",
        "title": "...",
        "description": "...",
        "timeframe": "immediate",
        "is_recommendation": true,
        "rationale": "..."
      }}
    ]
  }}
}}
"""
        raw_output = gemini_service.generate_content(
            prompt=prompt,
            system_instruction="You are a Technical Lead regenerating a single section of a handover with strict evidence grounding.",
            temperature=0.15,
        )

        cleaned_json = self._clean_json_response(raw_output)
        gen_section = GeneratedSection.model_validate(cleaned_json)

        # Update Section in database
        section.title = gen_section.title
        section.content = gen_section.content.model_dump()
        section.confidence = gen_section.confidence
        section.review_status = "pending"

        # Delete old evidence references for this section and insert refreshed ones
        await self.db.execute(
            delete(EvidenceReference).where(EvidenceReference.handover_section_id == section.id)
        )

        chunk_lookup = {str(c.chunk_id): c for c in evidence_chunks}
        for claim in gen_section.content.claims:
            for cid in claim.source_chunk_ids:
                cid_clean = str(cid).strip()
                if cid_clean in chunk_lookup:
                    ch = chunk_lookup[cid_clean]
                    ev = EvidenceReference(
                        id=uuid.uuid4(),
                        handover_section_id=section.id,
                        document_id=ch.document_id,
                        document_chunk_id=ch.chunk_id,
                        quoted_text=claim.quoted_text or claim.statement or ch.content[:200],
                        page_number=ch.page_number,
                        relevance_score=0.95 if claim.evidence_status == EvidenceStatus.SUPPORTED else 0.70,
                        verification_status=claim.evidence_status.value if hasattr(claim.evidence_status, "value") else str(claim.evidence_status),
                    )
                    self.db.add(ev)

        # Audit log
        audit = HandoverAuditLog(
            id=uuid.uuid4(),
            handover_id=handover.id,
            user_id=user_id,
            action="section_regenerated",
            details={
                "section_id": str(section.id),
                "section_type": section.section_type,
                "instructions": instructions,
            },
        )
        self.db.add(audit)

        await self.db.commit()
        await self.db.refresh(section)

        # Reload with evidence references
        stmt_reload = (
            select(HandoverSection)
            .where(HandoverSection.id == section.id)
            .options(selectinload(HandoverSection.evidence_references))
        )
        res_reload = await self.db.execute(stmt_reload)
        reloaded_sec = res_reload.scalars().first()

        logger.info(f"Regenerated section '{section.section_type}' ({section.id}) for Handover {handover.id}.")
        return reloaded_sec

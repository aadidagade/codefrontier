import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException, AiServiceException
from app.models.document import Document, DocumentChunk
from app.models.evidence import EvidenceReference, ClaimVerification
from app.models.handover import Handover, HandoverSection
from app.repositories.document_repository import DocumentRepository
from app.services.gemini_service import gemini_service
from app.schemas.handover import (
    EvidenceStatus,
    VerificationStatus,
    normalize_verification_status,
    ClaimVerificationResult,
    ClaimVerificationRecord,
    SectionVerificationReport,
    AdvancedHandoverVerificationReport,
    HandoverVerificationReport,
)

logger = logging.getLogger("app.services.verification")


class StructuredGeminiClaimEvaluation(BaseModel):
    """Pydantic schema to validate structured JSON returned by Gemini API."""
    verification_status: str
    alignment_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""
    supporting_chunk_id: Optional[str] = None
    supporting_document_id: Optional[str] = None
    source_filename: Optional[str] = None
    page_number: Optional[int] = None
    section_reference: Optional[str] = None
    supporting_text_excerpt: Optional[str] = None
    supported_facts: List[str] = Field(default_factory=list)
    unsupported_facts: List[str] = Field(default_factory=list)


class EvidenceVerificationService:
    """
    Advanced Evidence Verification Engine.
    
    Principles:
    1. Independent NLI evaluation comparing AI claims strictly against ground-truth source chunks.
    2. Zero hallucinated attribution: Never invent evidence, document IDs, or source references.
    3. 5-status classification:
       - Supported
       - Partially Supported
       - Unsupported
       - Conflicting
       - Insufficient Evidence
    4. Comprehensive claim storage:
       - claim_id, claim_text, verification_status, supporting_document_id, source_filename,
         page_number, section_reference, supporting_text_excerpt, verification_timestamp.
    5. Section-by-section analysis and retrieval of relevant original chunks.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)

    @staticmethod
    def _calculate_token_overlap(claim: str, passage: str) -> float:
        """Deterministic token overlap calculation for offline / test environments."""
        claim_words = set(re.findall(r"\w+", claim.lower()))
        passage_words = set(re.findall(r"\w+", passage.lower()))
        stopwords = {
            "the", "a", "an", "is", "are", "and", "or", "to", "in", "of", "for", "with",
            "on", "at", "by", "from", "it", "this", "that", "these", "those", "was", "were",
        }
        meaningful_claim_words = claim_words - stopwords
        if not meaningful_claim_words:
            return 1.0 if claim_words.issubset(passage_words) else 0.0

        overlap = meaningful_claim_words.intersection(passage_words)
        return len(overlap) / len(meaningful_claim_words)

    @staticmethod
    def _clean_json(raw_text: str) -> Dict[str, Any]:
        """Strips markdown code fences and returns parsed dictionary."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    pass
            raise AiServiceException(f"Failed to parse structured JSON from Gemini response: {cleaned[:200]}")

    # =========================================================================
    # 1. CORE CLAIM VERIFICATION AGAINST RETRIEVED CHUNKS
    # =========================================================================

    async def verify_claim(
        self,
        claim_id: str,
        claim_text: str,
        project_id: Optional[uuid.UUID] = None,
        candidate_chunks: Optional[List[Tuple[DocumentChunk, Document]]] = None,
        handover_section_id: Optional[uuid.UUID] = None,
        handover_id: Optional[uuid.UUID] = None,
    ) -> ClaimVerificationRecord:
        """
        Compares an AI-generated claim against ground-truth document chunks.
        Classifies into one of the 5 statuses:
        - Supported
        - Partially Supported
        - Unsupported
        - Conflicting
        - Insufficient Evidence
        Never invents evidence or references.
        """
        clean_claim = (claim_text or "").strip()
        if not clean_claim:
            clean_claim = "Empty claim"

        # If no chunks provided and project_id is available, retrieve from document retrieval system
        chunks_with_docs: List[Tuple[DocumentChunk, Document]] = list(candidate_chunks or [])
        if not chunks_with_docs and project_id:
            chunks_with_docs = await self._retrieve_relevant_chunks_for_claim(project_id, clean_claim)

        now = datetime.now(timezone.utc)

        # Rule 8: If evidence cannot be found, explicitly mark Unsupported or Insufficient Evidence
        if not chunks_with_docs:
            return ClaimVerificationRecord(
                id=uuid.uuid4(),
                claim_id=claim_id,
                claim_text=clean_claim,
                verification_status=VerificationStatus.INSUFFICIENT_EVIDENCE.value,
                supporting_document_id=None,
                source_filename=None,
                page_number=None,
                section_reference=None,
                supporting_text_excerpt=None,
                reasoning="No relevant document passages were found in repository to substantiate this claim.",
                alignment_score=0.0,
                verification_timestamp=now,
                handover_id=handover_id,
                handover_section_id=handover_section_id,
                document_chunk_id=None,
            )

        # Format retrieved evidence passages with strict traceable IDs
        chunk_map: Dict[str, Tuple[DocumentChunk, Document]] = {}
        passages_text_blocks = []
        for idx, (chunk, doc) in enumerate(chunks_with_docs, start=1):
            chunk_id_str = str(chunk.id)
            chunk_map[chunk_id_str] = (chunk, doc)
            header = (
                f"[PASSAGE {idx} | CHUNK_ID: {chunk.id} | DOC_ID: {doc.id} | "
                f"FILENAME: {doc.original_filename} | PAGE: {chunk.page_number or 1} | "
                f"SECTION: {chunk.section_title or 'N/A'}]"
            )
            passages_text_blocks.append(f"{header}\n{chunk.content}")

        combined_passages = "\n\n--------------------\n\n".join(passages_text_blocks)

        # Structured Gemini API evaluation if configured
        if settings.is_gemini_configured():
            try:
                eval_record = self._evaluate_claim_with_gemini(
                    claim_id=claim_id,
                    clean_claim=clean_claim,
                    combined_passages=combined_passages,
                    chunk_map=chunk_map,
                    now=now,
                    handover_id=handover_id,
                    handover_section_id=handover_section_id,
                )
                return eval_record
            except Exception as exc:
                logger.warning(f"Structured Gemini verification error: {exc}. Falling back to deterministic NLI heuristic.")

        # Fallback deterministic evaluation (token overlap & contradiction detection)
        return self._evaluate_claim_deterministic(
            claim_id=claim_id,
            clean_claim=clean_claim,
            chunks_with_docs=chunks_with_docs,
            now=now,
            handover_id=handover_id,
            handover_section_id=handover_section_id,
        )

    def _evaluate_claim_with_gemini(
        self,
        claim_id: str,
        clean_claim: str,
        combined_passages: str,
        chunk_map: Dict[str, Tuple[DocumentChunk, Document]],
        now: datetime,
        handover_id: Optional[uuid.UUID],
        handover_section_id: Optional[uuid.UUID],
    ) -> ClaimVerificationRecord:
        """Prompts Gemini using structured JSON output and validates the returned schema."""
        prompt = f"""
You are an Advanced Evidence Verification Evaluator and Fact-Checking Engine for Technical Knowledge Handovers.
Compare the following technical CLAIM against the retrieved SOURCE EVIDENCE PASSAGES from the repository.

CLAIM:
"{clean_claim}"

SOURCE EVIDENCE PASSAGES:
{combined_passages}

CLASSIFICATION RULES:
Classify the claim into EXACTLY ONE of the following 5 statuses:
1. "Supported": The source passages directly and completely substantiate all facts, figures, configurations, and assertions in the claim.
2. "Partially Supported": The evidence substantiates key parts of the claim, but some specific details, numbers, or elements are extrapolated or omitted.
3. "Unsupported": The claim's asserted facts are absent, unevidenced, or unrelated to the provided source passages.
4. "Conflicting": The evidence directly contradicts or conflicts with the claim (e.g. claim asserts X, source asserts contrary Y).
5. "Insufficient Evidence": The evidence is ambiguous, incomplete, or tangentially related, making verification inconclusive.

STRICT GROUNDING RULES:
- NEVER invent evidence, document IDs, filenames, page numbers, or quote excerpts.
- "supporting_chunk_id" MUST strictly match one of the exact CHUNK_ID values listed in the headers above, or be null.
- If the claim is Unsupported, Conflicting, or has Insufficient Evidence, do NOT invent a supporting chunk; set supporting_chunk_id, supporting_document_id, and supporting_text_excerpt to null.
- "supporting_text_excerpt" must be a verbatim excerpt from the supporting passage.

OUTPUT FORMAT:
Respond with ONLY valid JSON adhering strictly to:
{{
  "verification_status": "Supported" | "Partially Supported" | "Unsupported" | "Conflicting" | "Insufficient Evidence",
  "alignment_score": 0.95,
  "reasoning": "Direct explanation of factual alignment or discrepancy.",
  "supporting_chunk_id": "<valid CHUNK_ID from headers above or null>",
  "supporting_text_excerpt": "<exact verbatim quote from source or null>",
  "supported_facts": ["fact 1"],
  "unsupported_facts": ["fact 2"]
}}
"""
        system_instruction = (
            "You are an impartial fact-checking and Natural Language Inference (NLI) evaluator. "
            "Evaluate claims strictly against the provided source passages. Never assume facts not in the text."
        )

        raw_response = gemini_service.generate_structured_json(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.0,
        )

        parsed_dict = self._clean_json(raw_response)
        validated = StructuredGeminiClaimEvaluation.model_validate(parsed_dict)

        # Normalize verification status
        final_status = normalize_verification_status(validated.verification_status)

        # Validate supporting chunk attribution (Never invent references)
        sup_chunk_id = str(validated.supporting_chunk_id or "").strip()
        matched_chunk: Optional[DocumentChunk] = None
        matched_doc: Optional[Document] = None

        if sup_chunk_id and sup_chunk_id in chunk_map:
            matched_chunk, matched_doc = chunk_map[sup_chunk_id]
        else:
            # If the model returned an invalid/hallucinated chunk ID, discard it
            sup_chunk_id = ""

        # For Unsupported / Insufficient Evidence, do not attach fake supporting references
        if final_status in (VerificationStatus.UNSUPPORTED.value, VerificationStatus.INSUFFICIENT_EVIDENCE.value):
            matched_chunk = None
            matched_doc = None

        supporting_doc_id = matched_doc.id if matched_doc else None
        source_filename = matched_doc.original_filename if matched_doc else None
        page_num = matched_chunk.page_number if matched_chunk else None
        sec_ref = matched_chunk.section_title if matched_chunk else None
        chunk_uuid = matched_chunk.id if matched_chunk else None

        excerpt = validated.supporting_text_excerpt
        if matched_chunk and not excerpt:
            excerpt = matched_chunk.content[:250]

        return ClaimVerificationRecord(
            id=uuid.uuid4(),
            claim_id=claim_id,
            claim_text=clean_claim,
            verification_status=final_status,
            supporting_document_id=supporting_doc_id,
            source_filename=source_filename,
            page_number=page_num,
            section_reference=sec_ref,
            supporting_text_excerpt=excerpt,
            reasoning=validated.reasoning or f"Claim evaluated as {final_status}.",
            alignment_score=round(float(validated.alignment_score), 2),
            verification_timestamp=now,
            handover_id=handover_id,
            handover_section_id=handover_section_id,
            document_chunk_id=chunk_uuid,
        )

    def _evaluate_claim_deterministic(
        self,
        claim_id: str,
        clean_claim: str,
        chunks_with_docs: List[Tuple[DocumentChunk, Document]],
        now: datetime,
        handover_id: Optional[uuid.UUID],
        handover_section_id: Optional[uuid.UUID],
    ) -> ClaimVerificationRecord:
        """Deterministic lexical overlap fallback for offline environments and unit testing."""
        best_score = 0.0
        best_chunk: Optional[DocumentChunk] = None
        best_doc: Optional[Document] = None

        for chunk, doc in chunks_with_docs:
            score = self._calculate_token_overlap(clean_claim, chunk.content)
            if score > best_score:
                best_score = score
                best_chunk = chunk
                best_doc = doc

        # Check for direct negation or conflicting keywords
        claim_lower = clean_claim.lower()
        is_conflicting = False
        if best_chunk:
            chunk_lower = best_chunk.content.lower()
            # If claim asserts numbers/ports/versions that differ
            numbers_claim = set(re.findall(r"\b\d+\b", claim_lower))
            numbers_chunk = set(re.findall(r"\b\d+\b", chunk_lower))
            if numbers_claim and numbers_chunk and not numbers_claim.issubset(numbers_chunk) and best_score >= 0.40:
                is_conflicting = True

        if is_conflicting:
            status_val = VerificationStatus.CONFLICTING.value
            reasoning = f"Conflicting numerical or factual parameters detected between claim and source passage (overlap={best_score:.2f})."
        elif best_score >= 0.65:
            status_val = VerificationStatus.SUPPORTED.value
            reasoning = f"High lexical and entity overlap ({best_score:.2f}) confirms claim in source documentation."
        elif best_score >= 0.35:
            status_val = VerificationStatus.PARTIALLY_SUPPORTED.value
            reasoning = f"Moderate lexical overlap ({best_score:.2f}). Core statement partially supported by source evidence."
        elif best_score > 0.10:
            status_val = VerificationStatus.UNSUPPORTED.value
            reasoning = f"Low lexical overlap ({best_score:.2f}). Evidence does not adequately substantiate the claim."
        else:
            status_val = VerificationStatus.INSUFFICIENT_EVIDENCE.value
            reasoning = f"Negligible evidence overlap ({best_score:.2f}) found in repository."

        if status_val in (VerificationStatus.SUPPORTED.value, VerificationStatus.PARTIALLY_SUPPORTED.value, VerificationStatus.CONFLICTING.value) and best_chunk and best_doc:
            supporting_doc_id = best_doc.id
            source_filename = best_doc.original_filename
            page_num = best_chunk.page_number
            sec_ref = best_chunk.section_title
            excerpt = best_chunk.content[:250]
            chunk_uuid = best_chunk.id
        else:
            supporting_doc_id = None
            source_filename = None
            page_num = None
            sec_ref = None
            excerpt = None
            chunk_uuid = None

        return ClaimVerificationRecord(
            id=uuid.uuid4(),
            claim_id=claim_id,
            claim_text=clean_claim,
            verification_status=status_val,
            supporting_document_id=supporting_doc_id,
            source_filename=source_filename,
            page_number=page_num,
            section_reference=sec_ref,
            supporting_text_excerpt=excerpt,
            reasoning=reasoning,
            alignment_score=round(best_score, 2),
            verification_timestamp=now,
            handover_id=handover_id,
            handover_section_id=handover_section_id,
            document_chunk_id=chunk_uuid,
        )

    async def _retrieve_relevant_chunks_for_claim(
        self,
        project_id: uuid.UUID,
        query_text: str,
        limit: int = 5,
    ) -> List[Tuple[DocumentChunk, Document]]:
        """Queries the document retrieval system using hybrid semantic & keyword search."""
        query_embedding = None
        search_mode = "hybrid"

        if settings.is_gemini_configured():
            try:
                query_embedding = gemini_service.generate_embedding(query_text[:300])
            except Exception:
                search_mode = "keyword"
        else:
            search_mode = "keyword"

        retrieved_items = await self.repo.hybrid_search(
            project_id=project_id,
            query_text=query_text,
            query_embedding=query_embedding,
            top_k=limit,
            search_mode=search_mode,
        )

        if not retrieved_items:
            return []

        chunk_ids = [item.chunk_id for item in retrieved_items]
        stmt = (
            select(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(DocumentChunk.id.in_(chunk_ids))
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    # =========================================================================
    # 2. SECTION-BY-SECTION ANALYSIS & VERIFICATION
    # =========================================================================

    async def verify_section(
        self,
        section_id: uuid.UUID,
        handover_id: Optional[uuid.UUID] = None,
    ) -> SectionVerificationReport:
        """
        Analyses a single handover section section-by-section:
        1. Retrieves section and parent handover project.
        2. Gathers all important AI-generated claims.
        3. Retrieves relevant original document chunks for each claim.
        4. Compares claims against source passages.
        5. Saves ClaimVerification and EvidenceReference records in the database.
        """
        stmt = (
            select(HandoverSection, Handover)
            .join(Handover, HandoverSection.handover_id == Handover.id)
            .where(HandoverSection.id == section_id)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            raise NotFoundException("HandoverSection", section_id)

        section, handover = row
        claims_data = self._extract_claims_from_section(section)

        # Clear previous claim verifications for this section to avoid stale duplication
        await self.db.execute(
            delete(ClaimVerification).where(ClaimVerification.handover_section_id == section.id)
        )

        verified_records: List[ClaimVerificationRecord] = []
        counts = {
            VerificationStatus.SUPPORTED.value: 0,
            VerificationStatus.PARTIALLY_SUPPORTED.value: 0,
            VerificationStatus.UNSUPPORTED.value: 0,
            VerificationStatus.CONFLICTING.value: 0,
            VerificationStatus.INSUFFICIENT_EVIDENCE.value: 0,
        }

        for claim_dict in claims_data:
            c_id = claim_dict.get("claim_id") or f"claim_{uuid.uuid4().hex[:8]}"
            c_text = claim_dict.get("statement") or claim_dict.get("claim_text") or ""
            c_chunk_ids = [uuid.UUID(str(cid)) for cid in claim_dict.get("source_chunk_ids", []) if cid]

            # Fetch any pre-referenced chunks
            candidate_chunks: List[Tuple[DocumentChunk, Document]] = []
            if c_chunk_ids:
                c_stmt = (
                    select(DocumentChunk, Document)
                    .join(Document, DocumentChunk.document_id == Document.id)
                    .where(DocumentChunk.id.in_(c_chunk_ids))
                )
                c_res = await self.db.execute(c_stmt)
                candidate_chunks = list(c_res.all())

            # Verify claim against candidate chunks or retrieved chunks
            verif_record = await self.verify_claim(
                claim_id=c_id,
                claim_text=c_text,
                project_id=handover.project_id,
                candidate_chunks=candidate_chunks,
                handover_section_id=section.id,
                handover_id=handover.id,
            )

            # Persist ClaimVerification entity
            claim_entity = ClaimVerification(
                id=uuid.uuid4(),
                handover_id=handover.id,
                handover_section_id=section.id,
                claim_id=verif_record.claim_id,
                claim_text=verif_record.claim_text,
                verification_status=verif_record.verification_status,
                supporting_document_id=verif_record.supporting_document_id,
                document_chunk_id=verif_record.document_chunk_id,
                source_filename=verif_record.source_filename,
                page_number=verif_record.page_number,
                section_reference=verif_record.section_reference,
                supporting_text_excerpt=verif_record.supporting_text_excerpt,
                reasoning=verif_record.reasoning,
                alignment_score=verif_record.alignment_score,
                verification_timestamp=verif_record.verification_timestamp,
            )
            self.db.add(claim_entity)

            # Update or create EvidenceReference for backward compatibility
            ev_ref = EvidenceReference(
                id=uuid.uuid4(),
                handover_section_id=section.id,
                document_id=verif_record.supporting_document_id,
                document_chunk_id=verif_record.document_chunk_id,
                claim_id=verif_record.claim_id,
                claim_text=verif_record.claim_text,
                quoted_text=verif_record.supporting_text_excerpt or verif_record.claim_text,
                supporting_text_excerpt=verif_record.supporting_text_excerpt,
                source_filename=verif_record.source_filename,
                page_number=verif_record.page_number,
                section_reference=verif_record.section_reference,
                relevance_score=verif_record.alignment_score,
                verification_status=verif_record.verification_status,
                reasoning=verif_record.reasoning,
                verification_timestamp=verif_record.verification_timestamp,
            )
            self.db.add(ev_ref)

            verified_records.append(verif_record)
            norm_status = normalize_verification_status(verif_record.verification_status)
            counts[norm_status] = counts.get(norm_status, 0) + 1

        await self.db.commit()

        total = len(verified_records)
        supported_total = counts[VerificationStatus.SUPPORTED.value] + counts[VerificationStatus.PARTIALLY_SUPPORTED.value]
        sec_rate = round(supported_total / total, 2) if total > 0 else 1.0

        return SectionVerificationReport(
            section_id=section.id,
            section_type=section.section_type,
            section_title=section.title,
            total_claims=total,
            supported_claims=counts[VerificationStatus.SUPPORTED.value],
            partially_supported_claims=counts[VerificationStatus.PARTIALLY_SUPPORTED.value],
            unsupported_claims=counts[VerificationStatus.UNSUPPORTED.value],
            conflicting_claims=counts[VerificationStatus.CONFLICTING.value],
            insufficient_evidence_claims=counts[VerificationStatus.INSUFFICIENT_EVIDENCE.value],
            section_support_rate=sec_rate,
            claims=verified_records,
        )

    def _extract_claims_from_section(self, section: HandoverSection) -> List[Dict[str, Any]]:
        """Extracts structured or narrative factual claims from section content."""
        content = section.content or {}
        claims: List[Dict[str, Any]] = []

        # 1. Direct claims array if available
        if "claims" in content and isinstance(content["claims"], list):
            for c in content["claims"]:
                if isinstance(c, dict) and (c.get("statement") or c.get("claim_text")):
                    claims.append(c)

        if claims:
            return claims

        # 2. Extract key statements from markdown/summary
        markdown_text = content.get("markdown", "") or content.get("summary", "")
        if markdown_text:
            sentences = re.split(r"(?<=[.!?])\s+", markdown_text)
            for idx, sentence in enumerate(sentences[:8], start=1):
                clean_s = sentence.strip()
                if len(clean_s) > 20 and not clean_s.startswith("#") and not clean_s.startswith("- ["):
                    claims.append({
                        "claim_id": f"claim_{section.section_type}_{idx}",
                        "statement": clean_s,
                        "source_chunk_ids": [],
                    })

        # 3. Fallback: section title as statement if completely empty
        if not claims:
            claims.append({
                "claim_id": f"claim_{section.section_type}_default",
                "statement": f"Overview statement for {section.title}",
                "source_chunk_ids": [],
            })

        return claims

    # =========================================================================
    # 3. END-TO-END HANDOVER VERIFICATION
    # =========================================================================

    async def verify_handover(self, handover_id: uuid.UUID) -> AdvancedHandoverVerificationReport:
        """
        Executes complete section-by-section verification across all chapters of a handover:
        1. Loads all HandoverSections in sequence.
        2. Analyses each section, retrieving source chunks and auditing every claim.
        3. Updates database entities and compiles detailed accuracy metrics.
        """
        stmt = (
            select(Handover)
            .options(selectinload(Handover.sections))
            .where(Handover.id == handover_id)
        )
        result = await self.db.execute(stmt)
        handover = result.scalar_one_or_none()
        if not handover:
            raise NotFoundException("Handover", handover_id)

        # Clear existing claim_verifications for this handover to ensure a fresh audit
        await self.db.execute(
            delete(ClaimVerification).where(ClaimVerification.handover_id == handover.id)
        )
        await self.db.commit()

        section_reports: List[SectionVerificationReport] = []
        all_claims: List[ClaimVerificationRecord] = []
        total_counts = {
            VerificationStatus.SUPPORTED.value: 0,
            VerificationStatus.PARTIALLY_SUPPORTED.value: 0,
            VerificationStatus.UNSUPPORTED.value: 0,
            VerificationStatus.CONFLICTING.value: 0,
            VerificationStatus.INSUFFICIENT_EVIDENCE.value: 0,
        }

        # Sort sections by sort_order
        sections_sorted = sorted(handover.sections, key=lambda s: s.sort_order)

        for sec in sections_sorted:
            sec_report = await self.verify_section(section_id=sec.id, handover_id=handover.id)
            section_reports.append(sec_report)
            all_claims.extend(sec_report.claims)

            total_counts[VerificationStatus.SUPPORTED.value] += sec_report.supported_claims
            total_counts[VerificationStatus.PARTIALLY_SUPPORTED.value] += sec_report.partially_supported_claims
            total_counts[VerificationStatus.UNSUPPORTED.value] += sec_report.unsupported_claims
            total_counts[VerificationStatus.CONFLICTING.value] += sec_report.conflicting_claims
            total_counts[VerificationStatus.INSUFFICIENT_EVIDENCE.value] += sec_report.insufficient_evidence_claims

        total_claims_count = len(all_claims)
        supported_total = (
            total_counts[VerificationStatus.SUPPORTED.value]
            + total_counts[VerificationStatus.PARTIALLY_SUPPORTED.value]
        )
        overall_support_rate = round(supported_total / total_claims_count, 2) if total_claims_count > 0 else 1.0

        return AdvancedHandoverVerificationReport(
            handover_id=handover.id,
            total_claims=total_claims_count,
            supported_claims=total_counts[VerificationStatus.SUPPORTED.value],
            partially_supported_claims=total_counts[VerificationStatus.PARTIALLY_SUPPORTED.value],
            unsupported_claims=total_counts[VerificationStatus.UNSUPPORTED.value],
            conflicting_claims=total_counts[VerificationStatus.CONFLICTING.value],
            insufficient_evidence_claims=total_counts[VerificationStatus.INSUFFICIENT_EVIDENCE.value],
            overall_support_rate=overall_support_rate,
            verification_timestamp=datetime.now(timezone.utc).isoformat(),
            sections=section_reports,
            claims=all_claims,
        )

    # =========================================================================
    # 4. RETRIEVAL OF VERIFICATION RESULTS (Requirement 10)
    # =========================================================================

    async def get_handover_verification_results(
        self,
        handover_id: uuid.UUID,
    ) -> AdvancedHandoverVerificationReport:
        """Retrieves stored verification results for a handover from PostgreSQL."""
        # Check handover exists
        h_stmt = select(Handover).options(selectinload(Handover.sections)).where(Handover.id == handover_id)
        h_res = await self.db.execute(h_stmt)
        handover = h_res.scalar_one_or_none()
        if not handover:
            raise NotFoundException("Handover", handover_id)

        # Fetch stored ClaimVerifications
        stmt = (
            select(ClaimVerification)
            .where(ClaimVerification.handover_id == handover_id)
            .order_by(ClaimVerification.verification_timestamp.asc())
        )
        result = await self.db.execute(stmt)
        stored_claims = list(result.scalars().all())

        # If no claim_verifications exist yet, run verification now
        if not stored_claims:
            return await self.verify_handover(handover_id)

        # Group by section
        claims_by_section: Dict[uuid.UUID, List[ClaimVerificationRecord]] = {}
        all_records: List[ClaimVerificationRecord] = []
        counts = {
            VerificationStatus.SUPPORTED.value: 0,
            VerificationStatus.PARTIALLY_SUPPORTED.value: 0,
            VerificationStatus.UNSUPPORTED.value: 0,
            VerificationStatus.CONFLICTING.value: 0,
            VerificationStatus.INSUFFICIENT_EVIDENCE.value: 0,
        }

        for sc in stored_claims:
            rec = ClaimVerificationRecord(
                id=sc.id,
                claim_id=sc.claim_id,
                claim_text=sc.claim_text,
                verification_status=normalize_verification_status(sc.verification_status),
                supporting_document_id=sc.supporting_document_id,
                source_filename=sc.source_filename,
                page_number=sc.page_number,
                section_reference=sc.section_reference,
                supporting_text_excerpt=sc.supporting_text_excerpt,
                reasoning=sc.reasoning,
                alignment_score=sc.alignment_score,
                verification_timestamp=sc.verification_timestamp,
                handover_id=sc.handover_id,
                handover_section_id=sc.handover_section_id,
                document_chunk_id=sc.document_chunk_id,
            )
            all_records.append(rec)
            status_norm = rec.verification_status
            counts[status_norm] = counts.get(status_norm, 0) + 1

            sec_id = sc.handover_section_id
            if sec_id:
                if sec_id not in claims_by_section:
                    claims_by_section[sec_id] = []
                claims_by_section[sec_id].append(rec)

        sections_sorted = sorted(handover.sections, key=lambda s: s.sort_order)
        section_reports: List[SectionVerificationReport] = []

        for sec in sections_sorted:
            sec_claims = claims_by_section.get(sec.id, [])
            s_counts = {
                VerificationStatus.SUPPORTED.value: sum(1 for c in sec_claims if c.verification_status == VerificationStatus.SUPPORTED.value),
                VerificationStatus.PARTIALLY_SUPPORTED.value: sum(1 for c in sec_claims if c.verification_status == VerificationStatus.PARTIALLY_SUPPORTED.value),
                VerificationStatus.UNSUPPORTED.value: sum(1 for c in sec_claims if c.verification_status == VerificationStatus.UNSUPPORTED.value),
                VerificationStatus.CONFLICTING.value: sum(1 for c in sec_claims if c.verification_status == VerificationStatus.CONFLICTING.value),
                VerificationStatus.INSUFFICIENT_EVIDENCE.value: sum(1 for c in sec_claims if c.verification_status == VerificationStatus.INSUFFICIENT_EVIDENCE.value),
            }
            sec_total = len(sec_claims)
            s_supp = s_counts[VerificationStatus.SUPPORTED.value] + s_counts[VerificationStatus.PARTIALLY_SUPPORTED.value]
            s_rate = round(s_supp / sec_total, 2) if sec_total > 0 else 1.0

            section_reports.append(
                SectionVerificationReport(
                    section_id=sec.id,
                    section_type=sec.section_type,
                    section_title=sec.title,
                    total_claims=sec_total,
                    supported_claims=s_counts[VerificationStatus.SUPPORTED.value],
                    partially_supported_claims=s_counts[VerificationStatus.PARTIALLY_SUPPORTED.value],
                    unsupported_claims=s_counts[VerificationStatus.UNSUPPORTED.value],
                    conflicting_claims=s_counts[VerificationStatus.CONFLICTING.value],
                    insufficient_evidence_claims=s_counts[VerificationStatus.INSUFFICIENT_EVIDENCE.value],
                    section_support_rate=s_rate,
                    claims=sec_claims,
                )
            )

        total_all = len(all_records)
        overall_supp = counts[VerificationStatus.SUPPORTED.value] + counts[VerificationStatus.PARTIALLY_SUPPORTED.value]
        overall_rate = round(overall_supp / total_all, 2) if total_all > 0 else 1.0

        latest_time = (
            max(r.verification_timestamp for r in all_records).isoformat()
            if all_records
            else datetime.now(timezone.utc).isoformat()
        )

        return AdvancedHandoverVerificationReport(
            handover_id=handover_id,
            total_claims=total_all,
            supported_claims=counts[VerificationStatus.SUPPORTED.value],
            partially_supported_claims=counts[VerificationStatus.PARTIALLY_SUPPORTED.value],
            unsupported_claims=counts[VerificationStatus.UNSUPPORTED.value],
            conflicting_claims=counts[VerificationStatus.CONFLICTING.value],
            insufficient_evidence_claims=counts[VerificationStatus.INSUFFICIENT_EVIDENCE.value],
            overall_support_rate=overall_rate,
            verification_timestamp=latest_time,
            sections=section_reports,
            claims=all_records,
        )

    async def get_section_verification_results(
        self,
        section_id: uuid.UUID,
    ) -> SectionVerificationReport:
        """Retrieves verification results for a specific section."""
        stmt = (
            select(HandoverSection)
            .where(HandoverSection.id == section_id)
        )
        res = await self.db.execute(stmt)
        section = res.scalar_one_or_none()
        if not section:
            raise NotFoundException("HandoverSection", section_id)

        c_stmt = (
            select(ClaimVerification)
            .where(ClaimVerification.handover_section_id == section_id)
            .order_by(ClaimVerification.verification_timestamp.asc())
        )
        c_res = await self.db.execute(c_stmt)
        stored_claims = list(c_res.scalars().all())

        if not stored_claims:
            return await self.verify_section(section_id=section_id)

        records: List[ClaimVerificationRecord] = []
        counts = {
            VerificationStatus.SUPPORTED.value: 0,
            VerificationStatus.PARTIALLY_SUPPORTED.value: 0,
            VerificationStatus.UNSUPPORTED.value: 0,
            VerificationStatus.CONFLICTING.value: 0,
            VerificationStatus.INSUFFICIENT_EVIDENCE.value: 0,
        }

        for sc in stored_claims:
            rec = ClaimVerificationRecord(
                id=sc.id,
                claim_id=sc.claim_id,
                claim_text=sc.claim_text,
                verification_status=normalize_verification_status(sc.verification_status),
                supporting_document_id=sc.supporting_document_id,
                source_filename=sc.source_filename,
                page_number=sc.page_number,
                section_reference=sc.section_reference,
                supporting_text_excerpt=sc.supporting_text_excerpt,
                reasoning=sc.reasoning,
                alignment_score=sc.alignment_score,
                verification_timestamp=sc.verification_timestamp,
                handover_id=sc.handover_id,
                handover_section_id=sc.handover_section_id,
                document_chunk_id=sc.document_chunk_id,
            )
            records.append(rec)
            st = rec.verification_status
            counts[st] = counts.get(st, 0) + 1

        total = len(records)
        supp = counts[VerificationStatus.SUPPORTED.value] + counts[VerificationStatus.PARTIALLY_SUPPORTED.value]
        rate = round(supp / total, 2) if total > 0 else 1.0

        return SectionVerificationReport(
            section_id=section.id,
            section_type=section.section_type,
            section_title=section.title,
            total_claims=total,
            supported_claims=counts[VerificationStatus.SUPPORTED.value],
            partially_supported_claims=counts[VerificationStatus.PARTIALLY_SUPPORTED.value],
            unsupported_claims=counts[VerificationStatus.UNSUPPORTED.value],
            conflicting_claims=counts[VerificationStatus.CONFLICTING.value],
            insufficient_evidence_claims=counts[VerificationStatus.INSUFFICIENT_EVIDENCE.value],
            section_support_rate=rate,
            claims=records,
        )

    async def get_claim_verification(
        self,
        claim_id: str,
    ) -> Optional[ClaimVerificationRecord]:
        """Retrieves a single claim verification record by claim ID."""
        stmt = (
            select(ClaimVerification)
            .where(ClaimVerification.claim_id == claim_id)
            .order_by(ClaimVerification.verification_timestamp.desc())
        )
        res = await self.db.execute(stmt)
        sc = res.scalar_one_or_none()
        if not sc:
            return None

        return ClaimVerificationRecord(
            id=sc.id,
            claim_id=sc.claim_id,
            claim_text=sc.claim_text,
            verification_status=normalize_verification_status(sc.verification_status),
            supporting_document_id=sc.supporting_document_id,
            source_filename=sc.source_filename,
            page_number=sc.page_number,
            section_reference=sc.section_reference,
            supporting_text_excerpt=sc.supporting_text_excerpt,
            reasoning=sc.reasoning,
            alignment_score=sc.alignment_score,
            verification_timestamp=sc.verification_timestamp,
            handover_id=sc.handover_id,
            handover_section_id=sc.handover_section_id,
            document_chunk_id=sc.document_chunk_id,
        )

    # =========================================================================
    # 5. BACKWARD-COMPATIBLE METHODS FOR STEP 10 TESTS & CITATIONS
    # =========================================================================

    async def verify_claim_against_chunks(
        self,
        claim_text: str,
        chunks: List[DocumentChunk],
    ) -> ClaimVerificationResult:
        """
        Backward-compatible helper used in Step 10 unit tests.
        Compares an individual factual claim against one or more source chunks.
        """
        clean_claim = claim_text.strip()
        if not clean_claim:
            raise ValidationException("Claim text cannot be empty.")

        if not chunks:
            return ClaimVerificationResult(
                claim_text=clean_claim,
                verification_status=EvidenceStatus.UNSUPPORTED,
                alignment_score=0.0,
                reasoning="No referenced source chunks were found to substantiate this claim.",
                supported_facts=[],
                unsupported_facts=[clean_claim],
                chunks_evaluated=0,
            )

        passages = [f"[Chunk {idx+1} | Page {ch.page_number or 1}]: {ch.content}" for idx, ch in enumerate(chunks)]
        combined_passage = "\n\n".join(passages)

        if settings.is_gemini_configured():
            prompt = f"""
Compare the following technical CLAIM against the original SOURCE EVIDENCE PASSAGES.
Determine strictly whether the evidence directly substantiates the claim.

CLAIM:
"{clean_claim}"

SOURCE EVIDENCE PASSAGES:
{combined_passage}

INSTRUCTIONS:
Assign one of the 4 verification statuses:
- "SUPPORTED"
- "PARTIALLY_SUPPORTED"
- "UNSUPPORTED"
- "NEEDS_REVIEW"

OUTPUT FORMAT:
Respond with ONLY valid JSON:
{{
  "verification_status": "SUPPORTED" | "PARTIALLY_SUPPORTED" | "UNSUPPORTED" | "NEEDS_REVIEW",
  "alignment_score": 0.95,
  "reasoning": "...",
  "supported_facts": ["..."],
  "unsupported_facts": ["..."]
}}
"""
            system_instruction = (
                "You are an impartial fact-checking and Natural Language Inference (NLI) evaluator. "
                "Assess factual entailment strictly against the provided text. Never assume facts not in the text."
            )
            try:
                raw_eval = gemini_service.generate_content(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=0.0,
                )
                cleaned = self._clean_json(raw_eval)
                status_str = cleaned.get("verification_status", "NEEDS_REVIEW").upper()
                if status_str not in EvidenceStatus.__members__:
                    status_str = "NEEDS_REVIEW"

                return ClaimVerificationResult(
                    claim_text=clean_claim,
                    verification_status=EvidenceStatus(status_str),
                    alignment_score=float(cleaned.get("alignment_score", 0.8)),
                    reasoning=cleaned.get("reasoning", "Evaluated against ground truth chunks."),
                    supported_facts=cleaned.get("supported_facts", []),
                    unsupported_facts=cleaned.get("unsupported_facts", []),
                    chunks_evaluated=len(chunks),
                )
            except Exception as exc:
                logger.warning(f"Gemini NLI verification encountered an error: {exc}. Using deterministic fallback.")

        overlap_score = self._calculate_token_overlap(clean_claim, combined_passage)
        if overlap_score >= 0.60:
            status_val = EvidenceStatus.SUPPORTED
            reasoning = f"High lexical overlap ({overlap_score:.2f}) with source evidence."
        elif overlap_score >= 0.35:
            status_val = EvidenceStatus.PARTIALLY_SUPPORTED
            reasoning = f"Moderate lexical overlap ({overlap_score:.2f}). Some specific claim elements may require review."
        else:
            status_val = EvidenceStatus.UNSUPPORTED
            reasoning = f"Low lexical overlap ({overlap_score:.2f}). Evidence does not adequately substantiate the claim."

        return ClaimVerificationResult(
            claim_text=clean_claim,
            verification_status=status_val,
            alignment_score=round(overlap_score, 2),
            reasoning=reasoning,
            supported_facts=[clean_claim] if overlap_score >= 0.5 else [],
            unsupported_facts=[] if overlap_score >= 0.5 else [clean_claim],
            chunks_evaluated=len(chunks),
        )

    async def verify_evidence_reference(self, evidence_id: uuid.UUID) -> ClaimVerificationResult:
        """Verifies an existing EvidenceReference row in PostgreSQL against its linked chunk."""
        stmt = (
            select(EvidenceReference, DocumentChunk)
            .outerjoin(DocumentChunk, EvidenceReference.document_chunk_id == DocumentChunk.id)
            .where(EvidenceReference.id == evidence_id)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            raise NotFoundException("EvidenceReference", evidence_id)

        evidence, chunk = row
        chunks = [chunk] if chunk else []

        eval_result = await self.verify_claim_against_chunks(
            claim_text=evidence.quoted_text,
            chunks=chunks,
        )

        evidence.verification_status = eval_result.verification_status.value
        evidence.relevance_score = eval_result.alignment_score
        await self.db.commit()

        return eval_result

    async def verify_handover_all_claims(self, handover_id: uuid.UUID) -> HandoverVerificationReport:
        """Legacy helper: Audits all evidence references for a handover package against the original chunks."""
        adv_report = await self.verify_handover(handover_id)

        return HandoverVerificationReport(
            handover_id=handover_id,
            total_claims=adv_report.total_claims,
            supported_claims=adv_report.supported_claims,
            partially_supported_claims=adv_report.partially_supported_claims,
            unsupported_claims=adv_report.unsupported_claims,
            needs_review_claims=adv_report.insufficient_evidence_claims,
            overall_support_rate=adv_report.overall_support_rate,
            verification_timestamp=adv_report.verification_timestamp,
            conflicting_claims=adv_report.conflicting_claims,
            insufficient_evidence_claims=adv_report.insufficient_evidence_claims,
            claims=adv_report.claims,
        )

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.document import Document, DocumentChunk
from app.models.evidence import EvidenceReference
from app.models.handover import Handover, HandoverSection
from app.services.gemini_service import gemini_service
from app.schemas.handover import (
    EvidenceStatus,
    ClaimVerificationResult,
    HandoverVerificationReport,
)

logger = logging.getLogger("app.services.verification")


class EvidenceVerificationService:
    """
    Independent Evidence Verification & Factual Alignment Engine.
    
    Rule: Never treats Gemini's generation confidence as proof of correctness.
    Directly compares generated factual claims against the ground-truth text in source chunks.
    Assigns: SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, or NEEDS_REVIEW.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _calculate_token_overlap(claim: str, passage: str) -> float:
        """Fallback deterministic token overlap calculation for offline / test environments."""
        claim_words = set(re.findall(r"\w+", claim.lower()))
        passage_words = set(re.findall(r"\w+", passage.lower()))
        # Remove common stop words
        stopwords = {"the", "a", "an", "is", "are", "and", "or", "to", "in", "of", "for", "with", "on", "at", "by", "from"}
        meaningful_claim_words = claim_words - stopwords
        if not meaningful_claim_words:
            return 1.0 if claim_words.issubset(passage_words) else 0.0

        overlap = meaningful_claim_words.intersection(passage_words)
        return len(overlap) / len(meaningful_claim_words)

    async def verify_claim_against_chunks(
        self,
        claim_text: str,
        chunks: List[DocumentChunk],
    ) -> ClaimVerificationResult:
        """
        Compares an individual factual claim against one or more ground truth source chunks.
        Determines whether the evidence substantiates the claim.
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

        # If Gemini is configured, use impartial NLI evaluation prompt
        if settings.is_gemini_configured():
            prompt = f"""
Compare the following technical CLAIM against the original SOURCE EVIDENCE PASSAGES.
Determine strictly whether the evidence directly substantiates the claim.

CLAIM:
"{clean_claim}"

SOURCE EVIDENCE PASSAGES:
{combined_passage}

INSTRUCTIONS:
1. Assign one of the 4 verification statuses:
   - "SUPPORTED": The evidence fully confirms all aspects of the claim (numbers, configurations, names, relationships).
   - "PARTIALLY_SUPPORTED": The evidence partially supports the claim, but some specific facts/figures/details are missing or extrapolated.
   - "UNSUPPORTED": The evidence contradicts the claim, or the claim is not mentioned at all.
   - "NEEDS_REVIEW": The evidence is ambiguous, complex, or cannot be verified with certainty without human review.

2. Compute an alignment score between 0.0 and 1.0 (1.0 = fully substantiated, 0.0 = completely unsupported or contradictory).

3. Provide a concise explanation of the verdict, listing any supported facts and any unsupported/extrapolated facts.

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
                    temperature=0.0,  # Zero temperature for deterministic evaluation
                )
                # Clean JSON markdown fences
                cleaned = raw_eval.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
                    cleaned = re.sub(r"\n?```$", "", cleaned)
                data = json.loads(cleaned.strip())

                status_str = data.get("verification_status", "NEEDS_REVIEW").upper()
                if status_str not in EvidenceStatus.__members__:
                    status_str = "NEEDS_REVIEW"

                return ClaimVerificationResult(
                    claim_text=clean_claim,
                    verification_status=EvidenceStatus(status_str),
                    alignment_score=float(data.get("alignment_score", 0.8)),
                    reasoning=data.get("reasoning", "Evaluated against ground truth chunks."),
                    supported_facts=data.get("supported_facts", []),
                    unsupported_facts=data.get("unsupported_facts", []),
                    chunks_evaluated=len(chunks),
                )
            except Exception as exc:
                logger.warning(f"Gemini NLI verification encountered an error: {exc}. Using deterministic fallback.")

        # Fallback deterministic token overlap verification
        overlap_score = self._calculate_token_overlap(clean_claim, combined_passage)
        if overlap_score >= 0.70:
            status_val = EvidenceStatus.SUPPORTED
            reasoning = f"High lexical and entity overlap ({overlap_score:.2f}) with source evidence."
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
        """
        Verifies an existing EvidenceReference row in PostgreSQL against its linked DocumentChunk.
        Updates the verification status and relevance score in the database.
        """
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

        # Update evidence record
        evidence.verification_status = eval_result.verification_status.value
        evidence.relevance_score = eval_result.alignment_score
        await self.db.commit()

        return eval_result

    async def verify_handover_all_claims(self, handover_id: uuid.UUID) -> HandoverVerificationReport:
        """
        Audits all evidence references for a handover package against the original chunks.
        Updates verification statuses in the database and computes an accuracy report.
        """
        stmt = (
            select(EvidenceReference, DocumentChunk)
            .join(HandoverSection, EvidenceReference.handover_section_id == HandoverSection.id)
            .outerjoin(DocumentChunk, EvidenceReference.document_chunk_id == DocumentChunk.id)
            .where(HandoverSection.handover_id == handover_id)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        counts = {
            EvidenceStatus.SUPPORTED: 0,
            EvidenceStatus.PARTIALLY_SUPPORTED: 0,
            EvidenceStatus.UNSUPPORTED: 0,
            EvidenceStatus.NEEDS_REVIEW: 0,
        }

        for ev, chunk in rows:
            chunks = [chunk] if chunk else []
            eval_res = await self.verify_claim_against_chunks(claim_text=ev.quoted_text, chunks=chunks)
            ev.verification_status = eval_res.verification_status.value
            ev.relevance_score = eval_res.alignment_score
            counts[eval_res.verification_status] += 1

        await self.db.commit()

        total = len(rows)
        supported_or_partial = counts[EvidenceStatus.SUPPORTED] + counts[EvidenceStatus.PARTIALLY_SUPPORTED]
        overall_rate = round((supported_or_partial / total), 2) if total > 0 else 1.0

        return HandoverVerificationReport(
            handover_id=handover_id,
            total_claims=total,
            supported_claims=counts[EvidenceStatus.SUPPORTED],
            partially_supported_claims=counts[EvidenceStatus.PARTIALLY_SUPPORTED],
            unsupported_claims=counts[EvidenceStatus.UNSUPPORTED],
            needs_review_claims=counts[EvidenceStatus.NEEDS_REVIEW],
            overall_support_rate=overall_rate,
            verification_timestamp=datetime.now(timezone.utc).isoformat(),
        )

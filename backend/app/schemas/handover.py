import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class HandoverStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    SHARED = "SHARED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REJECTED = "REJECTED"


class FactualClaim(BaseModel):
    """Atomic factual claim with explicit source attribution and verification status."""
    claim_id: str = Field(default_factory=lambda: f"claim_{uuid.uuid4().hex[:8]}")
    statement: str = Field(..., description="The factual claim or observation")
    source_document_ids: List[str] = Field(default_factory=list, description="Document UUIDs backing this claim")
    source_chunk_ids: List[str] = Field(default_factory=list, description="Chunk UUIDs backing this claim")
    page_numbers: List[int] = Field(default_factory=list, description="Page numbers where evidence occurs")
    quoted_text: Optional[str] = Field(None, description="Exact short quote from the source chunk")
    evidence_status: EvidenceStatus = Field(EvidenceStatus.SUPPORTED, description="SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, NEEDS_REVIEW")


class Recommendation(BaseModel):
    """Explicitly distinguished AI suggestion, separated from documented facts."""
    recommendation_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:8]}")
    title: str
    description: str
    timeframe: str = Field("immediate", description="immediate, short_term, long_term")
    is_recommendation: bool = True
    rationale: Optional[str] = None


class SectionContent(BaseModel):
    """Structured and narrative content of an individual handover chapter."""
    summary: str = Field(..., description="High-level summary of the chapter")
    markdown: str = Field(..., description="Comprehensive markdown documentation")
    structured_data: Dict[str, Any] = Field(default_factory=dict, description="Domain specific structured key-values")
    claims: List[FactualClaim] = Field(default_factory=list, description="Factual claims backed by evidence")
    recommendations: List[Recommendation] = Field(default_factory=list, description="Recommendations explicitly labelled")


class GeneratedSection(BaseModel):
    """Single handover chapter produced by AI synthesis."""
    section_type: str = Field(..., description="Identifier: project_overview, technical_architecture, etc.")
    title: str = Field(..., description="Human-readable title")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    content: SectionContent


class GeneratedConflict(BaseModel):
    """Contradiction identified between source documents."""
    conflict_type: str = Field("architecture", description="architecture, owner, date, process, security")
    description: str
    source_a_chunk_id: Optional[str] = None
    source_a_quote: Optional[str] = None
    source_b_chunk_id: Optional[str] = None
    source_b_quote: Optional[str] = None


class GeneratedTask(BaseModel):
    """Actionable transition responsibility or pending task."""
    title: str
    description: Optional[str] = None
    priority: str = Field("medium", description="critical, high, medium, low")
    assigned_to_name: Optional[str] = None
    due_date_hint: Optional[str] = None


class HandoverAIGenerationOutput(BaseModel):
    """Complete structured JSON output format produced by Gemini RAG synthesis."""
    title: str = Field("Engineering Knowledge Handover", description="Handover package title")
    sections: List[GeneratedSection]
    conflicts: List[GeneratedConflict] = Field(default_factory=list)
    tasks: List[GeneratedTask] = Field(default_factory=list)


# =============================================================================
# REQUEST & RESPONSE SCHEMAS
# =============================================================================

class GenerationRequest(BaseModel):
    """Payload to trigger AI-powered structured handover synthesis."""
    projectId: Optional[uuid.UUID] = None
    targetRole: Optional[str] = Field("Incoming Engineer", description="Target role of the recipient")
    handoverScope: Optional[str] = Field("Comprehensive", description="Scope of handover (e.g. Architecture, Operational, Comprehensive)")
    timelineScope: Optional[str] = Field("All Time", description="Timeline window of documents to synthesize")
    selectedDocumentIds: Optional[List[uuid.UUID]] = Field(default_factory=list, description="Optional document filter")
    additionalInstructions: Optional[str] = Field(None, description="Special focus areas or user instructions")
    title: Optional[str] = Field(None, description="Custom title for the handover")


class SectionRegenerateRequest(BaseModel):
    """Payload to re-synthesize a single handover section without touching the rest."""
    instructions: Optional[str] = Field(None, description="Custom instructions or focus for regenerating this section")


class EvidenceReferenceResponse(BaseModel):
    """Citations linking synthesized claims directly to source chunks."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handover_section_id: uuid.UUID
    document_id: uuid.UUID
    document_chunk_id: Optional[uuid.UUID] = None
    quoted_text: str
    page_number: Optional[int] = None
    relevance_score: float = 1.0
    verification_status: str = "SUPPORTED"
    source_document_name: Optional[str] = None


class HandoverSectionResponse(BaseModel):
    """Structured chapter / section of the handover package."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handover_id: uuid.UUID
    section_type: str
    title: str
    content: Dict[str, Any]
    confidence: float = 1.0
    review_status: str = "pending"
    sort_order: int = 0
    evidence_references: List[EvidenceReferenceResponse] = []


class HandoverSectionUpdate(BaseModel):
    """Payload to edit or approve an individual handover section."""
    title: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    review_status: Optional[str] = Field(None, description="pending, approved, changes_requested, rejected")


class ConflictResponse(BaseModel):
    """Discrepancies or contradictory claims identified between documents."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    handover_id: Optional[uuid.UUID] = None
    conflict_type: str
    description: str
    source_a: Dict[str, Any]
    source_b: Dict[str, Any]
    status: str = "OPEN"  # OPEN, UNDER_REVIEW, RESOLVED, DISMISSED
    resolution: Optional[Dict[str, Any]] = None
    resolved_by: Optional[uuid.UUID] = None
    created_at: datetime


class ConflictUpdateRequest(BaseModel):
    """Payload to update conflict status (e.g. mark UNDER_REVIEW) or description."""
    status: Optional[str] = Field(None, description="OPEN, UNDER_REVIEW, RESOLVED, DISMISSED")
    description: Optional[str] = None
    notes: Optional[str] = None


class ConflictResolveRequest(BaseModel):
    """Payload to mark a contradiction resolved with human notes."""
    chosen_source: Optional[str] = Field(None, description="source_a, source_b, or custom")
    chosen_value: Optional[str] = Field(None, description="The accepted factual value")
    resolution_notes: str = Field(..., description="Human reviewer explanation of the resolution")
    status: str = Field("RESOLVED", description="RESOLVED or DISMISSED")


class ClaimVerificationRequest(BaseModel):
    """Payload to verify an ad-hoc factual claim against source chunk passages."""
    claim_text: str = Field(..., description="The factual claim to verify")
    chunk_ids: List[uuid.UUID] = Field(default_factory=list, description="Referenced source chunk UUIDs")


class ClaimVerificationResult(BaseModel):
    """Factual alignment verdict and evidence verification result."""
    claim_text: str
    verification_status: EvidenceStatus
    alignment_score: float
    reasoning: str
    supported_facts: List[str] = Field(default_factory=list)
    unsupported_facts: List[str] = Field(default_factory=list)
    chunks_evaluated: int


class HandoverVerificationReport(BaseModel):
    """Audit report detailing verification statuses across all handover claims."""
    handover_id: uuid.UUID
    total_claims: int
    supported_claims: int
    partially_supported_claims: int
    unsupported_claims: int
    needs_review_claims: int
    overall_support_rate: float
    verification_timestamp: str



class TaskResponse(BaseModel):
    """Continuation responsibility item transferred to incoming member."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    handover_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None


class HandoverSummaryResponse(BaseModel):
    """Summary overview for listing handovers."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    status: str
    version: str
    created_by: Optional[uuid.UUID] = None
    assigned_to: Optional[uuid.UUID] = None
    generated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    shared_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sections_count: Optional[int] = None
    conflicts_count: Optional[int] = None
    tasks_count: Optional[int] = None


class HandoverDetailResponse(BaseModel):
    """Full comprehensive handover representation including all sections, citations, and conflicts."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    assigned_to: Optional[uuid.UUID] = None
    title: str
    status: str
    version: str
    generated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    shared_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sections: List[HandoverSectionResponse] = []
    conflicts: List[ConflictResponse] = []
    tasks: List[TaskResponse] = []


class SubmitReviewRequest(BaseModel):
    """Payload to submit a draft or changes-requested handover for lead review."""
    notes: Optional[str] = Field(None, description="Optional notes or summary for reviewer")


class RequestChangesRequest(BaseModel):
    """Payload for reviewer to request changes on a handover."""
    feedback: str = Field(..., min_length=1, description="Detailed review feedback describing required changes")
    section_ids: Optional[List[uuid.UUID]] = Field(default_factory=list, description="Specific sections requiring revisions")


class ApproveHandoverRequest(BaseModel):
    """Payload for lead or admin to formally approve a handover."""
    notes: Optional[str] = Field(None, description="Formal approval comments or signoff notes")


class ShareHandoverRequest(BaseModel):
    """Payload to share an approved handover with incoming team members."""
    assigned_to: Optional[uuid.UUID] = Field(None, description="Incoming member UUID to assign and notify")
    recipient_emails: Optional[List[str]] = Field(default_factory=list, description="Optional incoming recipient emails")
    notes: Optional[str] = Field(None, description="Welcome or transition guidance notes for incoming members")


class AcknowledgeHandoverRequest(BaseModel):
    """Payload for incoming member to acknowledge receipt and accept responsibility."""
    checklist_confirmed: bool = Field(True, description="Confirmation that incoming member reviewed all sections and responsibilities")
    notes: Optional[str] = Field(None, description="Acknowledgement confirmation remarks")


class RejectHandoverRequest(BaseModel):
    """Payload to formally reject a handover."""
    reason: str = Field(..., min_length=1, description="Reason for rejection")


class HandoverAuditLogResponse(BaseModel):
    """Audit log entry tracking who took which action and when."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handover_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


class HandoverVersionResponse(BaseModel):
    """Immutable snapshot of an approved handover revision."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handover_id: uuid.UUID
    version_number: str
    created_by: Optional[uuid.UUID] = None
    creator_name: Optional[str] = None
    created_at: datetime
    snapshot: Dict[str, Any]


class HandoverHistoryResponse(BaseModel):
    """Complete audit timeline and immutable version snapshots for a handover."""
    handover_id: uuid.UUID
    current_version: str
    current_status: str
    audit_logs: List[HandoverAuditLogResponse] = []
    versions: List[HandoverVersionResponse] = []

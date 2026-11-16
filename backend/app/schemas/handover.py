import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class VerificationStatus(str, Enum):
    SUPPORTED = "Supported"
    PARTIALLY_SUPPORTED = "Partially Supported"
    UNSUPPORTED = "Unsupported"
    CONFLICTING = "Conflicting"
    INSUFFICIENT_EVIDENCE = "Insufficient Evidence"


def normalize_verification_status(status_input: Any) -> str:
    """Normalizes any verification status representation to human-readable Title Case."""
    if status_input is None:
        return VerificationStatus.INSUFFICIENT_EVIDENCE.value
    raw = str(getattr(status_input, "value", status_input)).strip().upper().replace(" ", "_")
    mapping = {
        "SUPPORTED": VerificationStatus.SUPPORTED.value,
        "PARTIALLY_SUPPORTED": VerificationStatus.PARTIALLY_SUPPORTED.value,
        "UNSUPPORTED": VerificationStatus.UNSUPPORTED.value,
        "CONFLICTING": VerificationStatus.CONFLICTING.value,
        "INSUFFICIENT_EVIDENCE": VerificationStatus.INSUFFICIENT_EVIDENCE.value,
        "NEEDS_REVIEW": VerificationStatus.INSUFFICIENT_EVIDENCE.value,
    }
    return mapping.get(raw, VerificationStatus.INSUFFICIENT_EVIDENCE.value)


class HandoverStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    SHARED = "SHARED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REJECTED = "REJECTED"


class HandoverTransitionStatus(str, Enum):
    """Lifecycle transition statuses for incoming member continuity workflow."""
    AWAITING_ACKNOWLEDGEMENT = "Awaiting Acknowledgement"
    ACKNOWLEDGED = "Acknowledged"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


def normalize_transition_status(status_input: Any) -> str:
    """Normalizes any transition status representation to human-readable Title Case."""
    if not status_input:
        return HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value
    raw = str(getattr(status_input, "value", status_input)).strip().upper().replace(" ", "_").replace("-", "_")
    mapping = {
        "AWAITING_ACKNOWLEDGEMENT": HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value,
        "AWAITING": HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value,
        "PENDING": HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value,
        "ACKNOWLEDGED": HandoverTransitionStatus.ACKNOWLEDGED.value,
        "IN_PROGRESS": HandoverTransitionStatus.IN_PROGRESS.value,
        "INPROGRESS": HandoverTransitionStatus.IN_PROGRESS.value,
        "COMPLETED": HandoverTransitionStatus.COMPLETED.value,
        "DONE": HandoverTransitionStatus.COMPLETED.value,
    }
    return mapping.get(raw, HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value)


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
    summary: str = Field(default="", description="High-level summary of the chapter")
    markdown: str = Field(default="", description="Comprehensive markdown documentation")
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
    document_id: Optional[uuid.UUID] = None
    document_chunk_id: Optional[uuid.UUID] = None
    claim_id: Optional[str] = None
    claim_text: Optional[str] = None
    quoted_text: str = ""
    supporting_text_excerpt: Optional[str] = None
    source_filename: Optional[str] = None
    page_number: Optional[int] = None
    section_reference: Optional[str] = None
    relevance_score: float = 1.0
    verification_status: str = "Supported"
    reasoning: Optional[str] = None
    verification_timestamp: Optional[datetime] = None
    source_document_name: Optional[str] = None


class HandoverSectionResponse(BaseModel):
    """Structured chapter / section of the handover package."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handover_id: uuid.UUID
    section_type: str
    title: str
    content: Dict[str, Any]
    confidence: Optional[float] = 1.0
    review_status: str = "pending"
    sort_order: Optional[int] = 0
    evidence_references: List[EvidenceReferenceResponse] = []


class HandoverSectionUpdate(BaseModel):
    """Payload to edit or approve an individual handover section."""
    title: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    review_status: Optional[str] = Field(None, description="pending, approved, changes_requested, rejected")


from app.schemas.conflict import (
    ConflictCategory,
    ConflictResolutionStatus,
    normalize_conflict_status,
    FactualStatement,
    ContradictionEvaluation,
    ConflictResponse,
    ConflictUpdateRequest,
    ConflictResolveRequest,
    ContradictionDetectionReport,
)


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


class ClaimVerificationRecord(BaseModel):
    """Traceable, audited claim record adhering to the 8 required evidence fields."""
    model_config = ConfigDict(from_attributes=True)

    claim_id: str
    claim_text: str
    verification_status: str  # Supported, Partially Supported, Unsupported, Conflicting, Insufficient Evidence
    supporting_document_id: Optional[uuid.UUID] = None
    source_filename: Optional[str] = None
    page_number: Optional[int] = None
    section_reference: Optional[str] = None
    supporting_text_excerpt: Optional[str] = None
    verification_timestamp: datetime
    # Optional supplementary audit fields
    id: Optional[uuid.UUID] = None
    handover_id: Optional[uuid.UUID] = None
    handover_section_id: Optional[uuid.UUID] = None
    document_chunk_id: Optional[uuid.UUID] = None
    alignment_score: float = 0.0
    reasoning: Optional[str] = None


class SectionVerificationReport(BaseModel):
    """Section-level verification breakdown with claim-level evidence results."""
    section_id: uuid.UUID
    section_type: str
    section_title: str
    total_claims: int
    supported_claims: int
    partially_supported_claims: int
    unsupported_claims: int
    conflicting_claims: int
    insufficient_evidence_claims: int
    section_support_rate: float
    claims: List[ClaimVerificationRecord] = []


class AdvancedHandoverVerificationReport(BaseModel):
    """Complete multi-chapter handover evidence verification report."""
    handover_id: uuid.UUID
    total_claims: int
    supported_claims: int
    partially_supported_claims: int
    unsupported_claims: int
    conflicting_claims: int
    insufficient_evidence_claims: int
    overall_support_rate: float
    verification_timestamp: str
    sections: List[SectionVerificationReport] = []
    claims: List[ClaimVerificationRecord] = []


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
    conflicting_claims: int = 0
    insufficient_evidence_claims: int = 0
    claims: List[ClaimVerificationRecord] = []



class TaskResponse(BaseModel):
    """Continuation responsibility item transferred to incoming member."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    handover_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    dependencies_count: int = 0
    dependents_count: int = 0
    is_blocked: bool = False


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
    transition_status: Optional[str] = "Awaiting Acknowledgement"
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[uuid.UUID] = None
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
    transition_status: Optional[str] = "Awaiting Acknowledgement"
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[uuid.UUID] = None
    acknowledgement_notes: Optional[str] = None
    checklist_confirmed: Optional[bool] = False
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


class RestoreVersionRequest(BaseModel):
    """Payload to restore a handover to a previous version snapshot."""
    reason: Optional[str] = Field("Restored from version snapshot", description="Reason for restoring previous version")


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
    """Immutable snapshot of a handover revision with approval status and parent lineage."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handover_id: uuid.UUID
    version_number: str
    version_description: Optional[str] = None
    approval_status: str = "DRAFT"
    parent_version_id: Optional[uuid.UUID] = None
    is_latest: bool = False
    created_by: Optional[uuid.UUID] = None
    creator_name: Optional[str] = None
    created_at: datetime
    snapshot: Dict[str, Any]


class VersionCreateRequest(BaseModel):
    """Payload to create a new manual revision snapshot."""
    version_description: Optional[str] = Field(None, description="Description / changelog summary for this revision")


class ContentChangeType(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    UNCHANGED = "UNCHANGED"


class SectionDiff(BaseModel):
    """Diff details for an individual chapter/section between two versions."""
    section_type: str
    title: str
    has_changed: bool
    change_type: str = "UNCHANGED"
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    added_lines: List[str] = []
    removed_lines: List[str] = []
    diff_summary: Optional[str] = None


class TaskDiff(BaseModel):
    """Diff details for tasks between two versions, highlighting status & assignee changes."""
    task_id: Optional[str] = None
    title: str
    change_type: str = "UNCHANGED"
    status_changed: bool = False
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    assignee_changed: bool = False
    old_assignee: Optional[str] = None
    new_assignee: Optional[str] = None
    priority_changed: bool = False
    old_priority: Optional[str] = None
    new_priority: Optional[str] = None
    description_changed: bool = False


class ResponsibilityDiff(BaseModel):
    """Changes in team responsibilities and task assignments between versions."""
    entity_type: str = "task"
    entity_id: Optional[str] = None
    entity_name: str
    change_type: str = "MODIFIED"
    old_assignee: Optional[str] = None
    new_assignee: Optional[str] = None
    details: Optional[str] = None


class ComparisonSummary(BaseModel):
    """High-level summary of additions, removals, modifications, status and responsibility changes."""
    total_sections_compared: int = 0
    added_sections_count: int = 0
    removed_sections_count: int = 0
    modified_sections_count: int = 0
    unchanged_sections_count: int = 0
    total_tasks_compared: int = 0
    added_tasks_count: int = 0
    removed_tasks_count: int = 0
    task_status_changes_count: int = 0
    responsibility_changes_count: int = 0
    has_differences: bool = False
    category_status: Dict[str, str] = {}


class VersionDiffResponse(BaseModel):
    """Structured section-by-section comparison between two version snapshots."""
    from_version_id: uuid.UUID
    from_version_number: str
    to_version_id: uuid.UUID
    to_version_number: str
    summary: ComparisonSummary = Field(default_factory=ComparisonSummary)
    section_diffs: List[SectionDiff] = []
    task_diffs: List[TaskDiff] = []
    responsibility_diffs: List[ResponsibilityDiff] = []


class HandoverHistoryResponse(BaseModel):
    """Complete audit timeline and immutable version snapshots for a handover."""
    handover_id: uuid.UUID
    current_version: str
    current_status: str
    audit_logs: List[HandoverAuditLogResponse] = []
    versions: List[HandoverVersionResponse] = []


class TransitionStatusUpdateRequest(BaseModel):
    """Payload to transition the handover continuation status."""
    transition_status: str = Field(..., description="Target status: Awaiting Acknowledgement, Acknowledged, In Progress, Completed")
    notes: Optional[str] = Field(None, description="Optional transition rationale or progress remarks")


class HandoverContinuityTaskSummary(BaseModel):
    """Aggregate progress metrics for incoming member continuity."""
    total_tasks: int = 0
    pending_tasks: int = 0
    in_progress_tasks: int = 0
    completed_tasks: int = 0
    blocked_tasks: int = 0
    overdue_tasks: int = 0
    completion_percentage: float = 0.0


class SharedHandoverResponse(BaseModel):
    """Handover accessible to incoming team member."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    project_title: Optional[str] = None
    title: str
    version: str = "v1.0"
    status: str = "APPROVED"
    transition_status: str = "Awaiting Acknowledgement"
    approved_at: Optional[datetime] = None
    shared_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[uuid.UUID] = None
    acknowledged_by_name: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None
    pending_tasks_count: int = 0
    overdue_tasks_count: int = 0


class HandoverContinuityResponse(BaseModel):
    """Comprehensive handover continuation dashboard for incoming members."""
    handover_id: uuid.UUID
    project_id: uuid.UUID
    project_title: Optional[str] = None
    title: str
    version: str = "v1.0"
    status: str = "APPROVED"
    transition_status: str = "Awaiting Acknowledgement"
    approved_at: Optional[datetime] = None
    shared_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[uuid.UUID] = None
    acknowledged_by_name: Optional[str] = None
    acknowledgement_notes: Optional[str] = None
    checklist_confirmed: bool = False
    assigned_to: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None

    # Latest approved version snapshot
    latest_version: Optional[HandoverVersionResponse] = None

    # Tasks and continuation responsibilities
    tasks_summary: HandoverContinuityTaskSummary = Field(default_factory=HandoverContinuityTaskSummary)
    pending_tasks: List[TaskResponse] = []
    in_progress_tasks: List[TaskResponse] = []
    completed_tasks: List[TaskResponse] = []
    blocked_tasks: List[TaskResponse] = []
    overdue_tasks: List[TaskResponse] = []
    all_tasks: List[TaskResponse] = []

    # Unresolved blockers and contradictions
    unresolved_blockers: List[Dict[str, Any]] = []
    unresolved_conflicts: List[ConflictResponse] = []

    # Team responsibilities
    responsibilities: List[Dict[str, Any]] = []

    # Recent progress notes / updates
    recent_progress_updates: List[Dict[str, Any]] = []

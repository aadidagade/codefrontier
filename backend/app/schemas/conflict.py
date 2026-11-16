import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConflictCategory(str, Enum):
    """Categorization of detected contradictions across project documents."""
    DEADLINE = "deadline"
    TECHNOLOGY_STACK = "technology_stack"
    TASK_STATUS = "task_status"
    TEAM_RESPONSIBILITY = "team_responsibility"
    DECISION = "decision"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    PROCESS = "process"
    CONFIGURATION = "configuration"


class ConflictResolutionStatus(str, Enum):
    """Rigorous conflict resolution lifecycle states."""
    UNRESOLVED = "Unresolved"
    UNDER_REVIEW = "Under Review"
    RESOLVED = "Resolved"
    DISMISSED = "Dismissed"


def normalize_conflict_status(val: Optional[str]) -> str:
    """Normalizes arbitrary status strings to one of the 4 standard resolution statuses."""
    if not val:
        return ConflictResolutionStatus.UNRESOLVED.value
    clean = str(val).strip().lower().replace("_", " ")
    if clean in ("unresolved", "open", "pending"):
        return ConflictResolutionStatus.UNRESOLVED.value
    elif clean in ("under review", "in review", "review"):
        return ConflictResolutionStatus.UNDER_REVIEW.value
    elif clean in ("resolved", "resolve", "accepted"):
        return ConflictResolutionStatus.RESOLVED.value
    elif clean in ("dismissed", "dismiss", "rejected"):
        return ConflictResolutionStatus.DISMISSED.value
    return ConflictResolutionStatus.UNRESOLVED.value


class FactualStatement(BaseModel):
    """Important factual statement extracted from a document chunk."""
    statement_id: str = Field(default_factory=lambda: f"stmt-{uuid.uuid4().hex[:8]}")
    statement: str = Field(..., description="The factual proposition asserted by the source document")
    entity_or_topic: str = Field(..., description="Subject or entity referenced (e.g. 'Project Deadline', 'Database Engine')")
    category: str = Field("architecture", description="deadline, technology_stack, task_status, team_responsibility, decision, architecture, etc.")
    document_id: uuid.UUID
    document_name: str
    chunk_id: uuid.UUID
    page_number: Optional[int] = None
    excerpt: str = Field(..., description="Exact context passage from the source chunk")


class ContradictionEvaluation(BaseModel):
    """Structured response from Gemini or deterministic NLI evaluating factual opposition."""
    is_contradiction: bool = Field(..., description="True if statements genuinely contradict and cannot both be true")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    conflict_category: str = Field("architecture", description="Identified category of discrepancy")
    description: str = Field(..., description="Explanation of why statements are incompatible")
    statement_a: str = Field(..., description="Assertion from Source Document A")
    statement_b: str = Field(..., description="Assertion from Source Document B")
    excerpt_a: str = Field(default="", description="Verbatim quote from Document A")
    excerpt_b: str = Field(default="", description="Verbatim quote from Document B")
    reasoning: str = Field(default="", description="Detailed factual entailment rationale")


class ConflictResponse(BaseModel):
    """
    Complete representation of a detected contradiction across project documents.
    Contains all 9 required fields and guarantees full backward compatibility.
    """
    model_config = ConfigDict(from_attributes=True)

    # 1. Conflict ID
    id: uuid.UUID
    conflict_id: Optional[uuid.UUID] = None

    project_id: uuid.UUID
    handover_id: Optional[uuid.UUID] = None

    # 2. Conflict Category
    conflict_type: str = "architecture"
    conflict_category: str = "architecture"
    description: str

    # 3. Conflicting Statement A & 4. Conflicting Statement B
    statement_a: Optional[str] = None
    statement_b: Optional[str] = None
    conflicting_statement_a: Optional[str] = None
    conflicting_statement_b: Optional[str] = None

    # 5. Source Document A & 6. Source Document B
    source_document_a: Optional[str] = None
    source_document_b: Optional[str] = None
    source_document_a_id: Optional[uuid.UUID] = None
    source_document_b_id: Optional[uuid.UUID] = None
    source_document_a_name: Optional[str] = None
    source_document_b_name: Optional[str] = None

    # 7. Relevant Source Excerpts
    source_excerpt_a: Optional[str] = None
    source_excerpt_b: Optional[str] = None
    relevant_source_excerpts: Optional[Dict[str, Any]] = None
    source_a: Dict[str, Any] = Field(default_factory=dict)
    source_b: Dict[str, Any] = Field(default_factory=dict)

    # 8. Detection Timestamp
    created_at: Optional[datetime] = None
    detection_timestamp: Optional[datetime] = None

    # 9. Resolution Status
    status: str = "Unresolved"
    resolution_status: str = "Unresolved"

    # Human Reviewer Resolution Details
    resolution: Optional[Dict[str, Any]] = None
    resolved_by: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def populate_aliases(self) -> "ConflictResponse":
        # Conflict ID alias
        if not self.conflict_id:
            self.conflict_id = self.id

        # Conflict Category alias
        if self.conflict_type and not self.conflict_category:
            self.conflict_category = self.conflict_type
        elif self.conflict_category and not self.conflict_type:
            self.conflict_type = self.conflict_category

        # Statement A & B aliases
        if not self.statement_a:
            self.statement_a = self.source_a.get("statement") or self.source_a.get("text")
        if not self.statement_b:
            self.statement_b = self.source_b.get("statement") or self.source_b.get("text")
        self.conflicting_statement_a = self.statement_a
        self.conflicting_statement_b = self.statement_b

        # Source Document A & B aliases
        if not self.source_document_a_name:
            self.source_document_a_name = self.source_a.get("document_name")
        if not self.source_document_b_name:
            self.source_document_b_name = self.source_b.get("document_name")
        self.source_document_a = self.source_document_a_name
        self.source_document_b = self.source_document_b_name

        # Excerpts aliases
        if not self.source_excerpt_a:
            self.source_excerpt_a = self.source_a.get("excerpt") or self.source_a.get("text")
        if not self.source_excerpt_b:
            self.source_excerpt_b = self.source_b.get("excerpt") or self.source_b.get("text")
        self.relevant_source_excerpts = {
            "source_a": {
                "document": self.source_document_a,
                "document_id": str(self.source_document_a_id) if self.source_document_a_id else None,
                "excerpt": self.source_excerpt_a,
                "chunk_id": self.source_a.get("chunk_id"),
                "page": self.source_a.get("page") or self.source_a.get("page_number"),
            },
            "source_b": {
                "document": self.source_document_b,
                "document_id": str(self.source_document_b_id) if self.source_document_b_id else None,
                "excerpt": self.source_excerpt_b,
                "chunk_id": self.source_b.get("chunk_id"),
                "page": self.source_b.get("page") or self.source_b.get("page_number"),
            },
        }

        # Timestamp alias
        if not self.detection_timestamp:
            self.detection_timestamp = self.created_at
        elif not self.created_at:
            self.created_at = self.detection_timestamp

        # Status alias
        self.resolution_status = normalize_conflict_status(self.resolution_status or self.status)
        return self


class ConflictUpdateRequest(BaseModel):
    """Payload to update conflict status (e.g. mark Under Review) or notes."""
    status: Optional[str] = Field(None, description="Unresolved, Under Review, Resolved, Dismissed")
    resolution_status: Optional[str] = Field(None, description="Alias for status")
    description: Optional[str] = None
    notes: Optional[str] = None


class ConflictResolveRequest(BaseModel):
    """
    Payload for a human reviewer to arbitrate and resolve a contradiction.
    The system NEVER auto-selects a statement as correct; a human reviewer decides.
    """
    chosen_source: Optional[str] = Field(None, description="source_a, source_b, or custom")
    authoritative_value: Optional[str] = Field(None, description="Authoritative information decided by reviewer")
    chosen_value: Optional[str] = Field(None, description="Alias for authoritative_value")
    resolution_notes: Optional[str] = Field(None, description="Human reviewer explanation of the resolution")
    explanation: Optional[str] = Field(None, description="Alias for resolution_notes")
    status: str = Field("Resolved", description="Resolved or Dismissed")


class ContradictionDetectionReport(BaseModel):
    """Comprehensive report output from running cross-document contradiction detection."""
    project_id: uuid.UUID
    documents_analyzed: int
    chunks_analyzed: int
    statements_extracted: int
    topics_evaluated: int
    contradictions_detected: int
    conflicts: List[ConflictResponse]
    scan_timestamp: datetime

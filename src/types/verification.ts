import { User } from './common';

// =============================================================================
// BACKEND-ALIGNED EVIDENCE VERIFICATION TYPES
// =============================================================================

export type ClaimVerificationStatusType =
  | 'Supported'
  | 'Partially Supported'
  | 'Unsupported'
  | 'Conflicting'
  | 'Insufficient Evidence';

export interface ClaimVerificationRecord {
  claim_id: string;
  claim_text: string;
  verification_status: ClaimVerificationStatusType | string;
  supporting_document_id?: string | null;
  source_filename?: string | null;
  page_number?: number | null;
  section_reference?: string | null;
  supporting_text_excerpt?: string | null;
  verification_timestamp: string;
  // Audit & linkage fields
  id?: string;
  handover_id?: string;
  handover_section_id?: string;
  document_chunk_id?: string;
  alignment_score?: number;
  reasoning?: string | null;
}

export interface SectionVerificationReport {
  section_id: string;
  section_type: string;
  section_title: string;
  total_claims: number;
  supported_claims: number;
  partially_supported_claims: number;
  unsupported_claims: number;
  conflicting_claims: number;
  insufficient_evidence_claims: number;
  section_support_rate: number;
  claims: ClaimVerificationRecord[];
}

export interface AdvancedHandoverVerificationReport {
  handover_id: string;
  total_claims: number;
  supported_claims: number;
  partially_supported_claims: number;
  unsupported_claims: number;
  conflicting_claims: number;
  insufficient_evidence_claims: number;
  overall_support_rate: number;
  verification_timestamp: string;
  sections: SectionVerificationReport[];
  claims: ClaimVerificationRecord[];
}

// =============================================================================
// BACKEND-ALIGNED CONTRADICTION & CONFLICT TYPES
// =============================================================================

export type ConflictCategoryType =
  | 'deadline'
  | 'technology_stack'
  | 'task_status'
  | 'team_responsibility'
  | 'decision'
  | 'architecture'
  | 'security'
  | 'process'
  | 'configuration'
  | string;

export type ConflictResolutionStatusType =
  | 'Unresolved'
  | 'Under Review'
  | 'Resolved'
  | 'Dismissed';

export interface SourceExcerptData {
  document?: string | null;
  document_id?: string | null;
  excerpt?: string | null;
  chunk_id?: string | null;
  page?: number | string | null;
}

export interface ConflictResolutionData {
  chosen_source?: string | null;
  authoritative_value?: string | null;
  chosen_value?: string | null;
  resolution_notes?: string | null;
  explanation?: string | null;
  status?: string;
  resolved_by?: {
    id: string;
    name: string;
    email?: string;
    role?: string;
  } | string | null;
  resolved_at?: string | null;
}

export interface ConflictResponse {
  // 1. Conflict ID
  id: string;
  conflict_id?: string;
  project_id: string;
  handover_id?: string | null;

  // 2. Conflict Category
  conflict_type: string;
  conflict_category: ConflictCategoryType;
  description: string;

  // 3. Conflicting Statement A & 4. Conflicting Statement B
  statement_a?: string | null;
  statement_b?: string | null;
  conflicting_statement_a?: string | null;
  conflicting_statement_b?: string | null;

  // 5. Source Document A & 6. Source Document B
  source_document_a?: string | null;
  source_document_b?: string | null;
  source_document_a_id?: string | null;
  source_document_b_id?: string | null;
  source_document_a_name?: string | null;
  source_document_b_name?: string | null;

  // 7. Relevant Source Excerpts
  source_excerpt_a?: string | null;
  source_excerpt_b?: string | null;
  relevant_source_excerpts?: {
    source_a?: SourceExcerptData;
    source_b?: SourceExcerptData;
  };
  source_a?: any;
  source_b?: any;

  // 8. Detection Timestamp
  created_at?: string;
  detection_timestamp?: string;

  // 9. Resolution Status
  status: string;
  resolution_status: ConflictResolutionStatusType | string;

  // Human Reviewer Decision
  resolution?: ConflictResolutionData | null;
  resolved_by?: string | null;
}

export type ConflictItem = ConflictResponse;

export interface ConflictResolveRequest {
  chosen_source?: 'source_a' | 'source_b' | 'custom' | string;
  authoritative_value?: string;
  chosen_value?: string;
  resolution_notes?: string;
  explanation?: string;
  status: 'Resolved' | 'Dismissed';
}

export interface ConflictUpdateRequest {
  status?: ConflictResolutionStatusType | string;
  resolution_status?: string;
  description?: string;
  notes?: string;
}

export interface ContradictionDetectionReport {
  project_id: string;
  documents_analyzed: number;
  chunks_analyzed: number;
  statements_extracted: number;
  topics_evaluated: number;
  contradictions_detected: number;
  conflicts: ConflictResponse[];
  scan_timestamp: string;
}

// =============================================================================
// BACKWARDS-COMPATIBLE LEGACY TYPES FOR EXISTING SCREENS
// =============================================================================

export type EvidenceStatus =
  | 'supported'
  | 'partially_supported'
  | 'unsupported'
  | 'Supported'
  | 'Partially Supported'
  | 'Unsupported'
  | 'Conflicting'
  | 'Insufficient Evidence';

export type UncertaintyType = 
  | 'missing_evidence'
  | 'unclear_ownership'
  | 'contradictory'
  | 'outdated'
  | 'unsupported_statement';

export type ClaimVerificationStatus = 'unverified' | 'verified' | 'disputed' | 'corrected';

export type DisputeType = 'date' | 'owner' | 'architecture' | 'process' | 'security' | string;

export type ConflictResolutionType = 
  | 'verify_source_a'
  | 'verify_source_b'
  | 'mark_unresolved'
  | 'custom_correction';

export interface ConflictSourcePassage {
  docId: string;
  docName: string;
  docType: 'pdf' | 'docx' | 'txt' | 'md' | string;
  pageOrSection: string;
  excerpt: string;
  claimedValue: string;
  author: string;
  date: string;
  lastModified?: string;
}

export interface ConflictResolution {
  resolvedBy: {
    id: string;
    name: string;
    email?: string;
    role?: string;
  };
  resolvedAt: string;
  resolutionType: ConflictResolutionType;
  chosenValue?: string;
  resolutionNote: string;
  correctionText?: string;
}

export interface KnowledgeConflictItem {
  id: string;
  projectId: string;
  projectKey: string;
  projectName: string;
  topic: string;
  disputeType: DisputeType;
  disputedField: string;
  severity: 'critical' | 'high' | 'medium';
  status: 'unresolved' | 'resolved' | 'flagged_for_lead' | 'under_review' | string;
  description: string;
  sourceA: ConflictSourcePassage;
  sourceB: ConflictSourcePassage;
  resolution?: ConflictResolution;
  isSyntheticModelOutput?: boolean;
}

export interface VerificationClaim {
  id: string;
  projectId: string;
  projectKey: string;
  projectName: string;
  section: 'overview' | 'decisions' | 'tasks' | 'risks' | 'dependencies' | 'runbooks' | string;
  claimText: string;
  sourceDocId: string;
  sourceDocName: string;
  sourceDocType: 'pdf' | 'docx' | 'txt' | 'md' | string;
  pageOrSection: string;
  evidenceSnippet: string;
  evidenceStatus: EvidenceStatus;
  uncertaintyFlags: UncertaintyType[];
  confidenceScore?: number;
  isSyntheticModelOutput?: boolean;
  verificationStatus: ClaimVerificationStatus;
  verifiedBy?: {
    id: string;
    name: string;
    role?: string;
  };
  verifiedAt?: string;
  verificationNotes?: string;
  disputedReason?: string;
  conflictId?: string;
  createdAt: string;
}

export type ClaimsFilter = 
  | 'all'
  | 'supported'
  | 'partially_supported'
  | 'unsupported'
  | 'conflicting'
  | 'insufficient_evidence'
  | 'uncertain'
  | 'conflicts'
  | 'verified'
  | 'unverified';

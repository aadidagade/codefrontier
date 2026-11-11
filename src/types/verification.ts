import { User } from './common';

export type EvidenceStatus = 'supported' | 'partially_supported' | 'unsupported';

export type UncertaintyType = 
  | 'missing_evidence'
  | 'unclear_ownership'
  | 'contradictory'
  | 'outdated'
  | 'unsupported_statement';

export type ClaimVerificationStatus = 'unverified' | 'verified' | 'disputed' | 'corrected';

export type DisputeType = 'date' | 'owner' | 'architecture' | 'process' | 'security';

export type ConflictResolutionType = 
  | 'verify_source_a'
  | 'verify_source_b'
  | 'mark_unresolved'
  | 'custom_correction';

export interface ConflictSourcePassage {
  docId: string;
  docName: string;
  docType: 'pdf' | 'docx' | 'txt' | 'md';
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
  status: 'unresolved' | 'resolved' | 'flagged_for_lead';
  description: string;
  sourceA: ConflictSourcePassage;
  sourceB: ConflictSourcePassage;
  resolution?: ConflictResolution;
  isSyntheticModelOutput: boolean; // Flag identifying synthetic/demo data
}

export interface VerificationClaim {
  id: string;
  projectId: string;
  projectKey: string;
  projectName: string;
  section: 'overview' | 'decisions' | 'tasks' | 'risks' | 'dependencies' | 'runbooks';
  claimText: string;
  sourceDocId: string;
  sourceDocName: string;
  sourceDocType: 'pdf' | 'docx' | 'txt' | 'md';
  pageOrSection: string;
  evidenceSnippet: string;
  evidenceStatus: EvidenceStatus;
  uncertaintyFlags: UncertaintyType[];
  confidenceScore?: number; // 0 - 100 synthetic score
  isSyntheticModelOutput: boolean; // Transparent demo indicator
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
  | 'uncertain'
  | 'conflicts'
  | 'verified'
  | 'unverified';

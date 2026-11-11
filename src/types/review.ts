import { User } from './common';
import {
  KeyDecisionItem,
  TaskOwnershipItem,
  BlockerRiskItem,
  DependencyItem,
  UnresolvedQuestionItem,
  RecommendedActionItem,
  EvidenceCitationItem,
} from './handover';

export type ApprovalStatus =
  | 'draft'
  | 'awaiting_review'
  | 'changes_requested'
  | 'approved'
  | 'rejected';

export type SectionReviewStatus = 'pending' | 'approved' | 'changes_requested' | 'rejected';

export type SectionKey =
  | 'overview'
  | 'decisions'
  | 'tasks'
  | 'ownership'
  | 'blockers'
  | 'risks'
  | 'dependencies'
  | 'open_questions'
  | 'next_actions';

export interface ReviewComment {
  id: string;
  sectionKey: SectionKey;
  author: User;
  text: string;
  createdAt: string;
  status: 'open' | 'resolved';
}

export interface SectionReviewItem {
  key: SectionKey;
  title: string;
  status: SectionReviewStatus;
  reviewedBy?: User;
  reviewedAt?: string;
  reviewNote?: string;
  commentCount: number;
  evidenceCount: number;
  isEdited?: boolean;
}

export interface ApprovalChecklistItem {
  id: string;
  label: string;
  description: string;
  passed: boolean;
  severity: 'critical' | 'warning';
  fixTargetSection?: SectionKey;
}

export interface ServiceOwnershipRecord {
  id: string;
  serviceName: string;
  primaryLead: User;
  secondaryOnCall: User;
  escalationPolicy: string;
  status: 'verified' | 'unclear';
}

export interface HandoverReviewContent {
  overview: {
    purpose: string;
    currentStatus: string;
    overallProgress: number;
  };
  decisions: KeyDecisionItem[];
  tasks: TaskOwnershipItem[];
  ownership: ServiceOwnershipRecord[];
  blockers: BlockerRiskItem[];
  risks: BlockerRiskItem[];
  dependencies: DependencyItem[];
  openQuestions: UnresolvedQuestionItem[];
  nextActions: RecommendedActionItem[];
}

export interface HandoverReviewRecord {
  id: string;
  projectId: string;
  projectKey: string;
  projectName: string;
  outgoingMember: User;
  incomingMember: User;
  designatedReviewer: User;
  generatedDate: string;
  lastUpdated: string;
  version: string; // e.g. "v1.0"
  revisionNumber: number;
  isLocked: boolean;
  approvalStatus: ApprovalStatus;
  evidenceScore: number;
  sections: Record<SectionKey, SectionReviewItem>;
  comments: ReviewComment[];
  approvedBy?: User;
  approvedAt?: string;
  approvalNotes?: string;
  rejectionReason?: string;
  changesRequestedNotes?: string;
  content: HandoverReviewContent;
  evidenceCitations: EvidenceCitationItem[];
}

export type ReviewDashboardFilter =
  | 'all'
  | 'draft'
  | 'awaiting_review'
  | 'changes_requested'
  | 'approved'
  | 'rejected';

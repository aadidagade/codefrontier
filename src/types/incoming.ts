import { User } from './common';

export type AcknowledgementStatus = 'pending' | 'acknowledged';

export interface ProgressNote {
  id: string;
  text: string;
  author: string;
  createdAt: string;
}

export interface ContinuationTaskItem {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
  priority: 'critical' | 'high' | 'medium';
  assignedTo: User;
  dependencies: string[];
  dueDate?: string;
  progressNotes: ProgressNote[];
  completedAt?: string;
}

export interface ImportantDecisionItem {
  id: string;
  decision: string;
  date: string;
  rationale: string;
  supportingSource: string;
  sourceSnippet?: string;
}

export interface HandoverBlockerItem {
  id: string;
  description: string;
  impact: string;
  severity: 'critical' | 'high' | 'medium';
  suggestedFollowUp: string;
  supportingEvidence?: string;
}

export interface HandoverDependencyItem {
  id: string;
  dependency: string;
  prerequisiteTask: string;
  requiredPersonOrResource: string;
  currentStatus: string;
}

export interface RecommendedStartingAction {
  id: string;
  action: string;
  timeframe: 'Day 1' | 'Day 2-3' | 'Week 1' | 'Month 1';
  priority: 'high' | 'medium' | 'low';
  reason: string;
}

export interface OpenQuestionItem {
  id: string;
  question: string;
  whyItMatters: string;
  whoNeedsToConfirm: string;
  status: 'unresolved' | 'clarified';
  clarificationResponse?: string;
}

export interface IncomingHandoverPackage {
  id: string;
  handoverId: string;
  projectId: string;
  projectKey: string;
  projectName: string;
  version: string;
  approvedDate: string;
  approvedBy: User;
  outgoingMember: User;
  projectLead: User;
  incomingMember: User;
  acknowledgementStatus: AcknowledgementStatus;
  acknowledgedAt?: string;
  acknowledgementComment?: string;

  // A. Project Introduction
  introduction: {
    purpose: string;
    objectives: string[];
    currentStage: string;
    overallStatus: string;
    healthScore: number;
    lastUpdated: string;
  };

  // B. Important Decisions
  decisions: ImportantDecisionItem[];

  // C. Your Responsibilities (Continuation Tasks)
  responsibilities: ContinuationTaskItem[];

  // D. Current Blockers
  blockers: HandoverBlockerItem[];

  // E. Project Dependencies
  dependencies: HandoverDependencyItem[];

  // F. Recommended Starting Actions
  recommendedStartingActions: RecommendedStartingAction[];

  // G. Open Questions
  openQuestions: OpenQuestionItem[];

  // Security & Audit
  isSanitized: boolean; // Confirms approved only, no private notes
}

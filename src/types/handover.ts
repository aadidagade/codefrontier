import { User, StatusVariant } from './common';

export type HandoverStage = 'upload' | 'analyze' | 'verify' | 'approve' | 'handover';

export interface HandoverChecklistItem {
  id: string;
  title: string;
  category: 'architecture' | 'credentials' | 'runbooks' | 'dependencies' | 'tribal_knowledge';
  completed: boolean;
  required: boolean;
  verifiedByAi: boolean;
  evidenceSnippet?: string;
  evidenceSourceId?: string;
  assignedTo?: User;
}

export interface HandoverSession {
  id: string;
  projectId: string;
  projectKey: string;
  projectTitle: string;
  initiator: User;
  recipient: User;
  reviewer?: User;
  currentStage: HandoverStage;
  status: StatusVariant;
  progressPercentage: number;
  aiReadinessScore: number;
  conflictsDetected: number;
  unresolvedGaps: number;
  checklist: HandoverChecklistItem[];
  startDate: string;
  targetCompletionDate: string;
  summaryExecutive?: string;
  keyGotchas: string[];
}

export interface GenerationConfig {
  incomingRole: string;
  handoverScope: string;
  timelineScope: string;
  additionalInstructions?: string;
  selectedDocumentIds: string[];
}

export interface AnalysisStageInfo {
  id: number;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
  detail?: string;
}

export interface KeyDecisionItem {
  id: string;
  decision: string;
  date: string;
  rationale: string;
  supportingSource: string;
  sourceDocId?: string;
  isUncertain?: boolean;
}

export interface TaskOwnershipItem {
  id: string;
  taskName: string;
  assignedOwner: User;
  status: 'in_progress' | 'pending_handover' | 'verified' | 'blocked';
  priority: 'critical' | 'high' | 'medium';
  dueDate?: string;
}

export interface BlockerRiskItem {
  id: string;
  description: string;
  impact: string;
  severity: 'critical' | 'high' | 'medium';
  supportingEvidence: string;
  isUncertain?: boolean;
}

export interface DependencyItem {
  id: string;
  dependency: string;
  relatedTask: string;
  requiredPersonOrResource: string;
  currentStatus: string;
}

export interface UnresolvedQuestionItem {
  id: string;
  question: string;
  whyItMatters: string;
  whoNeedsToConfirm: string;
  isUncertain?: boolean;
}

export interface RecommendedActionItem {
  id: string;
  action: string;
  priority: 'high' | 'medium' | 'low';
  suggestedOwner?: string;
  reason: string;
}

export interface EvidenceCitationItem {
  id: string;
  title: string;
  sourceDocName: string;
  excerpt: string;
  confidence: number;
  isFlagged?: boolean;
  externalLink?: string;
}

export interface GeneratedHandover {
  id: string;
  projectKey: string;
  projectName: string;
  createdAt: string;
  generatedBy: User;
  evidenceScore: number; // 0 - 100
  targetRole: string;
  scope: string;
  overview: {
    purpose: string;
    currentStatus: string;
    overallProgress: number;
  };
  decisions: KeyDecisionItem[];
  tasks: TaskOwnershipItem[];
  blockersAndRisks: BlockerRiskItem[];
  dependencies: DependencyItem[];
  unresolvedQuestions: UnresolvedQuestionItem[];
  recommendedNextActions: RecommendedActionItem[];
  evidenceCitations: EvidenceCitationItem[];
}

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

export interface HandoverVersionItem {
  id: string;
  handover_id: string;
  version_number: string;
  version_description?: string | null;
  approval_status: string;
  parent_version_id?: string | null;
  is_latest: boolean;
  created_by?: string | null;
  creator_name?: string | null;
  created_at: string;
  snapshot: Record<string, any>;
}

export interface SectionDiffItem {
  section_type: string;
  title: string;
  has_changed: boolean;
  change_type: 'ADDED' | 'REMOVED' | 'MODIFIED' | 'UNCHANGED';
  old_content?: string | null;
  new_content?: string | null;
  added_lines: string[];
  removed_lines: string[];
  diff_summary?: string | null;
}

export interface TaskDiffItem {
  task_id?: string | null;
  title: string;
  change_type: 'ADDED' | 'REMOVED' | 'MODIFIED' | 'UNCHANGED';
  status_changed: boolean;
  old_status?: string | null;
  new_status?: string | null;
  assignee_changed: boolean;
  old_assignee?: string | null;
  new_assignee?: string | null;
  priority_changed: boolean;
  old_priority?: string | null;
  new_priority?: string | null;
  description_changed: boolean;
}

export interface ResponsibilityDiffItem {
  entity_type: string;
  entity_id?: string | null;
  entity_name: string;
  change_type: 'ASSIGNED' | 'REASSIGNED' | 'UNASSIGNED' | 'MODIFIED';
  old_assignee?: string | null;
  new_assignee?: string | null;
  details?: string | null;
}

export interface ComparisonSummaryItem {
  total_sections_compared: number;
  added_sections_count: number;
  removed_sections_count: number;
  modified_sections_count: number;
  unchanged_sections_count: number;
  total_tasks_compared: number;
  added_tasks_count: number;
  removed_tasks_count: number;
  task_status_changes_count: number;
  responsibility_changes_count: number;
  has_differences: boolean;
  category_status: Record<string, string>;
}

export interface VersionDiffResponse {
  from_version_id: string;
  from_version_number: string;
  to_version_id: string;
  to_version_number: string;
  summary: ComparisonSummaryItem;
  section_diffs: SectionDiffItem[];
  task_diffs: TaskDiffItem[];
  responsibility_diffs: ResponsibilityDiffItem[];
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

export type HandoverTransitionStatus =
  | 'Awaiting Acknowledgement'
  | 'Acknowledged'
  | 'In Progress'
  | 'Completed';

export interface SharedHandoverItem {
  id: string;
  project_id: string;
  project_title?: string | null;
  title: string;
  version: string;
  status: string;
  transition_status: string;
  approved_at?: string | null;
  shared_at?: string | null;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  acknowledged_by_name?: string | null;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  pending_tasks_count: number;
  overdue_tasks_count: number;
}

export interface TaskProgressUpdateItem {
  id: string;
  task_id: string;
  task_title?: string | null;
  user_id: string;
  user_name?: string | null;
  update_text: string;
  status_before?: string | null;
  status_after?: string | null;
  created_at: string;
}

export interface HandoverContinuityTaskSummary {
  total_tasks: number;
  pending_tasks: number;
  in_progress_tasks: number;
  completed_tasks: number;
  blocked_tasks: number;
  overdue_tasks: number;
  completion_percentage: number;
}

export interface HandoverContinuityData {
  handover_id: string;
  project_id: string;
  project_title?: string | null;
  title: string;
  version: string;
  status: string;
  transition_status: string;
  approved_at?: string | null;
  shared_at?: string | null;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  acknowledged_by_name?: string | null;
  acknowledgement_notes?: string | null;
  checklist_confirmed: boolean;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  latest_version?: HandoverVersionItem | null;
  tasks_summary: HandoverContinuityTaskSummary;
  pending_tasks: any[];
  in_progress_tasks: any[];
  completed_tasks: any[];
  blocked_tasks: any[];
  overdue_tasks: any[];
  all_tasks: any[];
  unresolved_blockers: any[];
  unresolved_conflicts: any[];
  responsibilities: any[];
  recent_progress_updates: any[];
}

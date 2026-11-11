import { User } from './common';

export type ActivityType =
  | 'document_uploaded'
  | 'handover_generated'
  | 'review_requested'
  | 'handover_approved'
  | 'member_acknowledged';

export interface ActivityEvent {
  id: string;
  type: ActivityType;
  title: string;
  description: string;
  projectKey: string;
  projectName: string;
  user: User;
  timestamp: string;
  timeAgo: string;
  linkText?: string;
  metaBadge?: string;
}

export type PendingActionType =
  | 'review_handover'
  | 'resolve_conflict'
  | 'verify_ownership'
  | 'approve_handover';

export interface PendingAction {
  id: string;
  type: PendingActionType;
  title: string;
  description: string;
  priority: 'critical' | 'high' | 'medium';
  projectKey: string;
  projectName: string;
  dueDate: string;
  actionLabel: string;
  assignedTo: User;
  completed?: boolean;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  role: string;
  plan: string;
  activeProjects: number;
}

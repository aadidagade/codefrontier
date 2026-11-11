import { User, StatusVariant } from './common';

export interface ProjectPermissions {
  uploadDocs: 'all_members' | 'lead_and_outgoing' | 'admins_only';
  reviewApprove: 'lead_only' | 'architecture_reviewers' | 'dual_approval';
  incomingAccess: 'full_access' | 'read_only_until_approved' | 'restricted_vault';
  authorizedMemberIds: string[];
}

export interface Project {
  id: string;
  key: string; // e.g. "KH-CORE", "PAY-V2"
  title: string;
  description: string;
  category: string;
  status: StatusVariant;
  owner: User;
  successor?: User;
  outgoingMember?: User;
  incomingMember?: User;
  projectLead?: User;
  incomingRole?: string;
  handoverPurpose?: string;
  startDate: string;
  expectedDeadline: string;
  createdAt?: string;
  knowledgeHealthScore: number; // 0 - 100%
  lastAuditDate: string;
  handoverDueDate: string;
  totalDocuments: number;
  totalDecisions: number;
  unresolvedGaps: number;
  tags: string[];
  membersCount: number;
  members: User[];
  lastUpdatedText: string;
  handoverProgress: number; // 0 - 100
  repoUrl?: string;
  permissions?: ProjectPermissions;
}

export interface ProjectMetric {
  title: string;
  value: string | number;
  changePercent?: number;
  trend?: 'up' | 'down' | 'neutral';
  description?: string;
}

export interface CreateProjectFormData {
  // Step 1: Project details
  title: string;
  key: string;
  description: string;
  category: string;
  startDate: string;
  expectedDeadline: string;
  status: StatusVariant;

  // Step 2: Handover configuration
  outgoingMemberId: string;
  incomingMemberId: string;
  incomingRole: string;
  projectLeadId: string;
  handoverPurpose: string;
  handoverDeadline?: string;

  // Step 3: Permissions
  authorizedMemberIds: string[];
  uploadDocs: 'all_members' | 'lead_and_outgoing' | 'admins_only';
  reviewApprove: 'lead_only' | 'architecture_reviewers' | 'dual_approval';
  incomingAccess: 'full_access' | 'read_only_until_approved' | 'restricted_vault';
}

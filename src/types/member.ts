export type ProjectMemberRole =
  | 'ADMIN'
  | 'PROJECT_OWNER'
  | 'OUTGOING'
  | 'INCOMING'
  | 'REVIEWER'
  | 'LEAD';

export type MembershipStatus = 'active' | 'invited' | 'revoked';
export type InvitationStatus = 'accepted' | 'pending' | 'declined' | 'revoked';

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  full_name: string;
  email: string;
  profile_image?: string | null;
  role: ProjectMemberRole | string;
  role_display_name: string;
  status: MembershipStatus | string;
  invitation_status: InvitationStatus | string;
  invited_by?: string | null;
  invited_at?: string | null;
  joined_at: string;
  custom_permissions?: string[] | null;
}

export interface MemberAddPayload {
  email?: string;
  user_id?: string;
  role: ProjectMemberRole | string;
  status?: string;
  custom_permissions?: string[];
}

export interface MemberUpdateRolePayload {
  role: ProjectMemberRole | string;
  status?: string;
  custom_permissions?: string[];
}

export interface MemberRevokeResponse {
  member_id: string;
  project_id: string;
  user_id: string;
  status: string;
  invitation_status: string;
  revoked_at: string;
  message: string;
}

export interface PermissionDefinition {
  key: string;
  label: string;
  description: string;
  category: 'workspace' | 'documents' | 'handover' | 'governance';
}

export const AVAILABLE_PERMISSIONS: PermissionDefinition[] = [
  {
    key: 'view_project',
    label: 'View Project Workspace',
    description: 'Inspect workspace metrics, overview, and repository status',
    category: 'workspace',
  },
  {
    key: 'edit_project',
    label: 'Edit Project Settings',
    description: 'Modify workspace name, description, deadlines, and repositories',
    category: 'workspace',
  },
  {
    key: 'upload_documents',
    label: 'Upload Knowledge Sources',
    description: 'Index architectural decision records, runbooks, and credential guides',
    category: 'documents',
  },
  {
    key: 'delete_documents',
    label: 'Delete Knowledge Sources',
    description: 'Remove obsolete knowledge sources or superseded runbooks',
    category: 'documents',
  },
  {
    key: 'generate_handover',
    label: 'Generate AI Handover',
    description: 'Run automated AI knowledge synthesis and draft generation',
    category: 'handover',
  },
  {
    key: 'view_handover',
    label: 'View Handover Briefs',
    description: 'Read generated handover briefs and knowledge documentation',
    category: 'handover',
  },
  {
    key: 'edit_handover',
    label: 'Edit Handover Drafts',
    description: 'Edit draft sections, checklists, and transfer notes',
    category: 'handover',
  },
  {
    key: 'submit_handover_for_review',
    label: 'Submit for Review',
    description: 'Advance draft handovers to the review queue for sign-off',
    category: 'handover',
  },
  {
    key: 'approve_handover',
    label: 'Approve / Reject Handovers',
    description: 'Formally sign off on handovers or request architectural revisions',
    category: 'governance',
  },
  {
    key: 'share_handover',
    label: 'Share Handover Briefs',
    description: 'Export and share approved handover packages with stakeholders',
    category: 'governance',
  },
  {
    key: 'manage_project_members',
    label: 'Manage Project Members & RBAC',
    description: 'Invite members, modify assigned roles, and configure custom permissions',
    category: 'governance',
  },
  {
    key: 'view_audit_logs',
    label: 'View Audit Logs',
    description: 'Inspect immutable project activity timelines, security events, and changes',
    category: 'governance',
  },
  {
    key: 'edit_approved_handover',
    label: 'Edit Approved Handover',
    description: 'Special override to append notes to an already approved handover',
    category: 'handover',
  },
];

export const ROLE_DEFAULT_PERMISSIONS: Record<string, string[]> = {
  ADMIN: [
    'view_project',
    'edit_project',
    'upload_documents',
    'delete_documents',
    'generate_handover',
    'view_handover',
    'edit_handover',
    'submit_handover_for_review',
    'approve_handover',
    'share_handover',
    'manage_project_members',
    'view_audit_logs',
    'edit_approved_handover',
  ],
  PROJECT_OWNER: [
    'view_project',
    'edit_project',
    'upload_documents',
    'delete_documents',
    'generate_handover',
    'view_handover',
    'edit_handover',
    'submit_handover_for_review',
    'approve_handover',
    'share_handover',
    'manage_project_members',
    'view_audit_logs',
    'edit_approved_handover',
  ],
  OUTGOING: [
    'view_project',
    'upload_documents',
    'delete_documents',
    'generate_handover',
    'view_handover',
    'edit_handover',
    'submit_handover_for_review',
    'share_handover',
    'view_audit_logs',
  ],
  INCOMING: [
    'view_project',
    'view_handover',
  ],
  REVIEWER: [
    'view_project',
    'view_handover',
    'submit_handover_for_review',
    'approve_handover',
    'share_handover',
    'view_audit_logs',
  ],
  LEAD: [
    'view_project',
    'upload_documents',
    'view_handover',
    'edit_handover',
    'submit_handover_for_review',
    'approve_handover',
    'share_handover',
    'view_audit_logs',
  ],
};

export const ROLE_DISPLAY_NAMES: Record<string, string> = {
  ADMIN: 'Admin',
  PROJECT_OWNER: 'Project Owner',
  OUTGOING: 'Outgoing Member',
  INCOMING: 'Incoming Member',
  REVIEWER: 'Reviewer',
  LEAD: 'Project Lead',
};

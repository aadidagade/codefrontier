import { User } from './common';
import { HandoverAppRole } from '../context/RoleContext';

export type TeamMemberStatus = 'active' | 'pending_invite' | 'inactive';

export interface AssignedProjectItem {
  projectId: string;
  projectKey: string;
  projectTitle: string;
  roleInProject: string;
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: HandoverAppRole;
  roleTitle: string;
  department: string;
  avatarUrl: string;
  status: TeamMemberStatus;
  lastActive: string;
  invitedAt?: string;
  assignedProjects: AssignedProjectItem[];
  bio?: string;
}

export interface InviteMemberPayload {
  email: string;
  name?: string;
  role: HandoverAppRole;
  roleTitle?: string;
  department?: string;
  projectIds: string[];
  status?: TeamMemberStatus;
}

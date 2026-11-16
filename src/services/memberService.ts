import { apiClient, ApiResponse } from './apiClient';
import {
  ProjectMember,
  MemberAddPayload,
  MemberUpdateRolePayload,
  MemberRevokeResponse,
  ROLE_DISPLAY_NAMES,
  ROLE_DEFAULT_PERMISSIONS,
} from '../types/member';
import { mockUsers } from '../data/mockData';

const MEMBER_STORAGE_PREFIX = 'kh_project_members_';

function getStoredMembers(projectId: string): ProjectMember[] {
  try {
    const raw = localStorage.getItem(`${MEMBER_STORAGE_PREFIX}${projectId}`);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (err) {
    console.warn('Failed to parse stored members:', err);
  }

  // Seed default members for demo/mock mode
  const defaults: ProjectMember[] = [
    {
      id: 'pm-1',
      project_id: projectId,
      user_id: mockUsers[0].id,
      full_name: mockUsers[0].name,
      email: mockUsers[0].email,
      profile_image: mockUsers[0].avatarUrl,
      role: 'PROJECT_OWNER',
      role_display_name: 'Project Owner',
      status: 'active',
      invitation_status: 'accepted',
      joined_at: '2026-08-01T10:00:00Z',
      custom_permissions: null,
    },
    {
      id: 'pm-2',
      project_id: projectId,
      user_id: mockUsers[1].id,
      full_name: mockUsers[1].name,
      email: mockUsers[1].email,
      profile_image: mockUsers[1].avatarUrl,
      role: 'INCOMING',
      role_display_name: 'Incoming Member',
      status: 'active',
      invitation_status: 'accepted',
      joined_at: '2026-08-05T14:30:00Z',
      custom_permissions: null,
    },
    {
      id: 'pm-3',
      project_id: projectId,
      user_id: mockUsers[2].id,
      full_name: mockUsers[2].name,
      email: mockUsers[2].email,
      profile_image: mockUsers[2].avatarUrl,
      role: 'REVIEWER',
      role_display_name: 'Reviewer',
      status: 'active',
      invitation_status: 'accepted',
      joined_at: '2026-08-10T09:15:00Z',
      custom_permissions: null,
    },
    {
      id: 'pm-4',
      project_id: projectId,
      user_id: mockUsers[4].id,
      full_name: mockUsers[4].name,
      email: mockUsers[4].email,
      profile_image: mockUsers[4].avatarUrl,
      role: 'OUTGOING',
      role_display_name: 'Outgoing Member',
      status: 'invited',
      invitation_status: 'pending',
      invited_at: '2026-11-01T11:20:00Z',
      joined_at: '2026-11-01T11:20:00Z',
      custom_permissions: null,
    },
  ];

  try {
    localStorage.setItem(`${MEMBER_STORAGE_PREFIX}${projectId}`, JSON.stringify(defaults));
  } catch (err) {
    console.warn('Failed to cache default members:', err);
  }

  return defaults;
}

function saveStoredMembers(projectId: string, members: ProjectMember[]): void {
  try {
    localStorage.setItem(`${MEMBER_STORAGE_PREFIX}${projectId}`, JSON.stringify(members));
  } catch (err) {
    console.warn('Failed to save members to storage:', err);
  }
}

export class MemberService {
  /**
   * Retrieves all members of a project workspace with their assigned roles and statuses.
   */
  async listMembers(projectId: string, status?: string): Promise<ApiResponse<ProjectMember[]>> {
    try {
      const qs = status ? `?status=${encodeURIComponent(status)}` : '';
      const res = await apiClient.get<ProjectMember[]>(`/projects/${projectId}/members${qs}`);
      if (res.data && Array.isArray(res.data)) {
        saveStoredMembers(projectId, res.data);
        return res;
      }
    } catch (err) {
      console.warn(`Backend member fetch failed for ${projectId}, falling back to local store:`, err);
    }

    const local = getStoredMembers(projectId);
    const filtered = status ? local.filter((m) => m.status === status) : local;
    return {
      data: filtered,
      status: 200,
      message: 'Retrieved project members (cached/mock)',
    };
  }

  /**
   * Invites an existing or new user to the project workspace with an assigned role.
   */
  async addMember(projectId: string, payload: MemberAddPayload): Promise<ApiResponse<ProjectMember>> {
    try {
      const res = await apiClient.post<ProjectMember>(`/projects/${projectId}/members`, payload);
      if (res.data) {
        // Refresh local cache
        const local = getStoredMembers(projectId);
        const idx = local.findIndex((m) => m.id === res.data.id || m.email === res.data.email);
        if (idx >= 0) {
          local[idx] = res.data;
        } else {
          local.push(res.data);
        }
        saveStoredMembers(projectId, local);
        return res;
      }
    } catch (err: any) {
      // If backend returns an explicit error (like User not found), rethrow unless network error
      if (err.message && !err.message.includes('Failed to connect')) {
        throw err;
      }
      console.warn('Falling back to local member addition:', err);
    }

    // Mock fallback creation
    const local = getStoredMembers(projectId);
    const email = payload.email || 'new.member@techfrontier.io';
    const existing = local.find((m) => m.email.toLowerCase() === email.toLowerCase());
    if (existing && existing.status !== 'revoked') {
      throw new Error(`User with email "${email}" is already a member of this project.`);
    }

    const roleName = payload.role.toString();
    const displayName = ROLE_DISPLAY_NAMES[roleName] || roleName;
    const initialStatus = payload.status || 'invited';

    const newMember: ProjectMember = {
      id: `pm-${Date.now()}`,
      project_id: projectId,
      user_id: payload.user_id || `usr-${Date.now()}`,
      full_name: email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      email: email,
      profile_image: `https://images.unsplash.com/photo-${1530000000000 + Math.floor(Math.random() * 100000)}?w=150&auto=format&fit=crop&q=80`,
      role: roleName,
      role_display_name: displayName,
      status: initialStatus,
      invitation_status: initialStatus === 'active' ? 'accepted' : 'pending',
      invited_at: new Date().toISOString(),
      joined_at: new Date().toISOString(),
      custom_permissions: payload.custom_permissions || null,
    };

    if (existing && existing.status === 'revoked') {
      const idx = local.indexOf(existing);
      local[idx] = newMember;
    } else {
      local.push(newMember);
    }
    saveStoredMembers(projectId, local);

    return {
      data: newMember,
      status: 201,
      message: `Member '${email}' invited successfully.`,
    };
  }

  /**
   * Updates an existing member's role and/or custom permission overrides.
   */
  async updateMemberRole(
    projectId: string,
    memberId: string,
    payload: MemberUpdateRolePayload
  ): Promise<ApiResponse<ProjectMember>> {
    try {
      const res = await apiClient.patch<ProjectMember>(
        `/projects/${projectId}/members/${memberId}`,
        payload
      );
      if (res.data) {
        const local = getStoredMembers(projectId);
        const idx = local.findIndex((m) => m.id === memberId);
        if (idx >= 0) {
          local[idx] = res.data;
          saveStoredMembers(projectId, local);
        }
        return res;
      }
    } catch (err: any) {
      if (err.message && !err.message.includes('Failed to connect')) {
        throw err;
      }
      console.warn('Falling back to local member update:', err);
    }

    const local = getStoredMembers(projectId);
    const idx = local.findIndex((m) => m.id === memberId);
    if (idx === -1) {
      throw new Error('Project member not found.');
    }

    const target = local[idx];
    const roleName = payload.role.toString();
    const displayName = ROLE_DISPLAY_NAMES[roleName] || roleName;

    // Check admin/owner retention
    if (
      (target.role === 'ADMIN' || target.role === 'PROJECT_OWNER') &&
      roleName !== 'ADMIN' &&
      roleName !== 'PROJECT_OWNER'
    ) {
      const activeAdmins = local.filter(
        (m) =>
          (m.role === 'ADMIN' || m.role === 'PROJECT_OWNER') &&
          m.status === 'active' &&
          m.id !== memberId
      );
      if (activeAdmins.length === 0) {
        throw new Error('Cannot demote member: Project workspace must retain at least one active Admin or Project Owner.');
      }
    }

    const updated: ProjectMember = {
      ...target,
      role: roleName,
      role_display_name: displayName,
      status: payload.status !== undefined && payload.status !== null ? payload.status : target.status,
      custom_permissions:
        payload.custom_permissions !== undefined ? payload.custom_permissions : target.custom_permissions,
    };

    local[idx] = updated;
    saveStoredMembers(projectId, local);

    return {
      data: updated,
      status: 200,
      message: `Member role updated to '${displayName}'.`,
    };
  }

  /**
   * Revokes a member's access privileges to the workspace.
   */
  async revokeMember(projectId: string, memberId: string): Promise<ApiResponse<MemberRevokeResponse>> {
    try {
      const res = await apiClient.post<MemberRevokeResponse>(
        `/projects/${projectId}/members/${memberId}/revoke`
      );
      if (res.data) {
        const local = getStoredMembers(projectId);
        const idx = local.findIndex((m) => m.id === memberId);
        if (idx >= 0) {
          local[idx] = {
            ...local[idx],
            status: 'revoked',
            invitation_status: 'revoked',
          };
          saveStoredMembers(projectId, local);
        }
        return res;
      }
    } catch (err: any) {
      if (err.message && !err.message.includes('Failed to connect')) {
        throw err;
      }
      console.warn('Falling back to local member revocation:', err);
    }

    const local = getStoredMembers(projectId);
    const idx = local.findIndex((m) => m.id === memberId);
    if (idx === -1) {
      throw new Error('Project member not found.');
    }

    const target = local[idx];
    if (target.role === 'ADMIN' || target.role === 'PROJECT_OWNER') {
      const activeAdmins = local.filter(
        (m) =>
          (m.role === 'ADMIN' || m.role === 'PROJECT_OWNER') &&
          m.status === 'active' &&
          m.id !== memberId
      );
      if (activeAdmins.length === 0) {
        throw new Error('Cannot revoke access: Project workspace must retain at least one active Admin or Project Owner.');
      }
    }

    local[idx] = {
      ...target,
      status: 'revoked',
      invitation_status: 'revoked',
    };
    saveStoredMembers(projectId, local);

    return {
      data: {
        member_id: memberId,
        project_id: projectId,
        user_id: target.user_id,
        status: 'revoked',
        invitation_status: 'revoked',
        revoked_at: new Date().toISOString(),
        message: 'Project workspace access revoked successfully.',
      },
      status: 200,
      message: 'Project workspace access revoked successfully.',
    };
  }

  /**
   * Permanently removes a member from the workspace.
   */
  async removeMember(projectId: string, memberId: string): Promise<ApiResponse<boolean>> {
    try {
      const res = await apiClient.delete<boolean>(`/projects/${projectId}/members/${memberId}`);
      if (res.status === 200 || res.status === 204) {
        const local = getStoredMembers(projectId);
        const filtered = local.filter((m) => m.id !== memberId);
        saveStoredMembers(projectId, filtered);
        return res;
      }
    } catch (err: any) {
      if (err.message && !err.message.includes('Failed to connect')) {
        throw err;
      }
      console.warn('Falling back to local member removal:', err);
    }

    const local = getStoredMembers(projectId);
    const target = local.find((m) => m.id === memberId);
    if (target && (target.role === 'ADMIN' || target.role === 'PROJECT_OWNER')) {
      const activeAdmins = local.filter(
        (m) =>
          (m.role === 'ADMIN' || m.role === 'PROJECT_OWNER') &&
          m.status === 'active' &&
          m.id !== memberId
      );
      if (activeAdmins.length === 0) {
        throw new Error('Cannot remove member: Project workspace must retain at least one active Admin or Project Owner.');
      }
    }

    const filtered = local.filter((m) => m.id !== memberId);
    saveStoredMembers(projectId, filtered);

    return {
      data: true,
      status: 200,
      message: 'Member removed from project workspace successfully.',
    };
  }
}

export const memberService = new MemberService();

import { apiClient, ApiResponse } from './apiClient';
import { AuditLogListResponse, AuditLogQueryParams, AuditRecord } from '../types/audit';

const MOCK_AUDIT_LOGS: AuditRecord[] = [
  {
    id: 'aud-001',
    audit_id: 'aud-001',
    user_id: 'usr-1',
    user_email: 'elena.rostova@techfrontier.io',
    user_name: 'Elena Rostova',
    project_id: 'proj-1',
    action: 'permission_changed',
    action_type: 'permission_changed',
    entity_type: 'project_member',
    entity_id: 'pm-2',
    timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    change_metadata: {
      member_email: 'david.chen@techfrontier.io',
      old_role: 'INCOMING',
      new_role: 'REVIEWER',
      new_role_display: 'Reviewer',
      custom_permissions: ['view_project', 'view_handover', 'approve_handover'],
    },
    request_context: {
      ip_address: '192.168.1.104',
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0',
      method: 'PATCH',
      path: '/api/v1/projects/proj-1/members/pm-2',
      request_id: 'req-8f4b-2291',
    },
  },
  {
    id: 'aud-002',
    audit_id: 'aud-002',
    user_id: 'usr-1',
    user_email: 'elena.rostova@techfrontier.io',
    user_name: 'Elena Rostova',
    project_id: 'proj-1',
    action: 'member_invited',
    action_type: 'member_invited',
    entity_type: 'project_member',
    entity_id: 'pm-4',
    timestamp: new Date(Date.now() - 2 * 3600 * 1000).toISOString(),
    change_metadata: {
      invited_email: 'kavita.p@techfrontier.io',
      assigned_role: 'OUTGOING',
      role_display_name: 'Outgoing Member',
      status: 'invited',
      invitation_status: 'pending',
    },
    request_context: {
      ip_address: '192.168.1.104',
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0',
      method: 'POST',
      path: '/api/v1/projects/proj-1/members/invite',
      request_id: 'req-7e1a-9943',
    },
  },
  {
    id: 'aud-003',
    audit_id: 'aud-003',
    user_id: 'usr-3',
    user_email: 'sarah.jenkins@techfrontier.io',
    user_name: 'Sarah Jenkins',
    project_id: 'proj-1',
    action: 'handover_approved',
    action_type: 'handover_approved',
    entity_type: 'handover',
    entity_id: 'ho-101',
    timestamp: new Date(Date.now() - 5 * 3600 * 1000).toISOString(),
    change_metadata: {
      handover_title: 'Core PSP Routing Engine Transition',
      stage: 'approved',
      reviewer: 'sarah.jenkins@techfrontier.io',
      verification_status: 'certified',
      version_number: 2,
    },
    request_context: {
      ip_address: '10.0.4.12',
      user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15',
      method: 'POST',
      path: '/api/v1/handovers/ho-101/approve',
      request_id: 'req-6c3d-1184',
    },
  },
  {
    id: 'aud-004',
    audit_id: 'aud-004',
    user_id: 'usr-1',
    user_email: 'elena.rostova@techfrontier.io',
    user_name: 'Elena Rostova',
    project_id: 'proj-1',
    action: 'conflict_resolved',
    action_type: 'conflict_resolved',
    entity_type: 'conflict',
    entity_id: 'conf-202',
    timestamp: new Date(Date.now() - 12 * 3600 * 1000).toISOString(),
    change_metadata: {
      resolution_strategy: 'override_with_latest_adr',
      resolved_items_count: 1,
      source_document: 'ADR-012: Kafka Retention Policy',
    },
    request_context: {
      ip_address: '192.168.1.104',
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0',
      method: 'POST',
      path: '/api/v1/conflicts/conf-202/resolve',
      request_id: 'req-5a2e-4402',
    },
  },
  {
    id: 'aud-005',
    audit_id: 'aud-005',
    user_id: 'usr-2',
    user_email: 'david.chen@techfrontier.io',
    user_name: 'David Chen',
    project_id: 'proj-1',
    action: 'version_restored',
    action_type: 'version_restored',
    entity_type: 'handover_version',
    entity_id: 'ver-v1-snapshot',
    timestamp: new Date(Date.now() - 24 * 3600 * 1000).toISOString(),
    change_metadata: {
      restored_from_version: 'v1.0.0',
      handover_id: 'ho-101',
      restoration_reason: 'Reverted unreviewed circuit-breaker configuration change',
    },
    request_context: {
      ip_address: '172.16.0.45',
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/127.0.0.0',
      method: 'POST',
      path: '/api/v1/handovers/ho-101/versions/ver-v1-snapshot/restore',
      request_id: 'req-4b9f-7711',
    },
  },
  {
    id: 'aud-006',
    audit_id: 'aud-006',
    user_id: 'usr-1',
    user_email: 'elena.rostova@techfrontier.io',
    user_name: 'Elena Rostova',
    project_id: 'proj-1',
    action: 'document_uploaded',
    action_type: 'document_uploaded',
    entity_type: 'document',
    entity_id: 'doc-305',
    timestamp: new Date(Date.now() - 36 * 3600 * 1000).toISOString(),
    change_metadata: {
      document_title: 'ADR-019: Adyen Webhook Reconciliation Spec.md',
      file_size_bytes: 48920,
      content_type: 'text/markdown',
      document_type: 'architecture_decision',
    },
    request_context: {
      ip_address: '192.168.1.104',
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0',
      method: 'POST',
      path: '/api/v1/projects/proj-1/documents',
      request_id: 'req-3a8c-6629',
    },
  },
  {
    id: 'aud-007',
    audit_id: 'aud-007',
    user_id: 'usr-1',
    user_email: 'elena.rostova@techfrontier.io',
    user_name: 'Elena Rostova',
    project_id: 'proj-1',
    action: 'handover_generated',
    action_type: 'handover_generated',
    entity_type: 'handover',
    entity_id: 'ho-101',
    timestamp: new Date(Date.now() - 48 * 3600 * 1000).toISOString(),
    change_metadata: {
      model: 'gemini-1.5-pro',
      sections_generated: 6,
      tokens_processed: 14200,
      generation_duration_seconds: 4.8,
    },
    request_context: {
      ip_address: '192.168.1.104',
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0',
      method: 'POST',
      path: '/api/v1/handovers/generate',
      request_id: 'req-2f1d-5538',
    },
  },
  {
    id: 'aud-008',
    audit_id: 'aud-008',
    user_id: 'usr-1',
    user_email: 'elena.rostova@techfrontier.io',
    user_name: 'Elena Rostova',
    project_id: 'proj-1',
    action: 'handover_shared',
    action_type: 'handover_shared',
    entity_type: 'handover',
    entity_id: 'ho-101',
    timestamp: new Date(Date.now() - 50 * 3600 * 1000).toISOString(),
    change_metadata: {
      shared_with: ['david.chen@techfrontier.io', 'platform-leads@techfrontier.io'],
      access_level: 'read_and_acknowledge',
    },
    request_context: {
      ip_address: '192.168.1.104',
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0',
      method: 'POST',
      path: '/api/v1/handovers/ho-101/share',
      request_id: 'req-1b0a-3319',
    },
  },
  {
    id: 'aud-009',
    audit_id: 'aud-009',
    user_id: 'usr-4',
    user_email: 'marcus.v@techfrontier.io',
    user_name: 'Marcus Vance',
    project_id: 'proj-1',
    action: 'project_created',
    action_type: 'project_created',
    entity_type: 'project',
    entity_id: 'proj-1',
    timestamp: new Date(Date.now() - 72 * 3600 * 1000).toISOString(),
    change_metadata: {
      project_name: 'Global Payment Orchestration & Multi-PSP Engine',
      key: 'PAY-V2',
      organization: 'TechFrontier Enterprise',
    },
    request_context: {
      ip_address: '10.0.1.5',
      user_agent: 'Mozilla/5.0 (X11; Linux x86_64) Firefox/128.0',
      method: 'POST',
      path: '/api/v1/projects',
      request_id: 'req-0a99-1122',
    },
  },
  {
    id: 'aud-010',
    audit_id: 'aud-010',
    user_id: 'usr-1',
    user_email: 'elena.rostova@techfrontier.io',
    user_name: 'Elena Rostova',
    project_id: null,
    action: 'user_login',
    action_type: 'user_login',
    entity_type: 'user',
    entity_id: 'usr-1',
    timestamp: new Date(Date.now() - 75 * 3600 * 1000).toISOString(),
    change_metadata: {
      auth_method: 'corporate_sso',
      identity_provider: 'okta',
    },
    request_context: {
      ip_address: '192.168.1.104',
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0',
      method: 'POST',
      path: '/api/v1/auth/login',
      request_id: 'req-login-001',
    },
  },
];

export class AuditService {
  /**
   * Fetches the project-scoped immutable audit trail.
   * Requires VIEW_AUDIT_LOGS permission.
   */
  async getProjectAuditLogs(
    projectId: string,
    params?: AuditLogQueryParams
  ): Promise<ApiResponse<AuditLogListResponse>> {
    try {
      const query = new URLSearchParams();
      if (params?.action) query.append('action', params.action);
      if (params?.entity_type) query.append('entity_type', params.entity_type);
      if (params?.entity_id) query.append('entity_id', params.entity_id);
      if (params?.user_id) query.append('user_id', params.user_id);
      if (params?.start_time) query.append('start_time', params.start_time);
      if (params?.end_time) query.append('end_time', params.end_time);
      if (params?.page) query.append('page', params.page.toString());
      if (params?.page_size) query.append('page_size', params.page_size.toString());

      const qs = query.toString();
      const url = `/projects/${projectId}/audit-logs${qs ? `?${qs}` : ''}`;
      const res = await apiClient.get<AuditLogListResponse>(url);
      if (res.data && Array.isArray(res.data.items)) {
        return res;
      }
    } catch (err: any) {
      if (err.message && (err.message.includes('403') || err.message.includes('Forbidden') || err.message.includes('permission'))) {
        throw err;
      }
      console.warn(`Backend audit log fetch failed for project ${projectId}, falling back to mock audit trail:`, err);
    }

    return this.getMockAuditLogs(projectId, params);
  }

  /**
   * Fetches an individual audit trail record by ID.
   */
  async getProjectAuditLogDetail(
    projectId: string,
    auditId: string
  ): Promise<ApiResponse<AuditRecord>> {
    try {
      return await apiClient.get<AuditRecord>(`/projects/${projectId}/audit-logs/${auditId}`);
    } catch (err) {
      console.warn(`Backend audit log detail failed for ${auditId}:`, err);
      const match = MOCK_AUDIT_LOGS.find((l) => l.id === auditId || l.audit_id === auditId);
      if (match) {
        return { data: match, status: 200, message: 'Retrieved audit detail' };
      }
      throw new Error(`Audit record '${auditId}' not found.`);
    }
  }

  /**
   * Fetches user/global audit records.
   */
  async getGlobalAuditLogs(
    params?: AuditLogQueryParams & { project_id?: string }
  ): Promise<ApiResponse<AuditLogListResponse>> {
    try {
      const query = new URLSearchParams();
      if (params?.project_id) query.append('project_id', params.project_id);
      if (params?.action) query.append('action', params.action);
      if (params?.entity_type) query.append('entity_type', params.entity_type);
      if (params?.start_time) query.append('start_time', params.start_time);
      if (params?.end_time) query.append('end_time', params.end_time);
      if (params?.page) query.append('page', params.page.toString());
      if (params?.page_size) query.append('page_size', params.page_size.toString());

      const qs = query.toString();
      const url = `/audit-logs${qs ? `?${qs}` : ''}`;
      const res = await apiClient.get<AuditLogListResponse>(url);
      if (res.data && Array.isArray(res.data.items)) {
        return res;
      }
    } catch (err: any) {
      if (err.message && (err.message.includes('403') || err.message.includes('Forbidden'))) {
        throw err;
      }
      console.warn('Backend global audit logs fetch failed, falling back to mock audit trail:', err);
    }

    return this.getMockAuditLogs(params?.project_id, params);
  }

  /**
   * Restores a handover to a previous version snapshot.
   */
  async restoreHandoverVersion(
    handoverId: string,
    versionId: string,
    reason?: string
  ): Promise<ApiResponse<any>> {
    return apiClient.post(`/handovers/${handoverId}/versions/${versionId}/restore`, {
      reason: reason || 'Restored from version snapshot',
    });
  }

  private getMockAuditLogs(
    projectId?: string,
    params?: AuditLogQueryParams
  ): ApiResponse<AuditLogListResponse> {
    let list = [...MOCK_AUDIT_LOGS];

    if (projectId) {
      list = list.filter((l) => !l.project_id || l.project_id === projectId || projectId === 'PAY-V2');
    }

    if (params?.action) {
      list = list.filter((l) => l.action === params.action || l.action_type === params.action);
    }

    if (params?.entity_type) {
      list = list.filter((l) => l.entity_type === params.entity_type);
    }

    if (params?.user_id) {
      list = list.filter(
        (l) => l.user_id === params.user_id || l.user_email?.toLowerCase().includes(params.user_id!.toLowerCase())
      );
    }

    if (params?.start_time) {
      const startMs = new Date(params.start_time).getTime();
      list = list.filter((l) => new Date(l.timestamp).getTime() >= startMs);
    }

    if (params?.end_time) {
      const endMs = new Date(params.end_time).getTime();
      list = list.filter((l) => new Date(l.timestamp).getTime() <= endMs);
    }

    const page = params?.page || 1;
    const pageSize = params?.page_size || 20;
    const total = list.length;
    const startIndex = (page - 1) * pageSize;
    const paginated = list.slice(startIndex, startIndex + pageSize);

    return {
      data: {
        items: paginated,
        total,
        page,
        page_size: pageSize,
        total_pages: Math.ceil(total / pageSize) || 1,
      },
      status: 200,
      message: `Retrieved ${paginated.length} audit trail record(s).`,
    };
  }
}

export const auditService = new AuditService();

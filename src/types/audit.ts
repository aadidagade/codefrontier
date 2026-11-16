export type AuditAction =
  | 'user_login'
  | 'user_logout'
  | 'project_created'
  | 'project_updated'
  | 'document_uploaded'
  | 'document_deleted'
  | 'handover_generated'
  | 'handover_modified'
  | 'handover_approved'
  | 'handover_rejected'
  | 'handover_shared'
  | 'version_restored'
  | 'permission_changed'
  | 'member_invited'
  | 'access_revoked'
  | 'conflict_resolved';

export type AuditEntityType =
  | 'user'
  | 'project'
  | 'document'
  | 'handover'
  | 'handover_section'
  | 'project_member'
  | 'conflict'
  | 'handover_version';

export interface AuditRecord {
  id: string;
  audit_id: string;
  user_id: string | null;
  user_email: string | null;
  user_name: string | null;
  project_id: string | null;
  action: AuditAction | string;
  action_type: string;
  entity_type: AuditEntityType | string;
  entity_id: string | null;
  timestamp: string;
  change_metadata: Record<string, any>;
  request_context: {
    ip_address?: string;
    user_agent?: string;
    method?: string;
    path?: string;
    request_id?: string;
    [key: string]: any;
  };
}

export interface AuditLogListResponse {
  items: AuditRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AuditLogQueryParams {
  action?: string;
  entity_type?: string;
  entity_id?: string;
  user_id?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}

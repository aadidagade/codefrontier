export type NotificationEventType =
  | 'new_handover_received'
  | 'review_requested'
  | 'handover_approved'
  | 'changes_requested'
  | 'document_uploaded'
  | 'conflict_detected'
  | 'incoming_member_acknowledged';

export type NotificationCategory = 'all' | 'unread' | 'handovers' | 'reviews' | 'conflicts' | 'documents';

export interface NotificationItem {
  id: string;
  type: NotificationEventType;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  targetUrl: string;
  actorName: string;
  actorAvatar?: string;
  projectKey: string;
  projectName: string;
  severity: 'normal' | 'urgent' | 'success' | 'warning';
}

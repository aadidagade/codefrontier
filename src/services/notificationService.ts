import { NotificationItem, NotificationEventType } from '../types/notification';

const STORAGE_KEY = 'kh_notifications_v1';

const initialNotifications: NotificationItem[] = [
  {
    id: 'notif-1',
    type: 'new_handover_received',
    title: 'New Handover Received',
    message: 'Elena Rostova assigned you the Customer Identity & Passkey Migration handover package.',
    timestamp: '10m ago',
    read: false,
    targetUrl: '/my-handovers/inc-auth-zero',
    actorName: 'Sarah Jenkins',
    actorAvatar: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    severity: 'urgent',
  },
  {
    id: 'notif-2',
    type: 'review_requested',
    title: 'Review Requested',
    message: 'Global Payment Orchestration (PAY-V2) v1.4 is ready for Project Lead audit and sign-off.',
    timestamp: '25m ago',
    read: false,
    targetUrl: '/review/rev-pay-v2',
    actorName: 'Elena Rostova',
    actorAvatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    projectKey: 'PAY-V2',
    projectName: 'Global Payment Orchestration & Multi-PSP Engine',
    severity: 'urgent',
  },
  {
    id: 'notif-3',
    type: 'conflict_detected',
    title: 'Documentation Conflict Detected',
    message: 'Contradiction between Arch Spec and Runbook v2: Database partition cutover deadline is disputed (Nov 15 vs Nov 20).',
    timestamp: '45m ago',
    read: false,
    targetUrl: '/conflicts',
    actorName: 'AI Evidence Verification Engine',
    projectKey: 'PAY-V2',
    projectName: 'Global Payment Orchestration',
    severity: 'warning',
  },
  {
    id: 'notif-4',
    type: 'document_uploaded',
    title: 'New Project Document Uploaded',
    message: 'Sarah Jenkins uploaded "PostgreSQL_Passkey_Partition_Cutover.docx" for AI chunking and analysis.',
    timestamp: '2h ago',
    read: true,
    targetUrl: '/documents',
    actorName: 'Sarah Jenkins',
    actorAvatar: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    severity: 'normal',
  },
  {
    id: 'notif-5',
    type: 'changes_requested',
    title: 'Changes Requested on Handover Draft',
    message: 'Marcus Vance requested revision on Section C (Redis multi-region failover timeouts and SLA guarantees).',
    timestamp: '4h ago',
    read: true,
    targetUrl: '/review/rev-pay-v2',
    actorName: 'Marcus Vance',
    actorAvatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80',
    projectKey: 'PAY-V2',
    projectName: 'Global Payment Orchestration',
    severity: 'warning',
  },
  {
    id: 'notif-6',
    type: 'handover_approved',
    title: 'Handover Certified & Approved',
    message: 'Distributed CockroachDB & Event Replicator (DB-SYNC) has been fully certified by Marcus Vance.',
    timestamp: '1d ago',
    read: true,
    targetUrl: '/review/rev-db-sync',
    actorName: 'Marcus Vance',
    actorAvatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80',
    projectKey: 'DB-SYNC',
    projectName: 'Distributed CockroachDB & Event Replicator',
    severity: 'success',
  },
  {
    id: 'notif-7',
    type: 'incoming_member_acknowledged',
    title: 'Incoming Member Acknowledged Handover',
    message: 'David Chen confirmed receipt and took ownership of 4 active continuation responsibilities.',
    timestamp: '1d ago',
    read: true,
    targetUrl: '/my-handovers/inc-pay-v2',
    actorName: 'David Chen',
    actorAvatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
    projectKey: 'PAY-V2',
    projectName: 'Global Payment Orchestration',
    severity: 'success',
  },
];

type NotificationListener = () => void;

class NotificationService {
  private listeners: Set<NotificationListener> = new Set();

  private load(): NotificationItem[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(initialNotifications));
        return [...initialNotifications];
      }
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) && parsed.length > 0 ? parsed : [...initialNotifications];
    } catch {
      return [...initialNotifications];
    }
  }

  private save(items: NotificationItem[]): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
      this.notifyListeners();
    } catch (err) {
      console.warn('Failed to save notifications:', err);
    }
  }

  private notifyListeners(): void {
    this.listeners.forEach((listener) => {
      try {
        listener();
      } catch (err) {
        console.error('Error in notification listener:', err);
      }
    });
  }

  subscribe(listener: NotificationListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  getNotifications(): NotificationItem[] {
    return this.load();
  }

  getUnreadCount(): number {
    return this.load().filter((n) => !n.read).length;
  }

  markAsRead(id: string): void {
    const list = this.load();
    const item = list.find((n) => n.id === id);
    if (item && !item.read) {
      item.read = true;
      this.save(list);
    }
  }

  markAllAsRead(): void {
    const list = this.load().map((n) => ({ ...n, read: true }));
    this.save(list);
  }

  deleteNotification(id: string): void {
    const list = this.load().filter((n) => n.id !== id);
    this.save(list);
  }

  clearAll(): void {
    this.save([]);
  }

  triggerSampleNotification(type: NotificationEventType): NotificationItem {
    const list = this.load();

    const sampleMap: Record<NotificationEventType, { title: string; message: string; targetUrl: string; severity: NotificationItem['severity']; projectKey: string; projectName: string }> = {
      new_handover_received: {
        title: 'New Handover Received',
        message: 'You have been assigned as the incoming successor for Multi-Region OAuth 2.1 Core.',
        targetUrl: '/my-handovers/inc-auth-zero',
        severity: 'urgent',
        projectKey: 'AUTH-ZERO',
        projectName: 'Customer Identity & Passkey Migration',
      },
      review_requested: {
        title: 'Review Requested',
        message: 'Sarah Jenkins submitted Passkey Cutover Architecture brief for final verification.',
        targetUrl: '/review/rev-auth-zero',
        severity: 'urgent',
        projectKey: 'AUTH-ZERO',
        projectName: 'Customer Identity & Passkey Migration',
      },
      handover_approved: {
        title: 'Handover Approved',
        message: 'Global Payment Gateway Handover v1.4 was certified and locked by Project Lead.',
        targetUrl: '/review/rev-pay-v2',
        severity: 'success',
        projectKey: 'PAY-V2',
        projectName: 'Global Payment Orchestration',
      },
      changes_requested: {
        title: 'Changes Requested',
        message: 'Reviewer requested additional evidence for Stripe fallback idempotency claims.',
        targetUrl: '/review/rev-pay-v2',
        severity: 'warning',
        projectKey: 'PAY-V2',
        projectName: 'Global Payment Orchestration',
      },
      document_uploaded: {
        title: 'New Project Document Uploaded',
        message: 'Architecture_ADR_042_Failover.pdf was ingested and is now Ready for Analysis.',
        targetUrl: '/documents',
        severity: 'normal',
        projectKey: 'PAY-V2',
        projectName: 'Global Payment Orchestration',
      },
      conflict_detected: {
        title: 'Conflict Detected',
        message: 'Contradiction found between AWS ECS auto-scale threshold and Terraform manifest.',
        targetUrl: '/conflicts',
        severity: 'warning',
        projectKey: 'PAY-V2',
        projectName: 'Global Payment Orchestration',
      },
      incoming_member_acknowledged: {
        title: 'Incoming Member Acknowledged',
        message: 'Successor acknowledged the handover package and initiated task continuation.',
        targetUrl: '/my-handovers/inc-auth-zero',
        severity: 'success',
        projectKey: 'AUTH-ZERO',
        projectName: 'Customer Identity & Passkey Migration',
      },
    };

    const config = sampleMap[type];
    const newItem: NotificationItem = {
      id: `notif-${Date.now()}`,
      type,
      title: config.title,
      message: config.message,
      timestamp: 'Just now',
      read: false,
      targetUrl: config.targetUrl,
      actorName: 'System Automation',
      projectKey: config.projectKey,
      projectName: config.projectName,
      severity: config.severity,
    };

    list.unshift(newItem);
    this.save(list);
    return newItem;
  }
}

export const notificationService = new NotificationService();

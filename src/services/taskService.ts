import { ContinuationTaskItem, ProgressNote } from '../types/incoming';
import { User } from '../types/common';
import { mockUsers, mockProjects } from '../data/mockData';
import { notificationService } from './notificationService';

export interface UnifiedTask {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
  priority: 'critical' | 'high' | 'medium';
  projectId: string;
  projectKey: string;
  projectName: string;
  handoverId?: string;
  assignedTo: User;
  dueDate: string;
  completedAt?: string;
  progressNotes: ProgressNote[];
  source: 'handover_continuation' | 'project_action';
  dependencies?: string[];
}

const STORAGE_KEY = 'kh_unified_tasks_v1';

const initialTasks: UnifiedTask[] = [
  {
    id: 'task-auth-1',
    title: 'Execute PostgreSQL 16 Partition Split Cutover',
    description:
      'Execute zero-downtime maintenance window partition migration for 1.4M enterprise credentials during Nov 20 scheduled drain.',
    status: 'in_progress',
    priority: 'critical',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    handoverId: 'inc-auth-zero',
    assignedTo: mockUsers[0], // Elena Rostova
    dueDate: '2026-11-20',
    source: 'handover_continuation',
    dependencies: ['Pre-cutover dry run on staging', 'DBA sign-off'],
    progressNotes: [
      {
        id: 'note-1',
        author: 'Elena Rostova',
        text: 'Dry run completed on staging clone with 15ms connection drain latency.',
        createdAt: '2026-11-09T17:30:00Z',
      },
    ],
  },
  {
    id: 'task-auth-2',
    title: 'Verify FIDO2 WebAuthn Level 3 Biometric Fallback',
    description:
      'Validate Touch ID, Face ID, and Windows Hello platform authenticators across iOS 18 Safari and Android 15 Chrome.',
    status: 'pending',
    priority: 'high',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    handoverId: 'inc-auth-zero',
    assignedTo: mockUsers[0],
    dueDate: '2026-11-22',
    source: 'handover_continuation',
    dependencies: ['Mobile SDK build v3.4'],
    progressNotes: [],
  },
  {
    id: 'task-pay-1',
    title: 'Verify Stripe to Adyen Failover Thresholds in Staging',
    description:
      'Simulate circuit breaker trip on Stripe 503 errors and verify Adyen secondary routing within 800ms SLA.',
    status: 'in_progress',
    priority: 'high',
    projectId: 'proj-1',
    projectKey: 'PAY-V2',
    projectName: 'Global Payment Orchestration & Multi-PSP Engine',
    handoverId: 'inc-pay-v2',
    assignedTo: mockUsers[1], // David Chen
    dueDate: '2026-11-18',
    source: 'handover_continuation',
    dependencies: ['Stripe test webhooks mock server'],
    progressNotes: [
      {
        id: 'note-2',
        author: 'David Chen',
        text: 'Chaos testing harness prepared in k8s-staging namespace.',
        createdAt: '2026-11-08T11:00:00Z',
      },
    ],
  },
  {
    id: 'task-pay-2',
    title: 'Audit PCI-DSS Scope Reduction for Tokenized Payloads',
    description:
      'Obtain external QSA pre-audit validation on raw PAN isolation in HSM boundary.',
    status: 'pending',
    priority: 'critical',
    projectId: 'proj-1',
    projectKey: 'PAY-V2',
    projectName: 'Global Payment Orchestration & Multi-PSP Engine',
    handoverId: 'inc-pay-v2',
    assignedTo: mockUsers[1],
    dueDate: '2026-11-25',
    source: 'handover_continuation',
    dependencies: [],
    progressNotes: [],
  },
  {
    id: 'task-db-1',
    title: 'Conduct Hardware Security Module (HSM) Key Rotation Ceremony',
    description:
      'Rotate AES-256 session encryption keys with VP of Engineering and Lead Architect co-sign.',
    status: 'pending',
    priority: 'critical',
    projectId: 'proj-3',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    assignedTo: mockUsers[4], // Kavita Patel
    dueDate: '2026-11-28',
    source: 'project_action',
    dependencies: ['Key custodian quorum confirmation'],
    progressNotes: [],
  },
  {
    id: 'task-db-2',
    title: 'Decommission Legacy Redis Sentinel Node in eu-west-1',
    description:
      'Safely drain active pub/sub subscriptions after cutover to AWS ElastiCache Valkey multi-master cluster.',
    status: 'completed',
    priority: 'medium',
    projectId: 'proj-2',
    projectKey: 'DB-SYNC',
    projectName: 'Distributed CockroachDB & Event Replicator',
    assignedTo: mockUsers[2], // Sarah Jenkins
    dueDate: '2026-11-05',
    completedAt: '2026-11-05T14:20:00Z',
    source: 'project_action',
    dependencies: [],
    progressNotes: [
      {
        id: 'note-3',
        author: 'Sarah Jenkins',
        text: 'Drained 42,000 active socket connections without error.',
        createdAt: '2026-11-05T14:15:00Z',
      },
    ],
  },
];

type TaskListener = () => void;

class TaskService {
  private listeners: Set<TaskListener> = new Set();

  private load(): UnifiedTask[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(initialTasks));
        return [...initialTasks];
      }
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) && parsed.length > 0 ? parsed : [...initialTasks];
    } catch {
      return [...initialTasks];
    }
  }

  private save(tasks: UnifiedTask[]): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
      this.notifyListeners();
    } catch (err) {
      console.warn('Failed to save tasks:', err);
    }
  }

  private notifyListeners(): void {
    this.listeners.forEach((l) => {
      try {
        l();
      } catch (err) {
        console.error('Error in task listener:', err);
      }
    });
  }

  subscribe(listener: TaskListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  getTasks(filter?: {
    status?: string;
    priority?: string;
    projectId?: string;
    assigneeId?: string;
    query?: string;
  }): UnifiedTask[] {
    let list = this.load();

    if (!filter) return list;

    if (filter.status && filter.status !== 'all') {
      list = list.filter((t) => t.status === filter.status);
    }

    if (filter.priority && filter.priority !== 'all') {
      list = list.filter((t) => t.priority === filter.priority);
    }

    if (filter.projectId && filter.projectId !== 'all') {
      list = list.filter((t) => t.projectId === filter.projectId);
    }

    if (filter.assigneeId && filter.assigneeId !== 'all') {
      list = list.filter((t) => t.assignedTo.id === filter.assigneeId);
    }

    if (filter.query) {
      const q = filter.query.toLowerCase().trim();
      list = list.filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q) ||
          t.projectKey.toLowerCase().includes(q) ||
          t.projectName.toLowerCase().includes(q) ||
          t.assignedTo.name.toLowerCase().includes(q)
      );
    }

    return list;
  }

  getTaskById(id: string): UnifiedTask | undefined {
    return this.load().find((t) => t.id === id);
  }

  toggleTaskCompletion(id: string): UnifiedTask | null {
    const list = this.load();
    const item = list.find((t) => t.id === id);
    if (!item) return null;

    if (item.status === 'completed') {
      item.status = 'pending';
      item.completedAt = undefined;
    } else {
      item.status = 'completed';
      item.completedAt = new Date().toISOString();

      if (item.priority === 'critical') {
        notificationService.triggerSampleNotification('incoming_member_acknowledged');
      }
    }

    this.save(list);
    return item;
  }

  updateTaskStatus(
    id: string,
    status: 'pending' | 'in_progress' | 'completed'
  ): UnifiedTask | null {
    const list = this.load();
    const item = list.find((t) => t.id === id);
    if (!item) return null;

    item.status = status;
    item.completedAt = status === 'completed' ? new Date().toISOString() : undefined;
    this.save(list);
    return item;
  }

  addProgressNote(taskId: string, noteText: string, authorName: string): ProgressNote | null {
    const list = this.load();
    const item = list.find((t) => t.id === taskId);
    if (!item) return null;

    const newNote: ProgressNote = {
      id: `note-${Date.now()}`,
      author: authorName,
      text: noteText.trim(),
      createdAt: new Date().toISOString(),
    };

    item.progressNotes.unshift(newNote);
    this.save(list);
    return newNote;
  }

  createTask(payload: {
    title: string;
    description: string;
    priority: 'critical' | 'high' | 'medium';
    projectId: string;
    assignedToId?: string;
    dueDate?: string;
  }): UnifiedTask {
    const list = this.load();
    const project = mockProjects.find((p) => p.id === payload.projectId) || mockProjects[0];
    const assignee =
      mockUsers.find((u) => u.id === payload.assignedToId) || mockUsers[0];

    const newTask: UnifiedTask = {
      id: `task-${Date.now()}`,
      title: payload.title,
      description: payload.description,
      status: 'pending',
      priority: payload.priority,
      projectId: project.id,
      projectKey: project.key,
      projectName: project.title,
      assignedTo: assignee,
      dueDate: payload.dueDate || new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0],
      source: 'project_action',
      progressNotes: [],
    };

    list.unshift(newTask);
    this.save(list);
    return newTask;
  }

  deleteTask(id: string): boolean {
    const list = this.load();
    const filtered = list.filter((t) => t.id !== id);
    if (filtered.length === list.length) return false;
    this.save(filtered);
    return true;
  }
}

export const taskService = new TaskService();

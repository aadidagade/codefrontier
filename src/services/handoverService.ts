/**
 * Isolated Handover Service for Knowledge Handover Platform.
 * 
 * BACKEND INTEGRATION NOTE:
 * When connecting to FastAPI endpoints, set USE_MOCK = false in apiClient.ts.
 * The REST endpoints mirror standard AI generation contracts:
 * - POST   /api/v1/handovers/generate    -> Generates structured handover from document IDs (Server-Sent Events / streaming)
 * - GET    /api/v1/handovers/{id}        -> Retrieves synthesized handover draft
 * - PUT    /api/v1/handovers/{id}        -> Updates section content edited by user
 * - POST   /api/v1/handovers/{id}/sign   -> Cryptographic sign-off
 */

import { apiClient, ApiResponse } from './apiClient';
import {
  HandoverSession,
  HandoverStage,
  GenerationConfig,
  GeneratedHandover,
} from '../types/handover';
import { mockHandovers, mockUsers, mockCurrentUser } from '../data/mockData';

const GENERATED_STORE_KEY = 'kh_generated_handovers_store';

export const INITIAL_GENERATED_HANDOVER: GeneratedHandover = {
  id: 'gen-hnd-101',
  projectKey: 'PAY-V2',
  projectName: 'Global Payment Orchestration & Multi-PSP Engine',
  createdAt: '2026-11-10T00:15:00Z',
  generatedBy: mockCurrentUser,
  evidenceScore: 96,
  targetRole: 'Staff Site Reliability Engineer / Distributed Systems',
  scope: 'Full Architectural & Operational Handover',
  overview: {
    purpose:
      'High-throughput payment gateway routing with zero-downtime failover across Stripe, Adyen, and regional processors. Built to eliminate transaction failure cascades under peak traffic (50k RPS) through decoupled circuit breakers and real-time Kafka settlements.',
    currentStatus:
      'Core routing logic, cryptographic key rotation lambdas, and settlement reconciliation pipelines are codified and verified in staging. Dual-PSP failover tested against 50k RPS load tests. Final review pending on 3:00 AM banking timeout overrides.',
    overallProgress: 72,
  },
  decisions: [
    {
      id: 'dec-1',
      decision: 'Envoy Sidecar Dynamic Failover over Application-Layer Retries',
      date: 'Oct 14, 2026',
      rationale:
        'Prevents thread exhaustion in the Go gateway process during PSP latency spikes. Envoy handles timeouts in <1.4ms with 50ms Redis cluster TTL heartbeats.',
      supportingSource: 'ADR-014_Zero_Downtime_Circuit_Breaker.pdf (Page 3)',
      isUncertain: false,
    },
    {
      id: 'dec-2',
      decision: 'Dead-Letter Queue (DLQ) 14-Day Settlement Retention',
      date: 'Sep 22, 2026',
      rationale:
        'Banking partner reconciliation audits require a 10-business-day window to re-drive dropped settlement batches without loss of ledger idempotency.',
      supportingSource: 'Payment_Settlement_Runbook_3AM_Escalation.docx (Section 2.4)',
      isUncertain: false,
    },
    {
      id: 'dec-3',
      decision: 'Automated Multi-AZ RDS Failover Configuration',
      date: 'Nov 02, 2026',
      rationale:
        'Adopted automated DNS switchover in main.tf infrastructure. (Contradicts older Confluence doc stating manual failover via AWS console).',
      supportingSource: 'Terraform Infrastructure PR #612 (main.tf:L48)',
      isUncertain: true, // Uncertain / conflict flagged!
    },
  ],
  tasks: [
    {
      id: 'tsk-1',
      taskName: 'KMS Automated Key Rotation Lambda Validation',
      assignedOwner: mockUsers[0], // Elena
      status: 'verified',
      priority: 'critical',
      dueDate: 'Nov 12, 2026',
    },
    {
      id: 'tsk-2',
      taskName: 'Simulated 3:00 AM Banking Settlement Degradation Walkthrough',
      assignedOwner: mockUsers[1], // David
      status: 'pending_handover',
      priority: 'critical',
      dueDate: 'Nov 14, 2026',
    },
    {
      id: 'tsk-3',
      taskName: 'Transfer 1Password Bastion SSH Credentials Vault',
      assignedOwner: mockUsers[1], // David
      status: 'verified',
      priority: 'high',
      dueDate: 'Nov 15, 2026',
    },
    {
      id: 'tsk-4',
      taskName: 'Update Runbook Confluence Tree to reflect Terraform Multi-AZ',
      assignedOwner: mockUsers[2], // Sarah
      status: 'in_progress',
      priority: 'medium',
      dueDate: 'Nov 18, 2026',
    },
  ],
  blockersAndRisks: [
    {
      id: 'blk-1',
      description: 'PSP Webhook Secret Rotation in 12 Days',
      impact:
        'If webhook signature keys expire without KMS alias switch, merchant webhook callbacks will fail with HTTP 401 Unauthorized.',
      severity: 'critical',
      supportingEvidence: 'ADR-014 (Gotchas & Mitigations §1)',
      isUncertain: false,
    },
    {
      id: 'blk-2',
      description: 'Shadow Cron Jobs on Staging Bastion Host',
      impact:
        'Three background settlement reconciliation cron jobs run directly in /etc/cron.d without Kubernetes CronJob observability.',
      severity: 'high',
      supportingEvidence: 'Payment_Settlement_Runbook.docx (Appendix B)',
      isUncertain: true, // Highlighted
    },
    {
      id: 'blk-3',
      description: 'Third-party PSP Rate-limit Throttles',
      impact:
        'No documented backoff strategy exists for HTTP 429 responses in legacy Stripe retry loops during flash sales.',
      severity: 'medium',
      supportingEvidence: 'Open Knowledge Gap #gap-1',
      isUncertain: true,
    },
  ],
  dependencies: [
    {
      id: 'dep-1',
      dependency: 'Barclays BACS Clearing House SFTP Gateway',
      relatedTask: 'Batch Reconciliation Drain Protocol',
      requiredPersonOrResource: 'Treasury Banking API Gateway (VPN tunnel required)',
      currentStatus: 'Operational (Ping 24ms)',
    },
    {
      id: 'dep-2',
      dependency: 'Redis Multi-Cluster Circuit Breaker State',
      relatedTask: 'Envoy Sidecar Failover Routing',
      requiredPersonOrResource: 'Core Infra Team (ElastiCache Redis v7.2)',
      currentStatus: 'Healthy (0.8ms latency)',
    },
    {
      id: 'dep-3',
      dependency: 'HashiCorp Vault Production Root Token',
      relatedTask: 'Secrets & 1Password Vault Transfer',
      requiredPersonOrResource: 'Marcus Vance (Engineering Director)',
      currentStatus: 'Access Granted for Verification',
    },
  ],
  unresolvedQuestions: [
    {
      id: 'uq-1',
      question: 'Who maintains manual override authority for chargeback dispute batches?',
      whyItMatters:
        'Disputes over $50,000 automatically lock settlements unless authorized within 48 hours.',
      whoNeedsToConfirm: 'Elena Rostova (Lead) & Finance Ops Director',
      isUncertain: true,
    },
    {
      id: 'uq-2',
      question: 'Is Kafka consumer partition key keyed by merchant_id or currency_code?',
      whyItMatters:
        'Wrong partitioning could cause out-of-order ledger updates during concurrent multi-currency payments.',
      whoNeedsToConfirm: 'David Chen (Successor) to verify against schema registry',
      isUncertain: false,
    },
  ],
  recommendedNextActions: [
    {
      id: 'act-1',
      action: 'Perform live Bastion drain rehearsal in staging',
      priority: 'high',
      suggestedOwner: 'David Chen',
      reason: 'Ensures successor can execute manual partition flush under simulated 3:00 AM pressure.',
    },
    {
      id: 'act-2',
      action: 'Resolve Terraform vs Confluence RDS failover discrepancy',
      priority: 'high',
      suggestedOwner: 'Sarah Jenkins',
      reason: 'Prevents split-brain incident during database maintenance.',
    },
    {
      id: 'act-3',
      action: 'Schedule formal architectural sign-off meeting',
      priority: 'medium',
      suggestedOwner: 'Elena Rostova & Marcus Vance',
      reason: 'Final sign-off meeting required for SOC2 handover compliance.',
    },
  ],
  evidenceCitations: [
    {
      id: 'ev-1',
      title: 'ADR-014 Circuit Breaker Specification',
      sourceDocName: 'ADR-014_Zero_Downtime_Circuit_Breaker.pdf',
      excerpt: 'Envoy dynamic routing Decouples PSP failover from client retry storm. Benchmark latency < 1.4ms under 50k RPS.',
      confidence: 98,
      externalLink: 'https://github.com/techfrontier/payments/pull/412',
    },
    {
      id: 'ev-2',
      title: 'Settlement Batch Emergency Drain',
      sourceDocName: 'Payment_Settlement_Runbook_3AM_Escalation.docx',
      excerpt: 'kubectl exec -it deployment/settlement-drain-worker -n payments -- ./drain --force-flush',
      confidence: 94,
    },
    {
      id: 'ev-3',
      title: 'KMS Webhook Rotation Cycle',
      sourceDocName: 'Production_Infrastructure_Secrets_Audit.md',
      excerpt: 'Stripe live webhook secret rotated every 90 days. Auto-dispatched to KMS alias pay-webhook-live.',
      confidence: 96,
      isFlagged: false,
    },
    {
      id: 'ev-4',
      title: 'RDS Multi-AZ Conflict Warning',
      sourceDocName: 'Terraform PR #612 vs Confluence Runbook',
      excerpt: 'Terraform enables auto_failover=true while runbook specifies manual failover.',
      confidence: 68,
      isFlagged: true, // Flagged uncertain
    },
  ],
};

function loadGeneratedHandovers(): GeneratedHandover[] {
  try {
    const raw = localStorage.getItem(GENERATED_STORE_KEY);
    if (!raw) {
      localStorage.setItem(GENERATED_STORE_KEY, JSON.stringify([INITIAL_GENERATED_HANDOVER]));
      return [INITIAL_GENERATED_HANDOVER];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : [INITIAL_GENERATED_HANDOVER];
  } catch {
    return [INITIAL_GENERATED_HANDOVER];
  }
}

function saveGeneratedHandovers(handovers: GeneratedHandover[]): void {
  try {
    localStorage.setItem(GENERATED_STORE_KEY, JSON.stringify(handovers));
  } catch (err) {
    console.warn('Failed to persist generated handovers:', err);
  }
}

class HandoverService {
  async getAll(): Promise<ApiResponse<HandoverSession[]>> {
    return apiClient.executeMock(() => [...mockHandovers]);
  }

  async getById(id: string): Promise<ApiResponse<HandoverSession | undefined>> {
    return apiClient.executeMock(() => mockHandovers.find((h) => h.id === id));
  }

  async updateStage(id: string, stage: HandoverStage): Promise<ApiResponse<HandoverSession>> {
    return apiClient.executeMock(() => {
      const session = mockHandovers.find((h) => h.id === id);
      if (!session) throw new Error('Handover session not found');
      session.currentStage = stage;
      return session;
    });
  }

  async toggleChecklistItem(sessionId: string, itemId: string): Promise<ApiResponse<HandoverSession>> {
    return apiClient.executeMock(() => {
      const session = mockHandovers.find((h) => h.id === sessionId);
      if (!session) throw new Error('Handover session not found');
      const item = session.checklist.find((c) => c.id === itemId);
      if (item) {
        item.completed = !item.completed;
        const total = session.checklist.length;
        const done = session.checklist.filter((c) => c.completed).length;
        session.progressPercentage = Math.round((done / total) * 100);
      }
      return session;
    });
  }

  /**
   * Retrieves synthesized handover by ID
   */
  async getGeneratedHandover(id?: string): Promise<ApiResponse<GeneratedHandover>> {
    return apiClient.executeMock(() => {
      const list = loadGeneratedHandovers();
      const found = list.find((g) => g.id === id) || list[0] || INITIAL_GENERATED_HANDOVER;
      return found;
    });
  }

  /**
   * Updates section content in a generated handover
   */
  async updateGeneratedHandover(
    id: string,
    updates: Partial<GeneratedHandover>
  ): Promise<ApiResponse<GeneratedHandover>> {
    return apiClient.executeMock(() => {
      const list = loadGeneratedHandovers();
      const index = list.findIndex((g) => g.id === id);
      if (index === -1) {
        throw new Error('Handover record not found');
      }
      const updated: GeneratedHandover = {
        ...list[index],
        ...updates,
      };
      list[index] = updated;
      saveGeneratedHandovers(list);
      return updated;
    });
  }

  /**
   * Simulates AI Handover synthesis across the 8 stages with streaming stage updates
   */
  async generateHandover(
    config: GenerationConfig,
    onStageUpdate?: (stageId: number, detail: string) => void
  ): Promise<ApiResponse<GeneratedHandover>> {
    return apiClient.executeMock(async () => {
      const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

      const stages = [
        { id: 1, detail: 'Searching Qdrant vector space for project documentation & PR comments...' },
        { id: 2, detail: 'Synthesizing architectural purpose, high-throughput SLAs, and project boundaries...' },
        { id: 3, detail: 'Parsed 18 Architectural Decision Records (ADRs) with rationale and evidence links...' },
        { id: 4, detail: 'Extracted 4 on-call maintenance tasks and assigned owner mappings...' },
        { id: 5, detail: 'Flagged 1 critical secret rotation risk and 2 tribal gotchas...' },
        { id: 6, detail: 'Mapped Envoy proxies, Redis state, and Barclays SFTP clearing dependencies...' },
        { id: 7, detail: 'Detected configuration drift contradiction: main.tf vs Confluence runbook...' },
        { id: 8, detail: 'Assembled final structured handover draft with evidence citations...' },
      ];

      for (const st of stages) {
        onStageUpdate?.(st.id, st.detail);
        await delay(500); // realistic progressive simulation
      }

      const newHandover: GeneratedHandover = {
        ...INITIAL_GENERATED_HANDOVER,
        id: `gen-hnd-${Date.now()}`,
        createdAt: new Date().toISOString(),
        targetRole: config.incomingRole || INITIAL_GENERATED_HANDOVER.targetRole,
        scope: config.handoverScope || INITIAL_GENERATED_HANDOVER.scope,
      };

      const list = loadGeneratedHandovers();
      list.unshift(newHandover);
      saveGeneratedHandovers(list);

      return newHandover;
    });
  }
}

export const handoverService = new HandoverService();

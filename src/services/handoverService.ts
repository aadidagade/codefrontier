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
  HandoverVersionItem,
  VersionDiffResponse,
  SectionDiffItem,
  TaskDiffItem,
  ResponsibilityDiffItem,
  SharedHandoverItem,
  HandoverContinuityData,
  TaskProgressUpdateItem,
} from '../types/handover';
import { mockHandovers, mockUsers, mockCurrentUser } from '../data/mockData';
import { incomingService } from './incomingService';

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

function isUuid(val: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(val);
}

const MOCK_VERSIONS_STORAGE_KEY = 'kh_handover_versions_store_v2';

function getStoredMockVersions(handoverId: string): HandoverVersionItem[] {
  try {
    const raw = localStorage.getItem(`${MOCK_VERSIONS_STORAGE_KEY}_${handoverId}`);
    if (raw) return JSON.parse(raw);
  } catch (e) {}

  const initial: HandoverVersionItem[] = [
    {
      id: 'ver-1-0-baseline',
      handover_id: handoverId,
      version_number: 'v1.0',
      version_description: 'Initial formally approved baseline snapshot for customer migration.',
      approval_status: 'APPROVED',
      is_latest: false,
      created_by: 'usr-sarah-jenkins',
      creator_name: 'Sarah Jenkins',
      created_at: '2026-11-09T16:00:00Z',
      snapshot: {
        title: 'Customer Identity & Passkey Migration',
        version: 'v1.0',
        approval_status: 'APPROVED',
        project_overview:
          'Migrate 1.4 million active enterprise and consumer user sessions to passwordless WebAuthn/FIDO2 passkeys, eliminating phishing vulnerabilities and deprecating legacy SMS 2FA.',
        technical_architecture:
          'WebAuthn Level 3 platform biometrics with Redis eu-west-1 regional clustering and PostgreSQL 16 partition split cutover.',
        key_decisions:
          '1. Platform Authenticator Biometrics Default\n2. Database Cutover 20 November\n3. Active-Active DR Locality across EU',
        pending_tasks: [
          {
            title: 'Conduct Final PostgreSQL 16 Partition Rehearsal in Staging',
            status: 'pending',
            assigned_to_name: 'Elena Rostova',
            priority: 'critical',
          },
          {
            title: 'Verify Redis Multi-Region Sentinel Failover in eu-central-1',
            status: 'in_progress',
            assigned_to_name: 'David Chen',
            priority: 'high',
          },
        ],
        risks_and_blockers: 'Redis regional replication latency spike risk during partition split.',
        dependencies: 'DB Staging Bastion Access, Grafana DB Connection Pool Dashboard',
        team_responsibilities:
          'Sarah Jenkins (Outgoing Lead), Elena Rostova (Incoming Successor), Marcus Vance (Project Owner)',
        recommendations: 'Complete staging partition rehearsal by Nov 13.',
      },
    },
    {
      id: 'ver-1-1-revision',
      handover_id: handoverId,
      version_number: 'v1.1',
      version_description:
        'Sprint 42 updates: Extended cutover deadline by 5 days and added Redis Sentinel failover test runbooks.',
      approval_status: 'IN_REVIEW',
      parent_version_id: 'ver-1-0-baseline',
      is_latest: true,
      created_by: 'usr-elena-rostova',
      creator_name: 'Elena Rostova',
      created_at: '2026-11-12T11:30:00Z',
      snapshot: {
        title: 'Customer Identity & Passkey Migration',
        version: 'v1.1',
        approval_status: 'IN_REVIEW',
        project_overview:
          'Migrate 1.4 million active enterprise and consumer user sessions to passwordless WebAuthn/FIDO2 passkeys, eliminating phishing vulnerabilities and deprecating legacy SMS 2FA. Updated with Sprint 42 partition testing results and multi-region failover benchmarks.',
        technical_architecture:
          'WebAuthn Level 3 platform biometrics with Redis eu-west-1 regional clustering and PostgreSQL 16 partition split cutover with connection pool warmers.',
        key_decisions:
          '1. Platform Authenticator Biometrics Default\n2. Database Cutover 20 November (Extended by 5 days)\n3. Active-Active DR Locality across EU\n4. Connection pool pre-warming script validated in staging',
        pending_tasks: [
          {
            title: 'Conduct Final PostgreSQL 16 Partition Rehearsal in Staging',
            status: 'in_progress',
            assigned_to_name: 'Elena Rostova',
            priority: 'critical',
          },
          {
            title: 'Verify Redis Multi-Region Sentinel Failover in eu-central-1',
            status: 'completed',
            assigned_to_name: 'Elena Rostova',
            priority: 'high',
          },
          {
            title: 'Run SOC-2 Audit Token Redaction Simulation',
            status: 'pending',
            assigned_to_name: 'Alex Chen',
            priority: 'medium',
          },
        ],
        risks_and_blockers:
          'Redis regional replication latency spike risk mitigated via Sentinel buffer pools.',
        dependencies:
          'DB Staging Bastion Access, Grafana DB Connection Pool Dashboard, Vault Prod Secrets Access',
        team_responsibilities:
          'Elena Rostova (Continuity Lead), Marcus Vance (Project Owner), Alex Chen (Security Analyst)',
        recommendations:
          'Execute connection pool pre-warming script 30 minutes before cutover maintenance window.',
      },
    },
  ];

  try {
    localStorage.setItem(`${MOCK_VERSIONS_STORAGE_KEY}_${handoverId}`, JSON.stringify(initial));
  } catch (e) {}

  return initial;
}

function saveStoredMockVersions(handoverId: string, items: HandoverVersionItem[]): void {
  try {
    localStorage.setItem(`${MOCK_VERSIONS_STORAGE_KEY}_${handoverId}`, JSON.stringify(items));
  } catch (e) {}
}

function generateMockDiff(
  fromVer: HandoverVersionItem,
  toVer: HandoverVersionItem
): VersionDiffResponse {
  const s1 = fromVer.snapshot || {};
  const s2 = toVer.snapshot || {};

  const sectionKeys: { key: string; label: string }[] = [
    { key: 'project_overview', label: 'Project Overview' },
    { key: 'technical_architecture', label: 'Technical Architecture' },
    { key: 'key_decisions', label: 'Key Decisions & ADRs' },
    { key: 'risks_and_blockers', label: 'Blockers & Failure Modes' },
    { key: 'dependencies', label: 'External & Internal Dependencies' },
    { key: 'team_responsibilities', label: 'Team Ownership & Contacts' },
    { key: 'recommendations', label: 'Recommended Next Actions' },
  ];

  const sectionDiffs: SectionDiffItem[] = [];
  let addedCount = 0;
  let removedCount = 0;
  let modCount = 0;
  let unchCount = 0;

  for (const { key, label } of sectionKeys) {
    const oldText = typeof s1[key] === 'string' ? s1[key] : (s1[key] ? JSON.stringify(s1[key], null, 2) : '');
    const newText = typeof s2[key] === 'string' ? s2[key] : (s2[key] ? JSON.stringify(s2[key], null, 2) : '');

    const oldLines = oldText ? oldText.split('\n') : [];
    const newLines = newText ? newText.split('\n') : [];

    const hasChanged = oldText !== newText;
    let changeType: 'ADDED' | 'REMOVED' | 'MODIFIED' | 'UNCHANGED' = 'UNCHANGED';
    let addedLines: string[] = [];
    let removedLines: string[] = [];

    if (!oldText && newText) {
      changeType = 'ADDED';
      addedCount++;
      addedLines = newLines;
    } else if (oldText && !newText) {
      changeType = 'REMOVED';
      removedCount++;
      removedLines = oldLines;
    } else if (hasChanged) {
      changeType = 'MODIFIED';
      modCount++;
      addedLines = newLines.filter((l: string) => !oldLines.includes(l));
      removedLines = oldLines.filter((l: string) => !newLines.includes(l));
    } else {
      unchCount++;
    }

    sectionDiffs.push({
      section_type: key,
      title: label,
      has_changed: hasChanged,
      change_type: changeType,
      old_content: oldText || null,
      new_content: newText || null,
      added_lines: addedLines,
      removed_lines: removedLines,
      diff_summary: hasChanged
        ? `Modified in revision ${toVer.version_number}: ${addedLines.length} line(s) added, ${removedLines.length} line(s) removed.`
        : 'Identical between versions.',
    });
  }

  // Task differences
  const tasks1: any[] = Array.isArray(s1.pending_tasks) ? s1.pending_tasks : [];
  const tasks2: any[] = Array.isArray(s2.pending_tasks) ? s2.pending_tasks : [];

  const taskDiffs: TaskDiffItem[] = [];
  let taskStatusChanges = 0;
  let addedTasks = 0;
  let removedTasks = 0;
  const handledTitles = new Set<string>();

  for (const t2 of tasks2) {
    const title = t2.title || t2.taskName || 'Untitled Task';
    handledTitles.add(title);
    const t1 = tasks1.find((x) => (x.title || x.taskName) === title);

    if (!t1) {
      addedTasks++;
      taskDiffs.push({
        task_id: t2.id || null,
        title,
        change_type: 'ADDED',
        status_changed: true,
        old_status: null,
        new_status: t2.status || 'pending',
        assignee_changed: true,
        old_assignee: null,
        new_assignee: t2.assigned_to_name || t2.assignedOwner?.name || 'Unassigned',
        priority_changed: true,
        old_priority: null,
        new_priority: t2.priority || 'medium',
        description_changed: false,
      });
    } else {
      const statusChanged = t1.status !== t2.status;
      const assignee1 = t1.assigned_to_name || t1.assignedOwner?.name;
      const assignee2 = t2.assigned_to_name || t2.assignedOwner?.name;
      const assigneeChanged = assignee1 !== assignee2;
      const priorityChanged = t1.priority !== t2.priority;
      const isChanged = statusChanged || assigneeChanged || priorityChanged;

      if (statusChanged) taskStatusChanges++;

      taskDiffs.push({
        task_id: t2.id || t1.id || null,
        title,
        change_type: isChanged ? 'MODIFIED' : 'UNCHANGED',
        status_changed: statusChanged,
        old_status: t1.status || 'pending',
        new_status: t2.status || 'pending',
        assignee_changed: assigneeChanged,
        old_assignee: assignee1 || 'Unassigned',
        new_assignee: assignee2 || 'Unassigned',
        priority_changed: priorityChanged,
        old_priority: t1.priority || 'medium',
        new_priority: t2.priority || 'medium',
        description_changed: false,
      });
    }
  }

  for (const t1 of tasks1) {
    const title = t1.title || t1.taskName || 'Untitled Task';
    if (!handledTitles.has(title)) {
      removedTasks++;
      taskDiffs.push({
        task_id: t1.id || null,
        title,
        change_type: 'REMOVED',
        status_changed: true,
        old_status: t1.status || 'pending',
        new_status: null,
        assignee_changed: true,
        old_assignee: t1.assigned_to_name || t1.assignedOwner?.name || 'Unassigned',
        new_assignee: null,
        priority_changed: true,
        old_priority: t1.priority || 'medium',
        new_priority: null,
        description_changed: false,
      });
    }
  }

  // Responsibility diffs
  const respDiffs: ResponsibilityDiffItem[] = [];
  let respChangeCount = 0;
  if (s1.team_responsibilities !== s2.team_responsibilities) {
    respChangeCount++;
    respDiffs.push({
      entity_type: 'team_ownership',
      entity_id: 'resp-team-primary',
      entity_name: 'Primary Handover Lead & Continuity Contacts',
      change_type: 'MODIFIED',
      old_assignee: s1.team_responsibilities || 'Outgoing Lead',
      new_assignee: s2.team_responsibilities || 'Incoming Successor',
      details: 'Handover owner and continuity contact updated in revision.',
    });
  }

  const hasDifferences =
    modCount > 0 ||
    addedCount > 0 ||
    removedCount > 0 ||
    taskDiffs.some((t) => t.change_type !== 'UNCHANGED') ||
    respChangeCount > 0;

  return {
    from_version_id: fromVer.id,
    from_version_number: fromVer.version_number,
    to_version_id: toVer.id,
    to_version_number: toVer.version_number,
    summary: {
      total_sections_compared: sectionKeys.length,
      added_sections_count: addedCount,
      removed_sections_count: removedCount,
      modified_sections_count: modCount,
      unchanged_sections_count: unchCount,
      total_tasks_compared: taskDiffs.length,
      added_tasks_count: addedTasks,
      removed_tasks_count: removedTasks,
      task_status_changes_count: taskStatusChanges,
      responsibility_changes_count: respChangeCount,
      has_differences: hasDifferences,
      category_status: {
        architecture: modCount > 0 ? 'modified' : 'unchanged',
        tasks: taskStatusChanges > 0 ? 'shifted' : 'consistent',
        compliance: 'verified',
      },
    },
    section_diffs: sectionDiffs,
    task_diffs: taskDiffs,
    responsibility_diffs: respDiffs,
  };
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

  // =========================================================================
  // VERSION MANAGEMENT & COMPARISON ENGINE APIS
  // =========================================================================

  /**
   * List all historical version records for a handover
   */
  async listVersions(handoverId: string): Promise<ApiResponse<HandoverVersionItem[]>> {
    if (!isUuid(handoverId)) {
      return apiClient.executeMock(() => getStoredMockVersions(handoverId));
    }
    try {
      return await apiClient.get<HandoverVersionItem[]>(`/handovers/${handoverId}/versions`);
    } catch (err) {
      console.warn(`[handoverService] Falling back to local version store for ${handoverId}:`, err);
      return apiClient.executeMock(() => getStoredMockVersions(handoverId));
    }
  }

  /**
   * Get latest active version snapshot
   */
  async getLatestVersion(handoverId: string): Promise<ApiResponse<HandoverVersionItem>> {
    if (!isUuid(handoverId)) {
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const latest = versions.find((v) => v.is_latest) || versions[0];
        if (!latest) throw new Error('No versions found');
        return latest;
      });
    }
    try {
      return await apiClient.get<HandoverVersionItem>(`/handovers/${handoverId}/versions/latest`);
    } catch (err) {
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const latest = versions.find((v) => v.is_latest) || versions[0];
        if (!latest) throw new Error('No versions found');
        return latest;
      });
    }
  }

  /**
   * Get specific version snapshot by ID
   */
  async getVersion(handoverId: string, versionId: string): Promise<ApiResponse<HandoverVersionItem>> {
    if (!isUuid(handoverId)) {
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const found = versions.find((v) => v.id === versionId);
        if (!found) throw new Error(`Version ${versionId} not found`);
        return found;
      });
    }
    try {
      return await apiClient.get<HandoverVersionItem>(`/handovers/${handoverId}/versions/${versionId}`);
    } catch (err) {
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const found = versions.find((v) => v.id === versionId);
        if (!found) throw new Error(`Version ${versionId} not found`);
        return found;
      });
    }
  }

  /**
   * Create a new revision snapshot manually
   */
  async createVersion(handoverId: string, description?: string): Promise<ApiResponse<HandoverVersionItem>> {
    if (!isUuid(handoverId)) {
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const nextNum = `v1.${versions.length}`;
        const newVer: HandoverVersionItem = {
          id: `ver-${Date.now()}`,
          handover_id: handoverId,
          version_number: nextNum,
          version_description: description || `Revision snapshot created manually (${nextNum}).`,
          approval_status: 'IN_REVIEW',
          parent_version_id: versions.length > 0 ? versions[0].id : null,
          is_latest: true,
          created_by: 'usr-current',
          creator_name: 'Current User',
          created_at: new Date().toISOString(),
          snapshot: {
            title: `Handover Revision ${nextNum}`,
            version: nextNum,
            approval_status: 'IN_REVIEW',
            project_overview: 'Updated handover snapshot with latest verification notes and task shifts.',
            technical_architecture: 'Active architecture baseline snapshot.',
            key_decisions: '1. Up-to-date architectural decisions.',
            pending_tasks: [
              { title: 'Rehearsal execution in staging', status: 'pending', assigned_to_name: 'Current User' },
            ],
            risks_and_blockers: 'None identified.',
            dependencies: 'Production Vault credentials',
            team_responsibilities: 'Continuity team',
            recommendations: 'Proceed with migration.',
          },
        };
        versions.forEach((v) => {
          v.is_latest = false;
        });
        versions.unshift(newVer);
        saveStoredMockVersions(handoverId, versions);
        return newVer;
      });
    }
    try {
      return await apiClient.post<HandoverVersionItem>(`/handovers/${handoverId}/versions`, {
        version_description: description,
      });
    } catch (err) {
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const nextNum = `v1.${versions.length}`;
        const newVer: HandoverVersionItem = {
          id: `ver-${Date.now()}`,
          handover_id: handoverId,
          version_number: nextNum,
          version_description: description || `Revision snapshot (${nextNum}).`,
          approval_status: 'IN_REVIEW',
          parent_version_id: versions.length > 0 ? versions[0].id : null,
          is_latest: true,
          created_by: 'usr-current',
          creator_name: 'Current User',
          created_at: new Date().toISOString(),
          snapshot: {
            title: `Handover Revision ${nextNum}`,
            version: nextNum,
            approval_status: 'IN_REVIEW',
            project_overview: 'Updated snapshot baseline.',
            technical_architecture: 'Standard architecture.',
            key_decisions: 'Decisions baseline.',
            pending_tasks: [],
            risks_and_blockers: 'None',
            dependencies: 'None',
            team_responsibilities: 'Lead',
            recommendations: 'None',
          },
        };
        versions.forEach((v) => {
          v.is_latest = false;
        });
        versions.unshift(newVer);
        saveStoredMockVersions(handoverId, versions);
        return newVer;
      });
    }
  }

  /**
   * Restore an earlier version snapshot (creates a new revision without deleting historical data)
   */
  async restoreVersion(handoverId: string, versionId: string, reason?: string): Promise<ApiResponse<any>> {
    if (!isUuid(handoverId)) {
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const target = versions.find((v) => v.id === versionId);
        if (!target) throw new Error(`Target version ${versionId} not found`);

        const nextNum = `v1.${versions.length}`;
        const restored: HandoverVersionItem = {
          id: `ver-${Date.now()}`,
          handover_id: handoverId,
          version_number: nextNum,
          version_description: reason
            ? `Restored baseline from ${target.version_number}: ${reason}`
            : `Restored baseline from ${target.version_number}. Previous versions remain permanently preserved.`,
          approval_status: 'IN_REVIEW',
          parent_version_id: target.id,
          is_latest: true,
          created_by: 'usr-current',
          creator_name: 'Current User (Restored)',
          created_at: new Date().toISOString(),
          snapshot: {
            ...target.snapshot,
            version: nextNum,
            approval_status: 'IN_REVIEW',
          },
        };

        // Important: Never delete historical approved versions!
        versions.forEach((v) => {
          v.is_latest = false;
        });
        versions.unshift(restored);
        saveStoredMockVersions(handoverId, versions);

        return {
          message: `Successfully restored version ${target.version_number} as new revision ${nextNum}`,
          restored_version: restored,
        };
      });
    }
    try {
      return await apiClient.post<any>(`/handovers/${handoverId}/versions/${versionId}/restore`, {
        reason,
      });
    } catch (err) {
      console.warn(`[handoverService] Falling back to local restore for ${handoverId}:`, err);
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const target = versions.find((v) => v.id === versionId);
        if (!target) throw new Error(`Target version ${versionId} not found`);

        const nextNum = `v1.${versions.length}`;
        const restored: HandoverVersionItem = {
          id: `ver-${Date.now()}`,
          handover_id: handoverId,
          version_number: nextNum,
          version_description: reason
            ? `Restored baseline from ${target.version_number}: ${reason}`
            : `Restored baseline from ${target.version_number}. Previous versions remain permanently preserved.`,
          approval_status: 'IN_REVIEW',
          parent_version_id: target.id,
          is_latest: true,
          created_by: 'usr-current',
          creator_name: 'Current User (Restored)',
          created_at: new Date().toISOString(),
          snapshot: {
            ...target.snapshot,
            version: nextNum,
            approval_status: 'IN_REVIEW',
          },
        };
        versions.forEach((v) => {
          v.is_latest = false;
        });
        versions.unshift(restored);
        saveStoredMockVersions(handoverId, versions);

        return {
          message: `Successfully restored version ${target.version_number} as new revision ${nextNum}`,
          restored_version: restored,
        };
      });
    }
  }

  /**
   * Compare two handover versions via path parameters
   */
  async compareVersions(
    handoverId: string,
    fromVersionId: string,
    toVersionId: string
  ): Promise<ApiResponse<VersionDiffResponse>> {
    if (!isUuid(handoverId)) {
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const v1 = versions.find((v) => v.id === fromVersionId) || versions[0];
        const v2 = versions.find((v) => v.id === toVersionId) || versions[versions.length - 1] || v1;
        return generateMockDiff(v1, v2);
      });
    }
    try {
      return await apiClient.get<VersionDiffResponse>(
        `/handovers/${handoverId}/versions/${fromVersionId}/compare/${toVersionId}`
      );
    } catch (err) {
      console.warn(`[handoverService] Falling back to local compare for ${handoverId}:`, err);
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const v1 = versions.find((v) => v.id === fromVersionId) || versions[0];
        const v2 = versions.find((v) => v.id === toVersionId) || versions[versions.length - 1] || v1;
        return generateMockDiff(v1, v2);
      });
    }
  }

  /**
   * Compare two handover versions via query parameters
   */
  async compareVersionsByQuery(
    handoverId: string,
    fromVersion: string,
    toVersion: string
  ): Promise<ApiResponse<VersionDiffResponse>> {
    if (!isUuid(handoverId)) {
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const v1 = versions.find((v) => v.version_number === fromVersion) || versions[0];
        const v2 = versions.find((v) => v.version_number === toVersion) || versions[versions.length - 1] || v1;
        return generateMockDiff(v1, v2);
      });
    }
    try {
      return await apiClient.get<VersionDiffResponse>(
        `/handovers/${handoverId}/compare?from_version=${encodeURIComponent(fromVersion)}&to_version=${encodeURIComponent(toVersion)}`
      );
    } catch (err) {
      return apiClient.executeMock(() => {
        const versions = getStoredMockVersions(handoverId);
        const v1 = versions.find((v) => v.version_number === fromVersion) || versions[0];
        const v2 = versions.find((v) => v.version_number === toVersion) || versions[versions.length - 1] || v1;
        return generateMockDiff(v1, v2);
      });
    }
  }

  /**
   * Incoming-member continuity APIs
   */
  async getSharedWithMe(): Promise<ApiResponse<SharedHandoverItem[]>> {
    try {
      const res = await apiClient.get<SharedHandoverItem[]>('/handovers/shared-with-me');
      if (res && res.data && Array.isArray(res.data) && res.data.length > 0) {
        return res;
      }
    } catch (err) {
      console.warn('[handoverService] Falling back to local shared handovers:', err);
    }

    return apiClient.executeMock(async () => {
      const pkgs = await incomingService.getMyIncomingHandovers();
      return pkgs.map((p) => ({
        id: p.handoverId || p.id,
        project_id: p.projectId,
        project_title: p.projectName,
        title: p.projectName,
        version: p.version,
        status: 'APPROVED',
        transition_status:
          p.acknowledgementStatus === 'acknowledged'
            ? p.responsibilities.some((r) => r.status === 'completed')
              ? 'In Progress'
              : 'Acknowledged'
            : 'Awaiting Acknowledgement',
        approved_at: p.approvedDate,
        shared_at: p.approvedDate,
        acknowledged_at: p.acknowledgedAt || null,
        acknowledged_by: p.incomingMember?.id || null,
        acknowledged_by_name: p.incomingMember?.name || null,
        assigned_to: p.incomingMember?.id || null,
        assigned_to_name: p.incomingMember?.name || null,
        pending_tasks_count: p.responsibilities.filter((t) => t.status !== 'completed').length,
        overdue_tasks_count: 0,
      }));
    });
  }

  async getContinuity(handoverId: string): Promise<ApiResponse<HandoverContinuityData>> {
    if (isUuid(handoverId)) {
      try {
        const res = await apiClient.get<HandoverContinuityData>(`/handovers/${handoverId}/continuity`);
        if (res && res.data) {
          return res;
        }
      } catch (err) {
        console.warn(`[handoverService] Falling back to local continuity for ${handoverId}:`, err);
      }
    }

    return apiClient.executeMock(async () => {
      const pkgs = await incomingService.getMyIncomingHandovers();
      const pkg =
        pkgs.find((p) => p.id === handoverId || p.handoverId === handoverId) ||
        (await incomingService.getIncomingHandoverById(handoverId)) ||
        pkgs[0];

      if (!pkg) throw new Error('Handover continuity record not found');

      const isAck = pkg.acknowledgementStatus === 'acknowledged';
      const allTasks = pkg.responsibilities.map((r) => ({
        id: r.id,
        title: r.title,
        description: r.description,
        status: r.status,
        priority: r.priority,
        assigned_to: r.assignedTo?.id || 'usr-elena-rostova',
        assigned_to_name: r.assignedTo?.name || 'Elena Rostova',
        due_date: r.dueDate,
        is_blocked: r.status === 'blocked',
        dependencies_count: r.dependencies?.length || 0,
        progress_notes: r.progressNotes || [],
      }));

      const pendingTasks = allTasks.filter(
        (t) => t.status === 'pending' || t.status === 'not_started'
      );
      const inProgressTasks = allTasks.filter((t) => t.status === 'in_progress');
      const completedTasks = allTasks.filter((t) => t.status === 'completed');
      const blockedTasks = allTasks.filter((t) => t.status === 'blocked');
      const overdueTasks = allTasks.filter((t) => {
        if (!t.due_date || t.status === 'completed') return false;
        return new Date(t.due_date).getTime() < Date.now();
      });

      const total = allTasks.length;
      const completed = completedTasks.length;

      // Unresolved blockers
      const unresolvedBlockers = (pkg.blockers || []).map((b) => ({
        id: b.id,
        description: b.description,
        impact: b.impact,
        severity: b.severity,
        follow_up: b.suggestedFollowUp,
        evidence: b.supportingEvidence,
      }));

      // Unresolved conflicts
      const unresolvedConflicts = [
        {
          id: 'conf-auth-failover',
          project_id: pkg.projectId,
          section_id: pkg.handoverId,
          conflict_type: 'architectural_discrepancy',
          severity: 'high',
          description:
            'Terraform main.tf enables automatic RDS failover (auto_failover=true) while Runbook Section 4.2 specifies manual switchover via AWS console.',
          status: 'UNRESOLVED',
          source_a: 'Terraform PR #612 (main.tf:L48)',
          source_b: 'Production Runbook v2.4 (Appendix B)',
          resolution: null,
        },
      ];

      // Recent progress updates
      const recentUpdates: TaskProgressUpdateItem[] = [];
      pkg.responsibilities.forEach((t) => {
        (t.progressNotes || []).forEach((n) => {
          recentUpdates.push({
            id: n.id,
            task_id: t.id,
            task_title: t.title,
            user_id: 'usr-elena-rostova',
            user_name: n.author,
            update_text: n.text,
            status_before: 'pending',
            status_after: t.status,
            created_at: n.createdAt,
          });
        });
      });
      recentUpdates.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      // Dependencies
      const dependencies = (pkg.dependencies || []).map((d) => ({
        id: d.id,
        dependency: d.dependency,
        related_task: d.prerequisiteTask,
        required_resource: d.requiredPersonOrResource,
        current_status: d.currentStatus,
      }));

      const continuityData: HandoverContinuityData = {
        handover_id: pkg.handoverId || pkg.id,
        project_id: pkg.projectId,
        project_title: pkg.projectName,
        title: pkg.projectName,
        version: pkg.version,
        status: 'APPROVED',
        transition_status: isAck
          ? completedTasks.length > 0
            ? 'In Progress'
            : 'Acknowledged'
          : 'Awaiting Acknowledgement',
        approved_at: pkg.approvedDate,
        shared_at: pkg.approvedDate,
        acknowledged_at: pkg.acknowledgedAt || null,
        acknowledged_by: pkg.incomingMember?.id || null,
        acknowledged_by_name: pkg.incomingMember?.name || null,
        acknowledgement_notes: pkg.acknowledgementComment || null,
        checklist_confirmed: isAck,
        assigned_to: pkg.incomingMember?.id || null,
        assigned_to_name: pkg.incomingMember?.name || null,
        tasks_summary: {
          total_tasks: total,
          pending_tasks: pendingTasks.length,
          in_progress_tasks: inProgressTasks.length,
          completed_tasks: completedTasks.length,
          blocked_tasks: blockedTasks.length,
          overdue_tasks: overdueTasks.length,
          completion_percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
        },
        pending_tasks: pendingTasks,
        in_progress_tasks: inProgressTasks,
        completed_tasks: completedTasks,
        blocked_tasks: blockedTasks,
        overdue_tasks: overdueTasks,
        all_tasks: allTasks,
        unresolved_blockers: unresolvedBlockers,
        unresolved_conflicts: unresolvedConflicts,
        responsibilities: [
          {
            user_id: 'usr-elena-rostova',
            user_name: 'Elena Rostova (Incoming Successor)',
            total_tasks: total,
            completed_tasks: completed,
            pending_tasks: total - completed,
          },
        ],
        recent_progress_updates: recentUpdates,
      };

      return {
        ...continuityData,
        dependencies,
      } as any;
    });
  }

  async acknowledgeHandover(
    handoverId: string,
    checklistConfirmed: boolean = true,
    notes?: string
  ): Promise<ApiResponse<any>> {
    if (isUuid(handoverId)) {
      try {
        return await apiClient.post<any>(`/handovers/${handoverId}/acknowledge`, {
          checklist_confirmed: checklistConfirmed,
          notes,
        });
      } catch (err) {
        console.warn(`[handoverService] Falling back to local acknowledge for ${handoverId}:`, err);
      }
    }

    return apiClient.executeMock(async () => {
      const updatedPkg = await incomingService.acknowledgeHandover(
        handoverId,
        mockCurrentUser,
        notes
      );
      return {
        message: 'Handover receipt acknowledged successfully.',
        acknowledged_at: updatedPkg.acknowledgedAt,
        transition_status: 'Acknowledged',
        package: updatedPkg,
      };
    });
  }

  async updateTransitionStatus(
    handoverId: string,
    transitionStatus: string,
    notes?: string
  ): Promise<ApiResponse<any>> {
    if (isUuid(handoverId)) {
      try {
        return await apiClient.patch<any>(`/handovers/${handoverId}/transition-status`, {
          transition_status: transitionStatus,
          notes,
        });
      } catch (err) {
        console.warn(`[handoverService] Falling back to local transition-status for ${handoverId}:`, err);
      }
    }

    return apiClient.executeMock(() => ({
      handover_id: handoverId,
      transition_status: transitionStatus,
      notes,
    }));
  }

  async updateTaskStatus(
    taskId: string,
    status: string,
    notes?: string
  ): Promise<ApiResponse<any>> {
    if (isUuid(taskId)) {
      try {
        return await apiClient.patch<any>(`/tasks/${taskId}/status`, {
          status,
          notes,
        });
      } catch (err) {
        console.warn(`[handoverService] Falling back to local updateTaskStatus for ${taskId}:`, err);
      }
    }

    return apiClient.executeMock(async () => {
      const pkgs = await incomingService.getMyIncomingHandovers();
      for (const p of pkgs) {
        const t = p.responsibilities.find((x) => x.id === taskId);
        if (t) {
          await incomingService.updateTaskStatus(p.id, taskId, status as any);
          if (notes) {
            await incomingService.addTaskProgressNote(p.id, taskId, notes, mockCurrentUser.name);
          }
          break;
        }
      }
      return {
        task_id: taskId,
        status,
        message: `Task status updated to ${status}.`,
      };
    });
  }

  async addTaskProgress(
    taskId: string,
    updateText: string,
    newStatus?: string
  ): Promise<ApiResponse<any>> {
    if (isUuid(taskId)) {
      try {
        return await apiClient.post<any>(`/tasks/${taskId}/progress`, {
          update_text: updateText,
          new_status: newStatus,
        });
      } catch (err) {
        console.warn(`[handoverService] Falling back to local addTaskProgress for ${taskId}:`, err);
      }
    }

    return apiClient.executeMock(async () => {
      const pkgs = await incomingService.getMyIncomingHandovers();
      for (const p of pkgs) {
        const t = p.responsibilities.find((x) => x.id === taskId);
        if (t) {
          await incomingService.addTaskProgressNote(p.id, taskId, updateText, mockCurrentUser.name);
          if (newStatus) {
            await incomingService.updateTaskStatus(p.id, taskId, newStatus as any);
          }
          break;
        }
      }
      return {
        task_id: taskId,
        update_text: updateText,
        new_status: newStatus,
        created_at: new Date().toISOString(),
      };
    });
  }

  async getTaskProgress(taskId: string): Promise<ApiResponse<any[]>> {
    if (isUuid(taskId)) {
      try {
        return await apiClient.get<any[]>(`/tasks/${taskId}/progress`);
      } catch (err) {
        console.warn(`[handoverService] Falling back to local getTaskProgress for ${taskId}:`, err);
      }
    }

    return apiClient.executeMock(async () => {
      const pkgs = await incomingService.getMyIncomingHandovers();
      for (const p of pkgs) {
        const t = p.responsibilities.find((x) => x.id === taskId);
        if (t) {
          return (t.progressNotes || []).map((n) => ({
            id: n.id,
            task_id: taskId,
            task_title: t.title,
            user_id: 'usr-elena-rostova',
            user_name: n.author,
            update_text: n.text,
            created_at: n.createdAt,
          }));
        }
      }
      return [];
    });
  }
}

export const handoverService = new HandoverService();

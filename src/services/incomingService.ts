import {
  IncomingHandoverPackage,
  ContinuationTaskItem,
  AcknowledgementStatus,
} from '../types/incoming';
import { User } from '../types/common';
import { mockUsers, mockCurrentUser } from '../data/mockData';

const STORAGE_KEY = 'kh_incoming_handovers_v1';

const sarahJenkins: User = mockUsers[2];
const elenaRostova: User = mockUsers[0];
const davidChen: User = mockUsers[1];
const marcusVance: User = mockUsers[3];
const alexChen: User = mockUsers[4];

const initialPackages: IncomingHandoverPackage[] = [
  {
    id: 'inc-auth-zero',
    handoverId: 'rev-auth-zero',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    version: 'v1.0',
    approvedDate: '2026-11-09T16:00:00Z',
    approvedBy: marcusVance,
    outgoingMember: sarahJenkins,
    projectLead: marcusVance,
    incomingMember: elenaRostova,
    acknowledgementStatus: 'pending',
    isSanitized: true,

    // A. Project Introduction
    introduction: {
      purpose:
        'Migrate 1.4 million active enterprise and consumer user sessions to passwordless WebAuthn/FIDO2 passkeys, eliminating phishing vulnerabilities and deprecating legacy SMS 2FA.',
      objectives: [
        'Deploy standard WebAuthn Level 3 platform biometrics (Touch ID, Face ID, Windows Hello) across mobile and web.',
        'Execute zero-downtime PostgreSQL 16 partition split cutover during Nov 20 maintenance window.',
        'Achieve sub-80ms auth token latency with Redis regional replication in eu-west-1 and eu-central-1.',
        'Complete SOC-2 and NIST 800-63B AAL3 compliance verification.',
      ],
      currentStage: 'Staging Verification & Pre-Cutover Shadow Sync',
      overallStatus: 'On Track (Green) · 94% Readiness Score',
      healthScore: 94,
      lastUpdated: '2026-11-09T15:45:00Z',
    },

    // B. Important Decisions
    decisions: [
      {
        id: 'dec-1',
        decision: 'Platform Authenticator Biometrics Default with FIDO2 Hardware Fallback',
        date: '2026-10-14',
        rationale:
          'Significantly lowers user enrollment friction while fulfilling strict NIST 800-63B AAL3 requirements.',
        supportingSource: 'Architecture_Decision_Record_v2.pdf (Page 4 · §1.2)',
        sourceSnippet:
          'Authenticator attachment defaults to platform biometrics with security key fallback.',
      },
      {
        id: 'dec-2',
        decision: 'Database Migration Cutover Scheduled for 20 November',
        date: '2026-10-29',
        rationale:
          'Sprint triage consensus extended date by 5 business days to validate schema compatibility with downstream analytics pipelines.',
        supportingSource: 'Sprint_Review_Q4_Summary.docx (Page 3 · §1.4)',
        sourceSnippet:
          'Database migration deadline: 20 November. Extended by 5 business days to allow schema validation.',
      },
      {
        id: 'dec-3',
        decision: 'Active-Active DR Locality Enforced Across EU Regions',
        date: '2026-10-04',
        rationale:
          'EU data residency compliance strictly prohibits storing unhashed session metadata outside EEA territory.',
        supportingSource: 'Cloud_Security_Compliance_2026.pdf (Page 22)',
        sourceSnippet:
          'All customer authentication metadata and session tokens must run in active-active topology between eu-west-1 and eu-central-1.',
      },
    ],

    // C. Your Responsibilities (Continuation Tasks)
    responsibilities: [
      {
        id: 'tsk-101',
        title: 'Conduct Final PostgreSQL 16 Partition Rehearsal in Staging',
        description:
          'Verify that session table partition boundary splits perform under simulated 25k RPS write load without query latency spikes exceeding 15ms.',
        status: 'pending',
        priority: 'critical',
        assignedTo: elenaRostova,
        dependencies: ['DB Staging Bastion Access', 'Grafana DB Connection Pool Dashboard'],
        dueDate: '2026-11-13',
        progressNotes: [
          {
            id: 'n-1',
            text: 'Sarah provided the staging pg_bench scripts located in /infra/scripts/bench-partition.sh.',
            author: 'Sarah Jenkins',
            createdAt: '2026-11-09T16:10:00Z',
          },
        ],
      },
      {
        id: 'tsk-102',
        title: 'Rotate AWS KMS Master Key Alias for Challenge Nonce Signing',
        description:
          'Execute KMS alias switch in accordance with PCI/SOC-2 key lifecycle policy. Verify Go crypto handler decrypts existing challenge tokens without restarts.',
        status: 'in_progress',
        priority: 'critical',
        assignedTo: elenaRostova,
        dependencies: ['AWS IAM Role: AuthZeroKeyManager', 'Terraform PR #412 merged'],
        dueDate: '2026-11-15',
        progressNotes: [
          {
            id: 'n-2',
            text: 'Staging key rotated cleanly; validated 500 consecutive authentication requests with zero signature errors.',
            author: 'Elena Rostova',
            createdAt: '2026-11-09T18:30:00Z',
          },
        ],
      },
      {
        id: 'tsk-103',
        title: 'Verify Redis Multi-Cluster Circuit Breaker Sentinel Fallback',
        description:
          'Simulate cluster node eviction and ensure direct PostgreSQL query fallback trips within 120ms without throwing HTTP 500 errors to mobile clients.',
        status: 'pending',
        priority: 'high',
        assignedTo: elenaRostova,
        dependencies: ['ElastiCache Redis Staging Cluster'],
        dueDate: '2026-11-16',
        progressNotes: [],
      },
      {
        id: 'tsk-104',
        title: 'Assume Tier-1 On-Call Rotation Escalation Roster in PagerDuty',
        description:
          'Rotate secondary on-call ownership from Sarah Jenkins to Elena Rostova in PagerDuty policy "Identity-Tier1-P0".',
        status: 'pending',
        priority: 'high',
        assignedTo: elenaRostova,
        dependencies: ['PagerDuty Admin Schedule Access'],
        dueDate: '2026-11-18',
        progressNotes: [],
      },
    ],

    // D. Current Blockers
    blockers: [
      {
        id: 'blk-1',
        description: 'Pending EU Data Residency Governance Sign-Off Memo',
        impact:
          'Frankfurt (eu-central-1) standby read-replicas cannot receive production user records until Legal Ops returns the signed DPA addendum.',
        severity: 'high',
        suggestedFollowUp:
          'Ping Legal Director in #security-governance Slack; Marcus Vance escalated in Monday executive sync.',
        supportingEvidence: 'Cloud_Security_Compliance_2026.pdf (Page 22)',
      },
    ],

    // E. Project Dependencies
    dependencies: [
      {
        id: 'dep-1',
        dependency: 'AWS KMS Key Alias for Asymmetric Challenge Signing',
        prerequisiteTask: 'Rotate AWS KMS Master Key Alias (tsk-102)',
        requiredPersonOrResource: 'Cloud Platform Team (Key ARN: arn:aws:kms:eu-west-1:auth-zero)',
        currentStatus: 'Operational',
      },
      {
        id: 'dep-2',
        dependency: 'Datadog Passkey SLO Dashboard Access',
        prerequisiteTask: 'On-Call Handoff (tsk-104)',
        requiredPersonOrResource: 'DevOps Platform (Dashboard #datadog-auth-zero-slo)',
        currentStatus: 'Access Granted for Verification',
      },
      {
        id: 'dep-3',
        dependency: 'PostgreSQL 16 Read Replica Replication Lag < 20ms',
        prerequisiteTask: 'Database Cutover Rehearsal (tsk-101)',
        requiredPersonOrResource: 'Database Reliability Engineering (DBA Team on call)',
        currentStatus: 'Healthy (Lag: 4ms)',
      },
    ],

    // F. Recommended Starting Actions
    recommendedStartingActions: [
      {
        id: 'act-1',
        action: 'Review WebAuthn Handler in /src/auth/passkey.go and verify WebAuthn Level 3 assertions',
        timeframe: 'Day 1',
        priority: 'high',
        reason: 'Provides foundational understanding of the platform biometric challenge flow.',
      },
      {
        id: 'act-2',
        action: 'Execute simulated Redis failover in staging environment using Makefile task `make test-circuit-breaker`',
        timeframe: 'Day 2-3',
        priority: 'high',
        reason: 'Confirms fallback circuit breaker thresholds and prevents midnight panic during incidents.',
      },
      {
        id: 'act-3',
        action: 'Schedule 30-minute sync with David Chen regarding analytics downstream schema consumers',
        timeframe: 'Day 2-3',
        priority: 'medium',
        reason: 'Validates that the Nov 20 cutover window does not disrupt night batch reporting.',
      },
      {
        id: 'act-4',
        action: 'Participate as secondary shadow on PagerDuty alert triage rotation',
        timeframe: 'Week 1',
        priority: 'high',
        reason: 'Builds muscle memory on runbooks before Sarah Jenkins concludes transition period.',
      },
    ],

    // G. Open Questions
    openQuestions: [
      {
        id: 'oq-1',
        question: 'Should biometric passkey credentials sync across user iCloud / Google accounts?',
        whyItMatters:
          'Enterprise tenants in regulated finance may mandate non-exportable hardware security keys (YubiKey) rather than synced cloud passkeys.',
        whoNeedsToConfirm: 'Marcus Vance (Project Lead) & Enterprise CISO',
        status: 'unresolved',
      },
      {
        id: 'oq-2',
        question: 'What is the retry backoff duration when Redis memory reaches 92% direct fallback threshold?',
        whyItMatters:
          'Prolonged fallback direct query load can cause connection exhaustion on the primary PostgreSQL RDS cluster.',
        whoNeedsToConfirm: 'Database Reliability Team & Sarah Jenkins',
        status: 'unresolved',
      },
    ],
  },
  {
    id: 'inc-fraud-shield',
    handoverId: 'rev-fraud-shield',
    projectId: 'proj-3',
    projectKey: 'FRAUD-SHIELD',
    projectName: 'Real-Time Fraud Prevention & Graph Neural Network',
    version: 'v1.0',
    approvedDate: '2026-11-05T16:30:00Z',
    approvedBy: sarahJenkins,
    outgoingMember: alexChen,
    projectLead: sarahJenkins,
    incomingMember: elenaRostova,
    acknowledgementStatus: 'acknowledged',
    acknowledgedAt: '2026-11-06T09:15:00Z',
    acknowledgementComment:
      'Receipt acknowledged. Completed initial model weights verification on PyTorch inference pods.',
    isSanitized: true,

    introduction: {
      purpose:
        'Sub-50ms inference fraud detection pipeline utilizing Neo4j graph cluster and PyTorch GNN models to flag anomalous transaction clusters.',
      objectives: [
        'Maintain <45ms 99th percentile inference latency under 12k RPS.',
        'Continuous streaming graph feature extraction from Kafka transaction topic.',
        'Zero false positive escalations on verified VIP merchant transactions.',
      ],
      currentStage: 'Production Active Monitoring',
      overallStatus: 'Healthy & Certified · 99% Readiness Score',
      healthScore: 99,
      lastUpdated: '2026-11-06T09:15:00Z',
    },

    decisions: [
      {
        id: 'dec-201',
        decision: 'Triton Inference Server Deployment over Custom Flask Wrapper',
        date: '2026-09-12',
        rationale: 'Delivers dynamic model batching and 3.2x higher throughput with GPU utilization optimization.',
        supportingSource: 'Fraud_Model_Serving_Architecture.pdf (Page 8)',
      },
    ],

    responsibilities: [
      {
        id: 'tsk-201',
        title: 'Weekly Neo4j Graph Index Compaction Routine',
        description: 'Verify automated Sunday 03:00 UTC index compaction vacuum executes cleanly.',
        status: 'completed',
        priority: 'high',
        assignedTo: elenaRostova,
        dependencies: ['Neo4j Enterprise Admin Console'],
        dueDate: '2026-11-08',
        completedAt: '2026-11-08T03:30:00Z',
        progressNotes: [
          {
            id: 'n-201',
            text: 'Executed compaction; reclaimed 48GB disk space with zero latency regression.',
            author: 'Elena Rostova',
            createdAt: '2026-11-08T03:32:00Z',
          },
        ],
      },
      {
        id: 'tsk-202',
        title: 'Audit GNN Drift Detection Daily Slack Alerts',
        description: 'Inspect daily distribution drift metric and verify cosine divergence remains below 0.05.',
        status: 'in_progress',
        priority: 'medium',
        assignedTo: elenaRostova,
        dependencies: ['#fraud-model-alerts Slack Channel'],
        dueDate: '2026-11-15',
        progressNotes: [],
      },
    ],

    blockers: [],
    dependencies: [
      {
        id: 'dep-201',
        dependency: 'Neo4j Enterprise Cluster Read Replicas',
        prerequisiteTask: 'Graph Index Compaction (tsk-201)',
        requiredPersonOrResource: 'Graph Infra SRE',
        currentStatus: 'Healthy',
      },
    ],
    recommendedStartingActions: [
      {
        id: 'act-201',
        action: 'Review PyTorch inference pipeline in /services/fraud-gnn/serve.py',
        timeframe: 'Day 1',
        priority: 'high',
        reason: 'Core inference entrypoint for all incoming payment evaluations.',
      },
    ],
    openQuestions: [],
  },
  {
    id: 'inc-observability',
    handoverId: 'rev-telemetry',
    projectId: 'proj-5',
    projectKey: 'OBSERVABILITY',
    projectName: 'Telemetry Ingestion & Distributed Tracing Pipeline',
    version: 'v1.0',
    approvedDate: '2026-11-08T11:00:00Z',
    approvedBy: marcusVance,
    outgoingMember: davidChen,
    projectLead: marcusVance,
    incomingMember: elenaRostova,
    acknowledgementStatus: 'pending',
    isSanitized: true,

    introduction: {
      purpose:
        'Unified OpenTelemetry collector daemon and distributed Jaeger tracing mesh spanning 42 backend microservices.',
      objectives: [
        'Collect 100% of P0 error traces and 5% sampled standard HTTP traffic.',
        'Enforce tenant privacy scrubbing for PII and credit card numbers at collector boundary.',
      ],
      currentStage: 'Collector v2.4 Rollout in Kubernetes',
      overallStatus: 'Awaiting Successor Receipt · 90% Readiness',
      healthScore: 90,
      lastUpdated: '2026-11-08T11:00:00Z',
    },

    decisions: [
      {
        id: 'dec-301',
        decision: 'Tail-Based Sampling on Jaeger Collector Agents',
        date: '2026-10-02',
        rationale: 'Prevents trace saturation while ensuring 100% of error traces are retained for 30 days.',
        supportingSource: 'Tracing_Infrastructure_RFC.docx (Page 6)',
      },
    ],

    responsibilities: [
      {
        id: 'tsk-301',
        title: 'Inspect OTel DaemonSet Memory Threshold Limits in EKS',
        description: 'Ensure collector memory limit of 512MiB is sufficient under peak 40k RPS telemetry spikes.',
        status: 'pending',
        priority: 'high',
        assignedTo: elenaRostova,
        dependencies: ['Kubernetes Cluster Admin Context'],
        dueDate: '2026-11-14',
        progressNotes: [],
      },
    ],

    blockers: [],
    dependencies: [],
    recommendedStartingActions: [
      {
        id: 'act-301',
        action: 'Inspect OpenTelemetry collector configmap in k8s/otel-collector-config.yaml',
        timeframe: 'Day 1',
        priority: 'high',
        reason: 'Contains tenant privacy regex rules for scrubbing customer identifiers.',
      },
    ],
    openQuestions: [],
  },
];

class IncomingService {
  private getStore(): IncomingHandoverPackage[] {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(initialPackages));
      return initialPackages;
    }
    try {
      return JSON.parse(raw);
    } catch {
      return initialPackages;
    }
  }

  private saveStore(packages: IncomingHandoverPackage[]): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(packages));
  }

  async getMyIncomingHandovers(userEmailOrId?: string): Promise<IncomingHandoverPackage[]> {
    await new Promise((r) => setTimeout(r, 100));
    const items = this.getStore();
    // In mock, default to Elena Rostova or matching user
    if (!userEmailOrId) return items;
    return items.filter(
      (p) =>
        p.incomingMember.id === userEmailOrId ||
        p.incomingMember.email === userEmailOrId ||
        p.incomingMember.name.toLowerCase().includes(userEmailOrId.toLowerCase())
    );
  }

  async getIncomingHandoverById(id: string): Promise<IncomingHandoverPackage | null> {
    await new Promise((r) => setTimeout(r, 120));
    const items = this.getStore();
    return items.find((p) => p.id === id || p.handoverId === id) || null;
  }

  async publishApprovedHandover(
    record: any,
    approver: User
  ): Promise<IncomingHandoverPackage> {
    const items = this.getStore();
    const existingIndex = items.findIndex((p) => p.handoverId === record.id || p.id === `inc-${record.id}`);

    // Map decisions
    const decisions = (record.content?.decisions || []).map((d: any, idx: number) => ({
      id: `dec-${idx + 1}`,
      decision: d.decision || d.title,
      date: d.date || '2026-11-01',
      rationale: d.rationale || 'Architectural decision verified under primary evidence criteria.',
      supportingSource: d.supportingSource || 'Architecture Runbook & Spec',
      sourceSnippet: d.sourceSnippet,
    }));

    // Map tasks
    const responsibilities: ContinuationTaskItem[] = (record.content?.tasks || []).map((t: any, idx: number) => ({
      id: `task-${idx + 1}`,
      title: t.task || t.title,
      description: t.description || `Take ownership and execute: ${t.task || t.title}`,
      status: 'pending' as const,
      priority: (t.priority?.toLowerCase() === 'critical' ? 'critical' : t.priority?.toLowerCase() === 'high' ? 'high' : 'medium') as any,
      assignedTo: record.incomingMember || approver,
      dependencies: t.dependencies ? [t.dependencies] : [],
      dueDate: t.due || '2026-11-25',
      progressNotes: [],
    }));

    // Map blockers
    const blockers = (record.content?.blockers || []).map((b: any, idx: number) => ({
      id: `block-${idx + 1}`,
      description: b.blocker || b.description,
      impact: b.impact || 'Service integration blocker',
      severity: (b.severity?.toLowerCase() === 'critical' ? 'critical' : 'high') as any,
      suggestedFollowUp: b.followUp || 'Follow up with Project Lead in next standup.',
    }));

    // Map dependencies
    const dependencies = (record.content?.dependencies || []).map((dep: any, idx: number) => ({
      id: `dep-${idx + 1}`,
      dependency: dep.dependency,
      prerequisiteTask: dep.prerequisiteTask || 'Downstream system integration',
      requiredPersonOrResource: dep.requiredPersonOrResource || 'DevOps Team',
      currentStatus: dep.currentStatus || 'In Progress',
    }));

    const pkg: IncomingHandoverPackage = {
      id: `inc-${record.id}`,
      handoverId: record.id,
      projectId: record.projectId || 'proj-1',
      projectKey: record.projectKey || 'PAY-V2',
      projectName: record.projectName || 'Global Payment Orchestration',
      version: record.version || 'v1.0',
      approvedDate: new Date().toISOString(),
      approvedBy: approver,
      outgoingMember: record.outgoingMember || approver,
      projectLead: approver,
      incomingMember: record.incomingMember || approver,
      acknowledgementStatus: 'pending',
      isSanitized: true,
      introduction: {
        purpose: record.content?.overview?.purpose || 'Mission-critical engineering knowledge transfer.',
        objectives: [
          'Assume full operational ownership of production services and runbooks.',
          'Execute scheduled maintenance windows and continuation tasks with zero downtime.',
          'Maintain verified knowledge evidence trace across codebase repositories.',
        ],
        currentStage: 'Certified for Successor Handover',
        overallStatus: 'On Track (Green) · Certified',
        healthScore: record.readinessScore || 92,
        lastUpdated: new Date().toISOString(),
      },
      decisions: decisions.length > 0 ? decisions : [
        {
          id: 'dec-default',
          decision: 'Production failover architecture approved',
          date: '2026-11-01',
          rationale: 'Primary evidence verified across documentation sources.',
          supportingSource: 'Arch Spec v2.1',
        }
      ],
      responsibilities: responsibilities.length > 0 ? responsibilities : [
        {
          id: `task-${Date.now()}-1`,
          title: `Verify ${record.projectKey || 'PAY-V2'} Staging Ingress Configuration`,
          description: 'Validate health checks and ingress routing in staging namespace.',
          status: 'pending',
          priority: 'high',
          assignedTo: record.incomingMember || approver,
          dependencies: [],
          dueDate: '2026-11-20',
          progressNotes: [],
        }
      ],
      blockers: blockers.length > 0 ? blockers : [],
      dependencies: dependencies.length > 0 ? dependencies : [],
      recommendedStartingActions: [
        {
          id: 'act-1',
          action: 'Schedule 30-minute transition sync with outgoing lead',
          timeframe: 'Day 1',
          priority: 'high',
          reason: 'Review continuation milestones and verify on-call escalation policies.',
        },
        {
          id: 'act-2',
          action: 'Clone repositories and run integration test suites locally',
          timeframe: 'Day 2-3',
          priority: 'high',
          reason: 'Validate local dev container setup and environment variables.',
        },
      ],
      openQuestions: [],
    };

    if (existingIndex >= 0) {
      items[existingIndex] = pkg;
    } else {
      items.unshift(pkg);
    }

    this.saveStore(items);
    return pkg;
  }

  async acknowledgeHandover(
    id: string,
    user: User,
    comment?: string
  ): Promise<IncomingHandoverPackage> {
    await new Promise((r) => setTimeout(r, 180));
    const items = this.getStore();
    const index = items.findIndex((p) => p.id === id || p.handoverId === id);
    if (index === -1) throw new Error('Handover package not found');

    const updated: IncomingHandoverPackage = {
      ...items[index],
      acknowledgementStatus: 'acknowledged',
      acknowledgedAt: new Date().toISOString(),
      acknowledgementComment: comment || 'Handover package reviewed and receipt acknowledged.',
    };

    items[index] = updated;
    this.saveStore(items);

    // Also dispatch activity notification event in localStorage
    const activitiesRaw = localStorage.getItem('kh_activity_feed_v1') || '[]';
    try {
      const activities = JSON.parse(activitiesRaw);
      activities.unshift({
        id: `act-ack-${Date.now()}`,
        type: 'acknowledgement',
        title: `${user.name} Acknowledged Handover`,
        description: `Incoming member acknowledged receipt for ${updated.projectName} (${updated.projectKey}).`,
        timestamp: new Date().toISOString(),
        user: user.name,
        projectKey: updated.projectKey,
      });
      localStorage.setItem('kh_activity_feed_v1', JSON.stringify(activities.slice(0, 30)));
    } catch {
      // Ignore
    }

    return updated;
  }

  async updateTaskStatus(
    packageId: string,
    taskId: string,
    status: 'pending' | 'in_progress' | 'completed'
  ): Promise<IncomingHandoverPackage> {
    await new Promise((r) => setTimeout(r, 150));
    const items = this.getStore();
    const index = items.findIndex((p) => p.id === packageId || p.handoverId === packageId);
    if (index === -1) throw new Error('Handover package not found');

    const pkg = items[index];
    const updatedTasks = pkg.responsibilities.map((t) => {
      if (t.id === taskId) {
        return {
          ...t,
          status,
          completedAt: status === 'completed' ? new Date().toISOString() : undefined,
        };
      }
      return t;
    });

    const updated: IncomingHandoverPackage = {
      ...pkg,
      responsibilities: updatedTasks,
    };

    items[index] = updated;
    this.saveStore(items);
    return updated;
  }

  async addTaskProgressNote(
    packageId: string,
    taskId: string,
    noteText: string,
    author: string
  ): Promise<IncomingHandoverPackage> {
    await new Promise((r) => setTimeout(r, 150));
    const items = this.getStore();
    const index = items.findIndex((p) => p.id === packageId || p.handoverId === packageId);
    if (index === -1) throw new Error('Handover package not found');

    const pkg = items[index];
    const newNote = {
      id: `note-${Date.now()}`,
      text: noteText,
      author,
      createdAt: new Date().toISOString(),
    };

    const updatedTasks = pkg.responsibilities.map((t) => {
      if (t.id === taskId) {
        return {
          ...t,
          progressNotes: [...t.progressNotes, newNote],
        };
      }
      return t;
    });

    const updated: IncomingHandoverPackage = {
      ...pkg,
      responsibilities: updatedTasks,
    };

    items[index] = updated;
    this.saveStore(items);
    return updated;
  }

  async resolveOpenQuestion(
    packageId: string,
    questionId: string,
    response: string
  ): Promise<IncomingHandoverPackage> {
    await new Promise((r) => setTimeout(r, 150));
    const items = this.getStore();
    const index = items.findIndex((p) => p.id === packageId || p.handoverId === packageId);
    if (index === -1) throw new Error('Handover package not found');

    const pkg = items[index];
    const updatedQuestions = pkg.openQuestions.map((q) => {
      if (q.id === questionId) {
        return {
          ...q,
          status: 'clarified' as const,
          clarificationResponse: response,
        };
      }
      return q;
    });

    const updated: IncomingHandoverPackage = {
      ...pkg,
      openQuestions: updatedQuestions,
    };

    items[index] = updated;
    this.saveStore(items);
    return updated;
  }

  resetDemoData(): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(initialPackages));
  }
}

export const incomingService = new IncomingService();

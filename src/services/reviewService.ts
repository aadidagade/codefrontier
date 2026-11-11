import {
  HandoverReviewRecord,
  ReviewDashboardFilter,
  SectionKey,
  SectionReviewStatus,
  ReviewComment,
  ApprovalStatus,
} from '../types/review';
import { User } from '../types/common';
import { mockUsers, mockCurrentUser } from '../data/mockData';

const STORAGE_KEY = 'kh_handover_reviews_v2';

const sarahJenkins: User = mockUsers[2];
const elenaRostova: User = mockUsers[0];
const davidChen: User = mockUsers[1];
const marcusVance: User = mockUsers[3];
const alexChen: User = mockUsers[4];

const initialHandovers: HandoverReviewRecord[] = [
  {
    id: 'rev-auth-zero',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    outgoingMember: sarahJenkins,
    incomingMember: elenaRostova,
    designatedReviewer: elenaRostova,
    generatedDate: '2026-11-04T08:30:00Z',
    lastUpdated: '2026-11-09T14:20:00Z',
    version: 'v1.0',
    revisionNumber: 1,
    isLocked: false,
    approvalStatus: 'awaiting_review',
    evidenceScore: 94,
    sections: {
      overview: {
        key: 'overview',
        title: 'Project Overview',
        status: 'approved',
        reviewedBy: elenaRostova,
        reviewedAt: '2026-11-08T10:00:00Z',
        commentCount: 1,
        evidenceCount: 3,
      },
      decisions: {
        key: 'decisions',
        title: 'Key Decisions & ADRs',
        status: 'approved',
        reviewedBy: elenaRostova,
        reviewedAt: '2026-11-08T11:15:00Z',
        commentCount: 2,
        evidenceCount: 4,
      },
      tasks: {
        key: 'tasks',
        title: 'Tasks & System Ownership',
        status: 'approved',
        reviewedBy: elenaRostova,
        reviewedAt: '2026-11-08T14:30:00Z',
        commentCount: 0,
        evidenceCount: 3,
      },
      ownership: {
        key: 'ownership',
        title: 'Service Ownership & On-Call',
        status: 'approved',
        reviewedBy: elenaRostova,
        reviewedAt: '2026-11-09T09:00:00Z',
        commentCount: 1,
        evidenceCount: 2,
      },
      blockers: {
        key: 'blockers',
        title: 'Active Blockers',
        status: 'approved',
        reviewedBy: elenaRostova,
        reviewedAt: '2026-11-09T10:00:00Z',
        commentCount: 1,
        evidenceCount: 2,
      },
      risks: {
        key: 'risks',
        title: 'Operational Risks',
        status: 'changes_requested',
        reviewedBy: elenaRostova,
        reviewedAt: '2026-11-09T11:30:00Z',
        reviewNote: 'Please clarify Redis partitioned cluster recovery gotchas before sign-off.',
        commentCount: 3,
        evidenceCount: 2,
      },
      dependencies: {
        key: 'dependencies',
        title: 'System Dependencies',
        status: 'pending',
        commentCount: 0,
        evidenceCount: 3,
      },
      open_questions: {
        key: 'open_questions',
        title: 'Unresolved Open Questions',
        status: 'pending',
        commentCount: 1,
        evidenceCount: 2,
      },
      next_actions: {
        key: 'next_actions',
        title: 'Recommended Next Actions',
        status: 'pending',
        commentCount: 0,
        evidenceCount: 2,
      },
    },
    comments: [
      {
        id: 'cmt-1',
        sectionKey: 'overview',
        author: elenaRostova,
        text: 'The architectural goals for WebAuthn Level 3 look crystal clear and aligned with Q4 security OKRs.',
        createdAt: '2026-11-08T10:05:00Z',
        status: 'resolved',
      },
      {
        id: 'cmt-2',
        sectionKey: 'decisions',
        author: sarahJenkins,
        text: 'Added note regarding PostgreSQL partition split cutover scheduled for Nov 20.',
        createdAt: '2026-11-08T11:30:00Z',
        status: 'resolved',
      },
      {
        id: 'cmt-3',
        sectionKey: 'risks',
        author: elenaRostova,
        text: 'The sentinel failover threshold needs an explicit runbook link. Who triggers manual sentinel reset?',
        createdAt: '2026-11-09T11:32:00Z',
        status: 'open',
      },
    ],
    content: {
      overview: {
        purpose:
          'Migrate 1.4M customer identity records to passwordless FIDO2/WebAuthn passkeys with zero downtime and strict GDPR data locality across EU regions.',
        currentStatus:
          'Passkey registration endpoints verified in staging. Dual-write shadow sync operational. PostgreSQL 16 partition cutover ready for Nov 20 maintenance window.',
        overallProgress: 88,
      },
      decisions: [
        {
          id: 'dec-101',
          decision: 'Platform Authenticator Biometrics Default with FIDO2 Hardware Fallback',
          date: 'Oct 14, 2026',
          rationale: 'Reduces user login friction while achieving strict NIST 800-63B AAL3 compliance.',
          supportingSource: 'Architecture_Decision_Record_v2.pdf (Page 4)',
          isUncertain: false,
        },
        {
          id: 'dec-102',
          decision: 'Database Migration Cutover Scheduled for 20 November',
          date: 'Oct 29, 2026',
          rationale: 'Extended from Nov 15 per sprint triage to allow schema validation with downstream analytics.',
          supportingSource: 'Sprint_Review_Q4_Summary.docx (Page 3)',
          isUncertain: false,
        },
      ],
      tasks: [
        {
          id: 'tsk-101',
          taskName: 'WebAuthn Challenge Nonce Rotation Daemon Audit',
          assignedOwner: elenaRostova,
          status: 'verified',
          priority: 'critical',
          dueDate: 'Nov 12, 2026',
        },
        {
          id: 'tsk-102',
          taskName: 'Transfer Datadog Passkey Dashboard Permissions',
          assignedOwner: elenaRostova,
          status: 'verified',
          priority: 'high',
          dueDate: 'Nov 15, 2026',
        },
      ],
      ownership: [
        {
          id: 'own-1',
          serviceName: 'Auth-Zero Gateway (Go HTTP Server)',
          primaryLead: elenaRostova,
          secondaryOnCall: sarahJenkins,
          escalationPolicy: 'PagerDuty Policy: Identity-Tier1-P0 (15 min SLA)',
          status: 'verified',
        },
        {
          id: 'own-2',
          serviceName: 'Session Invalidation Redis Cluster',
          primaryLead: elenaRostova,
          secondaryOnCall: marcusVance,
          escalationPolicy: 'Platform SRE rotational escalation',
          status: 'verified',
        },
      ],
      blockers: [
        {
          id: 'blk-101',
          description: 'Awaiting Security Governance Council Sign-Off on EU Region Dual-Write',
          impact: 'Cannot enable production traffic routing to eu-central-1 until sign-off memo is signed.',
          severity: 'high',
          supportingEvidence: 'Cloud_Security_Compliance_2026.pdf (Page 22)',
          isUncertain: false,
        },
      ],
      risks: [
        {
          id: 'rsk-101',
          description: 'Redis Cluster Memory Saturation During Peak Flushes',
          impact: 'Direct PostgreSQL query fallback triggers elevated latencies if memory exceeds 92%.',
          severity: 'critical',
          supportingEvidence: 'Production_Incident_Runbook_v1.8.md (§5.3)',
          isUncertain: true,
        },
      ],
      dependencies: [
        {
          id: 'dep-101',
          dependency: 'AWS KMS Key Alias for Asymmetric Challenge Signing',
          relatedTask: 'WebAuthn Nonce Verification',
          requiredPersonOrResource: 'Cloud Infra Team (KMS Key ID: key/auth-zero-prod)',
          currentStatus: 'Operational',
        },
      ],
      openQuestions: [
        {
          id: 'oq-101',
          question: 'Should biometric passkey credentials sync across user iCloud / Google accounts?',
          whyItMatters: 'Enterprise tenants may require hardware-bound non-exportable passkeys.',
          whoNeedsToConfirm: 'Marcus Vance & Enterprise CISO',
          isUncertain: true,
        },
      ],
      nextActions: [
        {
          id: 'act-101',
          action: 'Conduct 3-hour shadow traffic drill with 15% canary load',
          priority: 'high',
          suggestedOwner: 'Elena Rostova',
          reason: 'Validates Redis session store cache hit ratio under real user traffic.',
        },
      ],
    },
    evidenceCitations: [
      {
        id: 'cit-101',
        title: 'WebAuthn Platform Biometric Attachment',
        sourceDocName: 'Architecture_Decision_Record_v2.pdf',
        excerpt:
          'The platform implements standard WebAuthn Level 3 specifications. Authenticator attachment defaults to platform biometrics with security key fallback.',
        confidence: 97,
      },
      {
        id: 'cit-102',
        title: 'Database Cutover Milestone Alignment',
        sourceDocName: 'Sprint_Review_Q4_Summary.docx',
        excerpt:
          'Database migration deadline: 20 November. Extended by 5 business days to allow schema validation with downstream analytics pipelines.',
        confidence: 92,
      },
    ],
  },
  {
    id: 'rev-pay-v2',
    projectId: 'proj-2',
    projectKey: 'PAY-V2',
    projectName: 'Global Payment Orchestration & Multi-PSP Engine',
    outgoingMember: elenaRostova,
    incomingMember: davidChen,
    designatedReviewer: marcusVance,
    generatedDate: '2026-11-08T14:00:00Z',
    lastUpdated: '2026-11-09T18:00:00Z',
    version: 'v1.0',
    revisionNumber: 1,
    isLocked: false,
    approvalStatus: 'draft',
    evidenceScore: 91,
    sections: {
      overview: { key: 'overview', title: 'Project Overview', status: 'pending', commentCount: 0, evidenceCount: 2 },
      decisions: { key: 'decisions', title: 'Key Decisions & ADRs', status: 'pending', commentCount: 0, evidenceCount: 3 },
      tasks: { key: 'tasks', title: 'Tasks & System Ownership', status: 'pending', commentCount: 0, evidenceCount: 4 },
      ownership: { key: 'ownership', title: 'Service Ownership & On-Call', status: 'pending', commentCount: 0, evidenceCount: 2 },
      blockers: { key: 'blockers', title: 'Active Blockers', status: 'pending', commentCount: 0, evidenceCount: 1 },
      risks: { key: 'risks', title: 'Operational Risks', status: 'pending', commentCount: 0, evidenceCount: 3 },
      dependencies: { key: 'dependencies', title: 'System Dependencies', status: 'pending', commentCount: 0, evidenceCount: 2 },
      open_questions: { key: 'open_questions', title: 'Unresolved Open Questions', status: 'pending', commentCount: 0, evidenceCount: 2 },
      next_actions: { key: 'next_actions', title: 'Recommended Next Actions', status: 'pending', commentCount: 0, evidenceCount: 2 },
    },
    comments: [],
    content: {
      overview: {
        purpose: 'Zero-downtime routing across Stripe, Adyen, and regional processors with automated 50k RPS failover.',
        currentStatus: 'Drafted from recent architecture sprints; awaiting outgoing engineer self-review before submitting to lead.',
        overallProgress: 65,
      },
      decisions: [],
      tasks: [],
      ownership: [],
      blockers: [],
      risks: [],
      dependencies: [],
      openQuestions: [],
      nextActions: [],
    },
    evidenceCitations: [],
  },
  {
    id: 'rev-fraud-shield',
    projectId: 'proj-3',
    projectKey: 'FRAUD-SHIELD',
    projectName: 'Real-Time Fraud Prevention & Graph Neural Network',
    outgoingMember: alexChen,
    incomingMember: elenaRostova,
    designatedReviewer: sarahJenkins,
    generatedDate: '2026-10-25T11:00:00Z',
    lastUpdated: '2026-11-05T16:30:00Z',
    version: 'v1.0',
    revisionNumber: 1,
    isLocked: true,
    approvalStatus: 'approved',
    approvedBy: sarahJenkins,
    approvedAt: '2026-11-05T16:30:00Z',
    approvalNotes: 'Cryptographically certified and signed by Principal Lead Sarah Jenkins. All 9 sections passed verification.',
    evidenceScore: 99,
    sections: {
      overview: { key: 'overview', title: 'Project Overview', status: 'approved', reviewedBy: sarahJenkins, reviewedAt: '2026-11-05T15:00:00Z', commentCount: 1, evidenceCount: 3 },
      decisions: { key: 'decisions', title: 'Key Decisions & ADRs', status: 'approved', reviewedBy: sarahJenkins, reviewedAt: '2026-11-05T15:15:00Z', commentCount: 2, evidenceCount: 4 },
      tasks: { key: 'tasks', title: 'Tasks & System Ownership', status: 'approved', reviewedBy: sarahJenkins, reviewedAt: '2026-11-05T15:30:00Z', commentCount: 0, evidenceCount: 3 },
      ownership: { key: 'ownership', title: 'Service Ownership & On-Call', status: 'approved', reviewedBy: sarahJenkins, reviewedAt: '2026-11-05T15:45:00Z', commentCount: 1, evidenceCount: 2 },
      blockers: { key: 'blockers', title: 'Active Blockers', status: 'approved', reviewedBy: sarahJenkins, reviewedAt: '2026-11-05T16:00:00Z', commentCount: 0, evidenceCount: 2 },
      risks: { key: 'risks', title: 'Operational Risks', status: 'approved', reviewedBy: sarahJenkins, reviewedAt: '2026-11-05T16:10:00Z', commentCount: 1, evidenceCount: 2 },
      dependencies: { key: 'dependencies', title: 'System Dependencies', status: 'approved', reviewedBy: sarahJenkins, reviewedAt: '2026-11-05T16:15:00Z', commentCount: 0, evidenceCount: 2 },
      open_questions: { key: 'open_questions', title: 'Unresolved Open Questions', status: 'approved', reviewedBy: sarahJenkins, reviewedAt: '2026-11-05T16:20:00Z', commentCount: 0, evidenceCount: 1 },
      next_actions: { key: 'next_actions', title: 'Recommended Next Actions', status: 'approved', reviewedBy: sarahJenkins, reviewedAt: '2026-11-05T16:25:00Z', commentCount: 0, evidenceCount: 2 },
    },
    comments: [
      {
        id: 'cmt-201',
        sectionKey: 'overview',
        author: sarahJenkins,
        text: 'Formally approved. Elena has completed shadow on-call rotation with zero anomalies.',
        createdAt: '2026-11-05T16:28:00Z',
        status: 'resolved',
      },
    ],
    content: {
      overview: {
        purpose: 'Sub-50ms inference fraud detection pipeline utilizing Neo4j graph cluster and PyTorch GNN models.',
        currentStatus: 'Certified & in production. Version locked for regulatory audit records.',
        overallProgress: 100,
      },
      decisions: [],
      tasks: [],
      ownership: [],
      blockers: [],
      risks: [],
      dependencies: [],
      openQuestions: [],
      nextActions: [],
    },
    evidenceCitations: [],
  },
  {
    id: 'rev-core-pay',
    projectId: 'proj-4',
    projectKey: 'CORE-PAY',
    projectName: 'Core Banking Clearing Bridge & Settlement Ledger',
    outgoingMember: marcusVance,
    incomingMember: sarahJenkins,
    designatedReviewer: davidChen,
    generatedDate: '2026-11-02T10:00:00Z',
    lastUpdated: '2026-11-07T12:00:00Z',
    version: 'v1.0',
    revisionNumber: 1,
    isLocked: false,
    approvalStatus: 'changes_requested',
    changesRequestedNotes: 'The 3:00 AM banking SFTP clearing protocol does not document the timeout fallback for the Barclays gateway.',
    evidenceScore: 78,
    sections: {
      overview: { key: 'overview', title: 'Project Overview', status: 'approved', commentCount: 0, evidenceCount: 2 },
      decisions: { key: 'decisions', title: 'Key Decisions & ADRs', status: 'changes_requested', reviewNote: 'Needs Barclays SFTP fallback procedure documented', commentCount: 2, evidenceCount: 3 },
      tasks: { key: 'tasks', title: 'Tasks & System Ownership', status: 'approved', commentCount: 0, evidenceCount: 2 },
      ownership: { key: 'ownership', title: 'Service Ownership & On-Call', status: 'approved', commentCount: 0, evidenceCount: 1 },
      blockers: { key: 'blockers', title: 'Active Blockers', status: 'pending', commentCount: 1, evidenceCount: 1 },
      risks: { key: 'risks', title: 'Operational Risks', status: 'pending', commentCount: 0, evidenceCount: 2 },
      dependencies: { key: 'dependencies', title: 'System Dependencies', status: 'pending', commentCount: 0, evidenceCount: 1 },
      open_questions: { key: 'open_questions', title: 'Unresolved Open Questions', status: 'pending', commentCount: 0, evidenceCount: 1 },
      next_actions: { key: 'next_actions', title: 'Recommended Next Actions', status: 'pending', commentCount: 0, evidenceCount: 1 },
    },
    comments: [
      {
        id: 'cmt-301',
        sectionKey: 'decisions',
        author: davidChen,
        text: 'Please append the manual SFTP retry command and credential rotation playbook before we approve.',
        createdAt: '2026-11-07T11:50:00Z',
        status: 'open',
      },
    ],
    content: {
      overview: {
        purpose: 'Settlement clearing bridge connecting internal ledger to SWIFT & SEPA banking gateways.',
        currentStatus: 'Changes requested by Lead Reviewer David Chen. Outgoing member updating documentation.',
        overallProgress: 60,
      },
      decisions: [],
      tasks: [],
      ownership: [],
      blockers: [],
      risks: [],
      dependencies: [],
      openQuestions: [],
      nextActions: [],
    },
    evidenceCitations: [],
  },
  {
    id: 'rev-telemetry',
    projectId: 'proj-5',
    projectKey: 'OBSERVABILITY',
    projectName: 'Telemetry Ingestion & Distributed Tracing Pipeline',
    outgoingMember: davidChen,
    incomingMember: elenaRostova,
    designatedReviewer: marcusVance,
    generatedDate: '2026-10-18T09:00:00Z',
    lastUpdated: '2026-10-30T17:00:00Z',
    version: 'v1.0',
    revisionNumber: 1,
    isLocked: false,
    approvalStatus: 'rejected',
    rejectionReason: 'Outdated Kafka 2.8 broker configuration referenced. Project was migrated to Strimzi Kafka on EKS last month. Handover must be regenerated from fresh sources.',
    evidenceScore: 42,
    sections: {
      overview: { key: 'overview', title: 'Project Overview', status: 'rejected', commentCount: 1, evidenceCount: 1 },
      decisions: { key: 'decisions', title: 'Key Decisions & ADRs', status: 'rejected', commentCount: 1, evidenceCount: 1 },
      tasks: { key: 'tasks', title: 'Tasks & System Ownership', status: 'pending', commentCount: 0, evidenceCount: 1 },
      ownership: { key: 'ownership', title: 'Service Ownership & On-Call', status: 'pending', commentCount: 0, evidenceCount: 1 },
      blockers: { key: 'blockers', title: 'Active Blockers', status: 'pending', commentCount: 0, evidenceCount: 1 },
      risks: { key: 'risks', title: 'Operational Risks', status: 'pending', commentCount: 0, evidenceCount: 1 },
      dependencies: { key: 'dependencies', title: 'System Dependencies', status: 'pending', commentCount: 0, evidenceCount: 1 },
      open_questions: { key: 'open_questions', title: 'Unresolved Open Questions', status: 'pending', commentCount: 0, evidenceCount: 1 },
      next_actions: { key: 'next_actions', title: 'Recommended Next Actions', status: 'pending', commentCount: 0, evidenceCount: 1 },
    },
    comments: [],
    content: {
      overview: {
        purpose: 'OpenTelemetry collector and Jaeger tracing daemon spanning all microservices.',
        currentStatus: 'Rejected due to obsolete underlying architecture documentation.',
        overallProgress: 30,
      },
      decisions: [],
      tasks: [],
      ownership: [],
      blockers: [],
      risks: [],
      dependencies: [],
      openQuestions: [],
      nextActions: [],
    },
    evidenceCitations: [],
  },
];

class ReviewService {
  private getStore(): HandoverReviewRecord[] {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(initialHandovers));
      return initialHandovers;
    }
    try {
      return JSON.parse(raw);
    } catch {
      return initialHandovers;
    }
  }

  private saveStore(data: HandoverReviewRecord[]): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }

  async getAllHandovers(
    filter?: ReviewDashboardFilter,
    search?: string
  ): Promise<HandoverReviewRecord[]> {
    await new Promise((r) => setTimeout(r, 120));
    let items = this.getStore();

    if (search && search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (h) =>
          h.projectName.toLowerCase().includes(q) ||
          h.projectKey.toLowerCase().includes(q) ||
          h.outgoingMember.name.toLowerCase().includes(q) ||
          h.incomingMember.name.toLowerCase().includes(q)
      );
    }

    if (filter && filter !== 'all') {
      items = items.filter((h) => h.approvalStatus === filter);
    }

    return items;
  }

  async getHandoverById(id: string): Promise<HandoverReviewRecord | null> {
    await new Promise((r) => setTimeout(r, 100));
    const items = this.getStore();
    return items.find((h) => h.id === id) || null;
  }

  async updateSectionStatus(
    handoverId: string,
    sectionKey: SectionKey,
    status: SectionReviewStatus,
    user: User,
    note?: string
  ): Promise<HandoverReviewRecord> {
    await new Promise((r) => setTimeout(r, 150));
    const items = this.getStore();
    const index = items.findIndex((h) => h.id === handoverId);
    if (index === -1) throw new Error('Handover not found');

    const handover = items[index];
    if (handover.isLocked) {
      throw new Error('Handover is locked and certified. Ordinary edits are prohibited.');
    }

    const updatedSection = {
      ...handover.sections[sectionKey],
      status,
      reviewedBy: user,
      reviewedAt: new Date().toISOString(),
      reviewNote: note,
    };

    const newSections = {
      ...handover.sections,
      [sectionKey]: updatedSection,
    };

    // Recalculate status if all approved
    const allSectionStatuses = Object.values(newSections).map((s) => s.status);
    let newApprovalStatus = handover.approvalStatus;
    if (allSectionStatuses.includes('changes_requested')) {
      newApprovalStatus = 'changes_requested';
    } else if (allSectionStatuses.includes('rejected')) {
      newApprovalStatus = 'rejected';
    }

    const updated: HandoverReviewRecord = {
      ...handover,
      lastUpdated: new Date().toISOString(),
      sections: newSections,
      approvalStatus: newApprovalStatus,
    };

    items[index] = updated;
    this.saveStore(items);
    return updated;
  }

  async updateSectionContent(
    handoverId: string,
    sectionKey: SectionKey,
    newContent: any
  ): Promise<HandoverReviewRecord> {
    await new Promise((r) => setTimeout(r, 180));
    const items = this.getStore();
    const index = items.findIndex((h) => h.id === handoverId);
    if (index === -1) throw new Error('Handover not found');

    const handover = items[index];
    if (handover.isLocked) {
      throw new Error('Handover is locked. Create a new revision to edit.');
    }

    const updated: HandoverReviewRecord = {
      ...handover,
      lastUpdated: new Date().toISOString(),
      sections: {
        ...handover.sections,
        [sectionKey]: {
          ...handover.sections[sectionKey],
          isEdited: true,
        },
      },
      content: {
        ...handover.content,
        [sectionKey]: newContent,
      },
    };

    items[index] = updated;
    this.saveStore(items);
    return updated;
  }

  async addComment(
    handoverId: string,
    sectionKey: SectionKey,
    author: User,
    text: string
  ): Promise<HandoverReviewRecord> {
    await new Promise((r) => setTimeout(r, 120));
    const items = this.getStore();
    const index = items.findIndex((h) => h.id === handoverId);
    if (index === -1) throw new Error('Handover not found');

    const handover = items[index];
    const newComment: ReviewComment = {
      id: `cmt-${Date.now()}`,
      sectionKey,
      author,
      text,
      createdAt: new Date().toISOString(),
      status: 'open',
    };

    const updated: HandoverReviewRecord = {
      ...handover,
      lastUpdated: new Date().toISOString(),
      comments: [...handover.comments, newComment],
      sections: {
        ...handover.sections,
        [sectionKey]: {
          ...handover.sections[sectionKey],
          commentCount: handover.sections[sectionKey].commentCount + 1,
        },
      },
    };

    items[index] = updated;
    this.saveStore(items);
    return updated;
  }

  async approveHandover(
    handoverId: string,
    approver: User,
    notes?: string
  ): Promise<HandoverReviewRecord> {
    await new Promise((r) => setTimeout(r, 220));
    const items = this.getStore();
    const index = items.findIndex((h) => h.id === handoverId);
    if (index === -1) throw new Error('Handover not found');

    const handover = items[index];

    // Approve all sections
    const approvedSections = { ...handover.sections };
    for (const key of Object.keys(approvedSections) as SectionKey[]) {
      approvedSections[key] = {
        ...approvedSections[key],
        status: 'approved',
        reviewedBy: approver,
        reviewedAt: new Date().toISOString(),
      };
    }

    const updated: HandoverReviewRecord = {
      ...handover,
      approvalStatus: 'approved',
      isLocked: true, // LOCK APPROVED HANDOVER AGAINST ORDINARY EDITS
      approvedBy: approver,
      approvedAt: new Date().toISOString(),
      approvalNotes: notes || 'Cryptographically signed off and certified for engineering handover.',
      lastUpdated: new Date().toISOString(),
      sections: approvedSections,
    };

    items[index] = updated;
    this.saveStore(items);
    return updated;
  }

  async requestChanges(
    handoverId: string,
    reviewer: User,
    notes: string
  ): Promise<HandoverReviewRecord> {
    await new Promise((r) => setTimeout(r, 180));
    const items = this.getStore();
    const index = items.findIndex((h) => h.id === handoverId);
    if (index === -1) throw new Error('Handover not found');

    const updated: HandoverReviewRecord = {
      ...items[index],
      approvalStatus: 'changes_requested',
      changesRequestedNotes: notes,
      lastUpdated: new Date().toISOString(),
    };

    items[index] = updated;
    this.saveStore(items);
    return updated;
  }

  async rejectHandover(
    handoverId: string,
    reviewer: User,
    reason: string
  ): Promise<HandoverReviewRecord> {
    await new Promise((r) => setTimeout(r, 180));
    const items = this.getStore();
    const index = items.findIndex((h) => h.id === handoverId);
    if (index === -1) throw new Error('Handover not found');

    const updated: HandoverReviewRecord = {
      ...items[index],
      approvalStatus: 'rejected',
      rejectionReason: reason,
      lastUpdated: new Date().toISOString(),
    };

    items[index] = updated;
    this.saveStore(items);
    return updated;
  }

  async saveDraft(
    handoverId: string,
    updates: Partial<HandoverReviewRecord>
  ): Promise<HandoverReviewRecord> {
    await new Promise((r) => setTimeout(r, 150));
    const items = this.getStore();
    const index = items.findIndex((h) => h.id === handoverId);
    if (index === -1) throw new Error('Handover not found');

    const updated: HandoverReviewRecord = {
      ...items[index],
      ...updates,
      lastUpdated: new Date().toISOString(),
    };

    items[index] = updated;
    this.saveStore(items);
    return updated;
  }

  /**
   * Fork an approved/locked handover to create a new unlocked revision (e.g. v1.1)
   */
  async createRevision(
    handoverId: string,
    creator: User
  ): Promise<HandoverReviewRecord> {
    await new Promise((r) => setTimeout(r, 200));
    const items = this.getStore();
    const source = items.find((h) => h.id === handoverId);
    if (!source) throw new Error('Source handover not found');

    const newRevisionNumber = source.revisionNumber + 1;
    const newVersion = `v1.${newRevisionNumber - 1}`;

    const newDraft: HandoverReviewRecord = {
      ...source,
      id: `${source.id}-rev${newRevisionNumber}`,
      version: newVersion,
      revisionNumber: newRevisionNumber,
      isLocked: false,
      approvalStatus: 'draft',
      approvedBy: undefined,
      approvedAt: undefined,
      approvalNotes: undefined,
      rejectionReason: undefined,
      changesRequestedNotes: undefined,
      generatedDate: new Date().toISOString(),
      lastUpdated: new Date().toISOString(),
    };

    items.unshift(newDraft);
    this.saveStore(items);
    return newDraft;
  }

  resetDemoData(): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(initialHandovers));
  }
}

export const reviewService = new ReviewService();

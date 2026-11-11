import {
  VerificationClaim,
  KnowledgeConflictItem,
  ClaimsFilter,
  ConflictResolution,
  ConflictResolutionType,
} from '../types/verification';
import { User } from '../types/common';

const CLAIMS_STORAGE_KEY = 'kh_verification_claims_v1';
const CONFLICTS_STORAGE_KEY = 'kh_conflicts_v1';

// Initial synthetic demonstration conflicts
const initialConflicts: KnowledgeConflictItem[] = [
  {
    id: 'conf-1',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    topic: 'Database Migration Cutover Deadline',
    disputeType: 'date',
    disputedField: 'Cutover Target Date',
    severity: 'critical',
    status: 'unresolved',
    description:
      'Conflicting migration target dates found between core Architecture Decision Record (v2) and recent Sprint Review minutes.',
    sourceA: {
      docId: 'doc-1',
      docName: 'Architecture_Decision_Record_v2.pdf',
      docType: 'pdf',
      pageOrSection: 'Page 14 · §3.2 Migration Milestones',
      excerpt:
        'Database migration deadline: 15 November. PostgreSQL 16 partition cutover scheduled during 02:00 UTC maintenance window A. All legacy sessions will be invalidated at this timestamp.',
      claimedValue: '15 November 2026',
      author: 'Sarah Jenkins (Outgoing Staff Lead)',
      date: '2026-10-12',
    },
    sourceB: {
      docId: 'doc-3',
      docName: 'Sprint_Review_Q4_Summary.docx',
      docType: 'docx',
      pageOrSection: 'Page 3 · §1.4 Infrastructure Schedule',
      excerpt:
        'Database migration deadline: 20 November. Extended by 5 business days to allow schema validation with downstream analytics pipelines and BI test harnesses.',
      claimedValue: '20 November 2026',
      author: 'David K. (Release Engineering)',
      date: '2026-10-29',
    },
    isSyntheticModelOutput: true,
  },
  {
    id: 'conf-2',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    topic: 'Disaster Recovery Primary Failover Region',
    disputeType: 'architecture',
    disputedField: 'DR Topology & Region',
    severity: 'high',
    status: 'unresolved',
    description:
      'Infrastructure runbook specifies warm standby in us-east-2, whereas cloud compliance spec mandates active-active in eu-west-1 for GDPR locality.',
    sourceA: {
      docId: 'doc-2',
      docName: 'Production_Incident_Runbook_v1.8.md',
      docType: 'md',
      pageOrSection: 'Section 4.1 · Regional Evacuation',
      excerpt:
        'In the event of us-east-1 outage, traffic fails over to warm standby instances in us-east-2 with 120s Route53 health check delay.',
      claimedValue: 'us-east-2 (Warm Standby)',
      author: 'DevOps Platform Team',
      date: '2026-08-15',
    },
    sourceB: {
      docId: 'doc-4',
      docName: 'Cloud_Security_Compliance_2026.pdf',
      docType: 'pdf',
      pageOrSection: 'Page 22 · European Data Residency',
      excerpt:
        'All customer authentication metadata and session tokens must run in active-active topology between eu-west-1 (Ireland) and eu-central-1 (Frankfurt).',
      claimedValue: 'eu-west-1 (Active-Active)',
      author: 'Security Governance Council',
      date: '2026-10-04',
    },
    isSyntheticModelOutput: true,
  },
  {
    id: 'conf-3',
    projectId: 'proj-2',
    projectKey: 'CORE-PAY',
    projectName: 'Payment Gateway PCI-DSS v4.0 Compliance',
    topic: 'Vault Secret Token Rotation Interval',
    disputeType: 'security',
    disputedField: 'Rotation Frequency',
    severity: 'high',
    status: 'unresolved',
    description:
      'Security runbook mentions 90-day manual rotation window, while audited compliance policy mandates automated weekly rotation.',
    sourceA: {
      docId: 'doc-5',
      docName: 'Vault_Secrets_Ops_Guide.md',
      docType: 'md',
      pageOrSection: 'Section 2.3 · Key Lifecycle',
      excerpt:
        'Database master service credentials must be rotated manually every 90 days following the scheduled sprint maintenance checklist.',
      claimedValue: 'Every 90 Days (Manual)',
      author: 'Legacy SecOps',
      date: '2026-05-10',
    },
    sourceB: {
      docId: 'doc-6',
      docName: 'PCI_DSS_v4_Remediation_Audit.pdf',
      docType: 'pdf',
      pageOrSection: 'Page 8 · Requirement 8.3.6',
      excerpt:
        'Automated weekly rotation enforced via HashiCorp Vault Agent sidecar with short-lived 7-day TTL certificates and automated zero-downtime reloads.',
      claimedValue: 'Weekly (Automated 7-day TTL)',
      author: 'External Auditor (Coalfire)',
      date: '2026-10-18',
    },
    isSyntheticModelOutput: true,
  },
  {
    id: 'conf-4',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    topic: 'Lead On-Call Escalation Ownership',
    disputeType: 'owner',
    disputedField: 'Primary Escalation Lead',
    severity: 'medium',
    status: 'unresolved',
    description:
      'Team on-call roster names Alex Chen as tier-3 escalation, but project handover notes indicate Marcus Vance took over effective November 1st.',
    sourceA: {
      docId: 'doc-7',
      docName: 'OnCall_Escalation_Roster_Q4.docx',
      docType: 'docx',
      pageOrSection: 'Page 2 · Tier 3 Engineering Leads',
      excerpt:
        'Tier 3 escalation lead: Alex Chen (alex.chen@acme.corp). PagerDuty policy escalates after 15 minutes of unacknowledged high-priority alert.',
      claimedValue: 'Alex Chen',
      author: 'Engineering Ops',
      date: '2026-09-28',
    },
    sourceB: {
      docId: 'doc-8',
      docName: 'Handover_Transition_Notes_Sarah.md',
      docType: 'md',
      pageOrSection: 'Section 1 · Ownership Handoff',
      excerpt:
        'Tier 3 escalation lead transitioned to Marcus Vance (marcus.v@acme.corp) effective 1 November 2026. PagerDuty schedule rotated.',
      claimedValue: 'Marcus Vance',
      author: 'Sarah Jenkins',
      date: '2026-10-31',
    },
    isSyntheticModelOutput: true,
  },
];

// Initial synthetic claims
const initialClaims: VerificationClaim[] = [
  {
    id: 'clm-1',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    section: 'decisions',
    claimText: 'Database cutover target is scheduled for 15 November with zero downtime read-replicas.',
    sourceDocId: 'doc-1',
    sourceDocName: 'Architecture_Decision_Record_v2.pdf',
    sourceDocType: 'pdf',
    pageOrSection: 'Page 14 · §3.2',
    evidenceSnippet:
      'Database migration deadline: 15 November. PostgreSQL 16 partition cutover scheduled during 02:00 UTC maintenance window A. All legacy sessions will be invalidated at this timestamp.',
    evidenceStatus: 'partially_supported',
    uncertaintyFlags: ['contradictory'],
    confidenceScore: 78,
    isSyntheticModelOutput: true,
    verificationStatus: 'unverified',
    conflictId: 'conf-1',
    createdAt: '2026-11-02T10:15:00Z',
  },
  {
    id: 'clm-2',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    section: 'overview',
    claimText: 'Passkey implementation uses WebAuthn with biometric authenticator attachment as default.',
    sourceDocId: 'doc-1',
    sourceDocName: 'Architecture_Decision_Record_v2.pdf',
    sourceDocType: 'pdf',
    pageOrSection: 'Page 4 · §1.2',
    evidenceSnippet:
      'The platform implements standard WebAuthn Level 3 specifications. Authenticator attachment defaults to platform biometrics (Face ID, Touch ID, Windows Hello) with security key fallback.',
    evidenceStatus: 'supported',
    uncertaintyFlags: [],
    confidenceScore: 97,
    isSyntheticModelOutput: true,
    verificationStatus: 'verified',
    verifiedBy: { id: 'u-1', name: 'Elena Rostova', role: 'Incoming Lead' },
    verifiedAt: '2026-11-04T14:20:00Z',
    verificationNotes: 'Verified against RFC 8252 and current production WebAuthn handler code.',
    createdAt: '2026-11-01T08:30:00Z',
  },
  {
    id: 'clm-3',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    section: 'risks',
    claimText: 'Redis circuit breakers lack automated recovery for cluster partitioned nodes.',
    sourceDocId: 'doc-2',
    sourceDocName: 'Production_Incident_Runbook_v1.8.md',
    sourceDocType: 'md',
    pageOrSection: 'Section 5.3 · Redis Memory Thresholds',
    evidenceSnippet:
      'When Redis cluster hits 92% memory saturation, fallback circuit breaker trips to PostgreSQL direct query mode. Automated self-healing requires manual operator intervention to reset sentinel state.',
    evidenceStatus: 'supported',
    uncertaintyFlags: [],
    confidenceScore: 92,
    isSyntheticModelOutput: true,
    verificationStatus: 'unverified',
    createdAt: '2026-11-03T11:45:00Z',
  },
  {
    id: 'clm-4',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    section: 'tasks',
    claimText: 'Elasticsearch index compaction and retention cleanup cron job is maintained by DevOps.',
    sourceDocId: 'doc-2',
    sourceDocName: 'Production_Incident_Runbook_v1.8.md',
    sourceDocType: 'md',
    pageOrSection: 'Section 8.1 · Log Aggregation',
    evidenceSnippet:
      'Daily index curation runs at 04:00 UTC via cron. Responsible team is ambiguous between Platform SRE and Data Engineering.',
    evidenceStatus: 'partially_supported',
    uncertaintyFlags: ['unclear_ownership'],
    confidenceScore: 64,
    isSyntheticModelOutput: true,
    verificationStatus: 'unverified',
    createdAt: '2026-11-03T12:00:00Z',
  },
  {
    id: 'clm-5',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    section: 'risks',
    claimText: 'Legacy sync daemon runs on an unmonitored AWS EC2 t3.medium instance with root keys.',
    sourceDocId: '',
    sourceDocName: 'No Document Found',
    sourceDocType: 'txt',
    pageOrSection: 'N/A',
    evidenceSnippet:
      'Synthesized based on indirect mention in Slack thread summary. No formal runbook, Terraform file, or architecture document verifies this host.',
    evidenceStatus: 'unsupported',
    uncertaintyFlags: ['missing_evidence', 'unsupported_statement'],
    confidenceScore: 28,
    isSyntheticModelOutput: true,
    verificationStatus: 'disputed',
    disputedReason: 'No primary repository code or AWS CloudFormation template tracks this instance. Flagged for immediate AWS console audit.',
    createdAt: '2026-11-04T09:10:00Z',
  },
  {
    id: 'clm-6',
    projectId: 'proj-1',
    projectKey: 'AUTH-ZERO',
    projectName: 'Customer Identity & Passkey Migration',
    section: 'decisions',
    claimText: 'Session revocation TTL is hardcoded to 14 days across all tenant tiers.',
    sourceDocId: 'doc-9',
    sourceDocName: 'Session_Management_RFC_2025.txt',
    sourceDocType: 'txt',
    pageOrSection: 'Line 84 · §Session Expiry Defaults',
    evidenceSnippet:
      'Base session lifetime is 14 days without activity. (Note: Superseded by Enterprise Config Policy in Q3 2026).',
    evidenceStatus: 'partially_supported',
    uncertaintyFlags: ['outdated'],
    confidenceScore: 55,
    isSyntheticModelOutput: true,
    verificationStatus: 'unverified',
    createdAt: '2026-11-04T10:00:00Z',
  },
  {
    id: 'clm-7',
    projectId: 'proj-2',
    projectKey: 'CORE-PAY',
    projectName: 'Payment Gateway PCI-DSS v4.0 Compliance',
    section: 'decisions',
    claimText: 'Master database credentials rotate manually every 90 days.',
    sourceDocId: 'doc-5',
    sourceDocName: 'Vault_Secrets_Ops_Guide.md',
    sourceDocType: 'md',
    pageOrSection: 'Section 2.3 · Key Lifecycle',
    evidenceSnippet:
      'Database master service credentials must be rotated manually every 90 days following the scheduled sprint maintenance checklist.',
    evidenceStatus: 'partially_supported',
    uncertaintyFlags: ['contradictory', 'outdated'],
    confidenceScore: 61,
    isSyntheticModelOutput: true,
    verificationStatus: 'unverified',
    conflictId: 'conf-3',
    createdAt: '2026-11-04T11:20:00Z',
  },
  {
    id: 'clm-8',
    projectId: 'proj-2',
    projectKey: 'CORE-PAY',
    projectName: 'Payment Gateway PCI-DSS v4.0 Compliance',
    section: 'tasks',
    claimText: 'Payment webhook payloads are signed with Ed25519 asymmetric signatures.',
    sourceDocId: 'doc-10',
    sourceDocName: 'Webhook_Security_Specification.pdf',
    sourceDocType: 'pdf',
    pageOrSection: 'Page 6 · Signature Verification',
    evidenceSnippet:
      'All egress webhooks are signed using Ed25519 asymmetric keypairs. Partners verify signatures against public key endpoints with 1-hour caching.',
    evidenceStatus: 'supported',
    uncertaintyFlags: [],
    confidenceScore: 99,
    isSyntheticModelOutput: true,
    verificationStatus: 'verified',
    verifiedBy: { id: 'u-2', name: 'Marcus Vance', role: 'Staff Security Engineer' },
    verifiedAt: '2026-11-05T16:00:00Z',
    verificationNotes: 'Cryptographic validation verified with integration test suite.',
    createdAt: '2026-11-02T13:00:00Z',
  },
];

class VerificationService {
  private getStoredClaims(): VerificationClaim[] {
    const raw = localStorage.getItem(CLAIMS_STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(CLAIMS_STORAGE_KEY, JSON.stringify(initialClaims));
      return initialClaims;
    }
    try {
      return JSON.parse(raw);
    } catch {
      return initialClaims;
    }
  }

  private saveClaims(claims: VerificationClaim[]): void {
    localStorage.setItem(CLAIMS_STORAGE_KEY, JSON.stringify(claims));
  }

  private getStoredConflicts(): KnowledgeConflictItem[] {
    const raw = localStorage.getItem(CONFLICTS_STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(CONFLICTS_STORAGE_KEY, JSON.stringify(initialConflicts));
      return initialConflicts;
    }
    try {
      return JSON.parse(raw);
    } catch {
      return initialConflicts;
    }
  }

  private saveConflicts(conflicts: KnowledgeConflictItem[]): void {
    localStorage.setItem(CONFLICTS_STORAGE_KEY, JSON.stringify(conflicts));
  }

  // --- API SIMULATION METHODS ---

  async getClaims(
    filter?: ClaimsFilter,
    projectId?: string,
    search?: string
  ): Promise<VerificationClaim[]> {
    await new Promise((r) => setTimeout(r, 120));
    let claims = this.getStoredClaims();

    if (projectId && projectId !== 'all') {
      claims = claims.filter((c) => c.projectId === projectId || c.projectKey === projectId);
    }

    if (search && search.trim()) {
      const q = search.toLowerCase();
      claims = claims.filter(
        (c) =>
          c.claimText.toLowerCase().includes(q) ||
          c.sourceDocName.toLowerCase().includes(q) ||
          c.evidenceSnippet.toLowerCase().includes(q) ||
          c.projectKey.toLowerCase().includes(q)
      );
    }

    if (filter && filter !== 'all') {
      switch (filter) {
        case 'supported':
          claims = claims.filter((c) => c.evidenceStatus === 'supported');
          break;
        case 'partially_supported':
          claims = claims.filter((c) => c.evidenceStatus === 'partially_supported');
          break;
        case 'unsupported':
          claims = claims.filter((c) => c.evidenceStatus === 'unsupported');
          break;
        case 'uncertain':
          claims = claims.filter((c) => c.uncertaintyFlags && c.uncertaintyFlags.length > 0);
          break;
        case 'conflicts':
          claims = claims.filter((c) => !!c.conflictId || c.uncertaintyFlags.includes('contradictory'));
          break;
        case 'verified':
          claims = claims.filter((c) => c.verificationStatus === 'verified');
          break;
        case 'unverified':
          claims = claims.filter((c) => c.verificationStatus === 'unverified');
          break;
      }
    }

    return claims;
  }

  async getClaimById(id: string): Promise<VerificationClaim | null> {
    const claims = this.getStoredClaims();
    return claims.find((c) => c.id === id) || null;
  }

  async getConflicts(projectId?: string): Promise<KnowledgeConflictItem[]> {
    await new Promise((r) => setTimeout(r, 120));
    let conflicts = this.getStoredConflicts();
    if (projectId && projectId !== 'all') {
      conflicts = conflicts.filter((c) => c.projectId === projectId || c.projectKey === projectId);
    }
    return conflicts;
  }

  async getConflictById(id: string): Promise<KnowledgeConflictItem | null> {
    const conflicts = this.getStoredConflicts();
    return conflicts.find((c) => c.id === id) || null;
  }

  /**
   * Verify an AI-generated claim with human reviewer audit trail
   */
  async verifyClaim(
    claimId: string,
    reviewer: { id: string; name: string; role?: string },
    notes?: string
  ): Promise<VerificationClaim> {
    await new Promise((r) => setTimeout(r, 180));
    const claims = this.getStoredClaims();
    const index = claims.findIndex((c) => c.id === claimId);
    if (index === -1) throw new Error('Claim not found');

    const updated: VerificationClaim = {
      ...claims[index],
      verificationStatus: 'verified',
      verifiedBy: reviewer,
      verifiedAt: new Date().toISOString(),
      verificationNotes: notes || 'Verified against primary evidence passage.',
    };

    claims[index] = updated;
    this.saveClaims(claims);
    return updated;
  }

  /**
   * Dispute or flag a claim
   */
  async flagClaim(
    claimId: string,
    reviewer: { id: string; name: string },
    reason: string
  ): Promise<VerificationClaim> {
    await new Promise((r) => setTimeout(r, 180));
    const claims = this.getStoredClaims();
    const index = claims.findIndex((c) => c.id === claimId);
    if (index === -1) throw new Error('Claim not found');

    const updated: VerificationClaim = {
      ...claims[index],
      verificationStatus: 'disputed',
      disputedReason: reason,
      uncertaintyFlags: Array.from(new Set([...claims[index].uncertaintyFlags, 'unsupported_statement'])),
    };

    claims[index] = updated;
    this.saveClaims(claims);
    return updated;
  }

  /**
   * Resolve a conflicting statement.
   * STRICT PLATFORM INVARIANT:
   * The system NEVER auto-selects a winner. Resolution requires explicit human reviewer choice
   * or manual custom correction with a recorded audit note.
   */
  async resolveConflict(
    conflictId: string,
    reviewer: { id: string; name: string; role?: string; email?: string },
    resolution: {
      resolutionType: ConflictResolutionType;
      chosenValue?: string;
      resolutionNote: string;
      correctionText?: string;
    }
  ): Promise<KnowledgeConflictItem> {
    await new Promise((r) => setTimeout(r, 220));
    const conflicts = this.getStoredConflicts();
    const index = conflicts.findIndex((c) => c.id === conflictId);
    if (index === -1) throw new Error('Conflict record not found');

    const isMarkedUnresolved = resolution.resolutionType === 'mark_unresolved';

    const resolutionRecord: ConflictResolution = {
      resolvedBy: reviewer,
      resolvedAt: new Date().toISOString(),
      resolutionType: resolution.resolutionType,
      chosenValue: resolution.chosenValue,
      resolutionNote: resolution.resolutionNote,
      correctionText: resolution.correctionText,
    };

    const updated: KnowledgeConflictItem = {
      ...conflicts[index],
      status: isMarkedUnresolved ? 'unresolved' : 'resolved',
      resolution: resolutionRecord,
    };

    conflicts[index] = updated;
    this.saveConflicts(conflicts);

    // Also update any claims referencing this conflict
    const claims = this.getStoredClaims();
    const updatedClaims = claims.map((claim) => {
      if (claim.conflictId === conflictId) {
        if (resolution.resolutionType === 'custom_correction' && resolution.correctionText) {
          return {
            ...claim,
            claimText: resolution.correctionText,
            verificationStatus: 'verified' as const,
            verificationNotes: `Resolved by ${reviewer.name}: ${resolution.resolutionNote}`,
            uncertaintyFlags: claim.uncertaintyFlags.filter((f) => f !== 'contradictory'),
          };
        } else if (resolution.resolutionType === 'verify_source_a') {
          return {
            ...claim,
            verificationStatus: 'verified' as const,
            verificationNotes: `Verified Source A (${conflicts[index].sourceA.claimedValue}) by ${reviewer.name}: ${resolution.resolutionNote}`,
            uncertaintyFlags: claim.uncertaintyFlags.filter((f) => f !== 'contradictory'),
          };
        } else if (resolution.resolutionType === 'verify_source_b') {
          return {
            ...claim,
            claimText: claim.claimText.replace(conflicts[index].sourceA.claimedValue, conflicts[index].sourceB.claimedValue),
            verificationStatus: 'verified' as const,
            verificationNotes: `Verified Source B (${conflicts[index].sourceB.claimedValue}) by ${reviewer.name}: ${resolution.resolutionNote}`,
            uncertaintyFlags: claim.uncertaintyFlags.filter((f) => f !== 'contradictory'),
          };
        }
      }
      return claim;
    });
    this.saveClaims(updatedClaims);

    return updated;
  }

  /**
   * Reopen a resolved conflict back into the unresolved queue
   */
  async reopenConflict(conflictId: string): Promise<KnowledgeConflictItem> {
    await new Promise((r) => setTimeout(r, 120));
    const conflicts = this.getStoredConflicts();
    const index = conflicts.findIndex((c) => c.id === conflictId);
    if (index === -1) throw new Error('Conflict record not found');

    const updated: KnowledgeConflictItem = {
      ...conflicts[index],
      status: 'unresolved',
      resolution: undefined,
    };

    conflicts[index] = updated;
    this.saveConflicts(conflicts);
    return updated;
  }

  /**
   * Reset demonstration state back to original sample data
   */
  resetDemoData(): void {
    localStorage.setItem(CLAIMS_STORAGE_KEY, JSON.stringify(initialClaims));
    localStorage.setItem(CONFLICTS_STORAGE_KEY, JSON.stringify(initialConflicts));
  }
}

export const verificationService = new VerificationService();

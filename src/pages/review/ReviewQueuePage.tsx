import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  GitCompare,
  ShieldCheck,
  CheckSquare,
  Sparkles,
  RotateCcw,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Layers,
  ArrowRight,
  Info,
  ArrowRightLeft,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Tabs } from '../../components/common/Tabs';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../hooks/useAuth';
import { verificationService } from '../../services/verificationService';
import { reviewService } from '../../services/reviewService';
import {
  KnowledgeConflictItem,
  VerificationClaim,
  ConflictResolutionType,
} from '../../types/verification';
import { HandoverReviewRecord } from '../../types/review';
import { ConflictsSection } from '../../components/verification/ConflictsSection';
import { ClaimsAuditSection } from '../../components/verification/ClaimsAuditSection';
import { ReviewDashboardView } from '../../components/review/ReviewDashboardView';
import { EvidenceDrawer } from '../../components/verification/EvidenceDrawer';
import { ConflictResolutionModal } from '../../components/verification/ConflictResolutionModal';
import { VerifyClaimModal } from '../../components/verification/VerifyClaimModal';

export const ReviewQueuePage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, info } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  // Active tab: 'handovers' | 'conflicts' | 'claims'
  const currentTab = (searchParams.get('tab') as 'handovers' | 'conflicts' | 'claims') || 'handovers';

  const [handovers, setHandovers] = useState<HandoverReviewRecord[]>([]);
  const [conflicts, setConflicts] = useState<KnowledgeConflictItem[]>([]);
  const [claims, setClaims] = useState<VerificationClaim[]>([]);
  const [loading, setLoading] = useState(true);

  // Modals & Drawers state
  const [selectedClaim, setSelectedClaim] = useState<VerificationClaim | null>(null);
  const [isEvidenceDrawerOpen, setIsEvidenceDrawerOpen] = useState(false);
  const [selectedConflict, setSelectedConflict] = useState<KnowledgeConflictItem | null>(null);
  const [isResolveModalOpen, setIsResolveModalOpen] = useState(false);

  const [claimToVerifyModal, setClaimToVerifyModal] = useState<{
    claim: VerificationClaim;
    mode: 'verify' | 'flag';
  } | null>(null);

  // Load data
  const loadData = async () => {
    setLoading(true);
    try {
      const [allHandovers, allConflicts, allClaims] = await Promise.all([
        reviewService.getAllHandovers(),
        verificationService.getConflicts(),
        verificationService.getClaims(),
      ]);
      setHandovers(allHandovers);
      setConflicts(allConflicts);
      setClaims(allClaims);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTabChange = (key: string) => {
    setSearchParams({ tab: key });
  };

  // Open Evidence Drawer for a claim
  const handleOpenEvidenceDrawer = (claim: VerificationClaim) => {
    setSelectedClaim(claim);
    setIsEvidenceDrawerOpen(true);
  };

  // Open Conflict Resolution Modal
  const handleOpenResolveConflict = (conflict: KnowledgeConflictItem) => {
    setSelectedConflict(conflict);
    setIsResolveModalOpen(true);
  };

  // Resolve conflict
  const handleResolveConflict = async (
    conflictId: string,
    resolution: {
      resolutionType: ConflictResolutionType;
      chosenValue?: string;
      resolutionNote: string;
      correctionText?: string;
    }
  ) => {
    const reviewer = {
      id: user?.id || 'u-1',
      name: user?.name || 'Elena Rostova',
      role: user?.role || 'Lead Engineer',
    };

    await verificationService.resolveConflict(conflictId, reviewer, resolution);
    success('Conflict Resolved', `Recorded human resolution for: ${resolution.chosenValue || 'Custom correction'}`);
    await loadData();
  };

  // Reopen conflict
  const handleReopenConflict = async (conflictId: string) => {
    await verificationService.reopenConflict(conflictId);
    info('Dispute Reopened', 'The conflict has been moved back to the unresolved review queue.');
    await loadData();
  };

  // Verify claim
  const handleConfirmVerifyClaim = async (claimId: string, notes: string) => {
    const reviewer = {
      id: user?.id || 'u-1',
      name: user?.name || 'Elena Rostova',
      role: user?.role || 'Staff Lead',
    };
    await verificationService.verifyClaim(claimId, reviewer, notes);
    success('Claim Verified', 'Claim provenance has been human-verified and recorded in the audit log.');
    await loadData();
    if (selectedClaim && selectedClaim.id === claimId) {
      const updated = await verificationService.getClaimById(claimId);
      setSelectedClaim(updated);
    }
  };

  // Flag claim
  const handleConfirmFlagClaim = async (claimId: string, reason: string) => {
    const reviewer = {
      id: user?.id || 'u-1',
      name: user?.name || 'Elena Rostova',
    };
    await verificationService.flagClaim(claimId, reviewer, reason);
    info('Claim Flagged', 'Discrepancy reason noted and uncertainty flag applied.');
    await loadData();
    if (selectedClaim && selectedClaim.id === claimId) {
      const updated = await verificationService.getClaimById(claimId);
      setSelectedClaim(updated);
    }
  };

  // Reset demo state
  const handleResetDemo = () => {
    reviewService.resetDemoData();
    verificationService.resetDemoData();
    loadData();
    success('Demo State Reset', 'Restored initial handovers, conflicts, and evidence claims.');
  };

  const pendingReviewHandovers = handovers.filter((h) => h.approvalStatus === 'awaiting_review').length;
  const unresolvedConflictsCount = conflicts.filter((c) => c.status === 'unresolved').length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-brand-400 uppercase tracking-wider">
              Verification & Governance
            </span>
            <Badge variant="ai" size="sm">
              Human Reviewer Gate
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
            Handover Review & Approval Desk
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            Inspect, edit, approve, or reject AI-generated handovers before knowledge sharing. Audit claims against primary evidence and resolve documentation contradictions.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetDemo}
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            className="text-xs"
          >
            Reset Demo Data
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <Tabs
        activeTab={currentTab}
        onChange={handleTabChange}
        tabs={[
          {
            id: 'handovers',
            label: 'Handovers to Review',
            count: pendingReviewHandovers,
            icon: <ArrowRightLeft className="h-3.5 w-3.5 text-brand-400" />,
          },
          {
            id: 'conflicts',
            label: 'Conflicts & Discrepancies',
            count: unresolvedConflictsCount,
            icon: <GitCompare className="h-3.5 w-3.5 text-red-400" />,
          },
          {
            id: 'claims',
            label: 'Claim Evidence Audit',
            count: claims.length,
            icon: <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />,
          },
        ]}
      />

      {/* TAB 1: HANDOVERS TO REVIEW DASHBOARD */}
      {currentTab === 'handovers' && (
        <ReviewDashboardView
          handovers={handovers}
          onSelectHandover={(h) => navigate(`/review/${h.id}`)}
          onResetDemo={handleResetDemo}
        />
      )}

      {/* TAB 2: CONFLICTS & DISCREPANCIES */}
      {currentTab === 'conflicts' && (
        <ConflictsSection
          conflicts={conflicts}
          onOpenResolve={handleOpenResolveConflict}
          onReopen={handleReopenConflict}
          onViewEvidenceForConflict={(conflict) => {
            const related = claims.find((c) => c.conflictId === conflict.id);
            if (related) {
              handleOpenEvidenceDrawer(related);
            } else {
              info('Viewing Conflict', `Reviewing evidence for: ${conflict.topic}`);
            }
          }}
        />
      )}

      {/* TAB 3: CLAIM EVIDENCE AUDIT */}
      {currentTab === 'claims' && (
        <ClaimsAuditSection
          claims={claims}
          onSelectClaim={handleOpenEvidenceDrawer}
          onVerifyClaim={(claim) => setClaimToVerifyModal({ claim, mode: 'verify' })}
          onFlagClaim={(claim) => setClaimToVerifyModal({ claim, mode: 'flag' })}
        />
      )}

      {/* REUSABLE RIGHT-SIDE EVIDENCE DRAWER */}
      <EvidenceDrawer
        isOpen={isEvidenceDrawerOpen}
        onClose={() => {
          setIsEvidenceDrawerOpen(false);
          setSelectedClaim(null);
        }}
        claim={selectedClaim}
        onVerify={(claim) => {
          setIsEvidenceDrawerOpen(false);
          setClaimToVerifyModal({ claim, mode: 'verify' });
        }}
        onFlag={(claim) => {
          setIsEvidenceDrawerOpen(false);
          setClaimToVerifyModal({ claim, mode: 'flag' });
        }}
        onOpenConflict={(conflictId) => {
          setIsEvidenceDrawerOpen(false);
          const found = conflicts.find((c) => c.id === conflictId);
          if (found) {
            handleTabChange('conflicts');
            handleOpenResolveConflict(found);
          }
        }}
        onOpenDocument={(docId, docName) => {
          info('Source Document', `Inspecting primary source document: ${docName}`);
        }}
      />

      {/* CONFLICT RESOLUTION MODAL */}
      <ConflictResolutionModal
        isOpen={isResolveModalOpen}
        onClose={() => {
          setIsResolveModalOpen(false);
          setSelectedConflict(null);
        }}
        conflict={selectedConflict}
        onResolve={handleResolveConflict}
      />

      {/* VERIFY / FLAG QUICK MODAL */}
      <VerifyClaimModal
        isOpen={!!claimToVerifyModal}
        onClose={() => setClaimToVerifyModal(null)}
        claim={claimToVerifyModal?.claim || null}
        mode={claimToVerifyModal?.mode || 'verify'}
        onSubmit={
          claimToVerifyModal?.mode === 'verify'
            ? handleConfirmVerifyClaim
            : handleConfirmFlagClaim
        }
      />
    </div>
  );
};

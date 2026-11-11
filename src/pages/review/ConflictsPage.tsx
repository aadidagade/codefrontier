import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  GitCompare,
  RotateCcw,
  ArrowLeft,
  Sparkles,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../hooks/useAuth';
import { verificationService } from '../../services/verificationService';
import {
  KnowledgeConflictItem,
  VerificationClaim,
  ConflictResolutionType,
} from '../../types/verification';
import { ConflictsSection } from '../../components/verification/ConflictsSection';
import { ConflictResolutionModal } from '../../components/verification/ConflictResolutionModal';
import { EvidenceDrawer } from '../../components/verification/EvidenceDrawer';

export const ConflictsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, info } = useToast();

  const [conflicts, setConflicts] = useState<KnowledgeConflictItem[]>([]);
  const [claims, setClaims] = useState<VerificationClaim[]>([]);
  const [selectedConflict, setSelectedConflict] = useState<KnowledgeConflictItem | null>(null);
  const [isResolveModalOpen, setIsResolveModalOpen] = useState(false);

  const [selectedClaim, setSelectedClaim] = useState<VerificationClaim | null>(null);
  const [isEvidenceDrawerOpen, setIsEvidenceDrawerOpen] = useState(false);

  const loadData = async () => {
    const [c, cl] = await Promise.all([
      verificationService.getConflicts(),
      verificationService.getClaims(),
    ]);
    setConflicts(c);
    setClaims(cl);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleResolve = async (
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
    success('Conflict Resolved', `Recorded human resolution for ${resolution.chosenValue || 'Custom correction'}`);
    await loadData();
  };

  const handleReopen = async (conflictId: string) => {
    await verificationService.reopenConflict(conflictId);
    info('Conflict Reopened', 'Moved back to unresolved state.');
    await loadData();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate(-1)}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-mono transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </button>
            <span className="text-slate-600">·</span>
            <Badge variant="ai" size="sm">
              Cross-Document Conflict Detection
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
            Knowledge Conflicts & Contradictions
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            Detect and resolve conflicting project claims across architecture records, sprint reviews, runbooks, and audit specifications.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/review?tab=claims')}
            className="text-xs"
          >
            Audit All Claims
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              verificationService.resetDemoData();
              loadData();
              success('Reset Completed', 'Initial synthetic conflicts reloaded.');
            }}
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            className="text-xs text-slate-400"
          >
            Reset
          </Button>
        </div>
      </div>

      <ConflictsSection
        conflicts={conflicts}
        onOpenResolve={(c) => {
          setSelectedConflict(c);
          setIsResolveModalOpen(true);
        }}
        onReopen={handleReopen}
        onViewEvidenceForConflict={(conflict) => {
          const rel = claims.find((c) => c.conflictId === conflict.id);
          if (rel) {
            setSelectedClaim(rel);
            setIsEvidenceDrawerOpen(true);
          }
        }}
      />

      <ConflictResolutionModal
        isOpen={isResolveModalOpen}
        onClose={() => {
          setIsResolveModalOpen(false);
          setSelectedConflict(null);
        }}
        conflict={selectedConflict}
        onResolve={handleResolve}
      />

      <EvidenceDrawer
        isOpen={isEvidenceDrawerOpen}
        onClose={() => {
          setIsEvidenceDrawerOpen(false);
          setSelectedClaim(null);
        }}
        claim={selectedClaim}
      />
    </div>
  );
};

import React, { useState } from 'react';
import {
  X,
  FileText,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Copy,
  Check,
  Sparkles,
  Info,
  Calendar,
  User,
  Quote,
  Flame,
} from 'lucide-react';
import { VerificationClaim } from '../../types/verification';
import { EvidenceStatusBadge } from './EvidenceStatusBadge';
import { UncertaintyBadge } from './UncertaintyBadge';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { useToast } from '../../hooks/useToast';
import { cn } from '../../utils/cn';

interface EvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  claim: VerificationClaim | null;
  onVerify?: (claim: VerificationClaim) => void;
  onFlag?: (claim: VerificationClaim) => void;
  onOpenConflict?: (conflictId: string) => void;
  onOpenDocument?: (docId: string, docName: string) => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  isOpen,
  onClose,
  claim,
  onVerify,
  onFlag,
  onOpenConflict,
  onOpenDocument,
}) => {
  const { info, success } = useToast();
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  if (!isOpen || !claim) return null;

  const handleCopySnippet = () => {
    navigator.clipboard.writeText(claim.evidenceSnippet);
    setCopiedSnippet(true);
    info('Copied to Clipboard', 'Supporting passage copied to clipboard.');
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const hasUncertainties = claim.uncertaintyFlags && claim.uncertaintyFlags.length > 0;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Slide-out Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-[#090D16] border-l border-slate-800 shadow-2xl flex flex-col transform transition-transform duration-300 ease-in-out">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0C1220]/70">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
                Primary Evidence Trace
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                  {claim.projectKey}
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Traceable source provenance for AI-generated knowledge claim
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Status & Confidence Summary Banner */}
          <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">Evidence Status</span>
              <EvidenceStatusBadge status={claim.evidenceStatus} />
            </div>

            {/* Confidence indicator with synthetic disclaimer */}
            {claim.confidenceScore !== undefined && (
              <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                    <Sparkles className="h-3.5 w-3.5 text-brand-400" />
                    <span>Passage Alignment Score</span>
                  </div>
                  <span className="font-mono font-bold text-brand-300 text-xs">
                    {claim.confidenceScore}%
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={cn(
                      'h-full transition-all duration-500',
                      claim.confidenceScore >= 85
                        ? 'bg-gradient-to-r from-brand-500 to-emerald-400'
                        : claim.confidenceScore >= 60
                        ? 'bg-gradient-to-r from-amber-500 to-yellow-400'
                        : 'bg-gradient-to-r from-rose-500 to-red-400'
                    )}
                    style={{ width: `${claim.confidenceScore}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-400 flex items-center gap-1 pt-0.5">
                  <Info className="h-3 w-3 shrink-0 text-slate-500" />
                  Demonstration synthetic metric · Reflects vector embedding similarity score.
                </p>
              </div>
            )}
          </div>

          {/* Uncertainty Flags (if any) */}
          {hasUncertainties && (
            <div className="rounded-xl bg-amber-500/5 border border-amber-500/20 p-4 space-y-2.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-amber-300">
                <AlertTriangle className="h-4 w-4" />
                <span>Uncertainty & Verification Flags</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {claim.uncertaintyFlags.map((flag) => (
                  <UncertaintyBadge key={flag} type={flag} />
                ))}
              </div>
              {claim.conflictId && (
                <div className="pt-2 border-t border-amber-500/20 flex items-center justify-between">
                  <span className="text-[11px] text-amber-200">
                    Contradictory information detected with another document.
                  </span>
                  {onOpenConflict && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onOpenConflict(claim.conflictId!)}
                      leftIcon={<Flame className="h-3 w-3 text-red-400" />}
                      className="text-xs h-7 border-amber-500/40 text-amber-300 hover:bg-amber-500/10"
                    >
                      View Conflict
                    </Button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Section 1: AI-Generated Claim */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold tracking-wider text-slate-400 uppercase font-mono">
              AI-Generated Handover Claim
            </label>
            <div className="p-4 rounded-xl bg-gradient-to-r from-brand-950/40 to-slate-900 border border-brand-500/25 relative">
              <Quote className="h-5 w-5 text-brand-500/20 absolute right-3 top-3" />
              <p className="text-sm font-medium text-white leading-relaxed pr-6">
                "{claim.claimText}"
              </p>
              <div className="mt-2.5 flex items-center gap-2 text-[11px] text-slate-400">
                <span className="font-mono text-brand-400 uppercase">§ Section:</span>
                <span className="capitalize text-slate-300">{claim.section}</span>
              </div>
            </div>
          </div>

          {/* Section 2: Supporting Text Passage (Verbatim Source) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold tracking-wider text-slate-400 uppercase font-mono">
                Exact Supporting Text Passage
              </label>
              <button
                onClick={handleCopySnippet}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-brand-300 transition-colors"
              >
                {copiedSnippet ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-400" />
                    <span className="text-emerald-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    <span>Copy snippet</span>
                  </>
                )}
              </button>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 font-mono leading-relaxed whitespace-pre-wrap selection:bg-brand-500/30 selection:text-white">
              {claim.evidenceSnippet}
            </div>
          </div>

          {/* Section 3: Original Document Metadata */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold tracking-wider text-slate-400 uppercase font-mono">
              Original Document Provenance
            </label>
            <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5">
                  <div className="p-2 rounded-lg bg-slate-800 text-brand-400 shrink-0">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-white break-all">
                      {claim.sourceDocName}
                    </h4>
                    <span className="text-[11px] font-mono text-brand-300">
                      {claim.pageOrSection}
                    </span>
                  </div>
                </div>

                <Badge variant="neutral" size="sm" className="uppercase font-mono text-[10px]">
                  {claim.sourceDocType}
                </Badge>
              </div>

              <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[11px] text-slate-500">
                  Indexed into Knowledge Continuity Graph
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (onOpenDocument) {
                      onOpenDocument(claim.sourceDocId, claim.sourceDocName);
                    } else {
                      info('Document Preview', `Opening document source: ${claim.sourceDocName}`);
                    }
                  }}
                  leftIcon={<ExternalLink className="h-3 w-3" />}
                  className="text-xs h-7 px-2.5"
                >
                  Open Document
                </Button>
              </div>
            </div>
          </div>

          {/* Section 4: Reviewer Verification Status */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold tracking-wider text-slate-400 uppercase font-mono">
              Reviewer Verification Status
            </label>

            {claim.verificationStatus === 'verified' ? (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/25 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                    <Check className="h-4 w-4" />
                    <span>Verified by Authorised Reviewer</span>
                  </div>
                  <Badge variant="success" size="sm">
                    Verified
                  </Badge>
                </div>

                <div className="text-[11px] text-slate-300 space-y-1 pt-1">
                  <div className="flex items-center gap-2 text-slate-400">
                    <User className="h-3 w-3" />
                    <span>
                      Reviewed by: <strong className="text-white">{claim.verifiedBy?.name}</strong> ({claim.verifiedBy?.role || 'Lead'})
                    </span>
                  </div>
                  {claim.verifiedAt && (
                    <div className="flex items-center gap-2 text-slate-400">
                      <Calendar className="h-3 w-3" />
                      <span>Timestamp: {new Date(claim.verifiedAt).toLocaleString()}</span>
                    </div>
                  )}
                  {claim.verificationNotes && (
                    <p className="mt-2 text-xs text-emerald-200/90 italic bg-emerald-950/40 p-2.5 rounded-lg border border-emerald-500/20">
                      "{claim.verificationNotes}"
                    </p>
                  )}
                </div>
              </div>
            ) : claim.verificationStatus === 'disputed' ? (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/25 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold text-rose-400">
                    <AlertTriangle className="h-4 w-4" />
                    <span>Flagged / Disputed Claim</span>
                  </div>
                  <Badge variant="danger" size="sm">
                    Disputed
                  </Badge>
                </div>
                <p className="text-xs text-rose-200/90 bg-rose-950/40 p-2.5 rounded-lg border border-rose-500/20">
                  {claim.disputedReason || 'Marked as disputed due to lack of verifiable evidence.'}
                </p>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="text-xs font-medium text-white">Pending Human Review</div>
                  <p className="text-[11px] text-slate-400">
                    This AI claim has not yet been audited by an engineering reviewer.
                  </p>
                </div>
                <Badge variant="warning" size="sm">
                  Unverified
                </Badge>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-[#0C1220] flex items-center justify-between gap-3">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>

          <div className="flex items-center gap-2">
            {claim.verificationStatus !== 'disputed' && onFlag && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onFlag(claim)}
                leftIcon={<AlertTriangle className="h-3.5 w-3.5 text-amber-400" />}
                className="border-slate-700 text-xs"
              >
                Flag Discrepancy
              </Button>
            )}

            {claim.verificationStatus !== 'verified' && onVerify && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => onVerify(claim)}
                leftIcon={<ShieldCheck className="h-3.5 w-3.5" />}
                className="text-xs"
              >
                Verify Claim
              </Button>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

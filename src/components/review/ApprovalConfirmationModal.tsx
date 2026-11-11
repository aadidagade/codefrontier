import React, { useState } from 'react';
import {
  X,
  ShieldCheck,
  Lock,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';
import { HandoverReviewRecord } from '../../types/review';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Textarea } from '../common/Textarea';
import { useAuth } from '../../hooks/useAuth';

interface ApprovalConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  handover: HandoverReviewRecord;
  onConfirm: (notes: string) => Promise<void>;
}

export const ApprovalConfirmationModal: React.FC<ApprovalConfirmationModalProps> = ({
  isOpen,
  onClose,
  handover,
  onConfirm,
}) => {
  const { user } = useAuth();
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(
        notes.trim() || 'Formally approved and certified by authorized lead reviewer.'
      );
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-xl rounded-2xl bg-[#090D16] border border-slate-800 shadow-2xl overflow-hidden z-10 flex flex-col space-y-5 p-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-brand-400">
                  {handover.projectKey}
                </span>
                <Badge variant="success" size="sm">
                  FINAL SIGN-OFF
                </Badge>
              </div>
              <h2 className="text-base font-bold text-white tracking-tight mt-0.5">
                Certify & Approve Handover
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Handover Details Summary */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Project:</span>
            <span className="font-semibold text-white">{handover.projectName}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Transfer:</span>
            <span className="text-slate-200">
              <strong className="text-white">{handover.outgoingMember.name}</strong> &rarr;{' '}
              <strong className="text-brand-300">{handover.incomingMember.name}</strong>
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Certifying Lead:</span>
            <span className="font-semibold text-emerald-400">
              {user?.name || 'Elena Rostova'} ({user?.role || 'Authorized Lead'})
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Evidence Alignment:</span>
            <span className="font-mono font-bold text-brand-300">
              {handover.evidenceScore}% Verified
            </span>
          </div>
        </div>

        {/* Lock Warning Notice */}
        <div className="p-4 rounded-xl bg-brand-500/10 border border-brand-500/25 flex items-start gap-3 text-xs">
          <Lock className="h-5 w-5 text-brand-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold text-white">Immutable Certified Ledger Notice</h4>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              Upon final approval, <strong>Version {handover.version}</strong> will be locked against ordinary edits to preserve compliance and audit integrity. If future operational changes occur, an authorized lead can fork a new revision (e.g. v1.1).
            </p>
          </div>
        </div>

        {/* Optional Sign-Off Notes */}
        <div className="space-y-1.5">
          <Textarea
            label="Approval Notes & Sign-Off Memo (Optional)"
            placeholder="e.g. Conducted architectural review with outgoing staff lead; confirmed all WebAuthn failover gotchas and verified 3:00 AM on-call runbook."
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>

        {/* Actions */}
        <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>

          <Button
            variant="primary"
            size="md"
            onClick={handleApprove}
            isLoading={isSubmitting}
            leftIcon={<ShieldCheck className="h-4 w-4" />}
            className="text-xs font-semibold"
          >
            Approve & Share Handover
          </Button>
        </div>
      </div>
    </div>
  );
};

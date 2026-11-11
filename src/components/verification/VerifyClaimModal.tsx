import React, { useState } from 'react';
import { X, ShieldCheck, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { VerificationClaim } from '../../types/verification';
import { Button } from '../common/Button';
import { Textarea } from '../common/Textarea';
import { useAuth } from '../../hooks/useAuth';

interface VerifyClaimModalProps {
  isOpen: boolean;
  onClose: () => void;
  claim: VerificationClaim | null;
  mode: 'verify' | 'flag';
  onSubmit: (claimId: string, notes: string) => Promise<void>;
}

export const VerifyClaimModal: React.FC<VerifyClaimModalProps> = ({
  isOpen,
  onClose,
  claim,
  mode,
  onSubmit,
}) => {
  const { user } = useAuth();
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !claim) return null;

  const isVerify = mode === 'verify';

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await onSubmit(
        claim.id,
        notes.trim() || (isVerify ? 'Verified against source evidence by human lead.' : 'Flagged for reviewer clarification.')
      );
      setNotes('');
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-lg rounded-2xl bg-[#090D16] border border-slate-800 shadow-2xl overflow-hidden z-10 space-y-5 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div
              className={`h-9 w-9 rounded-xl flex items-center justify-center ${
                isVerify
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
              }`}
            >
              {isVerify ? <ShieldCheck className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">
                {isVerify ? 'Human Verification of Claim' : 'Flag Claim Discrepancy'}
              </h3>
              <p className="text-[11px] text-slate-400">
                {claim.projectKey} · {claim.sourceDocName}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Claim Preview */}
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs space-y-1">
          <span className="text-[10px] uppercase font-mono text-slate-500">Claim to {isVerify ? 'Verify' : 'Flag'}:</span>
          <p className="text-slate-200 font-medium">"{claim.claimText}"</p>
        </div>

        {/* Notes Input */}
        <div className="space-y-1.5">
          <Textarea
            label={isVerify ? 'Verification Note (Optional)' : 'Discrepancy / Uncertainty Reason *'}
            placeholder={
              isVerify
                ? 'e.g. Cross-checked with production code and confirmed configuration values.'
                : 'e.g. Primary document mentions a different TTL and this lacks verification in git commit history.'
            }
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            autoFocus
          />
        </div>

        {/* Reviewer signature info */}
        <div className="text-[11px] text-slate-400 flex items-center justify-between border-t border-slate-800 pt-3">
          <span>Signed by: <strong className="text-white">{user?.name || 'Elena Rostova'}</strong></span>
          <span className="font-mono text-slate-500">Audit trail enabled</span>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2.5 pt-2">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant={isVerify ? 'primary' : 'danger'}
            size="sm"
            onClick={handleSubmit}
            isLoading={isSubmitting}
            leftIcon={isVerify ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
          >
            {isVerify ? 'Confirm Verification' : 'Submit Flag'}
          </Button>
        </div>
      </div>
    </div>
  );
};

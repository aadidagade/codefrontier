import React, { useState } from 'react';
import { X, AlertTriangle, XCircle, RotateCcw } from 'lucide-react';
import { HandoverReviewRecord } from '../../types/review';
import { Button } from '../common/Button';
import { Textarea } from '../common/Textarea';
import { useToast } from '../../hooks/useToast';

interface RequestChangesModalProps {
  isOpen: boolean;
  onClose: () => void;
  handover: HandoverReviewRecord;
  mode: 'changes' | 'reject';
  onSubmit: (reason: string) => Promise<void>;
}

export const RequestChangesModal: React.FC<RequestChangesModalProps> = ({
  isOpen,
  onClose,
  handover,
  mode,
  onSubmit,
}) => {
  const { error } = useToast();
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const isReject = mode === 'reject';

  const handleSubmit = async () => {
    if (!feedback.trim()) {
      error(
        isReject ? 'Rejection Reason Required' : 'Feedback Notes Required',
        'Please explain what needs to be changed or why the draft was rejected.'
      );
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(feedback.trim());
      setFeedback('');
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
      <div className="relative w-full max-w-lg rounded-2xl bg-[#090D16] border border-slate-800 shadow-2xl overflow-hidden z-10 flex flex-col space-y-4 p-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div
              className={`h-9 w-9 rounded-xl flex items-center justify-center ${
                isReject
                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
              }`}
            >
              {isReject ? <XCircle className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">
                {isReject ? 'Reject Handover Draft' : 'Request Changes on Handover'}
              </h3>
              <p className="text-[11px] text-slate-400">
                {handover.projectKey} · {handover.projectName}
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

        <div className="text-xs text-slate-300 leading-relaxed">
          {isReject ? (
            <p>
              Rejecting this handover draft will notify the outgoing lead <strong>{handover.outgoingMember.name}</strong> to regenerate or substantially revise the project documents.
            </p>
          ) : (
            <p>
              Requesting changes will flag the draft with your feedback notes so <strong>{handover.outgoingMember.name}</strong> can address missing Gotchas or update decisions before re-submitting for approval.
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Textarea
            label={isReject ? 'Rejection Reason *' : 'Detailed Changes Requested *'}
            placeholder={
              isReject
                ? 'e.g. Underlying architecture references outdated pre-migration repositories. Regenerate handover using current Q4 documents.'
                : 'e.g. The 3:00 AM banking failover section is missing the Barclays SFTP retry playbook. Please document the sentinel override procedure.'
            }
            rows={4}
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            autoFocus
          />
        </div>

        <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>

          <Button
            variant={isReject ? 'danger' : 'primary'}
            size="sm"
            onClick={handleSubmit}
            isLoading={isSubmitting}
            leftIcon={isReject ? <XCircle className="h-4 w-4" /> : <RotateCcw className="h-4 w-4" />}
          >
            {isReject ? 'Reject Handover' : 'Submit Changes Request'}
          </Button>
        </div>
      </div>
    </div>
  );
};

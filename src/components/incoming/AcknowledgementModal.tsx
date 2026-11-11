import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  User,
} from 'lucide-react';
import { IncomingHandoverPackage } from '../../types/incoming';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Textarea } from '../common/Textarea';
import { useAuth } from '../../hooks/useAuth';

interface AcknowledgementModalProps {
  isOpen: boolean;
  onClose: () => void;
  handoverPackage: IncomingHandoverPackage;
  onConfirm: (comment: string) => Promise<void>;
}

export const AcknowledgementModal: React.FC<AcknowledgementModalProps> = ({
  isOpen,
  onClose,
  handoverPackage,
  onConfirm,
}) => {
  const { user } = useAuth();
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleAcknowledge = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(
        comment.trim() ||
          'Formally acknowledged handover receipt. Reviewed project architecture, decisions, and on-call escalation procedures.'
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
      <div className="relative w-full max-w-lg rounded-2xl bg-[#090D16] border border-slate-800 shadow-2xl overflow-hidden z-10 flex flex-col space-y-4 p-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-brand-400">
                  {handoverPackage.projectKey}
                </span>
                <Badge variant="success" size="sm">
                  INCOMING ACKNOWLEDGEMENT
                </Badge>
              </div>
              <h3 className="text-base font-bold text-white tracking-tight mt-0.5">
                Acknowledge Handover Receipt
              </h3>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Transfer Confirmation Summary */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Project:</span>
            <span className="font-semibold text-white">{handoverPackage.projectName}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Outgoing Member:</span>
            <span className="text-slate-200">{handoverPackage.outgoingMember.name}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Project Lead:</span>
            <span className="text-slate-200">{handoverPackage.projectLead.name}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Approved Date:</span>
            <span className="font-mono text-slate-300">
              {new Date(handoverPackage.approvedDate).toLocaleDateString()}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Readiness Score:</span>
            <span className="font-mono text-emerald-400 font-bold">
              {handoverPackage.introduction.healthScore}% Certified
            </span>
          </div>
        </div>

        {/* Activity Feed Notification Notice */}
        <div className="p-3 rounded-xl bg-brand-500/10 border border-brand-500/20 text-xs text-brand-200 leading-relaxed">
          <p>
            Acknowledging confirms you have reviewed the architecture decisions, tasks, blockers, and on-call escalation duties. An immutable receipt timestamp will be recorded and <strong>{handoverPackage.projectLead.name}</strong> will be notified in the project activity feed.
          </p>
        </div>

        {/* Optional Comment Input */}
        <div className="space-y-1.5">
          <Textarea
            label="Acknowledgement Note / Initial Readiness Comment (Optional)"
            placeholder="e.g. Reviewed passkey migration architecture and verified staging DB connection. Scheduled initial on-call shadow rotation with Sarah."
            rows={3}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
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
            onClick={handleAcknowledge}
            isLoading={isSubmitting}
            leftIcon={<CheckCircle2 className="h-4 w-4" />}
            className="text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
          >
            Confirm & Acknowledge Receipt
          </Button>
        </div>
      </div>
    </div>
  );
};

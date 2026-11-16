import React, { useState } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  Clock,
  User,
  AlertCircle,
  X,
  FileText,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Textarea } from '../common/Textarea';
import { SharedHandoverItem } from '../../types/handover';

interface HandoverAcknowledgementModalProps {
  isOpen: boolean;
  onClose: () => void;
  handover: SharedHandoverItem | null;
  onConfirm: (handoverId: string, notes: string) => Promise<void>;
  isSubmitting?: boolean;
}

export const HandoverAcknowledgementModal: React.FC<HandoverAcknowledgementModalProps> = ({
  isOpen,
  onClose,
  handover,
  onConfirm,
  isSubmitting = false,
}) => {
  const [checklistConfirmed, setChecklistConfirmed] = useState(false);
  const [notes, setNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen || !handover) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!checklistConfirmed) {
      setErrorMsg('You must check the confirmation box to acknowledge handover receipt.');
      return;
    }
    setErrorMsg(null);
    await onConfirm(handover.id, notes);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg max-h-[90vh] flex flex-col bg-[#0F172A] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-900/60 shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Acknowledge Handover Receipt
              </h3>
              <p className="text-xs text-slate-400">
                Confirm understanding and formally accept knowledge continuity responsibilities
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
          {/* Target Handover Card */}
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-brand-400">
                {handover.project_title || 'Project Transfer'}
              </span>
              <Badge variant="accent" size="sm">
                {handover.version || 'v1.0'}
              </Badge>
            </div>
            <h4 className="text-sm font-semibold text-white">
              {handover.title}
            </h4>
            <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
              <span>Status: <strong className="text-emerald-400 font-mono">APPROVED</strong></span>
              <span>Pending Tasks: <strong className="text-white">{handover.pending_tasks_count}</strong></span>
            </div>
          </div>

          {/* Checklist Confirmation */}
          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-2">
            <label className="flex items-start gap-3 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={checklistConfirmed}
                onChange={(e) => {
                  setChecklistConfirmed(e.target.checked);
                  if (e.target.checked) setErrorMsg(null);
                }}
                className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-slate-900 text-emerald-600 focus:ring-emerald-500"
              />
              <span className="text-xs text-slate-200 leading-relaxed">
                I confirm that I have accessed the approved handover brief, reviewed the technical architecture decisions, identified open blockers and conflicts, and accept ownership of assigned continuation tasks.
              </span>
            </label>
          </div>

          {errorMsg && (
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/25 text-rose-300 text-xs">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Acknowledgement Notes */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              Receipt Notes or Initial Observations (Optional)
            </label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Reviewed WebAuthn architecture; starting staging cutover rehearsals this sprint..."
              rows={3}
              className="text-xs bg-slate-900 border-slate-800 focus:border-brand-500 text-slate-200"
            />
          </div>

          {/* Audit Guarantee Banner */}
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>
              Audit guarantee: Acknowledgement is recorded server-side with user ID and UTC timestamp.
            </span>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-xs text-slate-400"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              leftIcon={<CheckCircle2 className="h-4 w-4" />}
              className="text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              Confirm & Acknowledge Receipt
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { GitBranch, X, Plus, ShieldCheck } from 'lucide-react';
import { Button } from '../common/Button';
import { Textarea } from '../common/Textarea';

interface CreateVersionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (description: string) => Promise<void>;
  currentVersionNumber: string;
}

export const CreateVersionModal: React.FC<CreateVersionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  currentVersionNumber,
}) => {
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;
    setIsSubmitting(true);
    try {
      await onSubmit(description.trim());
      setDescription('');
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-md max-h-[90vh] flex flex-col bg-[#0F172A] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60 shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
              <GitBranch className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Create Version Snapshot</h2>
              <p className="text-xs text-slate-400">
                Capture immutable baseline from current handover
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">Current Base Version:</span>
            <span className="font-mono font-bold text-brand-400">{currentVersionNumber}</span>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              Revision Summary & Changes Description <span className="text-rose-400">*</span>
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Sprint 42 updates: Adjusted partition split schedule and added Redis Sentinel failover test runbooks."
              rows={3}
              required
              className="text-xs bg-slate-900 border-slate-800 focus:border-brand-500 text-slate-200"
            />
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>Immutable guarantee: Snapshot will be permanently archived and tamper-proof.</span>
          </div>

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
              leftIcon={<Plus className="h-4 w-4" />}
              className="text-xs font-semibold"
            >
              Archive Snapshot
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

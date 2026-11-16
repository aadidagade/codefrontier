import React, { useState } from 'react';
import { RotateCcw, AlertTriangle, ShieldCheck, Clock, User, Check, X } from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Textarea } from '../common/Textarea';
import { HandoverVersionItem } from '../../types/handover';

interface RestoreConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void>;
  version: HandoverVersionItem | null;
  currentLatestVersionNumber?: string;
  isRestoring?: boolean;
}

export const RestoreConfirmationModal: React.FC<RestoreConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  version,
  currentLatestVersionNumber = 'v1.0',
  isRestoring = false,
}) => {
  const [reason, setReason] = useState(
    version ? `Restored from historical snapshot ${version.version_number}` : ''
  );

  if (!isOpen || !version) return null;

  const handleConfirm = async () => {
    await onConfirm(reason.trim() || `Restored from snapshot ${version.version_number}`);
  };

  const formattedDate = version.created_at
    ? new Date(version.created_at).toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    : 'Unknown Date';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg max-h-[90vh] flex flex-col bg-[#0F172A] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50 shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center">
              <RotateCcw className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Restore Previous Version</h2>
              <p className="text-xs text-slate-400">
                Create new revision from baseline {version.version_number}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isRestoring}
            className="text-slate-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4 overflow-y-auto flex-1">
          {/* Historical Immutability Guarantee Callout */}
          <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 space-y-2">
            <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs">
              <ShieldCheck className="h-4 w-4 shrink-0 text-amber-400" />
              <span>Immutable Historical Guarantee</span>
            </div>
            <p className="text-xs text-amber-200/90 leading-relaxed">
              Restoring version <strong className="font-mono text-white">{version.version_number}</strong> will create a <strong>new draft revision</strong> based on this snapshot.
              Historical versions, approvals, and compliance audit logs remain permanently preserved and will <strong>never be overwritten or deleted</strong>.
            </p>
          </div>

          {/* Selected Version Metadata Card */}
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-bold text-brand-400">
                  {version.version_number}
                </span>
                <Badge
                  variant={
                    version.approval_status === 'APPROVED'
                      ? 'success'
                      : version.approval_status === 'IN_REVIEW'
                      ? 'accent'
                      : 'warning'
                  }
                  size="sm"
                >
                  {version.approval_status}
                </Badge>
              </div>
              <span className="text-[11px] font-mono text-slate-500">
                Target Snapshot
              </span>
            </div>

            {version.version_description && (
              <p className="text-xs text-slate-300 italic bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                "{version.version_description}"
              </p>
            )}

            <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 pt-1 border-t border-slate-800/80">
              <div className="flex items-center gap-1.5">
                <User className="h-3.5 w-3.5 text-slate-500" />
                <span className="truncate">{version.creator_name || 'System / Outgoing'}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-slate-500" />
                <span>{formattedDate}</span>
              </div>
            </div>
          </div>

          {/* Reason Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              Restoration Reason & Change Context <span className="text-rose-400">*</span>
            </label>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Reverting unapproved section changes back to verified baseline v1.0..."
              rows={3}
              className="text-xs bg-slate-900 border-slate-800 focus:border-brand-500 text-slate-200"
            />
            <p className="text-[11px] text-slate-500">
              This note will be recorded in the immutable compliance audit trail and visible to project leads.
            </p>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-800 bg-slate-900/40">
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={isRestoring}
            className="text-xs text-slate-400"
          >
            Cancel
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleConfirm}
            isLoading={isRestoring}
            leftIcon={<RotateCcw className="h-4 w-4" />}
            className="text-xs font-semibold text-amber-300 border-amber-500/50 hover:bg-amber-500/10"
          >
            Restore as New Revision
          </Button>
        </div>
      </div>
    </div>
  );
};

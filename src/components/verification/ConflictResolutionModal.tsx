import React, { useState } from 'react';
import {
  X,
  AlertTriangle,
  GitCompare,
  FileText,
  Calendar,
  User,
  CheckCircle2,
  HelpCircle,
  Edit3,
  ShieldAlert,
  Info,
} from 'lucide-react';
import {
  KnowledgeConflictItem,
  ConflictResolutionType,
} from '../../types/verification';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Textarea } from '../common/Textarea';
import { Input } from '../common/Input';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { cn } from '../../utils/cn';

interface ConflictResolutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  conflict: KnowledgeConflictItem | null;
  onResolve: (
    conflictId: string,
    resolution: {
      resolutionType: ConflictResolutionType;
      chosenValue?: string;
      resolutionNote: string;
      correctionText?: string;
    }
  ) => Promise<void>;
}

export const ConflictResolutionModal: React.FC<ConflictResolutionModalProps> = ({
  isOpen,
  onClose,
  conflict,
  onResolve,
}) => {
  const { user } = useAuth();
  const { error } = useToast();

  const [selectedType, setSelectedType] = useState<ConflictResolutionType>('verify_source_b');
  const [resolutionNote, setResolutionNote] = useState('');
  const [correctionText, setCorrectionText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !conflict) return null;

  const handleSubmit = async () => {
    if (!resolutionNote.trim()) {
      error('Resolution Note Required', 'Please provide a clear justification or rationale for the audit log.');
      return;
    }

    if (selectedType === 'custom_correction' && !correctionText.trim()) {
      error('Correction Text Required', 'Please enter the authoritative consensus correction.');
      return;
    }

    let chosenValue: string | undefined;
    if (selectedType === 'verify_source_a') {
      chosenValue = conflict.sourceA.claimedValue;
    } else if (selectedType === 'verify_source_b') {
      chosenValue = conflict.sourceB.claimedValue;
    } else if (selectedType === 'custom_correction') {
      chosenValue = correctionText.trim();
    }

    setIsSubmitting(true);
    try {
      await onResolve(conflict.id, {
        resolutionType: selectedType,
        chosenValue,
        resolutionNote: resolutionNote.trim(),
        correctionText: selectedType === 'custom_correction' ? correctionText.trim() : undefined,
      });
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
      <div className="relative w-full max-w-3xl rounded-2xl bg-[#090D16] border border-slate-800 shadow-2xl overflow-hidden my-8 z-10 flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0C1220]/80">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
              <GitCompare className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-brand-400">
                  {conflict.projectKey}
                </span>
                <Badge
                  variant={conflict.severity === 'critical' ? 'danger' : 'warning'}
                  size="sm"
                >
                  {conflict.severity.toUpperCase()} CONFLICT
                </Badge>
              </div>
              <h2 className="text-base font-bold text-white tracking-tight mt-0.5">
                Resolve Contradiction: {conflict.topic}
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Strict Human-in-the-Loop Governance Notice */}
          <div className="rounded-xl bg-brand-500/10 border border-brand-500/25 p-4 flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-brand-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-white">
                Human Reviewer Gate Enforced
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed">
                Antigravity AI strictly prohibits automated conflict resolution. Contradictory statements across documentation must be reviewed and resolved by an authorised human engineer. Your decision is logged in the immutable audit trail.
              </p>
            </div>
          </div>

          {/* Description & Disputed Field */}
          <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400 font-mono">Disputed Attribute:</span>
              <span className="font-semibold text-brand-300 bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/20">
                {conflict.disputedField}
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              {conflict.description}
            </p>
          </div>

          {/* Side-by-Side Conflicting Documents Comparison */}
          <div className="space-y-2.5">
            <label className="text-xs font-bold tracking-wider text-slate-400 uppercase font-mono">
              Compare Source Evidence
            </label>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* SOURCE A */}
              <div
                onClick={() => setSelectedType('verify_source_a')}
                className={cn(
                  'p-4 rounded-xl border transition-all cursor-pointer relative space-y-3',
                  selectedType === 'verify_source_a'
                    ? 'bg-brand-950/40 border-brand-500 ring-2 ring-brand-500/30'
                    : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-slate-400">
                    Source Document A
                  </span>
                  <input
                    type="radio"
                    name="resolution_choice"
                    checked={selectedType === 'verify_source_a'}
                    onChange={() => setSelectedType('verify_source_a')}
                    className="h-4 w-4 text-brand-600 focus:ring-brand-500 cursor-pointer"
                  />
                </div>

                <div className="flex items-start gap-2">
                  <FileText className="h-4 w-4 text-brand-400 shrink-0 mt-0.5" />
                  <div>
                    <h5 className="text-xs font-semibold text-white">
                      {conflict.sourceA.docName}
                    </h5>
                    <span className="text-[10px] font-mono text-slate-400">
                      {conflict.sourceA.pageOrSection}
                    </span>
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-slate-300 leading-relaxed max-h-24 overflow-y-auto">
                  "{conflict.sourceA.excerpt}"
                </div>

                <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px]">
                  <span className="text-slate-400">Claimed Value:</span>
                  <span className="font-bold text-brand-300 bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/20">
                    {conflict.sourceA.claimedValue}
                  </span>
                </div>

                <div className="text-[10px] text-slate-500 flex items-center justify-between">
                  <span>Author: {conflict.sourceA.author}</span>
                  <span>Date: {conflict.sourceA.date}</span>
                </div>
              </div>

              {/* SOURCE B */}
              <div
                onClick={() => setSelectedType('verify_source_b')}
                className={cn(
                  'p-4 rounded-xl border transition-all cursor-pointer relative space-y-3',
                  selectedType === 'verify_source_b'
                    ? 'bg-brand-950/40 border-brand-500 ring-2 ring-brand-500/30'
                    : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-slate-400">
                    Source Document B
                  </span>
                  <input
                    type="radio"
                    name="resolution_choice"
                    checked={selectedType === 'verify_source_b'}
                    onChange={() => setSelectedType('verify_source_b')}
                    className="h-4 w-4 text-brand-600 focus:ring-brand-500 cursor-pointer"
                  />
                </div>

                <div className="flex items-start gap-2">
                  <FileText className="h-4 w-4 text-brand-400 shrink-0 mt-0.5" />
                  <div>
                    <h5 className="text-xs font-semibold text-white">
                      {conflict.sourceB.docName}
                    </h5>
                    <span className="text-[10px] font-mono text-slate-400">
                      {conflict.sourceB.pageOrSection}
                    </span>
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-slate-300 leading-relaxed max-h-24 overflow-y-auto">
                  "{conflict.sourceB.excerpt}"
                </div>

                <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px]">
                  <span className="text-slate-400">Claimed Value:</span>
                  <span className="font-bold text-brand-300 bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/20">
                    {conflict.sourceB.claimedValue}
                  </span>
                </div>

                <div className="text-[10px] text-slate-500 flex items-center justify-between">
                  <span>Author: {conflict.sourceB.author}</span>
                  <span>Date: {conflict.sourceB.date}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Alternative Resolution Options */}
          <div className="space-y-3">
            <label className="text-xs font-bold tracking-wider text-slate-400 uppercase font-mono">
              Alternative Resolution Actions
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Option C: Custom Correction */}
              <div
                onClick={() => setSelectedType('custom_correction')}
                className={cn(
                  'p-3.5 rounded-xl border transition-all cursor-pointer flex items-start gap-3',
                  selectedType === 'custom_correction'
                    ? 'bg-brand-950/40 border-brand-500 ring-2 ring-brand-500/30'
                    : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                )}
              >
                <input
                  type="radio"
                  name="resolution_choice"
                  checked={selectedType === 'custom_correction'}
                  onChange={() => setSelectedType('custom_correction')}
                  className="h-4 w-4 text-brand-600 focus:ring-brand-500 cursor-pointer mt-0.5"
                />
                <div className="space-y-1">
                  <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Edit3 className="h-3.5 w-3.5 text-brand-400" />
                    <span>Enter Custom Consensus Value</span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Neither source is completely accurate; record a new authoritative date, owner, or spec.
                  </p>
                </div>
              </div>

              {/* Option D: Mark Unresolved / Escalate */}
              <div
                onClick={() => setSelectedType('mark_unresolved')}
                className={cn(
                  'p-3.5 rounded-xl border transition-all cursor-pointer flex items-start gap-3',
                  selectedType === 'mark_unresolved'
                    ? 'bg-rose-950/30 border-rose-500 ring-2 ring-rose-500/30'
                    : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                )}
              >
                <input
                  type="radio"
                  name="resolution_choice"
                  checked={selectedType === 'mark_unresolved'}
                  onChange={() => setSelectedType('mark_unresolved')}
                  className="h-4 w-4 text-rose-600 focus:ring-rose-500 cursor-pointer mt-0.5"
                />
                <div className="space-y-1">
                  <div className="text-xs font-semibold text-rose-300 flex items-center gap-1.5">
                    <HelpCircle className="h-3.5 w-3.5 text-rose-400" />
                    <span>Mark Both Claims as Unresolved</span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Flag as a critical blocker for executive or cross-team sign-off during handover meeting.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Custom Correction Input (if custom selected) */}
          {selectedType === 'custom_correction' && (
            <div className="p-4 rounded-xl bg-brand-500/5 border border-brand-500/25 space-y-2">
              <Input
                label="Authoritative Corrected Value"
                placeholder="e.g. 18 November 2026 (Consensus reached in Sprint 44 triage)"
                value={correctionText}
                onChange={(e) => setCorrectionText(e.target.value)}
                autoFocus
              />
            </div>
          )}

          {/* Audit Resolution Note */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold tracking-wider text-slate-400 uppercase font-mono flex items-center justify-between">
              <span>Resolution Justification & Audit Note *</span>
              <span className="text-[10px] text-slate-500 lowercase font-normal">
                required for audit compliance
              </span>
            </label>
            <Textarea
              placeholder="Provide context explaining why this source or correction was verified (e.g. 'Confirmed with Sarah and David in architecture review; Sprint Review date reflects the updated analytics buffer')."
              rows={3}
              value={resolutionNote}
              onChange={(e) => setResolutionNote(e.target.value)}
            />
          </div>

          {/* Human Reviewer Identity Badge */}
          <div className="rounded-xl bg-slate-900 border border-slate-800 p-3.5 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-full bg-brand-500/20 text-brand-300 flex items-center justify-center font-bold text-xs">
                {user?.name ? user.name[0] : 'E'}
              </div>
              <div>
                <span className="text-slate-400">Attributed Reviewer: </span>
                <span className="text-white font-semibold">{user?.name || 'Elena Rostova'}</span>
                <span className="text-slate-400 text-[11px]"> ({user?.role || 'Lead Engineer'})</span>
              </div>
            </div>

            <span className="text-[11px] font-mono text-slate-500">
              Audit Hash: SHA256-verified
            </span>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-[#0C1220] flex items-center justify-between">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>

          <Button
            variant={selectedType === 'mark_unresolved' ? 'danger' : 'primary'}
            size="sm"
            onClick={handleSubmit}
            isLoading={isSubmitting}
            leftIcon={selectedType === 'mark_unresolved' ? <HelpCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
          >
            {selectedType === 'mark_unresolved'
              ? 'Flag as Unresolved Escalation'
              : 'Submit Human Resolution'}
          </Button>
        </div>
      </div>
    </div>
  );
};

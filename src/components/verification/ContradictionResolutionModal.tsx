import React, { useState } from 'react';
import {
  X,
  GitCompare,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Edit3,
  HelpCircle,
  Quote,
  ShieldCheck,
  Check,
  Ban,
} from 'lucide-react';
import { ConflictResponse, ConflictResolveRequest } from '../../types/verification';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { useToast } from '../../hooks/useToast';
import { verificationService } from '../../services/verificationService';
import { cn } from '../../utils/cn';

interface ContradictionResolutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  conflict: ConflictResponse | null;
  onSuccess: () => void;
}

export const ContradictionResolutionModal: React.FC<ContradictionResolutionModalProps> = ({
  isOpen,
  onClose,
  conflict,
  onSuccess,
}) => {
  const { success, error, info } = useToast();

  const [chosenSource, setChosenSource] = useState<'source_a' | 'source_b' | 'custom'>('source_a');
  const [customValue, setCustomValue] = useState('');
  const [explanation, setExplanation] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen || !conflict) return null;

  const statementA = conflict.conflicting_statement_a || conflict.statement_a || '';
  const statementB = conflict.conflicting_statement_b || conflict.statement_b || '';
  const docA = conflict.source_document_a || conflict.source_document_a_name || 'Document A';
  const docB = conflict.source_document_b || conflict.source_document_b_name || 'Document B';
  const excerptA = conflict.source_excerpt_a || conflict.source_a?.excerpt || '';
  const excerptB = conflict.source_excerpt_b || conflict.source_b?.excerpt || '';

  const handleSubmit = async (targetStatus: 'Resolved' | 'Dismissed') => {
    if (!explanation.trim()) {
      error('Resolution Explanation Required', 'Please enter a resolution explanation justifying the decision.');
      return;
    }

    if (targetStatus === 'Resolved' && chosenSource === 'custom' && !customValue.trim()) {
      error('Custom Statement Required', 'Please provide the authoritative consensus text.');
      return;
    }

    let authoritativeValue = '';
    if (chosenSource === 'source_a') {
      authoritativeValue = statementA;
    } else if (chosenSource === 'source_b') {
      authoritativeValue = statementB;
    } else {
      authoritativeValue = customValue.trim();
    }

    setSubmitting(true);
    try {
      const payload: ConflictResolveRequest = {
        chosen_source: chosenSource,
        authoritative_value: authoritativeValue,
        chosen_value: authoritativeValue,
        resolution_notes: explanation.trim(),
        explanation: explanation.trim(),
        status: targetStatus,
      };

      await verificationService.resolveConflict(conflict.id, payload);
      success(
        targetStatus === 'Resolved' ? 'Contradiction Resolved' : 'Contradiction Dismissed',
        `Decision saved for conflict #${conflict.id.slice(0, 8)}.`
      );
      onSuccess();
      onClose();
    } catch (err: any) {
      error('Resolution Failed', err.message || 'Failed to save conflict decision.');
    } finally {
      setSubmitting(false);
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
      <div className="relative w-full max-w-2xl rounded-2xl bg-[#0B0F19] border border-slate-800 shadow-2xl overflow-hidden z-10 flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-brand-500/10 text-brand-400 border border-brand-500/20">
              <GitCompare className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-base">Human Conflict Arbitration</h3>
                <Badge variant="neutral" size="sm" className="font-mono text-[10px] uppercase">
                  {conflict.conflict_category}
                </Badge>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Select the authoritative statement and provide a mandatory resolution explanation.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 text-xs sm:text-sm">
          {/* Conflict Description */}
          <div className="p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/20 text-slate-200">
            <span className="font-semibold text-amber-400 block text-[11px] uppercase tracking-wider mb-1">
              Contradiction Summary
            </span>
            <p className="text-xs text-slate-300 leading-relaxed">{conflict.description}</p>
          </div>

          {/* Statement Selection */}
          <div className="space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">
              1. Select Authoritative Statement
            </span>

            {/* Option A: Source A */}
            <div
              onClick={() => setChosenSource('source_a')}
              className={cn(
                'p-4 rounded-xl border transition-all cursor-pointer space-y-2',
                chosenSource === 'source_a'
                  ? 'bg-brand-500/10 border-brand-500 shadow-sm'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="authoritative"
                    checked={chosenSource === 'source_a'}
                    onChange={() => setChosenSource('source_a')}
                    className="text-brand-500 focus:ring-brand-500"
                  />
                  <span className="font-semibold text-white text-xs">Statement A</span>
                </div>
                <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1 truncate max-w-xs">
                  <FileText className="h-3 w-3 text-brand-400 shrink-0" />
                  <span className="truncate">{docA}</span>
                </span>
              </div>
              <p className="font-medium text-slate-200 text-xs sm:text-sm pl-5">
                "{statementA}"
              </p>
              {excerptA && (
                <div className="pl-5 text-[11px] italic text-slate-400 border-l border-slate-700 ml-5 mt-1">
                  Excerpt: "{excerptA}"
                </div>
              )}
            </div>

            {/* Option B: Source B */}
            <div
              onClick={() => setChosenSource('source_b')}
              className={cn(
                'p-4 rounded-xl border transition-all cursor-pointer space-y-2',
                chosenSource === 'source_b'
                  ? 'bg-brand-500/10 border-brand-500 shadow-sm'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="authoritative"
                    checked={chosenSource === 'source_b'}
                    onChange={() => setChosenSource('source_b')}
                    className="text-brand-500 focus:ring-brand-500"
                  />
                  <span className="font-semibold text-white text-xs">Statement B</span>
                </div>
                <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1 truncate max-w-xs">
                  <FileText className="h-3 w-3 text-purple-400 shrink-0" />
                  <span className="truncate">{docB}</span>
                </span>
              </div>
              <p className="font-medium text-slate-200 text-xs sm:text-sm pl-5">
                "{statementB}"
              </p>
              {excerptB && (
                <div className="pl-5 text-[11px] italic text-slate-400 border-l border-slate-700 ml-5 mt-1">
                  Excerpt: "{excerptB}"
                </div>
              )}
            </div>

            {/* Option C: Custom Correction */}
            <div
              onClick={() => setChosenSource('custom')}
              className={cn(
                'p-4 rounded-xl border transition-all cursor-pointer space-y-2',
                chosenSource === 'custom'
                  ? 'bg-brand-500/10 border-brand-500 shadow-sm'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              )}
            >
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  name="authoritative"
                  checked={chosenSource === 'custom'}
                  onChange={() => setChosenSource('custom')}
                  className="text-brand-500 focus:ring-brand-500"
                />
                <span className="font-semibold text-white text-xs">
                  Custom Consensus Correction
                </span>
                <span className="text-[10px] text-slate-400">(Neither statement is solely correct)</span>
              </div>

              {chosenSource === 'custom' && (
                <div className="pl-5 pt-2">
                  <textarea
                    rows={2}
                    value={customValue}
                    onChange={(e) => setCustomValue(e.target.value)}
                    placeholder="Enter the authoritative synthesized statement decided by the reviewer..."
                    className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-brand-500"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Resolution Explanation */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">
              2. Resolution Explanation (Mandatory)
            </label>
            <p className="text-[11px] text-slate-500">
              Provide justification for the audit trail (e.g. "Sprint review v4 supersedes architecture draft per team consensus").
            </p>
            <textarea
              rows={3}
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              placeholder="Explain why this statement is authoritative and how the discrepancy was arbitrated..."
              className="w-full p-3 rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-900/40">
          <Button variant="outline" size="sm" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSubmit('Dismissed')}
              isLoading={submitting}
              className="text-slate-400 hover:text-white border-slate-700 hover:bg-slate-800 flex items-center gap-1.5"
            >
              <Ban className="h-3.5 w-3.5" />
              <span>Mark as Dismissed</span>
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={() => handleSubmit('Resolved')}
              isLoading={submitting}
              className="bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5"
            >
              <Check className="h-3.5 w-3.5" />
              <span>Mark as Resolved</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

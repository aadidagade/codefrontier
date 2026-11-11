import React, { useState } from 'react';
import { X, Save, Edit3, ShieldAlert } from 'lucide-react';
import { SectionKey, HandoverReviewRecord } from '../../types/review';
import { Button } from '../common/Button';
import { Textarea } from '../common/Textarea';
import { Input } from '../common/Input';
import { useToast } from '../../hooks/useToast';

interface SectionContentEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  handover: HandoverReviewRecord;
  sectionKey: SectionKey;
  onSave: (sectionKey: SectionKey, newContent: any) => Promise<void>;
}

export const SectionContentEditorModal: React.FC<SectionContentEditorModalProps> = ({
  isOpen,
  onClose,
  handover,
  sectionKey,
  onSave,
}) => {
  const { success } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Editable fields based on section
  const [overviewPurpose, setOverviewPurpose] = useState(
    handover.content.overview?.purpose || ''
  );
  const [overviewStatus, setOverviewStatus] = useState(
    handover.content.overview?.currentStatus || ''
  );
  const [singleText, setSingleText] = useState(
    sectionKey === 'overview'
      ? ''
      : JSON.stringify(handover.content[sectionKey as keyof typeof handover.content] || [], null, 2)
  );

  if (!isOpen) return null;

  const handleSave = async () => {
    setIsSubmitting(true);
    try {
      if (sectionKey === 'overview') {
        await onSave(sectionKey, {
          ...handover.content.overview,
          purpose: overviewPurpose,
          currentStatus: overviewStatus,
        });
      } else {
        try {
          const parsed = JSON.parse(singleText);
          await onSave(sectionKey, parsed);
        } catch {
          // Fallback if not valid JSON
          await onSave(sectionKey, singleText);
        }
      }
      success('Section Updated', `Successfully saved edits to ${handover.sections[sectionKey].title}`);
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
      <div className="relative w-full max-w-2xl rounded-2xl bg-[#090D16] border border-slate-800 shadow-2xl overflow-hidden z-10 flex flex-col space-y-4 p-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
              <Edit3 className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">
                Edit Section: {handover.sections[sectionKey].title}
              </h3>
              <p className="text-[11px] text-slate-400">
                {handover.projectKey} · Modifying handover draft content
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

        {sectionKey === 'overview' ? (
          <div className="space-y-4 text-xs">
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300">Project Purpose</label>
              <Textarea
                rows={4}
                value={overviewPurpose}
                onChange={(e) => setOverviewPurpose(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300">Current Status Summary</label>
              <Textarea
                rows={4}
                value={overviewStatus}
                onChange={(e) => setOverviewStatus(e.target.value)}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-2 text-xs">
            <label className="font-semibold text-slate-300">Section Items (JSON / Data)</label>
            <Textarea
              rows={10}
              className="font-mono text-[11px]"
              value={singleText}
              onChange={(e) => setSingleText(e.target.value)}
            />
            <p className="text-[10px] text-slate-500">
              Edits will update the section content for the incoming engineer and record a revision tag.
            </p>
          </div>
        )}

        <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-800">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
            isLoading={isSubmitting}
            leftIcon={<Save className="h-4 w-4" />}
          >
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  );
};

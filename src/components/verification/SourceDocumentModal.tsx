import React, { useState } from 'react';
import {
  FileText,
  Copy,
  Check,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  Hash,
  Clock,
  BookOpen,
} from 'lucide-react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { useToast } from '../../hooks/useToast';
import { ClaimVerificationRecord } from '../../types/verification';

interface SourceDocumentModalProps {
  isOpen: boolean;
  onClose: () => void;
  claim: ClaimVerificationRecord | null;
}

export const SourceDocumentModal: React.FC<SourceDocumentModalProps> = ({
  isOpen,
  onClose,
  claim,
}) => {
  const { info } = useToast();
  const [copied, setCopied] = useState(false);

  if (!claim) return null;

  const handleCopyExcerpt = () => {
    if (claim.supporting_text_excerpt) {
      navigator.clipboard.writeText(claim.supporting_text_excerpt);
      setCopied(true);
      info('Copied', 'Supporting source excerpt copied to clipboard.');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Supported':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Partially Supported':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'Unsupported':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      case 'Conflicting':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Source Document & Supporting Evidence"
      maxWidth="lg"
      footer={
        <div className="flex items-center justify-between w-full">
          <div className="text-[11px] text-slate-500 font-mono flex items-center gap-1.5">
            <Clock className="h-3 w-3" />
            <span>Audited: {new Date(claim.verification_timestamp).toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
            {claim.supporting_document_id && (
              <a
                href={`/documents?id=${claim.supporting_document_id}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white transition-colors"
              >
                <span>View Full Document</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </div>
        </div>
      }
    >
      <div className="space-y-5 text-sm">
        {/* Source Header Banner */}
        <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-400 shrink-0">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="font-semibold text-white text-sm">
                  {claim.source_filename || 'Original Source Document'}
                </h4>
                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border ${getStatusColor(
                    claim.verification_status
                  )}`}
                >
                  {claim.verification_status}
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-400 mt-1 flex-wrap">
                {claim.page_number && (
                  <span className="flex items-center gap-1">
                    <BookOpen className="h-3 w-3 text-slate-500" />
                    <span>Page {claim.page_number}</span>
                  </span>
                )}
                {claim.section_reference && (
                  <span className="flex items-center gap-1 text-slate-300">
                    <Hash className="h-3 w-3 text-slate-500" />
                    <span>{claim.section_reference}</span>
                  </span>
                )}
                {claim.supporting_document_id && (
                  <span className="text-[11px] font-mono text-slate-500">
                    Doc ID: {claim.supporting_document_id.slice(0, 8)}...
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* The Claim Under Verification */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Verified Handover Claim
            </span>
            <span className="text-[11px] font-mono text-slate-500">
              ID: {claim.claim_id}
            </span>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 text-slate-200 text-xs sm:text-sm leading-relaxed">
            "{claim.claim_text}"
          </div>
        </div>

        {/* Verbatim Supporting Passage */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" /> Supporting Document Excerpt
            </span>
            {claim.supporting_text_excerpt && (
              <button
                onClick={handleCopyExcerpt}
                className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-mono transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-400" /> Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" /> Copy Excerpt
                  </>
                )}
              </button>
            )}
          </div>

          {claim.supporting_text_excerpt ? (
            <div className="relative p-4 rounded-xl bg-slate-900/60 border border-emerald-500/20 text-slate-200 text-xs sm:text-sm leading-relaxed font-sans">
              <div className="absolute top-2 left-2 text-slate-700 select-none text-2xl font-serif">
                “
              </div>
              <p className="pl-4 italic text-slate-200 whitespace-pre-wrap">
                {claim.supporting_text_excerpt}
              </p>
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-slate-900/40 border border-dashed border-slate-800 text-slate-500 text-xs flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-500 shrink-0" />
              <span>
                No verbatim supporting excerpt was located in the source documents for this claim.
                The claim has been explicitly marked as {claim.verification_status}.
              </span>
            </div>
          )}
        </div>

        {/* Verification Reasoning / Alignment */}
        {claim.reasoning && (
          <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800 text-xs text-slate-300 space-y-1">
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
              Engine Verification Analysis
            </span>
            <p className="text-slate-300">{claim.reasoning}</p>
          </div>
        )}
      </div>
    </Modal>
  );
};

import React, { useState, useMemo } from 'react';
import {
  ShieldCheck,
  AlertCircle,
  XCircle,
  HelpCircle,
  FileText,
  ExternalLink,
  Search,
  Filter,
  CheckCircle2,
  BookOpen,
  Hash,
  Quote,
} from 'lucide-react';
import { ClaimVerificationRecord } from '../../types/verification';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { EmptyState } from '../common/EmptyState';
import { cn } from '../../utils/cn';

interface EvidenceDetailsTableProps {
  claims: ClaimVerificationRecord[];
  onOpenSourceModal: (claim: ClaimVerificationRecord) => void;
  activeStatusFilter: string;
  onFilterChange: (status: string) => void;
}

export const EvidenceDetailsTable: React.FC<EvidenceDetailsTableProps> = ({
  claims,
  onOpenSourceModal,
  activeStatusFilter,
  onFilterChange,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'Supported':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>Supported</span>
          </span>
        );
      case 'Partially Supported':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertCircle className="h-3.5 w-3.5" />
            <span>Partially Supported</span>
          </span>
        );
      case 'Unsupported':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="h-3.5 w-3.5" />
            <span>Unsupported</span>
          </span>
        );
      case 'Conflicting':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <AlertCircle className="h-3.5 w-3.5" />
            <span>Conflicting</span>
          </span>
        );
      case 'Insufficient Evidence':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <HelpCircle className="h-3.5 w-3.5" />
            <span>{status || 'Insufficient Evidence'}</span>
          </span>
        );
    }
  };

  const filteredClaims = useMemo(() => {
    return claims.filter((claim) => {
      // Status filter
      if (activeStatusFilter !== 'all' && claim.verification_status !== activeStatusFilter) {
        return false;
      }
      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const textMatch = claim.claim_text?.toLowerCase().includes(q);
        const docMatch = claim.source_filename?.toLowerCase().includes(q);
        const excerptMatch = claim.supporting_text_excerpt?.toLowerCase().includes(q);
        const sectionMatch = claim.section_reference?.toLowerCase().includes(q);
        return textMatch || docMatch || excerptMatch || sectionMatch;
      }
      return true;
    });
  }, [claims, activeStatusFilter, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search claims, documents, or excerpt passages..."
            className="w-full pl-9 pr-3 py-1.5 text-xs sm:text-sm rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
          />
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs text-slate-400 font-medium mr-1 flex items-center gap-1">
            <Filter className="h-3.5 w-3.5" /> Filter:
          </span>
          {[
            { label: 'All', value: 'all' },
            { label: 'Supported', value: 'Supported' },
            { label: 'Partially Supported', value: 'Partially Supported' },
            { label: 'Unsupported', value: 'Unsupported' },
            { label: 'Conflicting', value: 'Conflicting' },
            { label: 'Insufficient Evidence', value: 'Insufficient Evidence' },
          ].map((f) => {
            const count =
              f.value === 'all'
                ? claims.length
                : claims.filter((c) => c.verification_status === f.value).length;
            const isActive = activeStatusFilter === f.value;
            return (
              <button
                key={f.value}
                onClick={() => onFilterChange(f.value)}
                className={cn(
                  'px-2.5 py-1 text-xs rounded-lg font-medium transition-all flex items-center gap-1.5',
                  isActive
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
                )}
              >
                <span>{f.label}</span>
                <span
                  className={cn(
                    'text-[10px] px-1.5 py-0.2 rounded-full font-mono',
                    isActive ? 'bg-brand-700 text-white' : 'bg-slate-900 text-slate-400'
                  )}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Claims List */}
      {filteredClaims.length === 0 ? (
        <EmptyState
          title="No claims match your criteria"
          description="Try adjusting your filter or search query to see claims from the handover."
          icon={ShieldCheck}
        />
      ) : (
        <div className="space-y-3">
          {filteredClaims.map((claim, idx) => {
            const hasSource = Boolean(claim.source_filename || claim.supporting_document_id);
            return (
              <div
                key={claim.claim_id || claim.id || idx}
                className="p-4 sm:p-5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 transition-all space-y-3"
              >
                {/* Header row: Section, Status, Document Button */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    {renderStatusBadge(claim.verification_status)}
                    {claim.section_reference && (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 border border-slate-700/50 flex items-center gap-1">
                        <Hash className="h-3 w-3 text-slate-400" />
                        <span>{claim.section_reference}</span>
                      </span>
                    )}
                    <span className="text-[11px] text-slate-400 font-mono">
                      Claim #{idx + 1} ({claim.claim_id.slice(0, 8)})
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant={hasSource ? 'outline' : 'ghost'}
                      size="sm"
                      onClick={() => onOpenSourceModal(claim)}
                      disabled={!hasSource && !claim.supporting_text_excerpt}
                      className={cn(
                        'text-xs flex items-center gap-1.5',
                        hasSource
                          ? 'text-brand-400 border-brand-500/30 hover:border-brand-500/60 hover:bg-brand-500/10'
                          : 'text-slate-500'
                      )}
                    >
                      <FileText className="h-3.5 w-3.5" />
                      <span>Open Source Document</span>
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  </div>
                </div>

                {/* Claim Statement */}
                <div className="text-sm font-medium text-white leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-850">
                  "{claim.claim_text}"
                </div>

                {/* Supporting Document Excerpt / Provenance */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-3 pt-1 text-xs">
                  {/* Left: Document info */}
                  <div className="md:col-span-4 p-2.5 rounded-lg bg-slate-950/40 border border-slate-850 flex flex-col justify-between gap-1.5">
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                        Original Document
                      </span>
                      <div className="flex items-center gap-1.5 mt-0.5 font-medium text-slate-200 truncate">
                        <FileText className="h-3.5 w-3.5 text-brand-400 shrink-0" />
                        <span className="truncate" title={claim.source_filename || 'Unknown'}>
                          {claim.source_filename || 'No document reference found'}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 text-[11px] text-slate-400">
                      {claim.page_number && (
                        <span className="flex items-center gap-1">
                          <BookOpen className="h-3 w-3 text-slate-400" />
                          <span>Page {claim.page_number}</span>
                        </span>
                      )}
                      {claim.alignment_score !== undefined && claim.alignment_score > 0 && (
                        <span className="font-mono text-emerald-400">
                          {Math.round(claim.alignment_score * 100)}% Match
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Right: Supporting Excerpt */}
                  <div className="md:col-span-8 p-2.5 rounded-lg bg-slate-950/40 border border-slate-850 flex flex-col justify-between gap-1">
                    <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider flex items-center gap-1">
                      <Quote className="h-3 w-3 text-slate-400" /> Supporting Text Excerpt
                    </span>
                    {claim.supporting_text_excerpt ? (
                      <p className="italic text-slate-300 line-clamp-3 font-sans text-xs">
                        "{claim.supporting_text_excerpt}"
                      </p>
                    ) : (
                      <p className="italic text-slate-500 text-xs">
                        No supporting passage found in source materials. Explicitly marked as{' '}
                        {claim.verification_status}.
                      </p>
                    )}
                  </div>
                </div>

                {/* Engine Reasoning if Unsupported or Conflicting */}
                {claim.reasoning && claim.verification_status !== 'Supported' && (
                  <div className="p-2.5 rounded-lg bg-rose-500/5 border border-rose-500/20 text-xs text-rose-300">
                    <span className="font-semibold text-rose-400 mr-1.5">Verification Note:</span>
                    {claim.reasoning}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

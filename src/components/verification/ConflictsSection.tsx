import React, { useState } from 'react';
import {
  GitCompare,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Calendar,
  User,
  ArrowRight,
  ShieldAlert,
  RotateCcw,
  Sparkles,
  Info,
} from 'lucide-react';
import { KnowledgeConflictItem } from '../../types/verification';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { cn } from '../../utils/cn';

interface ConflictsSectionProps {
  conflicts: KnowledgeConflictItem[];
  onOpenResolve: (conflict: KnowledgeConflictItem) => void;
  onReopen: (conflictId: string) => void;
  onViewEvidenceForConflict?: (conflict: KnowledgeConflictItem) => void;
}

export const ConflictsSection: React.FC<ConflictsSectionProps> = ({
  conflicts,
  onOpenResolve,
  onReopen,
  onViewEvidenceForConflict,
}) => {
  const [filter, setFilter] = useState<'all' | 'unresolved' | 'resolved' | 'critical'>('all');

  const filteredConflicts = conflicts.filter((c) => {
    if (filter === 'unresolved') return c.status === 'unresolved';
    if (filter === 'resolved') return c.status === 'resolved';
    if (filter === 'critical') return c.severity === 'critical';
    return true;
  });

  const unresolvedCount = conflicts.filter((c) => c.status === 'unresolved').length;
  const resolvedCount = conflicts.filter((c) => c.status === 'resolved').length;

  return (
    <div className="space-y-6">
      {/* Platform Invariant Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-red-950/40 via-slate-900 to-amber-950/30 border border-red-500/25 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="h-10 w-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 shrink-0">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-tight">
                Authorised Human Reviewer Mandate
              </h3>
              <Badge variant="ai" size="sm">
                Strict Safety Rule
              </Badge>
            </div>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Antigravity AI highlights contradictions across project records but <strong>never auto-selects a winner</strong>. All conflicting dates, architectures, and role assignments require human sign-off with permanent audit trail logging.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="px-2.5 py-1 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
            {unresolvedCount} Unresolved
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            {resolvedCount} Resolved
          </span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-1.5">
          <Button
            variant={filter === 'all' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('all')}
            className="text-xs h-8"
          >
            All Conflicts ({conflicts.length})
          </Button>
          <Button
            variant={filter === 'unresolved' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('unresolved')}
            className="text-xs h-8"
          >
            Unresolved ({unresolvedCount})
          </Button>
          <Button
            variant={filter === 'resolved' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('resolved')}
            className="text-xs h-8"
          >
            Resolved ({resolvedCount})
          </Button>
          <Button
            variant={filter === 'critical' ? 'danger' : 'ghost'}
            size="sm"
            onClick={() => setFilter('critical')}
            className="text-xs h-8"
          >
            Critical Severity
          </Button>
        </div>

        <div className="flex items-center gap-2 text-[11px] text-slate-400">
          <Sparkles className="h-3.5 w-3.5 text-brand-400" />
          <span>Cross-document semantic contradiction detector</span>
        </div>
      </div>

      {/* Conflicts List */}
      <div className="space-y-5">
        {filteredConflicts.length === 0 ? (
          <Card className="bg-[#0F172A] border-slate-800 p-12 text-center">
            <CheckCircle2 className="h-10 w-10 text-emerald-400 mx-auto mb-3" />
            <h4 className="text-sm font-semibold text-white">No Conflicts in This View</h4>
            <p className="text-xs text-slate-400 mt-1">
              All detected contradictions have been reviewed or filter condition returned empty.
            </p>
          </Card>
        ) : (
          filteredConflicts.map((item) => (
            <Card
              key={item.id}
              className={cn(
                'bg-[#0F172A] border transition-all p-5 sm:p-6 space-y-5',
                item.status === 'unresolved'
                  ? item.severity === 'critical'
                    ? 'border-red-500/40 hover:border-red-500/60 shadow-lg'
                    : 'border-slate-800 hover:border-slate-700'
                  : 'border-emerald-500/25 bg-emerald-950/5'
              )}
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-brand-400">
                      {item.projectKey}
                    </span>
                    <Badge
                      variant={
                        item.severity === 'critical'
                          ? 'danger'
                          : item.severity === 'high'
                          ? 'warning'
                          : 'neutral'
                      }
                      size="sm"
                    >
                      {item.severity.toUpperCase()}
                    </Badge>
                    <span className="text-xs text-slate-400 font-mono">
                      Dispute: <strong className="text-slate-200">{item.disputedField}</strong>
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-white tracking-tight">
                    {item.topic}
                  </h3>
                </div>

                <div className="flex items-center gap-2">
                  {item.status === 'resolved' ? (
                    <Badge variant="success" size="sm" dot>
                      Resolved by Human Lead
                    </Badge>
                  ) : (
                    <Badge variant="danger" size="sm" dot>
                      Unresolved Contradiction
                    </Badge>
                  )}
                </div>
              </div>

              {/* Conflict Description */}
              <p className="text-xs text-slate-300 leading-relaxed">
                {item.description}
              </p>

              {/* Side-by-Side Comparative Evidence Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Source A Card */}
                <div
                  className={cn(
                    'p-4 rounded-xl border space-y-3',
                    item.resolution?.resolutionType === 'verify_source_a'
                      ? 'bg-emerald-950/20 border-emerald-500/40'
                      : 'bg-slate-900/70 border-slate-800'
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-brand-400 shrink-0" />
                      <div>
                        <h4 className="text-xs font-semibold text-white">
                          {item.sourceA.docName}
                        </h4>
                        <span className="text-[10px] font-mono text-brand-300">
                          {item.sourceA.pageOrSection}
                        </span>
                      </div>
                    </div>
                    {item.resolution?.resolutionType === 'verify_source_a' && (
                      <Badge variant="success" size="sm">
                        Verified Source
                      </Badge>
                    )}
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 leading-relaxed">
                    "{item.sourceA.excerpt}"
                  </div>

                  <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
                    <span className="text-slate-400">Asserted Value:</span>
                    <span className="font-bold text-brand-300 bg-brand-500/10 px-2.5 py-0.5 rounded border border-brand-500/20 font-mono">
                      {item.sourceA.claimedValue}
                    </span>
                  </div>

                  <div className="text-[10px] text-slate-500 flex items-center justify-between">
                    <span>{item.sourceA.author}</span>
                    <span>{item.sourceA.date}</span>
                  </div>
                </div>

                {/* Source B Card */}
                <div
                  className={cn(
                    'p-4 rounded-xl border space-y-3',
                    item.resolution?.resolutionType === 'verify_source_b'
                      ? 'bg-emerald-950/20 border-emerald-500/40'
                      : 'bg-slate-900/70 border-slate-800'
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-brand-400 shrink-0" />
                      <div>
                        <h4 className="text-xs font-semibold text-white">
                          {item.sourceB.docName}
                        </h4>
                        <span className="text-[10px] font-mono text-brand-300">
                          {item.sourceB.pageOrSection}
                        </span>
                      </div>
                    </div>
                    {item.resolution?.resolutionType === 'verify_source_b' && (
                      <Badge variant="success" size="sm">
                        Verified Source
                      </Badge>
                    )}
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 leading-relaxed">
                    "{item.sourceB.excerpt}"
                  </div>

                  <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
                    <span className="text-slate-400">Asserted Value:</span>
                    <span className="font-bold text-brand-300 bg-brand-500/10 px-2.5 py-0.5 rounded border border-brand-500/20 font-mono">
                      {item.sourceB.claimedValue}
                    </span>
                  </div>

                  <div className="text-[10px] text-slate-500 flex items-center justify-between">
                    <span>{item.sourceB.author}</span>
                    <span>{item.sourceB.date}</span>
                  </div>
                </div>
              </div>

              {/* Resolved State Audit Card (if resolved) */}
              {item.status === 'resolved' && item.resolution && (
                <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/20 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Resolution Recorded by {item.resolution.resolvedBy.name}</span>
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">
                      {new Date(item.resolution.resolvedAt).toLocaleString()}
                    </span>
                  </div>

                  <div className="text-xs text-slate-200">
                    <strong className="text-emerald-300">Consensus Value: </strong>
                    <span className="font-mono bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30 font-bold">
                      {item.resolution.chosenValue || item.resolution.correctionText}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 italic bg-slate-950/50 p-2.5 rounded-lg border border-slate-800">
                    "{item.resolution.resolutionNote}"
                  </p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3">
                <span className="text-[11px] text-slate-500">
                  Provenance: Synthetic demonstration contradiction model
                </span>

                <div className="flex items-center gap-2.5">
                  {item.status === 'resolved' ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onReopen(item.id)}
                      leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
                      className="text-xs"
                    >
                      Reopen Dispute
                    </Button>
                  ) : (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => onOpenResolve(item)}
                      leftIcon={<GitCompare className="h-4 w-4" />}
                      className="text-xs"
                    >
                      Resolve Conflict
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

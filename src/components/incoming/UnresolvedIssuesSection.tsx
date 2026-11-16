import React, { useState } from 'react';
import {
  AlertTriangle,
  Flame,
  ShieldAlert,
  GitCompare,
  ExternalLink,
  ChevronRight,
  Info,
} from 'lucide-react';
import { Badge } from '../common/Badge';

interface UnresolvedBlocker {
  id: string;
  description: string;
  impact: string;
  severity: string;
  follow_up?: string;
  evidence?: string;
}

interface UnresolvedConflict {
  id: string;
  project_id: string;
  conflict_type: string;
  severity: string;
  description: string;
  status: string;
  source_a?: string;
  source_b?: string;
}

interface UnresolvedIssuesSectionProps {
  blockers: UnresolvedBlocker[];
  conflicts: UnresolvedConflict[];
  className?: string;
}

export const UnresolvedIssuesSection: React.FC<UnresolvedIssuesSectionProps> = ({
  blockers,
  conflicts,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'blockers' | 'conflicts'>('all');

  const totalIssues = blockers.length + conflicts.length;

  const getSeverityBadge = (severity: string) => {
    switch ((severity || '').toLowerCase()) {
      case 'critical':
        return <Badge variant="danger" size="sm">CRITICAL</Badge>;
      case 'high':
        return <Badge variant="warning" size="sm">HIGH</Badge>;
      case 'medium':
        return <Badge variant="accent" size="sm">MEDIUM</Badge>;
      default:
        return <Badge variant="default" size="sm">{severity}</Badge>;
    }
  };

  return (
    <div className={`space-y-3.5 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center">
            <Flame className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-tight">
                4. Unresolved Issues & Blockers
              </h3>
              <Badge variant="danger" size="sm">
                {totalIssues} Active
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400">
              Technical blockers, architectural contradictions, and governance bottlenecks
            </p>
          </div>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1.5 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('all')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'all'
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            All ({totalIssues})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('blockers')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'blockers'
                ? 'bg-rose-950/40 text-rose-300 border border-rose-500/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Blockers ({blockers.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('conflicts')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'conflicts'
                ? 'bg-amber-950/40 text-amber-300 border border-amber-500/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Conflicts ({conflicts.length})
          </button>
        </div>
      </div>

      {totalIssues === 0 ? (
        <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-400">
          No unresolved blockers or conflicts detected. Handover package is fully aligned.
        </div>
      ) : (
        <div className="space-y-3">
          {/* Blockers */}
          {(activeTab === 'all' || activeTab === 'blockers') &&
            blockers.map((b) => (
              <div
                key={b.id}
                className="p-4 rounded-xl bg-rose-950/10 border border-rose-500/30 space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-mono font-semibold text-rose-400 flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Operational Blocker
                  </span>
                  {getSeverityBadge(b.severity)}
                </div>

                <h4 className="text-xs font-bold text-white leading-snug">
                  {b.description}
                </h4>

                {b.impact && (
                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                    <strong className="text-rose-300">Impact:</strong> {b.impact}
                  </p>
                )}

                {b.follow_up && (
                  <p className="text-[11px] text-slate-400 pt-0.5">
                    Suggested Action: <span className="text-slate-300">{b.follow_up}</span>
                  </p>
                )}

                {b.evidence && (
                  <div className="text-[10px] font-mono text-slate-500">
                    Source: {b.evidence}
                  </div>
                )}
              </div>
            ))}

          {/* Conflicts */}
          {(activeTab === 'all' || activeTab === 'conflicts') &&
            conflicts.map((c) => (
              <div
                key={c.id}
                className="p-4 rounded-xl bg-amber-950/10 border border-amber-500/30 space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-mono font-semibold text-amber-400 flex items-center gap-1.5">
                    <GitCompare className="h-3.5 w-3.5" />
                    Knowledge Contradiction
                  </span>
                  {getSeverityBadge(c.severity)}
                </div>

                <h4 className="text-xs font-bold text-white leading-snug">
                  {c.description}
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-300 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  {c.source_a && (
                    <div>
                      <span className="text-slate-500 font-mono block text-[10px] uppercase">Source A</span>
                      <span>{c.source_a}</span>
                    </div>
                  )}
                  {c.source_b && (
                    <div>
                      <span className="text-slate-500 font-mono block text-[10px] uppercase">Source B (Contradicts)</span>
                      <span>{c.source_b}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
};

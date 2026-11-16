import React from 'react';
import {
  GitBranch,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Server,
  Key,
  Database,
  ExternalLink,
} from 'lucide-react';
import { Badge } from '../common/Badge';

export interface ProjectDependencyItem {
  id: string;
  dependency: string;
  related_task?: string;
  required_resource?: string;
  current_status: string;
}

interface ProjectDependenciesSectionProps {
  dependencies: ProjectDependencyItem[];
  className?: string;
}

export const ProjectDependenciesSection: React.FC<ProjectDependenciesSectionProps> = ({
  dependencies,
  className = '',
}) => {
  const getStatusBadge = (status: string) => {
    const s = (status || '').toLowerCase();
    if (s.includes('operational') || s.includes('healthy') || s.includes('granted')) {
      return (
        <Badge variant="success" size="sm" dot>
          {status}
        </Badge>
      );
    }
    if (s.includes('pending') || s.includes('required') || s.includes('rehearsal')) {
      return (
        <Badge variant="warning" size="sm" dot>
          {status}
        </Badge>
      );
    }
    return (
      <Badge variant="default" size="sm">
        {status}
      </Badge>
    );
  };

  return (
    <div className={`space-y-3.5 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
            <Server className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-tight">
                5. Project Dependencies
              </h3>
              <Badge variant="ai" size="sm">
                {dependencies.length} Verified
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400">
              Upstream APIs, infrastructure clusters, security credentials, and access requirements
            </p>
          </div>
        </div>
      </div>

      {dependencies.length === 0 ? (
        <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-400">
          No external dependencies recorded for this handover.
        </div>
      ) : (
        <div className="space-y-3">
          {dependencies.map((dep) => (
            <div
              key={dep.id}
              className="p-4 rounded-xl bg-[#0F172A] border border-slate-800/90 hover:border-slate-700 transition-all space-y-2.5"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-1">
                  <h4 className="text-xs font-bold text-white">
                    {dep.dependency}
                  </h4>
                  {dep.required_resource && (
                    <p className="text-xs text-slate-400 flex items-center gap-1.5">
                      <Key className="h-3 w-3 text-slate-500 shrink-0" />
                      Required Resource: <span className="text-slate-300 font-mono text-[11px]">{dep.required_resource}</span>
                    </p>
                  )}
                </div>

                {getStatusBadge(dep.current_status)}
              </div>

              {dep.related_task && (
                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                  <span>Related Milestone:</span>
                  <span className="font-semibold text-brand-300 truncate max-w-xs">
                    {dep.related_task}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

import React from 'react';
import {
  FolderGit2,
  ArrowRight,
  Layers,
  ListTodo,
  CheckCircle2,
  Clock,
  Sparkles,
} from 'lucide-react';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { Button } from '../common/Button';

export interface SharedProjectSummary {
  id: string;
  key: string;
  title: string;
  leadName?: string;
  status: string;
  handoversCount: number;
  pendingTasksCount: number;
  healthScore?: number;
}

interface SharedProjectsSectionProps {
  projects: SharedProjectSummary[];
  selectedProjectId: string | 'all';
  onSelectProject: (projectId: string | 'all') => void;
  className?: string;
}

export const SharedProjectsSection: React.FC<SharedProjectsSectionProps> = ({
  projects,
  selectedProjectId,
  onSelectProject,
  className = '',
}) => {
  return (
    <div className={`space-y-3.5 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
            <FolderGit2 className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              1. Shared Projects
            </h3>
            <p className="text-[11px] text-slate-400">
              Active engineering repositories transferred or shared with your account
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-xs">
          <button
            type="button"
            onClick={() => onSelectProject('all')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              selectedProjectId === 'all'
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            All Projects ({projects.length})
          </button>
        </div>
      </div>

      {/* Grid of Shared Projects */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {projects.map((proj) => {
          const isSelected = selectedProjectId === proj.id;

          return (
            <div
              key={proj.id}
              onClick={() => onSelectProject(isSelected ? 'all' : proj.id)}
              className={`p-4 rounded-xl border transition-all cursor-pointer space-y-3 ${
                isSelected
                  ? 'bg-brand-950/30 border-brand-500/60 shadow-md ring-1 ring-brand-500/30'
                  : 'bg-[#0F172A] border-slate-800/90 hover:border-slate-700 hover:bg-slate-900/60'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-0.5">
                  <span className="font-mono text-xs font-bold text-brand-400">
                    {proj.key}
                  </span>
                  <h4 className="text-sm font-semibold text-white line-clamp-1">
                    {proj.title}
                  </h4>
                </div>

                <Badge
                  variant={
                    proj.status === 'in_progress' || proj.status === 'active'
                      ? 'success'
                      : 'accent'
                  }
                  size="sm"
                >
                  {proj.status.replace('_', ' ').toUpperCase()}
                </Badge>
              </div>

              {proj.leadName && (
                <p className="text-xs text-slate-400">
                  Project Lead: <strong className="text-slate-300">{proj.leadName}</strong>
                </p>
              )}

              {/* Stats Footer */}
              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                <span className="flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 text-slate-500" />
                  <strong>{proj.handoversCount}</strong> Handover{proj.handoversCount !== 1 ? 's' : ''}
                </span>

                <span className="flex items-center gap-1.5">
                  <ListTodo className="h-3.5 w-3.5 text-brand-400" />
                  <strong className="text-white">{proj.pendingTasksCount}</strong> Pending Tasks
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

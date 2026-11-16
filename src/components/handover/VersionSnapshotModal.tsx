import React, { useState } from 'react';
import {
  FileText,
  X,
  Clock,
  User,
  ShieldCheck,
  CheckCircle2,
  Layers,
  Flame,
  GitBranch,
  RotateCcw,
  Code,
  ListTodo,
  AlertTriangle,
  ArrowRightLeft,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { HandoverVersionItem } from '../../types/handover';

interface VersionSnapshotModalProps {
  isOpen: boolean;
  onClose: () => void;
  version: HandoverVersionItem | null;
  onRestoreClick?: (version: HandoverVersionItem) => void;
  onCompareClick?: (version: HandoverVersionItem) => void;
}

export const VersionSnapshotModal: React.FC<VersionSnapshotModalProps> = ({
  isOpen,
  onClose,
  version,
  onRestoreClick,
  onCompareClick,
}) => {
  const [activeTab, setActiveTab] = useState<'chapters' | 'tasks' | 'raw'>('chapters');

  if (!isOpen || !version) return null;

  const snapshot = version.snapshot || {};

  const formattedDate = version.created_at
    ? new Date(version.created_at).toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    : 'Unknown Date';

  const chapters: { title: string; content?: string; icon: React.ElementType }[] = [
    { title: 'Project Overview', content: snapshot.project_overview, icon: FileText },
    { title: 'Technical Architecture', content: snapshot.technical_architecture, icon: Layers },
    { title: 'Key Decisions & ADRs', content: snapshot.key_decisions, icon: CheckCircle2 },
    { title: 'Risks & Operational Blockers', content: snapshot.risks_and_blockers, icon: Flame },
    { title: 'Project Dependencies', content: snapshot.dependencies, icon: GitBranch },
    { title: 'Team Responsibilities', content: snapshot.team_responsibilities, icon: User },
    { title: 'Recommendations & Next Steps', content: snapshot.recommendations, icon: AlertTriangle },
  ];

  const tasks: any[] = Array.isArray(snapshot.pending_tasks)
    ? snapshot.pending_tasks
    : Array.isArray(snapshot.tasks)
    ? snapshot.tasks
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-[#0F172A] border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-base font-bold text-white">
                  Version {version.version_number}
                </span>
                {version.is_latest && (
                  <Badge variant="success" size="sm" dot>
                    Latest Active
                  </Badge>
                )}
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
              <p className="text-xs text-slate-400 mt-0.5">
                Snapshot captured on {formattedDate} by {version.creator_name || 'System / Outgoing Lead'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onCompareClick && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onCompareClick(version)}
                leftIcon={<ArrowRightLeft className="h-4 w-4" />}
                className="text-xs font-semibold"
              >
                Compare
              </Button>
            )}
            {onRestoreClick && !version.is_latest && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onRestoreClick(version)}
                leftIcon={<RotateCcw className="h-4 w-4" />}
                className="text-xs font-semibold text-amber-300 border-amber-500/50 hover:bg-amber-500/10"
              >
                Restore
              </Button>
            )}
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-slate-800"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Description Banner if available */}
        {version.version_description && (
          <div className="px-6 py-2.5 bg-slate-900/80 border-b border-slate-800/80 flex items-center gap-2 text-xs text-slate-300">
            <span className="font-semibold text-slate-400">Description:</span>
            <span>{version.version_description}</span>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 px-4 sm:px-6 pt-3 border-b border-slate-800 bg-slate-950/40 overflow-x-auto whitespace-nowrap">
          <button
            onClick={() => setActiveTab('chapters')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'chapters'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="h-4 w-4" />
            Knowledge Chapters ({chapters.filter((c) => !!c.content).length})
          </button>
          <button
            onClick={() => setActiveTab('tasks')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'tasks'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ListTodo className="h-4 w-4" />
            Snapshot Tasks ({tasks.length})
          </button>
          <button
            onClick={() => setActiveTab('raw')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'raw'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Code className="h-4 w-4" />
            Raw JSON Snapshot
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 bg-[#0B1120]">
          {activeTab === 'chapters' && (
            <div className="space-y-4">
              {chapters.map((ch, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 space-y-2"
                >
                  <div className="flex items-center gap-2">
                    <ch.icon className="h-4 w-4 text-brand-400" />
                    <h3 className="text-sm font-semibold text-white">{ch.title}</h3>
                  </div>
                  {ch.content ? (
                    <div className="text-xs text-slate-300 whitespace-pre-line leading-relaxed bg-slate-950/60 p-3.5 rounded-lg border border-slate-800/80 font-sans">
                      {ch.content}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic">No content recorded in this chapter snapshot.</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'tasks' && (
            <div className="space-y-3">
              {tasks.length > 0 ? (
                tasks.map((t, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex items-center justify-between gap-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white">
                          {t.title || t.task_title || `Continuation Task #${idx + 1}`}
                        </span>
                        {t.priority && (
                          <Badge
                            variant={
                              t.priority === 'critical'
                                ? 'danger'
                                : t.priority === 'high'
                                ? 'warning'
                                : 'default'
                            }
                            size="sm"
                          >
                            {t.priority}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-400">
                        <span>Assignee: <strong className="text-slate-300">{t.assigned_to_name || t.assigned_to || 'Unassigned'}</strong></span>
                        {t.due_date && <span>Due: {new Date(t.due_date).toLocaleDateString()}</span>}
                      </div>
                    </div>

                    <Badge
                      variant={
                        t.status === 'completed'
                          ? 'success'
                          : t.status === 'in_progress'
                          ? 'accent'
                          : 'warning'
                      }
                      size="sm"
                    >
                      {t.status || 'pending'}
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="text-center py-10 text-xs text-slate-500 bg-[#0F172A] rounded-xl border border-slate-800">
                  No tasks recorded in this snapshot.
                </div>
              )}
            </div>
          )}

          {activeTab === 'raw' && (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 overflow-x-auto">
              <pre className="text-xs font-mono text-brand-300 leading-relaxed">
                {JSON.stringify(version.snapshot, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-slate-800 bg-slate-900/60 text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>Immutable Snapshot ID: <code className="font-mono text-slate-300">{version.id.slice(0, 12)}...</code></span>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="text-xs text-slate-300">
            Close Viewer
          </Button>
        </div>
      </div>
    </div>
  );
};

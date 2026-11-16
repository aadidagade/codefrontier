import React, { useState, useEffect } from 'react';
import {
  ArrowRightLeft,
  X,
  Plus,
  Minus,
  Edit3,
  CheckCircle2,
  ListTodo,
  Users,
  Layers,
  ArrowRight,
  GitBranch,
  RefreshCw,
  Columns,
  AlignLeft,
  ShieldCheck,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import {
  HandoverVersionItem,
  VersionDiffResponse,
  SectionDiffItem,
  TaskDiffItem,
  ResponsibilityDiffItem,
} from '../../types/handover';
import { handoverService } from '../../services/handoverService';

interface VersionComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  handoverId: string;
  versions: HandoverVersionItem[];
  initialFromVersionId?: string;
  initialToVersionId?: string;
}

export const VersionComparisonModal: React.FC<VersionComparisonModalProps> = ({
  isOpen,
  onClose,
  handoverId,
  versions,
  initialFromVersionId,
  initialToVersionId,
}) => {
  // Sort versions chronological
  const sortedVersions = [...versions].sort((a, b) =>
    a.version_number.localeCompare(b.version_number, undefined, { numeric: true })
  );

  const defaultFrom = initialFromVersionId || sortedVersions[0]?.id || '';
  const defaultTo =
    initialToVersionId ||
    sortedVersions[sortedVersions.length - 1]?.id ||
    sortedVersions[0]?.id ||
    '';

  const [fromVersionId, setFromVersionId] = useState<string>(defaultFrom);
  const [toVersionId, setToVersionId] = useState<string>(defaultTo);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [diffData, setDiffData] = useState<VersionDiffResponse | null>(null);
  const [filterTab, setFilterTab] = useState<'all' | 'sections' | 'tasks' | 'responsibilities'>('all');
  const [diffLayout, setDiffLayout] = useState<'unified' | 'split'>('unified');

  // Sync initial version IDs when modal opens
  useEffect(() => {
    if (initialFromVersionId) setFromVersionId(initialFromVersionId);
    if (initialToVersionId) setToVersionId(initialToVersionId);
  }, [initialFromVersionId, initialToVersionId, isOpen]);

  // Load diff whenever from/to version changes
  const loadComparison = async () => {
    if (!fromVersionId || !toVersionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await handoverService.compareVersions(handoverId, fromVersionId, toVersionId);
      if (res && res.data) {
        setDiffData(res.data);
      } else {
        setError('No diff data returned from backend comparison engine.');
      }
    } catch (err: any) {
      console.error('Failed to compare versions:', err);
      setError(err?.message || 'Failed to compare handover versions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && fromVersionId && toVersionId) {
      loadComparison();
    }
  }, [isOpen, fromVersionId, toVersionId, handoverId]);

  if (!isOpen) return null;

  const handleSwap = () => {
    const temp = fromVersionId;
    setFromVersionId(toVersionId);
    setToVersionId(temp);
  };

  const fromVersionObj = versions.find((v) => v.id === fromVersionId);
  const toVersionObj = versions.find((v) => v.id === toVersionId);

  const summary = diffData?.summary;
  const sectionDiffs = diffData?.section_diffs || [];
  const taskDiffs = diffData?.task_diffs || [];
  const respDiffs = diffData?.responsibility_diffs || [];

  const modifiedSections = sectionDiffs.filter((s) => s.change_type !== 'UNCHANGED');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-6 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
      <div className="relative w-full max-w-6xl max-h-[92vh] bg-[#0F172A] border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header with Title and Version Selectors */}
        <div className="p-5 border-b border-slate-800 bg-slate-900/70 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
                <ArrowRightLeft className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  Version Comparison Engine
                  {summary && (
                    <Badge
                      variant={summary.has_differences ? 'warning' : 'success'}
                      size="sm"
                    >
                      {summary.has_differences ? 'Modifications Detected' : 'Identical Versions'}
                    </Badge>
                  )}
                </h2>
                <p className="text-xs text-slate-400">
                  Visual chapter-by-chapter and task diffing against immutable stored snapshots
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-slate-800"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Interactive Version Selector Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl bg-slate-950/70 border border-slate-800">
            <div className="flex flex-wrap items-center gap-3 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">
                  Base:
                </span>
                <select
                  value={fromVersionId}
                  onChange={(e) => setFromVersionId(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 font-mono focus:border-brand-500 focus:outline-none"
                >
                  {sortedVersions.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.version_number} ({v.approval_status}) {v.is_latest ? '★ Latest' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleSwap}
                title="Swap versions"
                className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-brand-400 border border-slate-800 transition-colors"
              >
                <ArrowRightLeft className="h-4 w-4" />
              </button>

              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">
                  Target:
                </span>
                <select
                  value={toVersionId}
                  onChange={(e) => setToVersionId(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 font-mono focus:border-brand-500 focus:outline-none"
                >
                  {sortedVersions.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.version_number} ({v.approval_status}) {v.is_latest ? '★ Latest' : ''}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Layout Toggle */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-slate-500 mr-1">Diff View:</span>
              <button
                onClick={() => setDiffLayout('unified')}
                className={`p-1.5 rounded text-xs flex items-center gap-1 border transition-colors ${
                  diffLayout === 'unified'
                    ? 'bg-brand-500/20 text-brand-300 border-brand-500/40'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
                title="Unified Line Diff"
              >
                <AlignLeft className="h-3.5 w-3.5" />
                Unified
              </button>
              <button
                onClick={() => setDiffLayout('split')}
                className={`p-1.5 rounded text-xs flex items-center gap-1 border transition-colors ${
                  diffLayout === 'split'
                    ? 'bg-brand-500/20 text-brand-300 border-brand-500/40'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
                title="Side-by-Side View"
              >
                <Columns className="h-3.5 w-3.5" />
                Side-by-Side
              </button>
            </div>
          </div>

          {/* High-Level Comparison Summary Chips */}
          {summary && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
              <div className="p-2.5 rounded-lg bg-emerald-950/25 border border-emerald-500/25 flex items-center justify-between">
                <span className="text-[11px] font-semibold text-emerald-300">Added Sections</span>
                <span className="font-mono text-xs font-bold text-emerald-400">
                  +{summary.added_sections_count}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-rose-950/25 border border-rose-500/25 flex items-center justify-between">
                <span className="text-[11px] font-semibold text-rose-300">Removed</span>
                <span className="font-mono text-xs font-bold text-rose-400">
                  -{summary.removed_sections_count}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-amber-950/25 border border-amber-500/25 flex items-center justify-between">
                <span className="text-[11px] font-semibold text-amber-300">Modified</span>
                <span className="font-mono text-xs font-bold text-amber-400">
                  ~{summary.modified_sections_count}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-400">Unchanged</span>
                <span className="font-mono text-xs font-bold text-slate-300">
                  ={summary.unchanged_sections_count}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-indigo-950/25 border border-indigo-500/25 flex items-center justify-between">
                <span className="text-[11px] font-semibold text-indigo-300">Task Shifts</span>
                <span className="font-mono text-xs font-bold text-indigo-400">
                  {summary.task_status_changes_count}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-cyan-950/25 border border-cyan-500/25 flex items-center justify-between">
                <span className="text-[11px] font-semibold text-cyan-300">Responsibilities</span>
                <span className="font-mono text-xs font-bold text-cyan-400">
                  {summary.responsibility_changes_count}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* View Filter Tabs */}
        <div className="flex items-center gap-2 px-4 sm:px-6 pt-3 border-b border-slate-800 bg-slate-950/40 overflow-x-auto whitespace-nowrap">
          <button
            onClick={() => setFilterTab('all')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              filterTab === 'all'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            All Differences
          </button>
          <button
            onClick={() => setFilterTab('sections')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              filterTab === 'sections'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            Chapters ({modifiedSections.length})
          </button>
          <button
            onClick={() => setFilterTab('tasks')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              filterTab === 'tasks'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ListTodo className="h-3.5 w-3.5" />
            Task Shifts ({taskDiffs.length})
          </button>
          <button
            onClick={() => setFilterTab('responsibilities')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              filterTab === 'responsibilities'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Users className="h-3.5 w-3.5" />
            Responsibilities ({respDiffs.length})
          </button>
        </div>

        {/* Scrollable Diff Viewport */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 bg-[#0B1120]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
              <span className="text-xs text-slate-400">Comparing stored snapshot baselines...</span>
            </div>
          ) : error ? (
            <div className="p-6 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs text-center space-y-2">
              <p className="font-semibold">{error}</p>
              <Button variant="outline" size="sm" onClick={loadComparison} className="text-xs">
                Retry Comparison
              </Button>
            </div>
          ) : (
            <>
              {/* 1. CHAPTER / SECTION DIFFS */}
              {(filterTab === 'all' || filterTab === 'sections') && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between pb-1 border-b border-slate-800">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                      Knowledge Chapter Diffs ({sectionDiffs.length})
                    </h3>
                    <span className="text-[11px] text-slate-500">
                      Comparing {fromVersionObj?.version_number || 'From'} &rarr; {toVersionObj?.version_number || 'To'}
                    </span>
                  </div>

                  {sectionDiffs.map((sec, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-card"
                    >
                      {/* Section Diff Header */}
                      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/60 border-b border-slate-800">
                        <div className="flex items-center gap-2.5">
                          <span className="text-xs font-bold text-white">{sec.title}</span>
                          <span className="text-[10px] font-mono text-slate-500">({sec.section_type})</span>
                        </div>

                        <Badge
                          variant={
                            sec.change_type === 'ADDED'
                              ? 'success'
                              : sec.change_type === 'REMOVED'
                              ? 'danger'
                              : sec.change_type === 'MODIFIED'
                              ? 'warning'
                              : 'default'
                          }
                          size="sm"
                        >
                          {sec.change_type === 'ADDED' && '+ ADDED'}
                          {sec.change_type === 'REMOVED' && '- REMOVED'}
                          {sec.change_type === 'MODIFIED' && '~ MODIFIED'}
                          {sec.change_type === 'UNCHANGED' && '= UNCHANGED'}
                        </Badge>
                      </div>

                      {/* Content Diff Body */}
                      <div className="p-4">
                        {sec.change_type === 'UNCHANGED' ? (
                          <div className="text-xs text-slate-500 italic p-3 rounded-lg bg-slate-950/40 border border-slate-800/60">
                            Content is identical between versions.
                          </div>
                        ) : diffLayout === 'split' ? (
                          /* Side-by-side split view */
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                            <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-500/20 space-y-1">
                              <span className="text-[10px] font-bold text-rose-400 block uppercase">
                                Prior ({fromVersionObj?.version_number})
                              </span>
                              <pre className="text-rose-200/90 whitespace-pre-wrap font-sans text-xs">
                                {sec.old_content || '(empty)'}
                              </pre>
                            </div>
                            <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/20 space-y-1">
                              <span className="text-[10px] font-bold text-emerald-400 block uppercase">
                                Revised ({toVersionObj?.version_number})
                              </span>
                              <pre className="text-emerald-200/90 whitespace-pre-wrap font-sans text-xs">
                                {sec.new_content || '(empty)'}
                              </pre>
                            </div>
                          </div>
                        ) : (
                          /* Unified line diff */
                          <div className="space-y-1 font-mono text-xs rounded-lg bg-slate-950 border border-slate-800/80 p-3 overflow-x-auto">
                            {sec.removed_lines.length > 0 &&
                              sec.removed_lines.map((line, lIdx) => (
                                <div
                                  key={`rem-${lIdx}`}
                                  className="flex items-start gap-2 bg-rose-950/30 text-rose-300 border-l-2 border-rose-500 px-2 py-0.5 rounded-sm"
                                >
                                  <span className="select-none text-rose-500 font-bold shrink-0">-</span>
                                  <span className="font-sans leading-relaxed">{line}</span>
                                </div>
                              ))}
                            {sec.added_lines.length > 0 &&
                              sec.added_lines.map((line, lIdx) => (
                                <div
                                  key={`add-${lIdx}`}
                                  className="flex items-start gap-2 bg-emerald-950/30 text-emerald-300 border-l-2 border-emerald-500 px-2 py-0.5 rounded-sm"
                                >
                                  <span className="select-none text-emerald-500 font-bold shrink-0">+</span>
                                  <span className="font-sans leading-relaxed">{line}</span>
                                </div>
                              ))}
                            {sec.removed_lines.length === 0 && sec.added_lines.length === 0 && (
                              <p className="text-xs text-slate-400 font-sans">{sec.new_content}</p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* 2. TASK SHIFTS & STATUS CHANGES */}
              {(filterTab === 'all' || filterTab === 'tasks') && taskDiffs.length > 0 && (
                <div className="space-y-4 pt-2">
                  <div className="flex items-center justify-between pb-1 border-b border-slate-800">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                      Task Status & Ownership Transitions ({taskDiffs.length})
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {taskDiffs.map((task, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 space-y-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-bold text-white truncate">
                            {task.title}
                          </span>
                          <Badge
                            variant={
                              task.change_type === 'ADDED'
                                ? 'success'
                                : task.change_type === 'REMOVED'
                                ? 'danger'
                                : 'warning'
                            }
                            size="sm"
                          >
                            {task.change_type}
                          </Badge>
                        </div>

                        {/* Status Change indicator */}
                        {task.status_changed && (
                          <div className="flex items-center gap-2 p-2 rounded bg-slate-900 border border-slate-800 text-xs">
                            <span className="text-slate-400 text-[11px]">Status:</span>
                            <Badge variant="warning" size="sm">
                              {task.old_status || 'pending'}
                            </Badge>
                            <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
                            <Badge variant="success" size="sm">
                              {task.new_status || 'completed'}
                            </Badge>
                          </div>
                        )}

                        {/* Assignee Change indicator */}
                        {task.assignee_changed && (
                          <div className="flex items-center gap-2 p-2 rounded bg-slate-900 border border-slate-800 text-xs">
                            <span className="text-slate-400 text-[11px]">Assignee:</span>
                            <span className="text-slate-300 line-through">
                              {task.old_assignee || 'Unassigned'}
                            </span>
                            <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
                            <strong className="text-brand-300">
                              {task.new_assignee || 'Unassigned'}
                            </strong>
                          </div>
                        )}

                        {/* Priority Change indicator */}
                        {task.priority_changed && (
                          <div className="flex items-center gap-2 p-2 rounded bg-slate-900 border border-slate-800 text-xs">
                            <span className="text-slate-400 text-[11px]">Priority:</span>
                            <span className="text-slate-400">{task.old_priority}</span>
                            <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
                            <span className="text-white font-semibold">{task.new_priority}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 3. TEAM RESPONSIBILITY TRANSFERS */}
              {(filterTab === 'all' || filterTab === 'responsibilities') && respDiffs.length > 0 && (
                <div className="space-y-4 pt-2">
                  <div className="flex items-center justify-between pb-1 border-b border-slate-800">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                      Responsibility Transfers & Reassignments ({respDiffs.length})
                    </h3>
                  </div>

                  <div className="space-y-2.5">
                    {respDiffs.map((r, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800 flex items-center justify-between gap-4"
                      >
                        <div className="space-y-0.5">
                          <span className="text-xs font-semibold text-white">
                            {r.entity_name}
                          </span>
                          <p className="text-[11px] text-slate-400">{r.details}</p>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {r.old_assignee && (
                            <span className="text-xs text-slate-400 line-through">
                              {r.old_assignee}
                            </span>
                          )}
                          {r.old_assignee && r.new_assignee && (
                            <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
                          )}
                          {r.new_assignee && (
                            <Badge variant="ai" size="sm">
                              {r.new_assignee}
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-slate-800 bg-slate-900/60 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>Actual immutable database snapshots compared. No AI hallucination or regeneration.</span>
          </div>

          <Button variant="ghost" size="sm" onClick={onClose} className="text-xs text-slate-300">
            Close Comparator
          </Button>
        </div>
      </div>
    </div>
  );
};

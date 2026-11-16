import React, { useState } from 'react';
import {
  ListTodo,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Plus,
  MessageSquare,
  ShieldCheck,
  Send,
  AlertCircle,
  Calendar,
  Lock,
  ChevronDown,
  ChevronUp,
  Filter,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { TaskProgressUpdateModal } from './TaskProgressUpdateModal';

interface ContinuityTasksManagerProps {
  tasks: any[];
  isAcknowledged: boolean;
  onUpdateStatus: (taskId: string, status: string, notes?: string) => Promise<void>;
  onAddProgress: (taskId: string, updateText: string, newStatus?: string) => Promise<void>;
  onTriggerAcknowledgePrompt?: () => void;
  className?: string;
}

export const ContinuityTasksManager: React.FC<ContinuityTasksManagerProps> = ({
  tasks,
  isAcknowledged,
  onUpdateStatus,
  onAddProgress,
  onTriggerAcknowledgePrompt,
  className = '',
}) => {
  const [filter, setFilter] = useState<'all' | 'pending' | 'in_progress' | 'blocked' | 'completed' | 'overdue'>('all');
  const [selectedTaskForProgress, setSelectedTaskForProgress] = useState<any | null>(null);
  const [isProgressModalOpen, setIsProgressModalOpen] = useState(false);
  const [expandedTaskIds, setExpandedTaskIds] = useState<Set<string>>(new Set());
  const [updatingTaskId, setUpdatingTaskId] = useState<string | null>(null);

  const toggleExpand = (taskId: string) => {
    setExpandedTaskIds((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  };

  const getTaskStatusCategory = (t: any) => {
    const s = (t.status || '').toLowerCase();
    if (s === 'completed' || s === 'verified') return 'completed';
    if (s === 'in_progress') return 'in_progress';
    if (s === 'blocked') return 'blocked';
    return 'pending'; // 'not_started' or 'pending'
  };

  const isTaskOverdue = (t: any) => {
    if (!t.due_date || t.status === 'completed') return false;
    return new Date(t.due_date).getTime() < Date.now();
  };

  const pendingCount = tasks.filter((t) => getTaskStatusCategory(t) === 'pending').length;
  const inProgressCount = tasks.filter((t) => getTaskStatusCategory(t) === 'in_progress').length;
  const blockedCount = tasks.filter((t) => getTaskStatusCategory(t) === 'blocked').length;
  const completedCount = tasks.filter((t) => getTaskStatusCategory(t) === 'completed').length;
  const overdueCount = tasks.filter(isTaskOverdue).length;

  const filteredTasks = tasks.filter((t) => {
    if (filter === 'all') return true;
    if (filter === 'overdue') return isTaskOverdue(t);
    return getTaskStatusCategory(t) === filter;
  });

  const handleStatusChange = async (taskId: string, newStatus: string) => {
    if (!isAcknowledged) {
      if (onTriggerAcknowledgePrompt) onTriggerAcknowledgePrompt();
      return;
    }
    setUpdatingTaskId(taskId);
    try {
      await onUpdateStatus(taskId, newStatus);
    } finally {
      setUpdatingTaskId(null);
    }
  };

  const getPriorityBadgeVariant = (priority: string) => {
    switch ((priority || '').toLowerCase()) {
      case 'critical':
        return 'danger';
      case 'high':
        return 'warning';
      case 'medium':
        return 'accent';
      default:
        return 'default';
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header and Summary Statistics */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
            <ListTodo className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-tight">
                3. Continuation Tasks & Assigned Responsibilities
              </h3>
              <Badge variant="ai" size="sm">
                {tasks.length} Assigned
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400">
              Manage operational cutover tasks, milestone tracking, and timestamped progress logs
            </p>
          </div>
        </div>

        {/* Task Completion Progress Meter */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">Completion:</span>
          <span className="font-mono font-bold text-emerald-400">
            {completedCount}/{tasks.length} ({tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0}%)
          </span>
        </div>
      </div>

      {/* Permission Callout: If Unacknowledged */}
      {!isAcknowledged && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-amber-300">
          <div className="flex items-center gap-2.5">
            <Lock className="h-4 w-4 text-amber-400 shrink-0" />
            <span>
              <strong>Receipt Acknowledgement Required:</strong> Please acknowledge receipt of the handover brief above to unlock status updates and progress logging.
            </span>
          </div>
          {onTriggerAcknowledgePrompt && (
            <Button
              variant="outline"
              size="sm"
              onClick={onTriggerAcknowledgePrompt}
              className="text-xs shrink-0 border-amber-500/40 text-amber-200 hover:bg-amber-500/10"
            >
              Acknowledge Receipt Now
            </Button>
          )}
        </div>
      )}

      {/* Status Filter Chips */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <button
          type="button"
          onClick={() => setFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            filter === 'all'
              ? 'bg-brand-600 text-white shadow-sm'
              : 'bg-slate-900/60 border border-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          All Tasks ({tasks.length})
        </button>

        <button
          type="button"
          onClick={() => setFilter('pending')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            filter === 'pending'
              ? 'bg-slate-700 text-white shadow-sm'
              : 'bg-slate-900/60 border border-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          Not Started ({pendingCount})
        </button>

        <button
          type="button"
          onClick={() => setFilter('in_progress')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            filter === 'in_progress'
              ? 'bg-brand-500/20 text-brand-300 border border-brand-500/50'
              : 'bg-slate-900/60 border border-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          In Progress ({inProgressCount})
        </button>

        <button
          type="button"
          onClick={() => setFilter('blocked')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            filter === 'blocked'
              ? 'bg-rose-950/40 text-rose-300 border border-rose-500/50'
              : 'bg-slate-900/60 border border-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          Blocked ({blockedCount})
        </button>

        <button
          type="button"
          onClick={() => setFilter('completed')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            filter === 'completed'
              ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-500/50'
              : 'bg-slate-900/60 border border-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          Completed ({completedCount})
        </button>

        {overdueCount > 0 && (
          <button
            type="button"
            onClick={() => setFilter('overdue')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              filter === 'overdue'
                ? 'bg-rose-600 text-white shadow-sm'
                : 'bg-rose-950/20 border border-rose-500/30 text-rose-300 hover:text-white'
            }`}
          >
            Overdue ({overdueCount})
          </button>
        )}
      </div>

      {/* Tasks List */}
      <div className="space-y-3">
        {filteredTasks.length === 0 ? (
          <div className="p-8 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-400">
            No continuation tasks found matching the selected filter.
          </div>
        ) : (
          filteredTasks.map((t) => {
            const statusCat = getTaskStatusCategory(t);
            const isOverdue = isTaskOverdue(t);
            const isExpanded = expandedTaskIds.has(t.id);
            const isUpdating = updatingTaskId === t.id;
            const progressNotes: any[] = t.progress_notes || t.progressNotes || [];

            return (
              <div
                key={t.id}
                className={`p-4 rounded-xl border transition-all space-y-3 ${
                  statusCat === 'completed'
                    ? 'bg-slate-900/30 border-slate-800/80 opacity-80'
                    : statusCat === 'blocked'
                    ? 'bg-rose-950/10 border-rose-500/30'
                    : statusCat === 'in_progress'
                    ? 'bg-brand-950/15 border-brand-500/30'
                    : 'bg-[#0F172A] border-slate-800/90 hover:border-slate-700'
                }`}
              >
                {/* Main Task Row */}
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={getPriorityBadgeVariant(t.priority)} size="sm">
                        {(t.priority || 'medium').toUpperCase()}
                      </Badge>

                      {isOverdue && (
                        <Badge variant="danger" size="sm" dot>
                          Overdue
                        </Badge>
                      )}

                      {statusCat === 'blocked' && (
                        <span className="text-[11px] font-mono text-rose-400 flex items-center gap-1 font-semibold">
                          <AlertTriangle className="h-3 w-3" /> Blocked
                        </span>
                      )}
                    </div>

                    <h4 className="text-sm font-semibold text-white">
                      {t.title}
                    </h4>

                    {t.description && (
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {t.description}
                      </p>
                    )}

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
                      <span>Assignee: <strong className="text-slate-200">{t.assigned_to_name || 'Elena Rostova (You)'}</strong></span>
                      {t.due_date && (
                        <span className={`flex items-center gap-1 font-mono text-[11px] ${isOverdue ? 'text-rose-400 font-semibold' : 'text-slate-400'}`}>
                          <Calendar className="h-3.5 w-3.5" />
                          Due: {new Date(t.due_date).toLocaleDateString()}
                        </span>
                      )}
                      {progressNotes.length > 0 && (
                        <span className="flex items-center gap-1 text-brand-300">
                          <MessageSquare className="h-3.5 w-3.5" />
                          {progressNotes.length} Progress Note{progressNotes.length !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Task Management Controls (Unlocked after acknowledgement) */}
                  <div className="flex flex-wrap items-center gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-slate-800/80 shrink-0">
                    {/* Status Dropdown with the 4 Required Statuses */}
                    <div className="relative">
                      <select
                        value={statusCat}
                        disabled={!isAcknowledged || isUpdating}
                        onChange={(e) => handleStatusChange(t.id, e.target.value)}
                        className={`text-xs rounded-lg px-2.5 py-1.5 font-medium border transition-all cursor-pointer bg-slate-900 ${
                          !isAcknowledged
                            ? 'opacity-60 cursor-not-allowed border-slate-800 text-slate-500'
                            : statusCat === 'completed'
                            ? 'border-emerald-500/40 text-emerald-300'
                            : statusCat === 'in_progress'
                            ? 'border-brand-500/40 text-brand-300'
                            : statusCat === 'blocked'
                            ? 'border-rose-500/40 text-rose-300'
                            : 'border-slate-700 text-slate-300'
                        }`}
                      >
                        <option value="pending">Not Started</option>
                        <option value="in_progress">In Progress</option>
                        <option value="blocked">Blocked</option>
                        <option value="completed">Completed</option>
                      </select>
                    </div>

                    {/* Add Progress Update Button */}
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!isAcknowledged}
                      onClick={() => {
                        setSelectedTaskForProgress(t);
                        setIsProgressModalOpen(true);
                      }}
                      leftIcon={<MessageSquare className="h-3.5 w-3.5 text-brand-400" />}
                      className="text-xs font-semibold"
                    >
                      Update
                    </Button>

                    {/* Expand/Collapse Progress History */}
                    {progressNotes.length > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleExpand(t.id)}
                        className="text-xs p-1.5 text-slate-400 hover:text-white"
                        title="Toggle progress history"
                      >
                        {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </Button>
                    )}
                  </div>
                </div>

                {/* Expanded Progress Updates Timeline */}
                {isExpanded && progressNotes.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-800 space-y-2">
                    <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider block">
                      Progress Notes & Timestamped Updates
                    </span>
                    <div className="space-y-2">
                      {progressNotes.map((note, idx) => (
                        <div
                          key={note.id || idx}
                          className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between text-[11px]">
                            <strong className="text-slate-300">{note.author || 'Elena Rostova'}</strong>
                            <span className="font-mono text-slate-500">
                              {note.createdAt || note.created_at
                                ? new Date(note.createdAt || note.created_at).toLocaleString()
                                : 'Recent'}
                            </span>
                          </div>
                          <p className="text-slate-300 leading-relaxed">{note.text || note.update_text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Progress Update Modal */}
      <TaskProgressUpdateModal
        isOpen={isProgressModalOpen}
        onClose={() => {
          setIsProgressModalOpen(false);
          setSelectedTaskForProgress(null);
        }}
        task={selectedTaskForProgress}
        onSaveProgress={async (taskId, updateText, newStatus) => {
          await onAddProgress(taskId, updateText, newStatus);
        }}
      />
    </div>
  );
};

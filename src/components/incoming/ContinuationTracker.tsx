import React, { useState } from 'react';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  Plus,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  GitBranch,
  Calendar,
  Check,
  Send,
} from 'lucide-react';
import { ContinuationTaskItem } from '../../types/incoming';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Textarea } from '../common/Textarea';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../hooks/useAuth';
import { cn } from '../../utils/cn';

interface ContinuationTrackerProps {
  tasks: ContinuationTaskItem[];
  onUpdateStatus: (taskId: string, status: 'pending' | 'in_progress' | 'completed') => Promise<void>;
  onAddProgressNote: (taskId: string, noteText: string, author: string) => Promise<void>;
}

export const ContinuationTracker: React.FC<ContinuationTrackerProps> = ({
  tasks,
  onUpdateStatus,
  onAddProgressNote,
}) => {
  const { user } = useAuth();
  const { success, info } = useToast();
  const [filter, setFilter] = useState<'all' | 'pending' | 'in_progress' | 'completed'>('all');
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [newNoteText, setNewNoteText] = useState<{ [taskId: string]: string }>({});

  const filteredTasks = tasks.filter((t) => {
    if (filter === 'all') return true;
    return t.status === filter;
  });

  const completedCount = tasks.filter((t) => t.status === 'completed').length;
  const inProgressCount = tasks.filter((t) => t.status === 'in_progress').length;
  const pendingCount = tasks.filter((t) => t.status === 'pending').length;

  const handleToggleComplete = async (task: ContinuationTaskItem) => {
    const newStatus = task.status === 'completed' ? 'in_progress' : 'completed';
    await onUpdateStatus(task.id, newStatus);
    if (newStatus === 'completed') {
      success('Task Completed!', `"${task.title}" marked as completed.`);
    } else {
      info('Task Reopened', `"${task.title}" moved to In Progress.`);
    }
  };

  const handleAddNote = async (taskId: string) => {
    const text = newNoteText[taskId]?.trim();
    if (!text) return;

    await onAddProgressNote(taskId, text, user?.name || 'Elena Rostova');
    setNewNoteText((prev) => ({ ...prev, [taskId]: '' }));
    success('Note Added', 'Progress note appended to task record.');
  };

  return (
    <div className="space-y-4">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">
            Progress: <strong className="text-white">{completedCount} of {tasks.length}</strong> Tasks Completed
          </span>
          <span className="font-mono text-xs font-bold text-emerald-400">
            ({Math.round((completedCount / (tasks.length || 1)) * 100)}%)
          </span>
        </div>

        <div className="flex items-center gap-1.5 text-xs">
          <Button
            variant={filter === 'all' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('all')}
            className="text-xs h-7 px-2.5"
          >
            All ({tasks.length})
          </Button>
          <Button
            variant={filter === 'pending' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('pending')}
            className="text-xs h-7 px-2.5 text-amber-300"
          >
            Pending ({pendingCount})
          </Button>
          <Button
            variant={filter === 'in_progress' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('in_progress')}
            className="text-xs h-7 px-2.5 text-brand-300"
          >
            In Progress ({inProgressCount})
          </Button>
          <Button
            variant={filter === 'completed' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('completed')}
            className="text-xs h-7 px-2.5 text-emerald-400"
          >
            Completed ({completedCount})
          </Button>
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-3">
        {filteredTasks.map((task) => {
          const isCompleted = task.status === 'completed';
          const isExpanded = expandedTaskId === task.id;

          return (
            <div
              key={task.id}
              className={cn(
                'rounded-xl border transition-all p-4 space-y-3',
                isCompleted
                  ? 'bg-slate-900/30 border-slate-800/80 opacity-75'
                  : task.status === 'in_progress'
                  ? 'bg-brand-950/20 border-brand-500/30'
                  : 'bg-slate-900/70 border-slate-800'
              )}
            >
              {/* Main Task Row */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <button
                    type="button"
                    onClick={() => handleToggleComplete(task)}
                    className={cn(
                      'mt-0.5 h-5 w-5 rounded-md border flex items-center justify-center transition-colors cursor-pointer shrink-0',
                      isCompleted
                        ? 'bg-emerald-500 border-emerald-500 text-black'
                        : 'border-slate-700 bg-slate-800/60 hover:border-brand-500'
                    )}
                  >
                    {isCompleted && <Check className="h-3.5 w-3.5 stroke-[3]" />}
                  </button>

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4
                        className={cn(
                          'text-sm font-semibold',
                          isCompleted ? 'line-through text-slate-400' : 'text-white'
                        )}
                      >
                        {task.title}
                      </h4>
                      <Badge
                        variant={
                          task.priority === 'critical'
                            ? 'danger'
                            : task.priority === 'high'
                            ? 'warning'
                            : 'neutral'
                        }
                        size="sm"
                      >
                        {task.priority.toUpperCase()}
                      </Badge>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      {task.description}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <select
                    value={task.status}
                    onChange={(e) =>
                      onUpdateStatus(task.id, e.target.value as 'pending' | 'in_progress' | 'completed')
                    }
                    className="rounded-lg bg-slate-900 border border-slate-700 px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-brand-500 cursor-pointer"
                  >
                    <option value="pending">Pending Handover</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>

                  <button
                    type="button"
                    onClick={() => setExpandedTaskId(isExpanded ? null : task.id)}
                    className="p-1 rounded text-slate-400 hover:text-white"
                  >
                    {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Task Metadata: Due Date & Dependencies */}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400">
                <div className="flex items-center gap-3">
                  {task.dueDate && (
                    <span className="flex items-center gap-1 font-mono text-slate-400">
                      <Calendar className="h-3 w-3 text-slate-500" />
                      Due: {task.dueDate}
                    </span>
                  )}
                  {task.dependencies && task.dependencies.length > 0 && (
                    <span className="flex items-center gap-1 text-brand-400 font-mono">
                      <GitBranch className="h-3 w-3" />
                      Prerequisites: {task.dependencies.join(' · ')}
                    </span>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => setExpandedTaskId(isExpanded ? null : task.id)}
                  className="flex items-center gap-1 text-slate-400 hover:text-brand-300 font-mono text-[10px]"
                >
                  <MessageSquare className="h-3 w-3" />
                  <span>{task.progressNotes.length} Notes</span>
                </button>
              </div>

              {/* Expanded Progress Notes Section */}
              {isExpanded && (
                <div className="pt-3 border-t border-slate-800/90 space-y-3 bg-slate-950/40 p-3 rounded-lg">
                  <h5 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                    Task Progress & Handover Audit Notes
                  </h5>

                  {task.progressNotes.length === 0 ? (
                    <p className="text-[11px] text-slate-500 italic">
                      No progress notes logged yet. Add your execution notes below.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {task.progressNotes.map((note) => (
                        <div
                          key={note.id}
                          className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/80 text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between text-[10px] text-slate-400">
                            <span className="font-semibold text-slate-200">{note.author}</span>
                            <span className="font-mono">
                              {new Date(note.createdAt).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-slate-300">{note.text}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Add Progress Note Input */}
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="text"
                      placeholder="Add an update note (e.g. 'Executed test script; validated clean log output')..."
                      value={newNoteText[task.id] || ''}
                      onChange={(e) =>
                        setNewNoteText((prev) => ({ ...prev, [task.id]: e.target.value }))
                      }
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleAddNote(task.id);
                      }}
                      className="flex-1 rounded-lg bg-slate-900 border border-slate-700/80 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
                    />
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleAddNote(task.id)}
                      disabled={!newNoteText[task.id]?.trim()}
                      className="h-8 text-xs px-3"
                    >
                      <Send className="h-3 w-3 mr-1" /> Add
                    </Button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

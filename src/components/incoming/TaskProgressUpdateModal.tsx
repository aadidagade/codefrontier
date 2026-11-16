import React, { useState } from 'react';
import {
  ListTodo,
  CheckCircle2,
  Clock,
  AlertTriangle,
  X,
  MessageSquare,
  ShieldCheck,
  Send,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Textarea } from '../common/Textarea';

interface TaskProgressUpdateModalProps {
  isOpen: boolean;
  onClose: () => void;
  task: any | null;
  onSaveProgress: (taskId: string, updateText: string, newStatus?: string) => Promise<void>;
  isSubmitting?: boolean;
}

export const TaskProgressUpdateModal: React.FC<TaskProgressUpdateModalProps> = ({
  isOpen,
  onClose,
  task,
  onSaveProgress,
  isSubmitting = false,
}) => {
  const [status, setStatus] = useState<string>(task?.status || 'in_progress');
  const [updateText, setUpdateText] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  React.useEffect(() => {
    if (task) {
      setStatus(task.status || 'in_progress');
      setUpdateText('');
      setErrorMsg(null);
    }
  }, [task, isOpen]);

  if (!isOpen || !task) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!updateText.trim()) {
      setErrorMsg('Please enter a brief note describing the progress update or blocker reason.');
      return;
    }
    setErrorMsg(null);
    await onSaveProgress(task.id, updateText.trim(), status);
    onClose();
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg max-h-[90vh] flex flex-col bg-[#0F172A] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-900/60 shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
              <MessageSquare className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Log Task Progress & Status Update
              </h3>
              <p className="text-xs text-slate-400">
                Update operational status and append a timestamped audit record
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

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
          {/* Task Info Card */}
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
            <div className="flex items-center justify-between">
              <Badge variant={getPriorityBadgeVariant(task.priority)} size="sm">
                {(task.priority || 'medium').toUpperCase()}
              </Badge>
              <span className="text-[11px] font-mono text-slate-500">
                Current: {task.status || 'pending'}
              </span>
            </div>
            <h4 className="text-sm font-semibold text-white">
              {task.title}
            </h4>
            {task.description && (
              <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                {task.description}
              </p>
            )}
          </div>

          {/* New Task Status Selector with 4 required statuses */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              Task Status
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { key: 'pending', label: 'Not Started', color: 'border-slate-700 text-slate-300' },
                { key: 'in_progress', label: 'In Progress', color: 'border-brand-500/50 text-brand-300' },
                { key: 'blocked', label: 'Blocked', color: 'border-rose-500/50 text-rose-300' },
                { key: 'completed', label: 'Completed', color: 'border-emerald-500/50 text-emerald-300' },
              ].map((opt) => {
                const isSelected = status === opt.key;
                return (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => setStatus(opt.key)}
                    className={`flex items-center justify-between p-2.5 rounded-xl border text-xs font-medium transition-all ${
                      isSelected
                        ? 'bg-slate-800 border-brand-500 ring-1 ring-brand-500 text-white shadow-sm'
                        : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/50 text-slate-400'
                    }`}
                  >
                    <span>{opt.label}</span>
                    {isSelected && <CheckCircle2 className="h-3.5 w-3.5 text-brand-400" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Progress Update Textarea */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              Progress Update / Notes <span className="text-rose-400">*</span>
            </label>
            <Textarea
              value={updateText}
              onChange={(e) => {
                setUpdateText(e.target.value);
                if (e.target.value.trim()) setErrorMsg(null);
              }}
              placeholder="e.g. Conducted dry-run partition test against staging DB; observed 12ms p99 latency..."
              rows={4}
              className="text-xs bg-slate-900 border-slate-800 focus:border-brand-500 text-slate-200"
            />
            {errorMsg && (
              <p className="text-xs text-rose-400">{errorMsg}</p>
            )}
          </div>

          {/* Timestamp notice */}
          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <Clock className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            <span>
              Timestamped update will be recorded in the task history and activity timeline.
            </span>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-xs text-slate-400"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              leftIcon={<Send className="h-4 w-4" />}
              className="text-xs font-semibold"
            >
              Post Progress Update
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

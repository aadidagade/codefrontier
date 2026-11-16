import React from 'react';
import {
  Clock,
  MessageSquare,
  CheckCircle2,
  ArrowRight,
  User,
  Activity,
} from 'lucide-react';
import { Badge } from '../common/Badge';
import { TaskProgressUpdateItem } from '../../types/handover';

interface RecentProgressFeedProps {
  updates: TaskProgressUpdateItem[];
  className?: string;
}

export const RecentProgressFeed: React.FC<RecentProgressFeedProps> = ({
  updates,
  className = '',
}) => {
  return (
    <div className={`space-y-3.5 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
            <Activity className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-tight">
                6. Recent Progress Updates & Activity Feed
              </h3>
              <Badge variant="ai" size="sm">
                {updates.length} Updates
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400">
              Real-time audit log of task advancements, milestone completions, and progress notes
            </p>
          </div>
        </div>
      </div>

      {updates.length === 0 ? (
        <div className="p-8 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-400">
          No progress updates recorded yet. Acknowledge handover receipt and log your first progress note above.
        </div>
      ) : (
        <div className="space-y-3">
          {updates.map((up) => {
            const formattedDate = up.created_at
              ? new Date(up.created_at).toLocaleString('en-US', {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                })
              : 'Just now';

            return (
              <div
                key={up.id}
                className="p-4 rounded-xl bg-[#0F172A] border border-slate-800/90 hover:border-slate-700 transition-all space-y-2"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="h-6 w-6 rounded-full bg-brand-500/20 text-brand-300 font-bold text-[10px] flex items-center justify-center">
                      {(up.user_name || 'E')[0]}
                    </div>
                    <span className="font-semibold text-white">
                      {up.user_name || 'Elena Rostova'}
                    </span>
                    {up.task_title && (
                      <>
                        <span className="text-slate-600">·</span>
                        <span className="text-brand-300 truncate max-w-xs font-medium">
                          {up.task_title}
                        </span>
                      </>
                    )}
                  </div>

                  <span className="font-mono text-[11px] text-slate-500 flex items-center gap-1">
                    <Clock className="h-3 w-3 text-slate-500" />
                    {formattedDate}
                  </span>
                </div>

                {/* Progress Text */}
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
                  {up.update_text}
                </p>

                {/* Status Transition Badge */}
                {up.status_after && up.status_before && up.status_after !== up.status_before && (
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400 pt-1">
                    <span>Status Transition:</span>
                    <Badge variant="default" size="sm">{up.status_before}</Badge>
                    <ArrowRight className="h-3 w-3 text-slate-500" />
                    <Badge variant="success" size="sm">{up.status_after}</Badge>
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

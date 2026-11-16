import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRightLeft,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  GitBranch,
  Calendar,
  AlertTriangle,
  Eye,
  FileText,
} from 'lucide-react';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { SharedHandoverItem } from '../../types/handover';

interface ReceivedHandoversSectionProps {
  handovers: SharedHandoverItem[];
  selectedHandoverId?: string;
  onSelectHandover?: (handoverId: string) => void;
  onAcknowledgeClick: (handover: SharedHandoverItem) => void;
  className?: string;
}

export const ReceivedHandoversSection: React.FC<ReceivedHandoversSectionProps> = ({
  handovers,
  selectedHandoverId,
  onSelectHandover,
  onAcknowledgeClick,
  className = '',
}) => {
  const navigate = useNavigate();

  const getTransitionBadge = (status: string) => {
    const s = (status || '').toLowerCase();
    if (s.includes('awaiting') || s.includes('pending')) {
      return (
        <Badge variant="warning" size="sm" dot>
          Awaiting Acknowledgement
        </Badge>
      );
    }
    if (s.includes('acknowledged')) {
      return (
        <Badge variant="success" size="sm" dot>
          Acknowledged
        </Badge>
      );
    }
    if (s.includes('in progress')) {
      return (
        <Badge variant="accent" size="sm" dot>
          In Progress
        </Badge>
      );
    }
    if (s.includes('completed')) {
      return (
        <Badge variant="success" size="sm">
          Completed
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
          <div className="h-8 w-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
            <ArrowRightLeft className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-tight">
                2. Received Handovers & Acknowledgement
              </h3>
              <Badge variant="ai" size="sm">
                {handovers.length} Total
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400">
              Formally approved engineering packages transferred to you with verifiable knowledge snapshots
            </p>
          </div>
        </div>
      </div>

      {/* List */}
      <div className="space-y-3">
        {handovers.map((h) => {
          const isSelected = selectedHandoverId === h.id;
          const isAck =
            (h.transition_status || '').toLowerCase().includes('acknowledged') ||
            (h.transition_status || '').toLowerCase().includes('in progress') ||
            (h.transition_status || '').toLowerCase().includes('completed') ||
            Boolean(h.acknowledged_at);

          const formattedAckDate = h.acknowledged_at
            ? new Date(h.acknowledged_at).toLocaleString('en-US', {
                dateStyle: 'medium',
                timeStyle: 'short',
              })
            : null;

          return (
            <div
              key={h.id}
              className={`p-4 sm:p-5 rounded-xl border transition-all ${
                isSelected
                  ? 'bg-slate-900 border-brand-500/60 shadow-lg ring-1 ring-brand-500/30'
                  : 'bg-[#0F172A] border-slate-800/90 hover:border-slate-700'
              }`}
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                {/* Handover Details */}
                <div className="space-y-2 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-brand-400">
                      {h.project_title || 'Project Transfer'}
                    </span>
                    <span className="text-slate-600">·</span>
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-200">
                      {h.version || 'v1.0'}
                    </span>
                    <Badge variant="success" size="sm">
                      APPROVED
                    </Badge>
                    {getTransitionBadge(h.transition_status || 'Awaiting Acknowledgement')}
                  </div>

                  <div>
                    <h4 className="text-base font-bold text-white tracking-tight">
                      {h.title}
                    </h4>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
                    {h.approved_at && (
                      <span className="flex items-center gap-1.5 font-mono text-[11px]">
                        <Calendar className="h-3.5 w-3.5 text-slate-500" />
                        Approved: {new Date(h.approved_at).toLocaleDateString()}
                      </span>
                    )}

                    <span className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-brand-400" />
                      Pending Tasks: <strong className="text-white">{h.pending_tasks_count}</strong>
                    </span>

                    {isAck && (
                      <span className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Acknowledged by {h.acknowledged_by_name || 'Successor'} {formattedAckDate ? `(${formattedAckDate})` : ''}
                      </span>
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-wrap items-center gap-2.5 pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-800/80 shrink-0">
                  {!isAck ? (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => onAcknowledgeClick(h)}
                      leftIcon={<CheckCircle2 className="h-4 w-4" />}
                      className="text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow"
                    >
                      Acknowledge Receipt
                    </Button>
                  ) : (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/30 border border-emerald-500/25 text-emerald-400 text-xs font-semibold select-none font-mono">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>Receipt Confirmed</span>
                    </div>
                  )}

                  {onSelectHandover && (
                    <Button
                      variant={isSelected ? 'secondary' : 'outline'}
                      size="sm"
                      onClick={() => onSelectHandover(h.id)}
                      className="text-xs"
                    >
                      {isSelected ? 'Viewing Tasks' : 'Filter Tasks'}
                    </Button>
                  )}

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/handovers/${h.id}/versions`)}
                    leftIcon={<GitBranch className="h-3.5 w-3.5 text-brand-400" />}
                    className="text-xs"
                    title="View version snapshots and compare revisions"
                  >
                    Versions
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate(`/my-handovers/${h.id}`)}
                    rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                    className="text-xs text-slate-300 hover:text-white"
                  >
                    Full Package
                  </Button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

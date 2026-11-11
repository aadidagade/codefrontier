import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  FileText,
  User,
  ArrowRight,
  ShieldCheck,
  Lock,
  RotateCcw,
  Sparkles,
  GitBranch,
} from 'lucide-react';
import {
  HandoverReviewRecord,
  ReviewDashboardFilter,
  ApprovalStatus,
} from '../../types/review';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { Input } from '../common/Input';
import { cn } from '../../utils/cn';

interface ReviewDashboardViewProps {
  handovers: HandoverReviewRecord[];
  onSelectHandover: (handover: HandoverReviewRecord) => void;
  onResetDemo?: () => void;
}

export const ReviewDashboardView: React.FC<ReviewDashboardViewProps> = ({
  handovers,
  onSelectHandover,
  onResetDemo,
}) => {
  const [filter, setFilter] = useState<ReviewDashboardFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = handovers.filter((h) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const match =
        h.projectName.toLowerCase().includes(q) ||
        h.projectKey.toLowerCase().includes(q) ||
        h.outgoingMember.name.toLowerCase().includes(q) ||
        h.incomingMember.name.toLowerCase().includes(q);
      if (!match) return false;
    }

    if (filter === 'all') return true;
    return h.approvalStatus === filter;
  });

  const getStatusBadge = (status: ApprovalStatus, isLocked: boolean) => {
    switch (status) {
      case 'approved':
        return (
          <Badge variant="success" size="sm" dot>
            {isLocked ? 'Approved & Locked' : 'Approved'}
          </Badge>
        );
      case 'awaiting_review':
        return (
          <Badge variant="warning" size="sm" dot>
            Awaiting Review
          </Badge>
        );
      case 'changes_requested':
        return (
          <Badge variant="accent" size="sm" dot>
            Changes Requested
          </Badge>
        );
      case 'rejected':
        return (
          <Badge variant="danger" size="sm" dot>
            Rejected
          </Badge>
        );
      case 'draft':
      default:
        return (
          <Badge variant="neutral" size="sm">
            Draft
          </Badge>
        );
    }
  };

  const countByStatus = (st: ApprovalStatus) =>
    handovers.filter((h) => h.approvalStatus === st).length;

  return (
    <div className="space-y-6">
      {/* Controls Bar: Search & Filter Pills */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="w-full md:w-80">
          <Input
            placeholder="Search by project, outgoing lead, successor..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            leftIcon={<Search className="h-4 w-4 text-slate-400" />}
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          <Button
            variant={filter === 'all' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('all')}
            className="text-xs h-8"
          >
            All ({handovers.length})
          </Button>
          <Button
            variant={filter === 'awaiting_review' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('awaiting_review')}
            className="text-xs h-8 text-amber-300"
          >
            Awaiting Review ({countByStatus('awaiting_review')})
          </Button>
          <Button
            variant={filter === 'changes_requested' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('changes_requested')}
            className="text-xs h-8 text-orange-400"
          >
            Changes Requested ({countByStatus('changes_requested')})
          </Button>
          <Button
            variant={filter === 'approved' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('approved')}
            className="text-xs h-8 text-emerald-400"
          >
            Approved ({countByStatus('approved')})
          </Button>
          <Button
            variant={filter === 'draft' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('draft')}
            className="text-xs h-8"
          >
            Draft ({countByStatus('draft')})
          </Button>
          <Button
            variant={filter === 'rejected' ? 'danger' : 'ghost'}
            size="sm"
            onClick={() => setFilter('rejected')}
            className="text-xs h-8"
          >
            Rejected ({countByStatus('rejected')})
          </Button>
        </div>
      </div>

      {/* Handover Review Cards Grid */}
      <div className="space-y-4">
        {filtered.length === 0 ? (
          <Card className="bg-[#0F172A] border-slate-800 p-12 text-center">
            <CheckCircle2 className="h-10 w-10 text-slate-500 mx-auto mb-3" />
            <h4 className="text-sm font-semibold text-white">No Handovers Found</h4>
            <p className="text-xs text-slate-400 mt-1">
              No handovers match the current filter or search criteria.
            </p>
          </Card>
        ) : (
          filtered.map((h) => {
            const sections = Object.values(h.sections);
            const approvedCount = sections.filter((s) => s.status === 'approved').length;
            const totalCount = sections.length;
            const progressPercent = Math.round((approvedCount / totalCount) * 100);

            return (
              <Card
                key={h.id}
                onClick={() => onSelectHandover(h)}
                className={cn(
                  'bg-[#0F172A] border transition-all p-5 sm:p-6 space-y-4 hover:border-brand-500/50 cursor-pointer shadow-lg',
                  h.approvalStatus === 'approved'
                    ? 'border-emerald-500/25 bg-emerald-950/5'
                    : h.approvalStatus === 'changes_requested'
                    ? 'border-orange-500/30'
                    : h.approvalStatus === 'rejected'
                    ? 'border-rose-500/30'
                    : 'border-slate-800'
                )}
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center font-bold text-xs shrink-0">
                      {h.version}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-brand-400">
                          {h.projectKey}
                        </span>
                        {getStatusBadge(h.approvalStatus, h.isLocked)}
                        {h.isLocked && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                            <Lock className="h-2.5 w-2.5" /> Immutable
                          </span>
                        )}
                      </div>
                      <h3 className="text-base font-bold text-white tracking-tight mt-0.5">
                        {h.projectName}
                      </h3>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Button
                      variant={h.approvalStatus === 'awaiting_review' ? 'primary' : 'outline'}
                      size="sm"
                      rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                      className="text-xs h-8"
                    >
                      {h.approvalStatus === 'approved'
                        ? 'Inspect Certified Brief'
                        : 'Open Review Workspace'}
                    </Button>
                  </div>
                </div>

                {/* Team Members Transfer Info */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
                    <div className="text-[10px] font-mono text-slate-500 uppercase">
                      Outgoing Team Member
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-6 w-6 rounded-full bg-slate-800 text-slate-200 flex items-center justify-center font-bold text-[10px]">
                        {h.outgoingMember.name[0]}
                      </div>
                      <div className="font-semibold text-white truncate">
                        {h.outgoingMember.name}
                      </div>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
                    <div className="text-[10px] font-mono text-slate-500 uppercase">
                      Incoming Successor
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-6 w-6 rounded-full bg-brand-500/20 text-brand-300 flex items-center justify-center font-bold text-[10px]">
                        {h.incomingMember.name[0]}
                      </div>
                      <div className="font-semibold text-brand-300 truncate">
                        {h.incomingMember.name}
                      </div>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
                    <div className="text-[10px] font-mono text-slate-500 uppercase">
                      Designated Lead Reviewer
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-6 w-6 rounded-full bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold text-[10px]">
                        {h.designatedReviewer.name[0]}
                      </div>
                      <div className="font-semibold text-purple-300 truncate">
                        {h.designatedReviewer.name}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Section Review Progress Bar */}
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">
                      Section Verification Progress: <strong className="text-white">{approvedCount} of {totalCount}</strong> Approved
                    </span>
                    <span className="font-mono text-brand-300 font-bold">
                      {progressPercent}%
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className={cn(
                        'h-full transition-all duration-300',
                        progressPercent === 100
                          ? 'bg-emerald-400'
                          : 'bg-gradient-to-r from-brand-500 to-indigo-400'
                      )}
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                </div>

                {/* Feedback Notes Banner if changes requested or rejected */}
                {h.approvalStatus === 'changes_requested' && h.changesRequestedNotes && (
                  <div className="p-3 rounded-xl bg-orange-500/10 border border-orange-500/25 text-xs text-orange-200">
                    <strong>Changes Requested: </strong>
                    <span>"{h.changesRequestedNotes}"</span>
                  </div>
                )}

                {h.approvalStatus === 'rejected' && h.rejectionReason && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/25 text-xs text-rose-200">
                    <strong>Rejection Reason: </strong>
                    <span>"{h.rejectionReason}"</span>
                  </div>
                )}

                {/* Footer Metadata */}
                <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500 font-mono">
                  <span>Generated: {new Date(h.generatedDate).toLocaleDateString()}</span>
                  <span>Last Updated: {new Date(h.lastUpdated).toLocaleDateString()}</span>
                  <span className="text-brand-400">
                    Evidence Alignment Score: {h.evidenceScore}%
                  </span>
                </div>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
};

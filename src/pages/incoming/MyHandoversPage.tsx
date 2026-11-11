import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Inbox,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  User,
  Calendar,
  Layers,
  Sparkles,
  RotateCcw,
  ListTodo,
} from 'lucide-react';
import { incomingService } from '../../services/incomingService';
import { IncomingHandoverPackage, AcknowledgementStatus } from '../../types/incoming';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { cn } from '../../utils/cn';

export const MyHandoversPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success } = useToast();

  const [packages, setPackages] = useState<IncomingHandoverPackage[]>([]);
  const [filter, setFilter] = useState<'all' | 'pending' | 'acknowledged'>('all');
  const [loading, setLoading] = useState(true);

  const loadPackages = async () => {
    setLoading(true);
    try {
      const data = await incomingService.getMyIncomingHandovers(user?.email || user?.id);
      setPackages(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPackages();
  }, []);

  const filtered = packages.filter((pkg) => {
    if (filter === 'all') return true;
    return pkg.acknowledgementStatus === filter;
  });

  const pendingCount = packages.filter((p) => p.acknowledgementStatus === 'pending').length;
  const acknowledgedCount = packages.filter((p) => p.acknowledgementStatus === 'acknowledged').length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-brand-400 uppercase tracking-wider">
              Successor Portal
            </span>
            <Badge variant="ai" size="sm">
              Incoming Handovers
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
            My Incoming Handovers
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            Projects transferred to you with approved architecture records, assigned responsibilities, blockers, and Day 1 starting actions.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              incomingService.resetDemoData();
              loadPackages();
              success('Demo Reset', 'Reset incoming handover state.');
            }}
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            className="text-xs"
          >
            Reset Demo Data
          </Button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2 text-xs">
          <Button
            variant={filter === 'all' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('all')}
            className="text-xs h-8"
          >
            All Transfers ({packages.length})
          </Button>
          <Button
            variant={filter === 'pending' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('pending')}
            className="text-xs h-8 text-amber-300"
          >
            Pending Acknowledgement ({pendingCount})
          </Button>
          <Button
            variant={filter === 'acknowledged' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('acknowledged')}
            className="text-xs h-8 text-emerald-400"
          >
            Acknowledged ({acknowledgedCount})
          </Button>
        </div>

        <span className="text-[11px] font-mono text-slate-500 hidden sm:inline-block">
          Only approved & certified handovers visible
        </span>
      </div>

      {/* Handover Cards List */}
      <div className="space-y-4">
        {filtered.length === 0 ? (
          <Card className="bg-[#0F172A] border-slate-800 p-12 text-center">
            <Inbox className="h-10 w-10 text-slate-500 mx-auto mb-3" />
            <h4 className="text-sm font-semibold text-white">No Handovers in This View</h4>
            <p className="text-xs text-slate-400 mt-1">
              You have no incoming handovers matching the selected filter.
            </p>
          </Card>
        ) : (
          filtered.map((pkg) => {
            const pendingTasksCount = pkg.responsibilities.filter((t) => t.status !== 'completed').length;
            const isAck = pkg.acknowledgementStatus === 'acknowledged';

            return (
              <Card
                key={pkg.id}
                onClick={() => navigate(`/my-handovers/${pkg.id}`)}
                className={cn(
                  'bg-[#0F172A] border transition-all p-5 sm:p-6 space-y-4 hover:border-brand-500/50 cursor-pointer shadow-lg',
                  isAck
                    ? 'border-emerald-500/25 bg-emerald-950/5'
                    : 'border-amber-500/30 hover:border-amber-500/50'
                )}
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center font-bold text-xs shrink-0">
                      {pkg.version}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-brand-400">
                          {pkg.projectKey}
                        </span>
                        {isAck ? (
                          <Badge variant="success" size="sm" dot>
                            Receipt Acknowledged
                          </Badge>
                        ) : (
                          <Badge variant="warning" size="sm" dot>
                            Pending Acknowledgement
                          </Badge>
                        )}
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          {pkg.introduction.healthScore}% Certified
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-white tracking-tight mt-0.5">
                        {pkg.projectName}
                      </h3>
                    </div>
                  </div>

                  <Button
                    variant={isAck ? 'outline' : 'primary'}
                    size="sm"
                    rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                    className="text-xs h-8"
                  >
                    {isAck ? 'Open Knowledge Overview' : 'Review & Acknowledge'}
                  </Button>
                </div>

                {/* Team Info Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">
                      Outgoing Team Member
                    </span>
                    <div className="flex items-center gap-2">
                      <div className="h-6 w-6 rounded-full bg-slate-800 text-slate-200 flex items-center justify-center font-bold text-[10px]">
                        {pkg.outgoingMember.name[0]}
                      </div>
                      <div className="font-semibold text-white">{pkg.outgoingMember.name}</div>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">
                      Project Lead / Certifier
                    </span>
                    <div className="flex items-center gap-2">
                      <div className="h-6 w-6 rounded-full bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold text-[10px]">
                        {pkg.projectLead.name[0]}
                      </div>
                      <div className="font-semibold text-purple-300">{pkg.projectLead.name}</div>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">
                      Approved Sign-off Date
                    </span>
                    <div className="flex items-center gap-2 font-mono text-slate-200 pt-0.5">
                      <Calendar className="h-4 w-4 text-slate-400" />
                      <span>{new Date(pkg.approvedDate).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                {/* Purpose Brief */}
                <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                  {pkg.introduction.purpose}
                </p>

                {/* Tasks & Acknowledgement Status Footer */}
                <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1.5 text-slate-300">
                      <ListTodo className="h-4 w-4 text-brand-400" />
                      Pending Responsibilities: <strong className="text-white">{pendingTasksCount} Tasks</strong>
                    </span>
                    {pkg.blockers.length > 0 && (
                      <span className="text-amber-400 font-mono text-[11px]">
                        · {pkg.blockers.length} Active Blocker
                      </span>
                    )}
                  </div>

                  {isAck && pkg.acknowledgedAt && (
                    <span className="text-[11px] font-mono text-emerald-400">
                      Acknowledged on {new Date(pkg.acknowledgedAt).toLocaleString()}
                    </span>
                  )}
                </div>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
};

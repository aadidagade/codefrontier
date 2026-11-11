import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FolderGit2,
  ArrowRightLeft,
  CheckSquare,
  AlertTriangle,
  Clock,
  Sparkles,
  Search,
  Plus,
  Users,
  CheckCircle2,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  ArrowRight,
  Filter,
  FileText,
  FileCheck,
  Flame,
  Check,
  ChevronRight,
  Layers,
  Building2,
  Compass,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/common/Card';
import { Modal } from '../../components/common/Modal';
import { Input } from '../../components/common/Input';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import {
  mockProjects,
  mockActivities,
  mockPendingActions,
  mockRecentHandoversList,
  mockHandovers,
  mockConflicts,
} from '../../data/mockData';
import { Project } from '../../types/project';
import { ActivityEvent, PendingAction } from '../../types/dashboard';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, warning, info: toastInfo } = useToast();

  // Filter & Search states
  const [projectSearch, setProjectSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'in_progress' | 'under_review' | 'at_risk'>('all');
  const [activeStatFilter, setActiveStatFilter] = useState<string | null>(null);

  // Interactive Modal States
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [selectedActivity, setSelectedActivity] = useState<ActivityEvent | null>(null);
  const [selectedPendingAction, setSelectedPendingAction] = useState<PendingAction | null>(null);
  const [isNewHandoverModalOpen, setIsNewHandoverModalOpen] = useState(false);

  // Mutable local actions state to enable live interaction
  const [pendingActionsList, setPendingActionsList] = useState<PendingAction[]>(mockPendingActions);

  // Time-aware greeting: Good morning / afternoon / evening
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }, []);

  // Filtered projects
  const filteredProjects = useMemo(() => {
    return mockProjects.filter((p) => {
      const matchesSearch =
        p.title.toLowerCase().includes(projectSearch.toLowerCase()) ||
        p.key.toLowerCase().includes(projectSearch.toLowerCase()) ||
        p.tags.some((t) => t.toLowerCase().includes(projectSearch.toLowerCase()));

      const matchesStatus =
        statusFilter === 'all'
          ? true
          : p.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [projectSearch, statusFilter]);

  // Handle completing a pending action
  const handleResolveAction = (actionId: string, actionTitle: string) => {
    setPendingActionsList((prev) =>
      prev.map((a) => (a.id === actionId ? { ...a, completed: true } : a))
    );
    setSelectedPendingAction(null);
    success('Action Resolved', `Completed: "${actionTitle}". Handover state synchronized.`);
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* 1. WELCOME SECTION */}
      <div className="relative rounded-2xl bg-gradient-to-r from-brand-950/80 via-slate-900 to-indigo-950/70 border border-brand-500/25 p-6 sm:p-8 overflow-hidden shadow-card">
        <div className="absolute right-0 top-0 w-96 h-full bg-brand-500/10 blur-3xl pointer-events-none" />
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-brand-400 uppercase tracking-wider font-mono">
                Project Knowledge Continuity
              </span>
              <Badge variant="ai" size="sm">
                AI Continuous Engine
              </Badge>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {greeting}, {user?.name || 'Elena Rostova'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
              Here's what's happening across your projects. 4 active handovers in flight, 1 high-severity drift conflict detected in failover routing.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate('/documents')}
              leftIcon={<Search className="h-3.5 w-3.5" />}
              className="text-xs"
            >
              Browse Runbooks
            </Button>
            <Button
              variant="ai"
              size="sm"
              onClick={() => setIsNewHandoverModalOpen(true)}
              leftIcon={<Plus className="h-3.5 w-3.5" />}
              className="text-xs"
            >
              Initialize Handover
            </Button>
          </div>
        </div>
      </div>

      {/* 2. STATISTICS CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Projects */}
        <Card
          hoverable
          onClick={() => {
            setActiveStatFilter('projects');
            setStatusFilter('all');
            toastInfo('Filter Applied', 'Showing all 6 monitored projects.');
          }}
          className={`p-5 bg-[#0F172A] border-slate-800 transition-all ${
            activeStatFilter === 'projects' ? 'ring-2 ring-brand-500/50 bg-[#121B32]' : ''
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Total Projects</span>
            <div className="h-8 w-8 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center">
              <FolderGit2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">6</span>
            <span className="text-xs text-emerald-400 font-medium">↑ +2 this month</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Click to view all repositories</p>
        </Card>

        {/* Active Handovers */}
        <Card
          hoverable
          onClick={() => {
            setActiveStatFilter('handovers');
            setStatusFilter('in_progress');
            toastInfo('Filter Applied', 'Filtered to active in-progress handovers.');
          }}
          className={`p-5 bg-[#0F172A] border-slate-800 transition-all ${
            activeStatFilter === 'handovers' ? 'ring-2 ring-brand-500/50 bg-[#121B32]' : ''
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Active Handovers</span>
            <div className="h-8 w-8 rounded-lg bg-indigo-500/10 text-brand-300 flex items-center justify-center">
              <ArrowRightLeft className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">4</span>
            <span className="text-xs text-brand-400 font-medium">2 On Track · 1 At Risk</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Click to filter active sessions</p>
        </Card>

        {/* Pending Approvals */}
        <Card
          hoverable
          onClick={() => {
            setActiveStatFilter('approvals');
            setStatusFilter('under_review');
            toastInfo('Filter Applied', 'Filtered to projects under review.');
          }}
          className={`p-5 bg-[#0F172A] border-slate-800 transition-all ${
            activeStatFilter === 'approvals' ? 'ring-2 ring-brand-500/50 bg-[#121B32]' : ''
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Pending Approvals</span>
            <div className="h-8 w-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <CheckSquare className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">3</span>
            <span className="text-xs text-amber-400 font-medium">Sign-off required</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Click to view pending reviews</p>
        </Card>

        {/* Unresolved Issues */}
        <Card
          hoverable
          onClick={() => {
            setActiveStatFilter('issues');
            setStatusFilter('at_risk');
            warning('High Severity Drift', 'Confluence Runbook contradicts main.tf failover in PAY-V2.');
          }}
          className={`p-5 bg-[#0F172A] border-slate-800 transition-all ${
            activeStatFilter === 'issues' ? 'ring-2 ring-rose-500/50 bg-[#121B32]' : ''
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Unresolved Issues</span>
            <div className="h-8 w-8 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-rose-300">2</span>
            <span className="text-xs text-rose-400 font-medium">1 High Severity</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Click to view at-risk systems</p>
        </Card>
      </div>

      {/* 3. ACTIVE PROJECTS SECTION */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <FolderGit2 className="h-4 w-4 text-brand-400" />
              <span>Active Projects</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Click any project card to inspect knowledge metrics and workspace handover topology
            </p>
          </div>

          {/* Search & Filter Controls */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="relative w-48 sm:w-60">
              <Input
                placeholder="Search projects..."
                value={projectSearch}
                onChange={(e) => setProjectSearch(e.target.value)}
                leftIcon={<Search className="h-3.5 w-3.5" />}
                className="h-8 text-xs py-1"
              />
            </div>

            <div className="flex items-center gap-1 p-0.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
              <button
                onClick={() => setStatusFilter('all')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  statusFilter === 'all'
                    ? 'bg-slate-800 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setStatusFilter('in_progress')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  statusFilter === 'in_progress'
                    ? 'bg-slate-800 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                In Progress
              </button>
              <button
                onClick={() => setStatusFilter('under_review')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  statusFilter === 'under_review'
                    ? 'bg-slate-800 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Under Review
              </button>
              <button
                onClick={() => setStatusFilter('at_risk')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  statusFilter === 'at_risk'
                    ? 'bg-slate-800 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                At Risk
              </button>
            </div>
          </div>
        </div>

        {/* Projects Grid or Useful Empty State */}
        {filteredProjects.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-[#0F172A] border border-slate-800 space-y-3">
            <div className="h-10 w-10 rounded-xl bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
              <FolderGit2 className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-semibold text-white">No matching projects found</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              No projects matched your search term "{projectSearch}" or filter selection.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setProjectSearch('');
                setStatusFilter('all');
                setActiveStatFilter(null);
              }}
              className="text-xs"
            >
              Clear Filters
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredProjects.map((project) => (
              <Card
                key={project.id}
                hoverable
                onClick={() => setSelectedProject(project)}
                className="bg-[#0F172A] border-slate-800 flex flex-col justify-between group"
              >
                <div>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-brand-400 group-hover:text-brand-300 transition-colors">
                        {project.key}
                      </span>
                      <Badge
                        variant={
                          project.status === 'in_progress'
                            ? 'accent'
                            : project.status === 'at_risk'
                            ? 'danger'
                            : project.status === 'under_review'
                            ? 'warning'
                            : 'success'
                        }
                        size="sm"
                        dot
                      >
                        {project.status.replace('_', ' ')}
                      </Badge>
                    </div>

                    <CardTitle className="text-base text-white mt-2 group-hover:text-slate-100 line-clamp-1">
                      {project.title}
                    </CardTitle>
                    <CardDescription className="line-clamp-2 mt-1">
                      {project.description}
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="space-y-3.5 pt-0">
                    {/* Handover Progress Indicator */}
                    <div className="space-y-1.5 p-3 rounded-lg bg-slate-900/60 border border-slate-800/80">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400 font-medium">Handover Progress</span>
                        <span className="font-mono font-bold text-white">
                          {project.handoverProgress}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            project.status === 'at_risk'
                              ? 'bg-rose-500'
                              : project.handoverProgress > 80
                              ? 'bg-emerald-400'
                              : 'bg-brand-500'
                          }`}
                          style={{ width: `${project.handoverProgress}%` }}
                        />
                      </div>
                    </div>

                    {/* Team Members & Last Updated */}
                    <div className="flex items-center justify-between text-xs pt-1">
                      {/* Avatar Stack */}
                      <div className="flex items-center gap-2">
                        <div className="flex -space-x-2 overflow-hidden">
                          {project.members.slice(0, 3).map((m) => (
                            <img
                              key={m.id}
                              src={m.avatarUrl}
                              alt={m.name}
                              className="inline-block h-6 w-6 rounded-full ring-2 ring-[#0F172A] object-cover"
                            />
                          ))}
                        </div>
                        <span className="text-slate-400 text-[11px] font-medium">
                          {project.membersCount} members
                        </span>
                      </div>

                      <div className="text-[11px] text-slate-500 font-mono">
                        {project.lastUpdatedText}
                      </div>
                    </div>
                  </CardContent>
                </div>

                <div className="p-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400 bg-slate-900/30">
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-brand-400" />
                    <span>Health: {project.knowledgeHealthScore}%</span>
                  </div>
                  <span className="text-brand-400 group-hover:text-brand-300 font-medium flex items-center gap-1 text-[11px]">
                    Workspace <ChevronRight className="h-3 w-3" />
                  </span>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* 4 & 5: DUAL COLUMN: RECENT ACTIVITY & PENDING ACTIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* RECENT ACTIVITY (Column 7) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <Clock className="h-4 w-4 text-brand-400" />
              <span>Recent Activity</span>
            </h2>
            <span className="text-xs text-slate-400">Live stream</span>
          </div>

          <Card className="bg-[#0F172A] border-slate-800 divide-y divide-slate-800/60">
            {mockActivities.map((act) => {
              const icons = {
                document_uploaded: <FileText className="h-4 w-4 text-brand-400" />,
                handover_generated: <Sparkles className="h-4 w-4 text-purple-400" />,
                review_requested: <CheckSquare className="h-4 w-4 text-amber-400" />,
                handover_approved: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
                member_acknowledged: <Users className="h-4 w-4 text-teal-400" />,
              };

              return (
                <div
                  key={act.id}
                  onClick={() => setSelectedActivity(act)}
                  className="p-4 hover:bg-slate-850/50 transition-colors cursor-pointer flex items-start gap-3.5 group"
                >
                  <div className="h-8 w-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center shrink-0 mt-0.5 group-hover:border-slate-700">
                    {icons[act.type]}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11px] font-semibold text-brand-400">
                          {act.projectKey}
                        </span>
                        <h4 className="text-xs font-semibold text-white group-hover:text-brand-300 transition-colors truncate">
                          {act.title}
                        </h4>
                      </div>
                      <span className="text-[11px] text-slate-500 shrink-0 font-mono">
                        {act.timeAgo}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                      {act.description}
                    </p>

                    <div className="mt-2 flex items-center gap-3 text-[11px] text-slate-500">
                      <span className="flex items-center gap-1.5 text-slate-300">
                        <img
                          src={act.user.avatarUrl}
                          alt={act.user.name}
                          className="h-4 w-4 rounded-full object-cover"
                        />
                        <span>{act.user.name}</span>
                      </span>
                      <span>•</span>
                      {act.metaBadge && (
                        <Badge variant="neutral" size="sm">
                          {act.metaBadge}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </Card>
        </div>

        {/* PENDING ACTIONS (Column 5) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <CheckSquare className="h-4 w-4 text-amber-400" />
              <span>Pending Actions</span>
            </h2>
            <Badge variant="warning" size="sm">
              {pendingActionsList.filter((a) => !a.completed).length} Requires Attention
            </Badge>
          </div>

          <div className="space-y-3">
            {pendingActionsList.map((item) => {
              if (item.completed) return null;

              return (
                <Card
                  key={item.id}
                  className="bg-[#0F172A] border-slate-800 p-4 space-y-3 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-brand-400">
                          {item.projectKey}
                        </span>
                        <Badge
                          variant={
                            item.priority === 'critical'
                              ? 'danger'
                              : item.priority === 'high'
                              ? 'warning'
                              : 'neutral'
                          }
                          size="sm"
                        >
                          {item.priority}
                        </Badge>
                      </div>
                      <h4 className="text-xs font-semibold text-white mt-1.5">
                        {item.title}
                      </h4>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 leading-relaxed">
                    {item.description}
                  </p>

                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-[11px] text-slate-500 font-mono">
                      Due: {item.dueDate}
                    </span>
                    <Button
                      variant={item.priority === 'critical' ? 'danger' : 'primary'}
                      size="sm"
                      onClick={() => setSelectedPendingAction(item)}
                      className="h-7 text-xs px-3"
                    >
                      {item.actionLabel}
                    </Button>
                  </div>
                </Card>
              );
            })}

            {pendingActionsList.every((a) => a.completed) && (
              <div className="p-8 text-center rounded-xl bg-[#0F172A] border border-slate-800 text-xs text-slate-400 space-y-2">
                <CheckCircle2 className="h-6 w-6 text-emerald-400 mx-auto" />
                <div className="font-semibold text-white">All Pending Actions Completed!</div>
                <p className="text-slate-500">
                  Every handover review, conflict resolution, and ownership verification is up to date.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 6. RECENT HANDOVERS TABLE */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <ArrowRightLeft className="h-4 w-4 text-brand-400" />
              <span>Recent Handovers</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Continuity transfers between outgoing leads and incoming engineering successors
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/handover')}
            className="text-xs text-brand-400 hover:text-brand-300"
            rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
          >
            View All Handovers
          </Button>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-800 bg-[#0F172A]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold text-[11px]">
                  <th className="px-5 py-3.5">Project</th>
                  <th className="px-5 py-3.5">Outgoing Member</th>
                  <th className="px-5 py-3.5">Incoming Member</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Target Date</th>
                  <th className="px-5 py-3.5 text-right">Progress</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {mockRecentHandoversList.map((h) => (
                  <tr
                    key={h.id}
                    onClick={() => navigate('/handover')}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                  >
                    <td className="px-5 py-4">
                      <div className="font-mono text-xs font-bold text-brand-400">
                        {h.projectKey}
                      </div>
                      <div className="text-xs text-slate-300 font-medium">
                        {h.projectName}
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <img
                          src={h.outgoingMember.avatarUrl}
                          alt={h.outgoingMember.name}
                          className="h-6 w-6 rounded-full object-cover"
                        />
                        <div>
                          <div className="text-xs font-medium text-slate-200">
                            {h.outgoingMember.name}
                          </div>
                          <div className="text-[10px] text-slate-500 capitalize">
                            {h.outgoingMember.role.replace('_', ' ')}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <img
                          src={h.incomingMember.avatarUrl}
                          alt={h.incomingMember.name}
                          className="h-6 w-6 rounded-full object-cover"
                        />
                        <div>
                          <div className="text-xs font-medium text-slate-200">
                            {h.incomingMember.name}
                          </div>
                          <div className="text-[10px] text-slate-500 capitalize">
                            {h.incomingMember.role.replace('_', ' ')}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      <Badge
                        variant={
                          h.status === 'in_progress'
                            ? 'accent'
                            : h.status === 'under_review'
                            ? 'warning'
                            : h.status === 'approved'
                            ? 'success'
                            : 'danger'
                        }
                        size="sm"
                        dot
                      >
                        {h.status.replace('_', ' ')}
                      </Badge>
                    </td>

                    <td className="px-5 py-4 font-mono text-slate-400 text-xs">
                      {h.date}
                    </td>

                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2.5">
                        <div className="w-20 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              h.status === 'approved'
                                ? 'bg-emerald-400'
                                : h.status === 'at_risk'
                                ? 'bg-rose-500'
                                : 'bg-brand-500'
                            }`}
                            style={{ width: `${h.progressPercentage}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs font-semibold text-slate-200">
                          {h.progressPercentage}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* MODAL 1: PROJECT WORKSPACE DRAWER / MODAL */}
      {selectedProject && (
        <Modal
          isOpen={Boolean(selectedProject)}
          onClose={() => setSelectedProject(null)}
          maxWidth="lg"
          title={`${selectedProject.key} - ${selectedProject.title}`}
          description={selectedProject.description}
          footer={
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedProject(null)}
              >
                Close
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setSelectedProject(null);
                  navigate('/handover');
                }}
              >
                Open Handover Session
              </Button>
            </>
          }
        >
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-slate-400">Knowledge Health:</span>
                <div className="text-lg font-bold text-emerald-400 mt-1">
                  {selectedProject.knowledgeHealthScore}%
                </div>
              </div>
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-slate-400">Verified Decisions:</span>
                <div className="text-lg font-bold text-brand-300 mt-1">
                  {selectedProject.totalDecisions} ADRs
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
              <div className="font-semibold text-slate-200">Repository & Leads</div>
              <div className="text-slate-400 flex items-center justify-between">
                <span>Owner:</span>
                <span className="text-slate-200 font-medium">{selectedProject.owner.name}</span>
              </div>
              {selectedProject.successor && (
                <div className="text-slate-400 flex items-center justify-between">
                  <span>Successor:</span>
                  <span className="text-slate-200 font-medium">{selectedProject.successor.name}</span>
                </div>
              )}
              {selectedProject.repoUrl && (
                <div className="text-slate-400 flex items-center justify-between pt-1 border-t border-slate-800">
                  <span>GitHub Repository:</span>
                  <a
                    href={selectedProject.repoUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-brand-400 hover:text-brand-300 inline-flex items-center gap-1"
                  >
                    <span>Inspect Code</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}
            </div>

            <div>
              <div className="font-semibold text-slate-200 mb-1.5">Project Tags</div>
              <div className="flex flex-wrap gap-1.5">
                {selectedProject.tags.map((t) => (
                  <span
                    key={t}
                    className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 2: ACTIVITY RECORD DETAIL */}
      {selectedActivity && (
        <Modal
          isOpen={Boolean(selectedActivity)}
          onClose={() => setSelectedActivity(null)}
          title={selectedActivity.title}
          description={`Logged for project ${selectedActivity.projectKey} · ${selectedActivity.timeAgo}`}
          footer={
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedActivity(null)}
            >
              Done
            </Button>
          }
        >
          <div className="space-y-3.5 text-xs">
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 leading-relaxed text-slate-300">
              {selectedActivity.description}
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Triggered by:</span>
              <div className="flex items-center gap-2">
                <img
                  src={selectedActivity.user.avatarUrl}
                  alt={selectedActivity.user.name}
                  className="h-5 w-5 rounded-full object-cover"
                />
                <span className="font-medium text-slate-200">{selectedActivity.user.name}</span>
              </div>
            </div>

            {selectedActivity.linkText && (
              <div className="p-3 rounded-lg bg-brand-500/10 border border-brand-500/25 flex items-center justify-between text-brand-300">
                <span>Associated Knowledge Artifact:</span>
                <span className="font-mono font-semibold">{selectedActivity.linkText}</span>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* MODAL 3: PENDING ACTION RESOLVER */}
      {selectedPendingAction && (
        <Modal
          isOpen={Boolean(selectedPendingAction)}
          onClose={() => setSelectedPendingAction(null)}
          title={selectedPendingAction.title}
          description={`Priority: ${selectedPendingAction.priority.toUpperCase()} · Project: ${selectedPendingAction.projectKey}`}
          footer={
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedPendingAction(null)}
              >
                Cancel
              </Button>
              {selectedPendingAction.title.toLowerCase().includes('conflict') && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    setSelectedPendingAction(null);
                    navigate('/conflicts');
                  }}
                  leftIcon={<Flame className="h-4 w-4" />}
                >
                  Open Conflict Desk
                </Button>
              )}
              {(selectedPendingAction.title.toLowerCase().includes('review') ||
                selectedPendingAction.title.toLowerCase().includes('approve') ||
                selectedPendingAction.title.toLowerCase().includes('handover')) && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    setSelectedPendingAction(null);
                    navigate('/review/rev-auth-zero');
                  }}
                  leftIcon={<ShieldCheck className="h-4 w-4" />}
                >
                  Open Review Workspace
                </Button>
              )}
              <Button
                variant={selectedPendingAction.priority === 'critical' ? 'danger' : 'primary'}
                size="sm"
                onClick={() =>
                  handleResolveAction(selectedPendingAction.id, selectedPendingAction.title)
                }
              >
                Mark as Resolved & Sign Off
              </Button>
            </>
          }
        >
          <div className="space-y-3.5 text-xs">
            <p className="text-slate-300 leading-relaxed">
              {selectedPendingAction.description}
            </p>

            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-200 space-y-1">
              <div className="font-semibold text-amber-300">Verification Requirement:</div>
              <p className="text-[11px] leading-relaxed">
                Resolving this action will trigger an automated AI hash verification and notify incoming successor{' '}
                <strong>{selectedPendingAction.assignedTo.name}</strong>.
              </p>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 4: NEW HANDOVER INITIALIZATION */}
      <Modal
        isOpen={isNewHandoverModalOpen}
        onClose={() => setIsNewHandoverModalOpen(false)}
        title="Initialize New Project Handover"
        description="Select a project and assign incoming engineering successors"
        footer={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsNewHandoverModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="ai"
              size="sm"
              onClick={() => {
                setIsNewHandoverModalOpen(false);
                success('Handover Initialized', 'AI has started scanning repositories for architectural decisions.');
              }}
            >
              Start Handover
            </Button>
          </>
        }
      >
        <div className="space-y-3.5 text-xs">
          <div>
            <label className="block font-medium text-slate-300 mb-1">Target Project</label>
            <select className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2.5 text-slate-200">
              {mockProjects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.key} - {p.title}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-medium text-slate-300 mb-1">Outgoing Lead Engineer</label>
            <input
              type="text"
              readOnly
              value={user?.name || 'Elena Rostova'}
              className="w-full rounded-lg bg-slate-900/60 border border-slate-800 p-2.5 text-slate-400"
            />
          </div>

          <div>
            <label className="block font-medium text-slate-300 mb-1">Incoming Successor Email</label>
            <input
              type="email"
              placeholder="successor@techfrontier.io"
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2.5 text-slate-200"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

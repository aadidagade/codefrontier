import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Inbox,
  ArrowRightLeft,
  CheckCircle2,
  Clock,
  ShieldCheck,
  RotateCcw,
  RefreshCw,
  FolderGit2,
  ListTodo,
  Flame,
  Server,
  Activity,
  Layers,
  Sparkles,
  Lock,
  ArrowRight,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { handoverService } from '../../services/handoverService';
import {
  SharedHandoverItem,
  HandoverContinuityData,
  TaskProgressUpdateItem,
} from '../../types/handover';

import { SharedProjectsSection, SharedProjectSummary } from '../../components/incoming/SharedProjectsSection';
import { ReceivedHandoversSection } from '../../components/incoming/ReceivedHandoversSection';
import { ContinuityTasksManager } from '../../components/incoming/ContinuityTasksManager';
import { UnresolvedIssuesSection } from '../../components/incoming/UnresolvedIssuesSection';
import { ProjectDependenciesSection } from '../../components/incoming/ProjectDependenciesSection';
import { RecentProgressFeed } from '../../components/incoming/RecentProgressFeed';
import { HandoverAcknowledgementModal } from '../../components/incoming/HandoverAcknowledgementModal';

export const IncomingMemberDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, error, info } = useToast();

  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  // Core Data
  const [sharedHandovers, setSharedHandovers] = useState<SharedHandoverItem[]>([]);
  const [selectedHandoverId, setSelectedHandoverId] = useState<string>('');
  const [selectedProjectId, setSelectedProjectId] = useState<string | 'all'>('all');
  const [continuityData, setContinuityData] = useState<HandoverContinuityData | null>(null);

  // Acknowledgement Modal State
  const [acknowledgingHandover, setAcknowledgingHandover] = useState<SharedHandoverItem | null>(null);
  const [isAckModalOpen, setIsAckModalOpen] = useState<boolean>(false);
  const [isSubmittingAck, setIsSubmittingAck] = useState<boolean>(false);

  // Load Dashboard Data from backend database
  const loadDashboardData = async (targetHandoverId?: string) => {
    try {
      const sharedRes = await handoverService.getSharedWithMe();
      const list = sharedRes.data || [];
      setSharedHandovers(list);

      // Determine target handover to load detailed continuity data
      const activeId =
        targetHandoverId ||
        selectedHandoverId ||
        (list.length > 0 ? list[0].id : 'rev-auth-zero');

      setSelectedHandoverId(activeId);

      // Load full continuity details (tasks, blockers, conflicts, dependencies, progress)
      const contRes = await handoverService.getContinuity(activeId);
      if (contRes && contRes.data) {
        setContinuityData(contRes.data);
      }
    } catch (err: any) {
      console.error('Failed to load incoming member dashboard data:', err);
      error('Dashboard Load Error', err?.message || 'Could not fetch continuity records.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData(selectedHandoverId);
    info('Dashboard Synchronized', 'Retrieved latest continuity data from database.');
  };

  // Switch selected handover
  const handleSelectHandover = async (handoverId: string) => {
    setSelectedHandoverId(handoverId);
    setLoading(true);
    try {
      const contRes = await handoverService.getContinuity(handoverId);
      if (contRes && contRes.data) {
        setContinuityData(contRes.data);
      }
    } finally {
      setLoading(false);
    }
  };

  // Open Acknowledgement Modal
  const handleOpenAcknowledge = (h: SharedHandoverItem) => {
    setAcknowledgingHandover(h);
    setIsAckModalOpen(true);
  };

  // Execute Acknowledgement API
  const handleConfirmAcknowledge = async (handoverId: string, notes: string) => {
    setIsSubmittingAck(true);
    try {
      await handoverService.acknowledgeHandover(handoverId, true, notes);
      success(
        'Handover Receipt Formally Acknowledged!',
        'Your acknowledgement has been logged with server-side audit timestamps. Task management is now unlocked.'
      );
      setIsAckModalOpen(false);
      setAcknowledgingHandover(null);
      await loadDashboardData(handoverId);
    } catch (err: any) {
      console.error('Failed to acknowledge handover:', err);
      error('Acknowledgement Failed', err?.message || 'Server error while acknowledging handover.');
    } finally {
      setIsSubmittingAck(false);
    }
  };

  // Execute Task Status Update
  const handleUpdateTaskStatus = async (taskId: string, status: string, notes?: string) => {
    try {
      await handoverService.updateTaskStatus(taskId, status, notes);
      success('Task Status Updated', `Task moved to ${status}.`);
      // Refresh continuity data
      const contRes = await handoverService.getContinuity(selectedHandoverId);
      if (contRes && contRes.data) {
        setContinuityData(contRes.data);
      }
    } catch (err: any) {
      console.error('Failed to update task status:', err);
      error('Task Update Failed', err?.message || 'Could not update task status.');
    }
  };

  // Execute Add Progress Update
  const handleAddProgress = async (taskId: string, updateText: string, newStatus?: string) => {
    try {
      await handoverService.addTaskProgress(taskId, updateText, newStatus);
      success('Progress Note Recorded', 'Update added to activity timeline and task audit history.');
      // Refresh continuity data
      const contRes = await handoverService.getContinuity(selectedHandoverId);
      if (contRes && contRes.data) {
        setContinuityData(contRes.data);
      }
    } catch (err: any) {
      console.error('Failed to log progress note:', err);
      error('Progress Log Failed', err?.message || 'Could not save progress update.');
    }
  };

  // Extract shared projects summary
  const projectsSummary: SharedProjectSummary[] = React.useMemo(() => {
    const projectMap = new Map<string, SharedProjectSummary>();

    sharedHandovers.forEach((h) => {
      const pId = h.project_id || 'proj-default';
      const existing = projectMap.get(pId);
      if (existing) {
        existing.handoversCount += 1;
        existing.pendingTasksCount += h.pending_tasks_count || 0;
      } else {
        projectMap.set(pId, {
          id: pId,
          key: (h.project_title || h.title || 'PROJ').slice(0, 8).toUpperCase(),
          title: h.project_title || h.title || 'Project Transfer',
          leadName: h.assigned_to_name || 'Outgoing Lead',
          status: 'in_progress',
          handoversCount: 1,
          pendingTasksCount: h.pending_tasks_count || 0,
        });
      }
    });

    return Array.from(projectMap.values());
  }, [sharedHandovers]);

  // Determine if active handover is acknowledged
  const activeHandoverObj = sharedHandovers.find((h) => h.id === selectedHandoverId);
  const isCurrentHandoverAcknowledged = React.useMemo(() => {
    if (continuityData) {
      const s = (continuityData.transition_status || '').toLowerCase();
      return (
        s.includes('acknowledged') ||
        s.includes('in progress') ||
        s.includes('completed') ||
        Boolean(continuityData.acknowledged_at)
      );
    }
    if (activeHandoverObj) {
      const s = (activeHandoverObj.transition_status || '').toLowerCase();
      return (
        s.includes('acknowledged') ||
        s.includes('in progress') ||
        s.includes('completed') ||
        Boolean(activeHandoverObj.acknowledged_at)
      );
    }
    return false;
  }, [continuityData, activeHandoverObj]);

  // Filtered handovers based on selected project
  const displayHandovers =
    selectedProjectId === 'all'
      ? sharedHandovers
      : sharedHandovers.filter((h) => h.project_id === selectedProjectId);

  // Metrics calculation
  const totalTasks = continuityData?.all_tasks?.length || 0;
  const completedTasks = continuityData?.completed_tasks?.length || 0;
  const pendingTasks = continuityData?.pending_tasks?.length || 0;
  const blockedTasks = continuityData?.blocked_tasks?.length || 0;
  const blockersCount = continuityData?.unresolved_blockers?.length || 0;
  const conflictsCount = continuityData?.unresolved_conflicts?.length || 0;
  const dependenciesList: any[] = (continuityData as any)?.dependencies || [];
  const progressUpdates: TaskProgressUpdateItem[] = continuityData?.recent_progress_updates || [];

  if (loading && !continuityData) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          <span className="text-xs text-slate-400">Loading Incoming Member Continuity Dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-7 max-w-7xl mx-auto pb-16">
      {/* Top Banner / Role Greeting Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-brand-400 uppercase tracking-wider">
              Successor Continuity Workspace
            </span>
            <Badge variant="ai" size="sm">
              Incoming Member
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Incoming Member Dashboard
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 max-w-2xl">
            Access shared projects, review and acknowledge received handovers, update assigned responsibilities, and monitor blockers and project dependencies.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            isLoading={refreshing}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
            className="text-xs text-slate-300 hover:text-white"
          >
            Refresh Data
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/my-handovers')}
            className="text-xs font-semibold"
          >
            My Handovers List
          </Button>
        </div>
      </div>

      {/* Global Continuity Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="bg-[#0F172A] border-slate-800 p-3.5 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Shared Projects</span>
          <div className="text-xl font-bold text-white">{projectsSummary.length}</div>
          <div className="text-[10px] text-slate-500">Accessible repositories</div>
        </Card>

        <Card className="bg-[#0F172A] border-slate-800 p-3.5 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Received Handovers</span>
          <div className="text-xl font-bold text-brand-400">{sharedHandovers.length}</div>
          <div className="text-[10px] text-slate-500">Certified transfers</div>
        </Card>

        <Card className="bg-[#0F172A] border-slate-800 p-3.5 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Active Status</span>
          <div className="text-sm font-bold text-white truncate">
            {continuityData?.transition_status || 'Awaiting Ack'}
          </div>
          <div className="text-[10px] text-emerald-400">
            {isCurrentHandoverAcknowledged ? 'Receipt confirmed' : 'Action needed'}
          </div>
        </Card>

        <Card className="bg-[#0F172A] border-slate-800 p-3.5 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Pending Tasks</span>
          <div className="text-xl font-bold text-amber-400">{pendingTasks}</div>
          <div className="text-[10px] text-slate-500">{completedTasks} completed</div>
        </Card>

        <Card className="bg-[#0F172A] border-slate-800 p-3.5 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Active Blockers</span>
          <div className="text-xl font-bold text-rose-400">{blockersCount + conflictsCount}</div>
          <div className="text-[10px] text-rose-300/80">{conflictsCount} contradictions</div>
        </Card>

        <Card className="bg-[#0F172A] border-slate-800 p-3.5 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Dependencies</span>
          <div className="text-xl font-bold text-indigo-400">{dependenciesList.length}</div>
          <div className="text-[10px] text-emerald-400">All verified</div>
        </Card>
      </div>

      {/* SECTION 1: Shared Projects */}
      <SharedProjectsSection
        projects={projectsSummary}
        selectedProjectId={selectedProjectId}
        onSelectProject={(pId) => {
          setSelectedProjectId(pId);
          if (pId !== 'all') {
            const match = sharedHandovers.find((h) => h.project_id === pId);
            if (match) handleSelectHandover(match.id);
          }
        }}
      />

      {/* SECTION 2: Received Handovers & Acknowledgement Action */}
      <ReceivedHandoversSection
        handovers={displayHandovers}
        selectedHandoverId={selectedHandoverId}
        onSelectHandover={handleSelectHandover}
        onAcknowledgeClick={handleOpenAcknowledge}
      />

      {/* SECTION 3: Continuation Tasks & Responsibilities (With 4 Statuses & Progress) */}
      <Card className="bg-[#0F172A] border-slate-800 p-5 sm:p-6 shadow-card">
        <ContinuityTasksManager
          tasks={continuityData?.all_tasks || []}
          isAcknowledged={isCurrentHandoverAcknowledged}
          onUpdateStatus={handleUpdateTaskStatus}
          onAddProgress={handleAddProgress}
          onTriggerAcknowledgePrompt={() => {
            if (activeHandoverObj) handleOpenAcknowledge(activeHandoverObj);
            else if (sharedHandovers.length > 0) handleOpenAcknowledge(sharedHandovers[0]);
          }}
        />
      </Card>

      {/* SECTION 4 & 5: Two-Column Layout for Unresolved Issues and Project Dependencies */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Unresolved Issues & Blockers */}
        <Card className="bg-[#0F172A] border-slate-800 p-5 sm:p-6 shadow-card">
          <UnresolvedIssuesSection
            blockers={continuityData?.unresolved_blockers || []}
            conflicts={continuityData?.unresolved_conflicts || []}
          />
        </Card>

        {/* Project Dependencies */}
        <Card className="bg-[#0F172A] border-slate-800 p-5 sm:p-6 shadow-card">
          <ProjectDependenciesSection
            dependencies={dependenciesList}
          />
        </Card>
      </div>

      {/* SECTION 6: Recent Progress Updates Feed */}
      <Card className="bg-[#0F172A] border-slate-800 p-5 sm:p-6 shadow-card">
        <RecentProgressFeed
          updates={progressUpdates}
        />
      </Card>

      {/* Acknowledgement Modal */}
      <HandoverAcknowledgementModal
        isOpen={isAckModalOpen}
        onClose={() => {
          setIsAckModalOpen(false);
          setAcknowledgingHandover(null);
        }}
        handover={acknowledgingHandover}
        onConfirm={handleConfirmAcknowledge}
        isSubmitting={isSubmittingAck}
      />
    </div>
  );
};

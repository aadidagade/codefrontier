import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  FolderGit2,
  ArrowRightLeft,
  FileText,
  Users,
  CheckSquare,
  Clock,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  ExternalLink,
  Plus,
  Calendar,
  Layers,
  ArrowLeft,
  CheckCircle2,
  FileCheck,
  Flame,
  Lock,
  GitBranch,
  ShieldAlert,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/common/Card';
import { Tabs } from '../../components/common/Tabs';
import { Modal } from '../../components/common/Modal';
import { projectService } from '../../services/projectService';
import { Project } from '../../types/project';
import { mockDocuments, mockHandovers, mockConflicts, mockGaps, mockUsers, mockActivities } from '../../data/mockData';
import { useToast } from '../../hooks/useToast';

export const ProjectWorkspacePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { success, warning, info } = useToast();

  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  // Interactive local states for tasks inside workspace
  const [isAddDocModalOpen, setIsAddDocModalOpen] = useState(false);
  const [newDocTitle, setNewDocTitle] = useState('');
  const [newDocType, setNewDocType] = useState('architecture_decision');
  const [newDocExcerpt, setNewDocExcerpt] = useState('');

  // Fetch project from service
  useEffect(() => {
    async function loadProject() {
      setIsLoading(true);
      if (!id) return;
      const res = await projectService.getById(id);
      if (res.data) {
        setProject(res.data);
      }
      setIsLoading(false);
    }
    loadProject();
  }, [id]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh] text-slate-400">
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          <span className="text-sm">Loading Project Workspace...</span>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-12 text-center rounded-2xl bg-[#0F172A] border border-slate-800 space-y-4 max-w-lg mx-auto mt-12">
        <div className="h-12 w-12 rounded-xl bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
          <FolderGit2 className="h-6 w-6" />
        </div>
        <h2 className="text-lg font-bold text-white">Project Not Found</h2>
        <p className="text-xs text-slate-400">
          The requested project workspace could not be located in your active organization.
        </p>
        <Button variant="primary" size="sm" onClick={() => navigate('/projects')}>
          Return to Projects
        </Button>
      </div>
    );
  }

  // Filter associated records
  const projectDocs = mockDocuments.filter((d) => d.projectId === project.id || project.key === 'PAY-V2');
  const projectHandovers = mockHandovers.filter((h) => h.projectId === project.id || project.key === 'PAY-V2');
  const projectActivities = mockActivities.filter((a) => a.projectKey === project.key);

  const handleCreateDocument = () => {
    if (!newDocTitle.trim()) return;
    success('Knowledge Source Added', `"${newDocTitle}" indexed with evidence verification queue.`);
    setIsAddDocModalOpen(false);
    setNewDocTitle('');
    setNewDocExcerpt('');
  };

  const tabsList = [
    { id: 'overview', label: 'Overview', icon: <Layers className="h-3.5 w-3.5" /> },
    { id: 'members', label: 'Members', count: project.membersCount, icon: <Users className="h-3.5 w-3.5" /> },
    { id: 'documents', label: 'Documents & Runbooks', count: project.totalDocuments, icon: <FileText className="h-3.5 w-3.5" /> },
    { id: 'tasks', label: 'Tasks & Checklist', count: 4, icon: <CheckSquare className="h-3.5 w-3.5" /> },
    { id: 'handovers', label: 'Handovers', count: projectHandovers.length, icon: <ArrowRightLeft className="h-3.5 w-3.5" /> },
    { id: 'activity', label: 'Activity Log', count: projectActivities.length, icon: <Clock className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Back button & Breadcrumb header */}
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Link
          to="/projects"
          className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Projects</span>
        </Link>
        <span>/</span>
        <span className="font-mono text-brand-400 font-bold">{project.key}</span>
      </div>

      {/* Workspace Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-brand-950/70 via-slate-900 to-indigo-950/60 border border-brand-500/25 p-6 sm:p-7 relative overflow-hidden shadow-card">
        <div className="absolute right-0 top-0 w-80 h-full bg-brand-500/10 blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="font-mono text-xs font-bold text-brand-400 bg-brand-500/10 px-2.5 py-0.5 rounded border border-brand-500/20">
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
              <Badge variant="neutral" size="sm">
                {project.category}
              </Badge>
            </div>

            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              {project.title}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 max-w-3xl leading-relaxed">
              {project.description}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            {project.repoUrl && (
              <a
                href={project.repoUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-300 hover:text-white hover:border-slate-600 transition-colors"
              >
                <GitBranch className="h-3.5 w-3.5" />
                <span>GitHub Repo</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
            <Button
              variant="outline"
              size="sm"
              leftIcon={<FileText className="h-3.5 w-3.5" />}
              onClick={() => navigate('/knowledge-sources')}
              className="text-xs hidden sm:flex"
            >
              Upload Sources
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Sparkles className="h-3.5 w-3.5" />}
              onClick={() => navigate('/handover/generate')}
              className="text-xs"
            >
              Generate AI Handover
            </Button>
            <Button
              variant="ai"
              size="sm"
              leftIcon={<Plus className="h-3.5 w-3.5" />}
              onClick={() => setIsAddDocModalOpen(true)}
              className="text-xs"
            >
              Add Document
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <Tabs
        tabs={tabsList}
        activeTab={activeTab}
        onChange={setActiveTab}
        variant="pill"
      />

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Top Metrics Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 bg-[#0F172A] border-slate-800">
              <span className="text-xs text-slate-400 font-medium">Knowledge Health</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-emerald-400">
                  {project.knowledgeHealthScore}%
                </span>
                <span className="text-xs text-emerald-400 font-medium">Verified</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">Zero unreferenced claims</p>
            </Card>

            <Card className="p-4 bg-[#0F172A] border-slate-800">
              <span className="text-xs text-slate-400 font-medium">Handover Progress</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-brand-300">
                  {project.handoverProgress}%
                </span>
                <span className="text-xs text-slate-400 font-medium">In Flight</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">Due {project.handoverDueDate}</p>
            </Card>

            <Card className="p-4 bg-[#0F172A] border-slate-800">
              <span className="text-xs text-slate-400 font-medium">Documented ADRs</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white">
                  {project.totalDecisions}
                </span>
                <span className="text-xs text-brand-400 font-medium">PR Linked</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">Architecture Decision Records</p>
            </Card>

            <Card className="p-4 bg-[#0F172A] border-slate-800">
              <span className="text-xs text-slate-400 font-medium">Unresolved Drift Gaps</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-amber-300">
                  {project.unresolvedGaps}
                </span>
                <span className="text-xs text-amber-400 font-medium">Attention needed</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">Configuration drift warnings</p>
            </Card>
          </div>

          {/* Main 2-Column Split */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Col (8) */}
            <div className="lg:col-span-8 space-y-6">
              {/* Progress Overview */}
              <Card className="bg-[#0F172A] border-slate-800 p-5 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-brand-400" />
                    <span>Handover Continuity Progress Overview</span>
                  </h3>
                  <Badge variant="accent" size="sm">
                    {project.handoverProgress}% Ready
                  </Badge>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-slate-300">
                    <span>Overall Handover Readiness</span>
                    <span className="font-mono font-bold">{project.handoverProgress}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-brand-500 to-indigo-500 h-full rounded-full transition-all duration-500"
                      style={{ width: `${project.handoverProgress}%` }}
                    />
                  </div>
                </div>

                {project.handoverPurpose && (
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs">
                    <span className="font-semibold text-slate-200">Handover Mission:</span>
                    <p className="mt-0.5 text-slate-400 leading-relaxed">{project.handoverPurpose}</p>
                  </div>
                )}
              </Card>

              {/* Outstanding Work & Gaps */}
              <Card className="bg-[#0F172A] border-slate-800 p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    <span>Outstanding Work & Knowledge Gaps</span>
                  </h3>
                  <Badge variant="warning" size="sm">
                    {mockConflicts.length} Conflict · {mockGaps.length} Gaps
                  </Badge>
                </div>

                <div className="space-y-2.5 pt-1">
                  {mockConflicts.map((c) => (
                    <div
                      key={c.id}
                      className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/25 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-amber-300">{c.topic}</span>
                        <Badge variant="danger" size="sm">
                          {c.severity} drift
                        </Badge>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed">
                        {c.description}
                      </p>
                      <div className="text-[10px] text-amber-400">
                        Resolution: {c.suggestedResolution}
                      </div>
                    </div>
                  ))}

                  {mockGaps.map((g) => (
                    <div
                      key={g.id}
                      className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-200">{g.area}</span>
                        <Badge variant="warning" size="sm">
                          {g.importance}
                        </Badge>
                      </div>
                      <p className="text-slate-400 text-[11px]">{g.missingInformation}</p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            {/* Right Col (4) */}
            <div className="lg:col-span-4 space-y-6">
              {/* Important Deadlines */}
              <Card className="bg-[#0F172A] border-slate-800 p-5 space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-brand-400" />
                  <span>Important Deadlines</span>
                </h3>

                <div className="space-y-2.5 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Handover Due:</span>
                    <span className="font-mono font-semibold text-brand-300">
                      {project.handoverDueDate}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Expected Delivery:</span>
                    <span className="font-mono font-semibold text-slate-200">
                      {project.expectedDeadline}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Next Secret Key Rotation:</span>
                    <span className="font-mono font-semibold text-amber-400">12 Days</span>
                  </div>
                </div>
              </Card>

              {/* Members and Roles */}
              <Card className="bg-[#0F172A] border-slate-800 p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Users className="h-4 w-4 text-indigo-400" />
                    <span>Project Members</span>
                  </h3>
                  <span className="text-xs text-slate-400">{project.membersCount} total</span>
                </div>

                <div className="space-y-2.5">
                  {project.members.map((m) => (
                    <div
                      key={m.id}
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-900/40 border border-slate-800/80 text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <img
                          src={m.avatarUrl}
                          alt={m.name}
                          className="h-6 w-6 rounded-full object-cover"
                        />
                        <div>
                          <div className="font-medium text-slate-200">{m.name}</div>
                          <div className="text-[10px] text-slate-500 capitalize">{m.role.replace('_', ' ')}</div>
                        </div>
                      </div>

                      {project.owner?.id === m.id && (
                        <Badge variant="accent" size="sm">Lead</Badge>
                      )}
                      {project.successor?.id === m.id && (
                        <Badge variant="ai" size="sm">Successor</Badge>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: MEMBERS */}
      {activeTab === 'members' && (
        <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">Project Members & Access Governance</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Engineers with active credentials, runbook read/write, and audit permissions
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => info('Invite Member', 'Member invitation dialog opened.')}
            >
              Add Member
            </Button>
          </div>

          <div className="divide-y divide-slate-800">
            {project.members.map((m) => (
              <div key={m.id} className="py-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <img
                    src={m.avatarUrl}
                    alt={m.name}
                    className="h-8 w-8 rounded-full object-cover border border-slate-700"
                  />
                  <div>
                    <div className="font-semibold text-white">{m.name}</div>
                    <div className="text-[11px] text-slate-400">{m.email} · {m.department}</div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Badge variant="neutral" size="sm">
                    {m.role.replace('_', ' ')}
                  </Badge>
                  {project.owner?.id === m.id && (
                    <Badge variant="accent" size="sm">Project Lead</Badge>
                  )}
                  {project.successor?.id === m.id && (
                    <Badge variant="ai" size="sm">Successor</Badge>
                  )}
                  <span className="text-[11px] text-slate-500 font-mono">Active {m.lastActive}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* TAB 3: DOCUMENTS */}
      {activeTab === 'documents' && (
        <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">Indexed Knowledge & Runbooks</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Architectural decision records, incident runbooks, and credential guides linked to git evidence
              </p>
            </div>
            <Button
              variant="ai"
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => setIsAddDocModalOpen(true)}
            >
              Add Knowledge Document
            </Button>
          </div>

          <div className="space-y-3 pt-2">
            {projectDocs.map((doc) => (
              <div
                key={doc.id}
                className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-brand-400" />
                    <span className="font-semibold text-white">{doc.title}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="ai" size="sm">
                      {doc.confidenceScore}% Confidence
                    </Badge>
                    <Badge variant="success" size="sm" dot>
                      {doc.verificationStatus}
                    </Badge>
                  </div>
                </div>

                <p className="text-slate-400 leading-relaxed text-[11px]">
                  {doc.excerpt}
                </p>

                {doc.evidenceLinks.length > 0 && (
                  <div className="p-2 rounded bg-slate-800/60 border border-slate-700/60 flex items-center justify-between text-[11px]">
                    <span className="text-slate-400 font-mono">
                      Evidence commit: {doc.evidenceLinks[0].excerpt}
                    </span>
                    <a
                      href={doc.evidenceLinks[0].externalUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="text-brand-400 hover:text-brand-300 font-semibold inline-flex items-center gap-1"
                    >
                      <span>Inspect PR</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* TAB 4: TASKS */}
      {activeTab === 'tasks' && (
        <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">Handover Tasks & Verification Checklists</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Checklist items that must be verified before outgoing lead sign-off
              </p>
            </div>
            <Badge variant="accent" size="sm">
              4 Tasks Remaining
            </Badge>
          </div>

          <div className="space-y-2.5 pt-2">
            {[
              { id: 't-1', title: 'Verify KMS webhook rotation Lambda and signing secret', priority: 'critical', done: true },
              { id: 't-2', title: 'Document Envoy circuit breaker Redis threshold ADR', priority: 'high', done: true },
              { id: 't-3', title: 'Conduct simulated 3:00 AM banking outage walkthrough', priority: 'critical', done: false },
              { id: 't-4', title: 'Transfer 1Password staging bastion vault to incoming successor', priority: 'high', done: true },
            ].map((task) => (
              <div
                key={task.id}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs"
              >
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    defaultChecked={task.done}
                    className="rounded border-slate-700 bg-slate-800 text-brand-600 focus:ring-brand-500 h-4 w-4"
                  />
                  <span className={`font-medium ${task.done ? 'line-through text-slate-500' : 'text-slate-200'}`}>
                    {task.title}
                  </span>
                </div>
                <Badge variant={task.priority === 'critical' ? 'danger' : 'warning'} size="sm">
                  {task.priority}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* TAB 5: HANDOVERS */}
      {activeTab === 'handovers' && (
        <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">Active Handover Sessions</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Active knowledge continuity transfer pipelines for this project
              </p>
            </div>
            <Button
              variant="ai"
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => navigate('/handover')}
            >
              New Handover Session
            </Button>
          </div>

          <div className="space-y-4 pt-2">
            {projectHandovers.map((h) => (
              <div
                key={h.id}
                className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3 text-xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-brand-400">{h.projectKey}</span>
                    <Badge variant="success" size="sm" dot>
                      Stage: {h.currentStage.toUpperCase()}
                    </Badge>
                  </div>
                  <span className="font-mono text-slate-400 text-[11px]">Due {h.targetCompletionDate}</span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-slate-400">
                  <div>Outgoing: <span className="text-white font-medium">{h.initiator.name}</span></div>
                  <div>Successor: <span className="text-white font-medium">{h.recipient.name}</span></div>
                  <div>Readiness: <span className="text-emerald-400 font-bold">{h.aiReadinessScore}%</span></div>
                </div>

                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-brand-500 h-full rounded-full transition-all duration-300"
                    style={{ width: `${h.progressPercentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* TAB 6: ACTIVITY */}
      {activeTab === 'activity' && (
        <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-white">Workspace Audit Trail</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Verified historical changes, runbook updates, and sign-offs for this repository
            </p>
          </div>

          <div className="divide-y divide-slate-800">
            {projectActivities.map((act) => (
              <div key={act.id} className="py-3 flex items-start gap-3 text-xs">
                <div className="h-7 w-7 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-brand-400 shrink-0 mt-0.5">
                  <Clock className="h-3.5 w-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white">{act.title}</span>
                    <span className="text-[11px] text-slate-500 font-mono">{act.timeAgo}</span>
                  </div>
                  <p className="text-slate-400 text-[11px] mt-0.5">{act.description}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Add Document Modal */}
      <Modal
        isOpen={isAddDocModalOpen}
        onClose={() => setIsAddDocModalOpen(false)}
        title="Add Knowledge Document / Runbook"
        description="Index an architectural decision record, runbook, or postmortem for this workspace"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsAddDocModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleCreateDocument}>
              Index Document
            </Button>
          </>
        }
      >
        <div className="space-y-3.5 text-xs">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Document Title *
            </label>
            <input
              type="text"
              placeholder="e.g. ADR-015: Kafka Idempotency & Dispute Handling"
              value={newDocTitle}
              onChange={(e) => setNewDocTitle(e.target.value)}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2.5 text-slate-200 text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Document Type
            </label>
            <select
              value={newDocType}
              onChange={(e) => setNewDocType(e.target.value)}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2.5 text-slate-200 text-xs"
            >
              <option value="architecture_decision">Architecture Decision Record (ADR)</option>
              <option value="runbook">Operational Runbook</option>
              <option value="incident_postmortem">Incident Postmortem</option>
              <option value="credentials_guide">Credentials & Secrets Guide</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Summary / Excerpt
            </label>
            <textarea
              rows={3}
              placeholder="Summary of architectural choices, gotchas, or mitigation commands..."
              value={newDocExcerpt}
              onChange={(e) => setNewDocExcerpt(e.target.value)}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2.5 text-slate-200 text-xs"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

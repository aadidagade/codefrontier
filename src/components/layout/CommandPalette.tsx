import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  FolderGit2,
  ArrowRightLeft,
  FileText,
  CheckSquare,
  Sparkles,
  Plus,
  GitBranch,
  ShieldCheck,
  Users,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Upload,
  BookOpen,
  Hash,
  Briefcase,
  ChevronRight,
  Filter,
} from 'lucide-react';
import { Modal } from '../common/Modal';
import { Badge } from '../common/Badge';
import { mockProjects, mockHandovers, mockDocuments } from '../../data/mockData';
import { teamService } from '../../services/teamService';
import { incomingService } from '../../services/incomingService';
import { documentService } from '../../services/documentService';
import { projectService } from '../../services/projectService';
import { ContinuationTaskItem } from '../../types/incoming';
import { TeamMember } from '../../types/team';
import { KnowledgeSourceDocument } from '../../types/document';
import { Project } from '../../types/project';

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

type SearchCategory = 'all' | 'projects' | 'documents' | 'handovers' | 'tasks' | 'team';

interface SearchTaskResult {
  id: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  projectName: string;
  projectKey: string;
  assigneeName: string;
  url: string;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<SearchCategory>('all');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const [projects, setProjects] = useState<Project[]>(mockProjects);
  const [documents, setDocuments] = useState<KnowledgeSourceDocument[]>([]);
  const [tasks, setTasks] = useState<SearchTaskResult[]>([]);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);

  const navigate = useNavigate();

  // Load live data from services
  useEffect(() => {
    if (isOpen) {
      // 1. Projects
      projectService.getAll().then((res) => {
        if (res.data) setProjects(res.data);
      });

      // 2. Documents
      documentService.getAll().then((res) => {
        if (res.data) setDocuments(res.data);
      });

      // 3. Team Members
      setTeamMembers(teamService.getMembers());

      // 4. Tasks from Incoming Service
      incomingService.getMyIncomingHandovers().then((packages) => {
        const gatheredTasks: SearchTaskResult[] = [];
        packages.forEach((pkg) => {
          pkg.responsibilities.forEach((t) => {
            gatheredTasks.push({
              id: t.id,
              title: t.title,
              description: t.description,
              priority: t.priority,
              status: t.status,
              projectName: pkg.projectName,
              projectKey: pkg.projectKey,
              assigneeName: t.assignedTo?.name || 'Incoming Member',
              url: `/my-handovers/${pkg.id}`,
            });
          });
        });

        // Add additional sample project tasks if empty
        if (gatheredTasks.length === 0) {
          gatheredTasks.push(
            {
              id: 'task-1',
              title: 'Execute PostgreSQL 16 Partition Split Cutover',
              description: 'Zero-downtime maintenance window schema migration and connection drain.',
              priority: 'critical',
              status: 'pending',
              projectName: 'Customer Identity & Passkey Migration',
              projectKey: 'AUTH-ZERO',
              assigneeName: 'Elena Rostova',
              url: '/my-handovers',
            },
            {
              id: 'task-2',
              title: 'Verify Stripe to Adyen Failover Thresholds in Staging',
              description: 'Chaos engineering test with simulated 503 gateway responses.',
              priority: 'high',
              status: 'in_progress',
              projectName: 'Global Payment Orchestration & Multi-PSP Engine',
              projectKey: 'PAY-V2',
              assigneeName: 'David Chen',
              url: '/projects/proj-1',
            },
            {
              id: 'task-3',
              title: 'Conduct Hardware Security Module (HSM) Key Rotation Ceremony',
              description: 'Rotate AES-256 session encryption keys with VP of Engineering sign-off.',
              priority: 'critical',
              status: 'pending',
              projectName: 'Customer Identity & Passkey Migration',
              projectKey: 'AUTH-ZERO',
              assigneeName: 'Kavita Patel',
              url: '/my-handovers',
            }
          );
        }

        setTasks(gatheredTasks);
      });
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setCategory('all');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Filtering
  const q = query.toLowerCase().trim();

  const filteredProjects = useMemo(() => {
    if (!q) return projects;
    return projects.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.key.toLowerCase().includes(q) ||
        (p.description && p.description.toLowerCase().includes(q)) ||
        (p.category && p.category.toLowerCase().includes(q))
    );
  }, [projects, q]);

  const filteredDocuments = useMemo(() => {
    if (!q) return documents;
    return documents.filter(
      (d) =>
        d.fileName.toLowerCase().includes(q) ||
        d.projectKey.toLowerCase().includes(q) ||
        d.fileFormat.toLowerCase().includes(q) ||
        d.uploadedBy.name.toLowerCase().includes(q) ||
        (d.extractedTextPreview && d.extractedTextPreview.toLowerCase().includes(q))
    );
  }, [documents, q]);

  const filteredHandovers = useMemo(() => {
    if (!q) return mockHandovers;
    return mockHandovers.filter(
      (h) =>
        h.projectTitle.toLowerCase().includes(q) ||
        h.projectKey.toLowerCase().includes(q) ||
        h.currentStage.toLowerCase().includes(q)
    );
  }, [q]);

  const filteredTasks = useMemo(() => {
    if (!q) return tasks;
    return tasks.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.projectKey.toLowerCase().includes(q) ||
        t.projectName.toLowerCase().includes(q) ||
        t.assigneeName.toLowerCase().includes(q)
    );
  }, [tasks, q]);

  const filteredTeam = useMemo(() => {
    if (!q) return teamMembers;
    return teamMembers.filter(
      (m) =>
        m.name.toLowerCase().includes(q) ||
        m.email.toLowerCase().includes(q) ||
        m.roleTitle.toLowerCase().includes(q) ||
        m.department.toLowerCase().includes(q) ||
        m.role.toLowerCase().includes(q)
    );
  }, [teamMembers, q]);

  // Combined flat items list for keyboard navigation
  const allSelectableItems = useMemo(() => {
    const list: Array<{ id: string; url: string }> = [];

    if (category === 'all' || category === 'projects') {
      filteredProjects.forEach((p) => list.push({ id: `proj-${p.id}`, url: `/projects/${p.id}` }));
    }
    if (category === 'all' || category === 'documents') {
      filteredDocuments.forEach((d) => list.push({ id: `doc-${d.id}`, url: '/documents' }));
    }
    if (category === 'all' || category === 'handovers') {
      filteredHandovers.forEach((h) => list.push({ id: `ho-${h.id}`, url: '/review' }));
    }
    if (category === 'all' || category === 'tasks') {
      filteredTasks.forEach((t) => list.push({ id: `task-${t.id}`, url: t.url }));
    }
    if (category === 'all' || category === 'team') {
      filteredTeam.forEach((m) => list.push({ id: `team-${m.id}`, url: '/team' }));
    }
    return list;
  }, [
    category,
    filteredProjects,
    filteredDocuments,
    filteredHandovers,
    filteredTasks,
    filteredTeam,
  ]);

  const handleSelect = (url: string) => {
    navigate(url);
    onClose();
  };

  // Keyboard Navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % Math.max(1, allSelectableItems.length));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + allSelectableItems.length) % Math.max(1, allSelectableItems.length));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (allSelectableItems[selectedIndex]) {
          handleSelect(allSelectableItems[selectedIndex].url);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, allSelectableItems]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} maxWidth="2xl" className="p-0 overflow-hidden bg-[#0A0F1D] border-slate-800 shadow-2xl">
      {/* Search Input Bar */}
      <div className="flex items-center px-4 py-3.5 border-b border-slate-800/90 bg-slate-900/60">
        <Search className="h-4 w-4 text-violet-400 shrink-0" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelectedIndex(0);
          }}
          placeholder="Search projects, documents, handovers, continuation tasks, and team members..."
          className="w-full bg-transparent px-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
          autoFocus
        />
        <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-800 border border-slate-700 rounded shrink-0">
          ESC
        </kbd>
      </div>

      {/* Category Pills Bar */}
      <div className="px-3 py-2 border-b border-slate-800/60 bg-slate-950/40 flex items-center gap-1.5 overflow-x-auto text-[11px]">
        {[
          { id: 'all', label: 'All Results' },
          { id: 'projects', label: `Projects (${filteredProjects.length})` },
          { id: 'documents', label: `Documents (${filteredDocuments.length})` },
          { id: 'handovers', label: `Handovers (${filteredHandovers.length})` },
          { id: 'tasks', label: `Tasks (${filteredTasks.length})` },
          { id: 'team', label: `Team (${filteredTeam.length})` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setCategory(tab.id as SearchCategory);
              setSelectedIndex(0);
            }}
            className={`px-2.5 py-1 rounded-full whitespace-nowrap transition-colors ${
              category === tab.id
                ? 'bg-violet-500/20 text-violet-300 font-semibold border border-violet-500/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Results Container */}
      <div className="max-h-[440px] overflow-y-auto p-3 space-y-4">
        {/* Quick Actions (Shown when query is empty) */}
        {!q && category === 'all' && (
          <div>
            <div className="px-2 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Quick Shortcuts & Actions
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 mt-1">
              <button
                onClick={() => handleSelect('/handover/generate')}
                className="flex items-center gap-2.5 px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/80 rounded-lg text-left transition-colors border border-transparent hover:border-slate-700"
              >
                <Sparkles className="h-3.5 w-3.5 text-violet-400" />
                <span>Initialize AI Handover Generation</span>
              </button>
              <button
                onClick={() => handleSelect('/documents')}
                className="flex items-center gap-2.5 px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/80 rounded-lg text-left transition-colors border border-transparent hover:border-slate-700"
              >
                <Upload className="h-3.5 w-3.5 text-cyan-400" />
                <span>Upload Knowledge Source Document</span>
              </button>
              <button
                onClick={() => handleSelect('/my-handovers')}
                className="flex items-center gap-2.5 px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/80 rounded-lg text-left transition-colors border border-transparent hover:border-slate-700"
              >
                <CheckSquare className="h-3.5 w-3.5 text-emerald-400" />
                <span>My Successor Portal (Tasks & Ack)</span>
              </button>
              <button
                onClick={() => handleSelect('/conflicts')}
                className="flex items-center gap-2.5 px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/80 rounded-lg text-left transition-colors border border-transparent hover:border-slate-700"
              >
                <GitBranch className="h-3.5 w-3.5 text-rose-400" />
                <span>Resolve Documentation Conflicts</span>
              </button>
              <button
                onClick={() => handleSelect('/review')}
                className="flex items-center gap-2.5 px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/80 rounded-lg text-left transition-colors border border-transparent hover:border-slate-700"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
                <span>Handover Review Queue & Approvals</span>
              </button>
              <button
                onClick={() => handleSelect('/team')}
                className="flex items-center gap-2.5 px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/80 rounded-lg text-left transition-colors border border-transparent hover:border-slate-700"
              >
                <Users className="h-3.5 w-3.5 text-indigo-400" />
                <span>Team Members & Role Directory</span>
              </button>
            </div>
          </div>
        )}

        {/* 1. PROJECTS */}
        {(category === 'all' || category === 'projects') && filteredProjects.length > 0 && (
          <div>
            <div className="px-2 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span>Projects ({filteredProjects.length})</span>
            </div>
            <div className="space-y-1 mt-1">
              {filteredProjects.map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleSelect(`/projects/${p.id}`)}
                  className="w-full flex items-center justify-between px-3 py-2.5 text-xs text-slate-300 hover:text-white hover:bg-slate-800/70 rounded-lg text-left transition-colors group"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <FolderGit2 className="h-4 w-4 text-violet-400 shrink-0" />
                    <span className="font-mono font-bold text-violet-300 shrink-0">{p.key}</span>
                    <span className="text-slate-200 font-medium truncate">{p.title}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <span className="text-[10px] text-slate-400 uppercase">{p.status.replace('_', ' ')}</span>
                    <span className="text-[10px] text-violet-300 font-mono bg-violet-500/10 px-2 py-0.5 rounded border border-violet-500/20">
                      {p.knowledgeHealthScore}% Health
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 2. DOCUMENTS */}
        {(category === 'all' || category === 'documents') && filteredDocuments.length > 0 && (
          <div>
            <div className="px-2 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Knowledge Source Documents ({filteredDocuments.length})
            </div>
            <div className="space-y-1 mt-1">
              {filteredDocuments.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => handleSelect('/documents')}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/70 rounded-lg text-left transition-colors"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <FileText className="h-4 w-4 text-cyan-400 shrink-0" />
                    <span className="truncate text-slate-200 font-medium">{doc.fileName}</span>
                    <span className="font-mono text-[10px] text-slate-500 uppercase shrink-0">
                      {doc.fileFormat}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <span className="text-[10px] text-slate-400 font-mono">{doc.projectKey}</span>
                    <Badge variant={doc.processingStatus === 'ready' ? 'success' : 'warning'} size="sm">
                      {doc.processingStatus}
                    </Badge>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 3. HANDOVERS */}
        {(category === 'all' || category === 'handovers') && filteredHandovers.length > 0 && (
          <div>
            <div className="px-2 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Handover Sessions & Briefs ({filteredHandovers.length})
            </div>
            <div className="space-y-1 mt-1">
              {filteredHandovers.map((h) => (
                <button
                  key={h.id}
                  onClick={() => handleSelect('/review')}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/70 rounded-lg text-left transition-colors"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <ArrowRightLeft className="h-4 w-4 text-amber-400 shrink-0" />
                    <span className="font-mono font-bold text-amber-300 shrink-0">{h.projectKey}</span>
                    <span className="text-slate-200 truncate">{h.projectTitle}</span>
                  </div>
                  <span className="text-[10px] text-slate-400 capitalize shrink-0 ml-2">
                    Stage: <strong className="text-white">{h.currentStage}</strong>
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 4. TASKS */}
        {(category === 'all' || category === 'tasks') && filteredTasks.length > 0 && (
          <div>
            <div className="px-2 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Continuation Tasks & Responsibilities ({filteredTasks.length})
            </div>
            <div className="space-y-1 mt-1">
              {filteredTasks.map((task) => (
                <button
                  key={task.id}
                  onClick={() => handleSelect(task.url)}
                  className="w-full flex items-center justify-between px-3 py-2.5 text-xs text-slate-300 hover:text-white hover:bg-slate-800/70 rounded-lg text-left transition-colors group"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <CheckSquare className="h-4 w-4 text-emerald-400 shrink-0" />
                    <div className="min-w-0">
                      <div className="text-slate-200 font-medium truncate">{task.title}</div>
                      <div className="text-[10px] text-slate-400 flex items-center gap-2 mt-0.5">
                        <span className="font-mono text-brand-400 font-bold">{task.projectKey}</span>
                        <span>·</span>
                        <span>Assignee: {task.assigneeName}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${
                        task.priority === 'critical'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}
                    >
                      {task.priority}
                    </span>
                    <span className="text-[10px] text-slate-400 capitalize">{task.status.replace('_', ' ')}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 5. TEAM MEMBERS */}
        {(category === 'all' || category === 'team') && filteredTeam.length > 0 && (
          <div>
            <div className="px-2 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Team Members ({filteredTeam.length})
            </div>
            <div className="space-y-1 mt-1">
              {filteredTeam.map((m) => (
                <button
                  key={m.id}
                  onClick={() => handleSelect('/team')}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/70 rounded-lg text-left transition-colors"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <img
                      src={m.avatarUrl}
                      alt={m.name}
                      className="h-6 w-6 rounded-full border border-slate-700 object-cover shrink-0"
                    />
                    <div className="min-w-0">
                      <span className="text-slate-200 font-medium">{m.name}</span>
                      <span className="text-[11px] text-slate-400 font-mono ml-2">({m.email})</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <span className="text-[10px] text-slate-400">{m.department}</span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        m.role === 'project_lead'
                          ? 'bg-violet-500/10 text-violet-300 border border-violet-500/30'
                          : m.role === 'outgoing_member'
                          ? 'bg-amber-500/10 text-amber-300 border border-amber-500/30'
                          : 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {m.role.replace('_', ' ')}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* No Results Fallback */}
        {allSelectableItems.length === 0 && (
          <div className="p-8 text-center text-slate-500 text-xs">
            <Search className="h-8 w-8 text-slate-600 mx-auto mb-2 opacity-50" />
            <p className="font-semibold text-slate-400">No matching results found for "{query}"</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Try searching by project key (e.g. PAY-V2), document name, teammate email, or task title.
            </p>
          </div>
        )}
      </div>

      {/* Footer Shortcut Hints */}
      <div className="px-4 py-2.5 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-3">
          <span>
            Navigate with <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">↑</kbd>{' '}
            <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">↓</kbd>
          </span>
          <span>
            Select with <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">↵</kbd>
          </span>
        </div>
        <span className="font-mono text-slate-500 text-[10px]">Knowledge Handover AI · Unified Index</span>
      </div>
    </Modal>
  );
};

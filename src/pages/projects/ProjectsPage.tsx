import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderGit2,
  Plus,
  Search,
  LayoutGrid,
  List,
  Filter,
  ArrowUpDown,
  ChevronRight,
  Sparkles,
  Users,
  ExternalLink,
  ShieldCheck,
  Clock,
  Calendar,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/common/Card';
import { Input } from '../../components/common/Input';
import { CreateProjectWizardModal } from '../../components/projects/CreateProjectWizardModal';
import { projectService } from '../../services/projectService';
import { Project } from '../../types/project';
import { useToast } from '../../hooks/useToast';

export const ProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const { info } = useToast();

  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters, search, view mode, sorting
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'updated' | 'created' | 'health' | 'name'>('updated');
  const [isWizardOpen, setIsWizardOpen] = useState(false);

  // Load projects from persistent projectService
  const loadProjects = async () => {
    setIsLoading(true);
    const res = await projectService.getAll();
    if (res.data) {
      setProjects(res.data);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    loadProjects();
  }, []);

  // Filter and sort projects
  const filteredProjects = useMemo(() => {
    return projects
      .filter((p) => {
        const matchesSearch =
          p.title.toLowerCase().includes(search.toLowerCase()) ||
          p.key.toLowerCase().includes(search.toLowerCase()) ||
          p.description.toLowerCase().includes(search.toLowerCase()) ||
          p.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()));

        const matchesStatus =
          statusFilter === 'all'
            ? true
            : statusFilter === 'active'
            ? p.status === 'in_progress'
            : statusFilter === 'completed'
            ? p.status === 'approved'
            : statusFilter === 'archived'
            ? p.status === 'archived'
            : p.status === statusFilter;

        const matchesCategory =
          categoryFilter === 'all'
            ? true
            : p.category.toLowerCase() === categoryFilter.toLowerCase();

        return matchesSearch && matchesStatus && matchesCategory;
      })
      .sort((a, b) => {
        if (sortBy === 'name') return a.title.localeCompare(b.title);
        if (sortBy === 'health') return b.knowledgeHealthScore - a.knowledgeHealthScore;
        if (sortBy === 'created') return (b.createdAt || '').localeCompare(a.createdAt || '');
        // default: updated
        return b.handoverProgress - a.handoverProgress;
      });
  }, [projects, search, statusFilter, categoryFilter, sortBy]);

  const handleProjectCreated = (newProject: Project) => {
    setProjects((prev) => [newProject, ...prev]);
    navigate(`/projects/${newProject.id}`);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-brand-400 uppercase tracking-wider font-mono">
              Knowledge Workspaces
            </span>
            <Badge variant="neutral" size="sm">
              {projects.length} Total
            </Badge>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1">
            Projects & Repositories
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage repository continuity, handover sessions, and successor ownership assignments
          </p>
        </div>

        <Button
          variant="ai"
          size="md"
          leftIcon={<Plus className="h-4 w-4" />}
          onClick={() => setIsWizardOpen(true)}
          className="text-xs font-semibold"
        >
          Create Project
        </Button>
      </div>

      {/* Control Bar: Search, Filters, Sort, View Toggle */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        {/* Search */}
        <div className="flex-1 max-w-md">
          <Input
            placeholder="Search projects by key, name, tag, or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            leftIcon={<Search className="h-4 w-4 text-slate-400" />}
            className="h-9 text-xs"
          />
        </div>

        {/* Filter Pills & View Mode */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Status Filter */}
          <div className="flex items-center gap-1 p-0.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            {[
              { id: 'all', label: 'All' },
              { id: 'active', label: 'Active' },
              { id: 'under_review', label: 'Review' },
              { id: 'completed', label: 'Completed' },
              { id: 'at_risk', label: 'At Risk' },
            ].map((st) => (
              <button
                key={st.id}
                onClick={() => setStatusFilter(st.id)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  statusFilter === st.id
                    ? 'bg-slate-800 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>

          {/* Sort Dropdown */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
            <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-transparent text-xs text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="updated" className="bg-slate-900 text-slate-200">Sort: Last Updated</option>
              <option value="health" className="bg-slate-900 text-slate-200">Sort: Health Score</option>
              <option value="created" className="bg-slate-900 text-slate-200">Sort: Creation Date</option>
              <option value="name" className="bg-slate-900 text-slate-200">Sort: Name (A-Z)</option>
            </select>
          </div>

          {/* Grid / List View Toggle */}
          <div className="flex items-center p-0.5 rounded-lg bg-slate-900 border border-slate-800">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-md transition-colors ${
                viewMode === 'grid'
                  ? 'bg-slate-800 text-brand-400'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Grid View"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-md transition-colors ${
                viewMode === 'list'
                  ? 'bg-slate-800 text-brand-400'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="List View"
            >
              <List className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Projects Content: Grid or List */}
      {isLoading ? (
        <div className="py-16 text-center text-slate-400">
          <div className="flex items-center justify-center gap-2">
            <div className="h-5 w-5 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            <span className="text-xs">Loading projects...</span>
          </div>
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-[#0F172A] border border-slate-800 space-y-3">
          <div className="h-10 w-10 rounded-xl bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
            <FolderGit2 className="h-5 w-5" />
          </div>
          <h3 className="text-sm font-semibold text-white">No projects found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            No projects matched your search "{search}" or status filter.
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearch('');
                setStatusFilter('all');
                setCategoryFilter('all');
              }}
              className="text-xs"
            >
              Reset Filters
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsWizardOpen(true)}
              className="text-xs"
            >
              Create Project
            </Button>
          </div>
        </div>
      ) : viewMode === 'grid' ? (
        /* GRID VIEW */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((p) => (
            <Card
              key={p.id}
              hoverable
              onClick={() => navigate(`/projects/${p.id}`)}
              className="bg-[#0F172A] border-slate-800 flex flex-col justify-between group"
            >
              <div>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-brand-400 group-hover:text-brand-300 transition-colors">
                      {p.key}
                    </span>
                    <Badge
                      variant={
                        p.status === 'in_progress'
                          ? 'accent'
                          : p.status === 'at_risk'
                          ? 'danger'
                          : p.status === 'under_review'
                          ? 'warning'
                          : 'success'
                      }
                      size="sm"
                      dot
                    >
                      {p.status.replace('_', ' ')}
                    </Badge>
                  </div>

                  <CardTitle className="text-base text-white mt-2 group-hover:text-slate-100 line-clamp-1">
                    {p.title}
                  </CardTitle>
                  <CardDescription className="line-clamp-2 mt-1">
                    {p.description}
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-3 pt-0">
                  {/* Category tag */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 border border-slate-700/60">
                      {p.category}
                    </span>
                    <span className="text-[10px] text-emerald-400 font-mono">
                      {p.knowledgeHealthScore}% Health
                    </span>
                  </div>

                  {/* Handover Progress Indicator */}
                  <div className="space-y-1.5 p-3 rounded-lg bg-slate-900/60 border border-slate-800/80">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 font-medium">Handover Progress</span>
                      <span className="font-mono font-bold text-white">{p.handoverProgress}%</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          p.status === 'at_risk'
                            ? 'bg-rose-500'
                            : p.handoverProgress > 80
                            ? 'bg-emerald-400'
                            : 'bg-brand-500'
                        }`}
                        style={{ width: `${p.handoverProgress}%` }}
                      />
                    </div>
                  </div>

                  {/* Members & Last Activity */}
                  <div className="flex items-center justify-between text-xs pt-1">
                    <div className="flex items-center gap-2">
                      <div className="flex -space-x-2 overflow-hidden">
                        {p.members.slice(0, 3).map((m) => (
                          <img
                            key={m.id}
                            src={m.avatarUrl}
                            alt={m.name}
                            className="inline-block h-6 w-6 rounded-full ring-2 ring-[#0F172A] object-cover"
                          />
                        ))}
                      </div>
                      <span className="text-slate-400 text-[11px]">
                        {p.membersCount} members
                      </span>
                    </div>

                    <span className="text-[11px] text-slate-500 font-mono">
                      {p.lastUpdatedText}
                    </span>
                  </div>
                </CardContent>
              </div>

              <div className="p-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400 bg-slate-900/30">
                <span className="text-[11px] text-slate-400">
                  {p.totalDocuments} verified docs
                </span>
                <span className="text-brand-400 group-hover:text-brand-300 font-semibold flex items-center gap-1 text-[11px]">
                  Workspace <ChevronRight className="h-3 w-3" />
                </span>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        /* LIST VIEW */
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-[#0F172A]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold text-[11px]">
                  <th className="px-5 py-3.5">Project</th>
                  <th className="px-5 py-3.5">Category</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Members</th>
                  <th className="px-5 py-3.5">Last Activity</th>
                  <th className="px-5 py-3.5">Health</th>
                  <th className="px-5 py-3.5 text-right">Handover Progress</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {filteredProjects.map((p) => (
                  <tr
                    key={p.id}
                    onClick={() => navigate(`/projects/${p.id}`)}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer group"
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-brand-400 group-hover:text-brand-300">
                          {p.key}
                        </span>
                        <div className="font-semibold text-white truncate max-w-xs">{p.title}</div>
                      </div>
                      <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">{p.description}</div>
                    </td>

                    <td className="px-5 py-4">
                      <span className="font-mono text-[11px] text-slate-300 bg-slate-800 px-2 py-0.5 rounded">
                        {p.category}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      <Badge
                        variant={
                          p.status === 'in_progress'
                            ? 'accent'
                            : p.status === 'at_risk'
                            ? 'danger'
                            : p.status === 'under_review'
                            ? 'warning'
                            : 'success'
                        }
                        size="sm"
                        dot
                      >
                        {p.status.replace('_', ' ')}
                      </Badge>
                    </td>

                    <td className="px-5 py-4">
                      <div className="flex items-center gap-1.5">
                        <div className="flex -space-x-1.5 overflow-hidden">
                          {p.members.slice(0, 3).map((m) => (
                            <img
                              key={m.id}
                              src={m.avatarUrl}
                              alt={m.name}
                              className="h-5 w-5 rounded-full object-cover ring-1 ring-[#0F172A]"
                            />
                          ))}
                        </div>
                        <span className="text-slate-400 text-[11px] font-mono">
                          {p.membersCount}
                        </span>
                      </div>
                    </td>

                    <td className="px-5 py-4 font-mono text-slate-400 text-[11px]">
                      {p.lastUpdatedText}
                    </td>

                    <td className="px-5 py-4">
                      <span className="font-mono text-xs font-bold text-emerald-400">
                        {p.knowledgeHealthScore}%
                      </span>
                    </td>

                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2.5">
                        <div className="w-20 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              p.status === 'at_risk' ? 'bg-rose-500' : 'bg-brand-500'
                            }`}
                            style={{ width: `${p.handoverProgress}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs font-semibold text-slate-200">
                          {p.handoverProgress}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Multi-step Project Creation Wizard Modal */}
      <CreateProjectWizardModal
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        onSuccess={handleProjectCreated}
      />
    </div>
  );
};

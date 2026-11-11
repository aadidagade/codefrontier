import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ListTodo,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Filter,
  ArrowRight,
  Plus,
  Search,
  MessageSquare,
  Calendar,
  Send,
  Trash2,
  FolderGit2,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { Modal } from '../../components/common/Modal';
import { Skeleton } from '../../components/common/Skeleton';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../hooks/useToast';
import { useRole } from '../../context/RoleContext';
import { taskService, UnifiedTask } from '../../services/taskService';
import { mockProjects, mockUsers, mockCurrentUser } from '../../data/mockData';

export const MyTasksPage: React.FC = () => {
  const navigate = useNavigate();
  const { roleLabel } = useRole();
  const { success, info } = useToast();

  const [tasks, setTasks] = useState<UnifiedTask[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedPriority, setSelectedPriority] = useState<string>('all');
  const [selectedProject, setSelectedProject] = useState<string>('all');

  // Expanded notes thread map
  const [expandedNotes, setExpandedNotes] = useState<Record<string, boolean>>({});
  const [noteInputs, setNoteInputs] = useState<Record<string, string>>({});

  // Create Task Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState<'critical' | 'high' | 'medium'>('high');
  const [newProjectId, setNewProjectId] = useState<string>(mockProjects[0]?.id || '');
  const [newDueDate, setNewDueDate] = useState<string>(
    new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0]
  );

  const refreshTasks = () => {
    const list = taskService.getTasks({
      status: selectedStatus,
      priority: selectedPriority,
      projectId: selectedProject,
      query: searchQuery,
    });
    setTasks(list);
    setIsLoading(false);
  };

  useEffect(() => {
    setIsLoading(true);
    const timer = setTimeout(() => {
      refreshTasks();
    }, 200);
    const unsubscribe = taskService.subscribe(refreshTasks);
    return () => {
      clearTimeout(timer);
      unsubscribe();
    };
  }, [selectedStatus, selectedPriority, selectedProject, searchQuery]);

  const handleToggle = (id: string) => {
    const updated = taskService.toggleTaskCompletion(id);
    if (updated) {
      if (updated.status === 'completed') {
        success('Task Completed', `"${updated.title}" marked as resolved.`);
      } else {
        info('Task Reopened', `"${updated.title}" returned to pending.`);
      }
    }
  };

  const handleStatusChange = (id: string, status: 'pending' | 'in_progress' | 'completed') => {
    taskService.updateTaskStatus(id, status);
    success('Status Updated', `Task moved to ${status.replace('_', ' ')}.`);
  };

  const toggleNotesExpanded = (taskId: string) => {
    setExpandedNotes((prev) => ({ ...prev, [taskId]: !prev[taskId] }));
  };

  const handleAddNote = (taskId: string) => {
    const text = noteInputs[taskId];
    if (!text || !text.trim()) return;

    taskService.addProgressNote(taskId, text, mockCurrentUser.name);
    setNoteInputs((prev) => ({ ...prev, [taskId]: '' }));
    success('Note Logged', 'Continuation note appended to task audit trail.');
  };

  const handleCreateTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    taskService.createTask({
      title: newTitle,
      description: newDesc,
      priority: newPriority,
      projectId: newProjectId,
      dueDate: newDueDate,
    });

    setIsCreateOpen(false);
    setNewTitle('');
    setNewDesc('');
    success('Task Created', 'New action item added to workspace.');
  };

  // Metrics
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter((t) => t.status === 'completed').length;
  const criticalTasks = tasks.filter((t) => t.priority === 'critical' && t.status !== 'completed').length;
  const inProgressTasks = tasks.filter((t) => t.status === 'in_progress').length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Tasks & Responsibilities</h1>
            <Badge variant="accent" size="sm">
              {totalTasks} Items
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Continuation responsibilities, verification runbooks, and handover action items
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/my-handovers')}
            rightIcon={<ArrowRight className="h-4 w-4" />}
          >
            My Handovers
          </Button>

          <Button
            variant="primary"
            size="sm"
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={() => setIsCreateOpen(true)}
          >
            Add Task
          </Button>
        </div>
      </div>

      {/* Metrics Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
          <div className="text-[11px] font-medium text-slate-400">Total Assigned</div>
          <div className="text-xl font-bold text-white mt-1">{totalTasks}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
          <div className="text-[11px] font-medium text-amber-400">In Progress</div>
          <div className="text-xl font-bold text-amber-400 mt-1">{inProgressTasks}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
          <div className="text-[11px] font-medium text-rose-400">Critical Pending</div>
          <div className="text-xl font-bold text-rose-400 mt-1">{criticalTasks}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
          <div className="text-[11px] font-medium text-emerald-400">Completed</div>
          <div className="text-xl font-bold text-emerald-400 mt-1">{completedTasks}</div>
        </div>
      </div>

      {/* Toolbar: Search & Filters */}
      <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search tasks, descriptions, or project keys..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Status */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-2.5 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
          </select>

          {/* Priority */}
          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="px-2.5 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="all">All Priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
          </select>

          {/* Project */}
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="px-2.5 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-brand-500 max-w-[180px] truncate"
          >
            <option value="all">All Projects</option>
            {mockProjects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.key} - {p.title}
              </option>
            ))}
          </select>

          {(searchQuery || selectedStatus !== 'all' || selectedPriority !== 'all' || selectedProject !== 'all') && (
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedStatus('all');
                setSelectedPriority('all');
                setSelectedProject('all');
              }}
              className="px-2 py-1 text-xs text-slate-400 hover:text-white underline"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Tasks List */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, idx) => (
            <Card key={idx} className="p-4 bg-[#0F172A] border-slate-800 space-y-2">
              <div className="flex items-center gap-3">
                <Skeleton variant="rectangular" width={18} height={18} />
                <Skeleton variant="text" width="60%" height={16} />
              </div>
              <Skeleton variant="text" width="85%" height={12} className="ml-7" />
            </Card>
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState
          icon={ListTodo}
          title="No tasks match your filters"
          description="Adjust your search query or reset the filters to see active continuation items and action items."
          actionLabel="Clear Filters"
          onAction={() => {
            setSearchQuery('');
            setSelectedStatus('all');
            setSelectedPriority('all');
            setSelectedProject('all');
          }}
        />
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => {
            const isCompleted = task.status === 'completed';
            const isExpanded = !!expandedNotes[task.id];

            return (
              <Card
                key={task.id}
                className={`p-4 bg-[#0F172A] border-slate-800 hover:border-slate-700 transition-all ${
                  isCompleted ? 'opacity-65 bg-slate-900/30' : ''
                }`}
              >
                <div className="flex items-start gap-3.5">
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={isCompleted}
                    onChange={() => handleToggle(task.id)}
                    className="mt-1 h-4 w-4 rounded border-slate-700 bg-slate-800 text-brand-500 focus:ring-0 cursor-pointer shrink-0"
                    title={isCompleted ? 'Mark as Incomplete' : 'Mark as Completed'}
                  />

                  {/* Body */}
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-mono text-xs font-bold text-violet-400 shrink-0">
                          {task.projectKey}
                        </span>
                        <h3
                          className={`text-sm font-semibold text-white truncate ${
                            isCompleted ? 'line-through text-slate-400' : ''
                          }`}
                        >
                          {task.title}
                        </h3>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Badge
                          variant={
                            task.priority === 'critical'
                              ? 'danger'
                              : task.priority === 'high'
                              ? 'warning'
                              : 'neutral'
                          }
                          size="sm"
                        >
                          {task.priority}
                        </Badge>

                        <select
                          value={task.status}
                          onChange={(e) =>
                            handleStatusChange(
                              task.id,
                              e.target.value as 'pending' | 'in_progress' | 'completed'
                            )
                          }
                          className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-[11px] text-slate-300 focus:outline-none"
                        >
                          <option value="pending">Pending</option>
                          <option value="in_progress">In Progress</option>
                          <option value="completed">Completed</option>
                        </select>
                      </div>
                    </div>

                    <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                      {task.description}
                    </p>

                    {/* Metadata & Actions */}
                    <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-400">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3 text-slate-500" />
                          <span>Due: {task.dueDate}</span>
                        </span>

                        <span className="flex items-center gap-1.5">
                          <img
                            src={task.assignedTo.avatarUrl}
                            alt={task.assignedTo.name}
                            className="h-4 w-4 rounded-full border border-slate-700 object-cover"
                          />
                          <span>{task.assignedTo.name}</span>
                        </span>

                        {task.handoverId && (
                          <span
                            onClick={() => navigate(`/my-handovers/${task.handoverId}`)}
                            className="text-violet-400 hover:underline cursor-pointer flex items-center gap-1"
                          >
                            <Sparkles className="h-3 w-3" />
                            <span>Handover Package</span>
                          </span>
                        )}
                      </div>

                      {/* Notes Toggle Button */}
                      <button
                        onClick={() => toggleNotesExpanded(task.id)}
                        className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
                      >
                        <MessageSquare className="h-3 w-3 text-brand-400" />
                        <span>
                          {task.progressNotes.length}{' '}
                          {task.progressNotes.length === 1 ? 'Note' : 'Notes'}
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="h-3 w-3 ml-0.5" />
                        ) : (
                          <ChevronDown className="h-3 w-3 ml-0.5" />
                        )}
                      </button>
                    </div>

                    {/* Expandable Progress Notes Section */}
                    {isExpanded && (
                      <div className="mt-3 p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-3">
                        <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                          Continuation Notes & Execution Log
                        </div>

                        {task.progressNotes.length === 0 ? (
                          <p className="text-xs text-slate-500 italic">No notes logged yet.</p>
                        ) : (
                          <div className="space-y-2">
                            {task.progressNotes.map((note) => (
                              <div
                                key={note.id}
                                className="p-2.5 rounded bg-slate-950/60 border border-slate-800 text-xs text-slate-300"
                              >
                                <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
                                  <span className="font-semibold text-slate-400">{note.author}</span>
                                  <span>{new Date(note.createdAt).toLocaleString()}</span>
                                </div>
                                <p className="leading-relaxed">{note.text}</p>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Add note input */}
                        <div className="flex items-center gap-2 pt-1">
                          <input
                            type="text"
                            placeholder="Log progress, staging test results, or next steps..."
                            value={noteInputs[task.id] || ''}
                            onChange={(e) =>
                              setNoteInputs((prev) => ({ ...prev, [task.id]: e.target.value }))
                            }
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleAddNote(task.id);
                            }}
                            className="flex-1 px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
                          />
                          <Button
                            variant="secondary"
                            size="sm"
                            leftIcon={<Send className="h-3 w-3" />}
                            onClick={() => handleAddNote(task.id)}
                          >
                            Post Note
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* CREATE TASK MODAL */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        maxWidth="md"
        title="Add Project Action Item"
      >
        <form onSubmit={handleCreateTask} className="space-y-4">
          <p className="text-xs text-slate-400">
            Create an operational task or verification milestone assigned to your project workspace.
          </p>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Task Title <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Conduct DB Failover Dry Run in Staging"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Description</label>
            <textarea
              rows={2}
              placeholder="Detailed technical context, acceptance criteria, or command line instructions..."
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 resize-none"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Priority</label>
              <select
                value={newPriority}
                onChange={(e) => setNewPriority(e.target.value as any)}
                className="w-full px-2.5 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Project</label>
              <select
                value={newProjectId}
                onChange={(e) => setNewProjectId(e.target.value)}
                className="w-full px-2.5 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white truncate"
              >
                {mockProjects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.key}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Due Date</label>
              <input
                type="date"
                value={newDueDate}
                onChange={(e) => setNewDueDate(e.target.value)}
                className="w-full px-2.5 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
              />
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2">
            <Button variant="ghost" size="sm" type="button" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit" leftIcon={<Plus className="h-3.5 w-3.5" />}>
              Create Task
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Clock,
  ShieldCheck,
  ShieldAlert,
  Search,
  Filter,
  Calendar,
  User as UserIcon,
  Layers,
  ArrowLeft,
  FileText,
  RotateCcw,
  ExternalLink,
  ChevronRight,
  Code2,
  Copy,
  Check,
  Download,
  Lock,
  Sparkles,
  GitCommit,
  CheckCircle2,
  AlertTriangle,
  ArrowRightLeft,
  Users,
  Eye,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { Modal } from '../../components/common/Modal';
import { auditService } from '../../services/auditService';
import { projectService } from '../../services/projectService';
import { useToast } from '../../hooks/useToast';
import { useRole } from '../../context/RoleContext';
import { AuditRecord, AuditLogQueryParams } from '../../types/audit';
import { Project } from '../../types/project';

export const AuditLogsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentRole, permissions } = useRole();
  const { success, error, info } = useToast();

  const [project, setProject] = useState<Project | null>(null);
  const [logs, setLogs] = useState<AuditRecord[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'timeline' | 'table'>('timeline');

  // Filter States
  const [selectedUser, setSelectedUser] = useState<string>('');
  const [selectedAction, setSelectedAction] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 25;

  // Selected Detail Modal
  const [selectedRecord, setSelectedRecord] = useState<AuditRecord | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  // Authorization Check:
  // Authorized roles: Project Lead, Outgoing Member, or anyone with canManagePermissions / canReviewHandovers
  const isAuthorized =
    currentRole === 'project_lead' ||
    currentRole === 'outgoing_member' ||
    permissions.canManagePermissions ||
    permissions.canReviewHandovers;

  const fetchLogs = async () => {
    if (!isAuthorized) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const params: AuditLogQueryParams = {
        page,
        page_size: pageSize,
      };

      if (selectedAction) params.action = selectedAction;
      if (selectedUser) params.user_id = selectedUser;
      if (startDate) params.start_time = new Date(startDate).toISOString();
      if (endDate) params.end_time = new Date(endDate).toISOString();

      let res;
      if (id) {
        res = await auditService.getProjectAuditLogs(id, params);
      } else {
        res = await auditService.getGlobalAuditLogs(params);
      }

      if (res.data) {
        setLogs(res.data.items || []);
        setTotalCount(res.data.total || 0);
      }
    } catch (err: any) {
      console.error('Failed to load audit trail:', err);
      error('Audit Trail Error', err.message || 'Could not fetch audit records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      projectService.getById(id).then((res) => {
        if (res.data) setProject(res.data);
      });
    }
    fetchLogs();
  }, [id, selectedAction, selectedUser, startDate, endDate, page, currentRole]);

  const handleClearFilters = () => {
    setSelectedUser('');
    setSelectedAction('');
    setStartDate('');
    setEndDate('');
    setPage(1);
  };

  const handleCopyMetadata = () => {
    if (!selectedRecord) return;
    navigator.clipboard.writeText(JSON.stringify(selectedRecord, null, 2));
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
    success('Copied to Clipboard', 'Full audit record metadata copied.');
  };

  const formatTimestamp = (iso: string) => {
    const d = new Date(iso);
    return {
      formatted: d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short',
      }),
      relative: getRelativeTime(d),
    };
  };

  const getRelativeTime = (d: Date) => {
    const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const getActionBadge = (action: string) => {
    const act = action.toLowerCase();
    if (act.includes('approved') || act.includes('restored') || act.includes('created')) {
      return { variant: 'success' as const, label: action.replace(/_/g, ' ') };
    }
    if (act.includes('rejected') || act.includes('deleted') || act.includes('revoked')) {
      return { variant: 'danger' as const, label: action.replace(/_/g, ' ') };
    }
    if (act.includes('permission') || act.includes('modified') || act.includes('conflict')) {
      return { variant: 'warning' as const, label: action.replace(/_/g, ' ') };
    }
    if (act.includes('generated') || act.includes('uploaded') || act.includes('shared')) {
      return { variant: 'ai' as const, label: action.replace(/_/g, ' ') };
    }
    return { variant: 'neutral' as const, label: action.replace(/_/g, ' ') };
  };

  // Preset date ranges
  const applyDatePreset = (preset: '24h' | '7d' | '30d') => {
    const now = new Date();
    let past = new Date();
    if (preset === '24h') past.setHours(past.getHours() - 24);
    if (preset === '7d') past.setDate(past.getDate() - 7);
    if (preset === '30d') past.setDate(past.getDate() - 30);

    setStartDate(past.toISOString().split('T')[0]);
    setEndDate(now.toISOString().split('T')[0]);
  };

  // Unauthorized Screen
  if (!isAuthorized) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-4">
        <Card className="p-8 bg-[#0F172A] border-rose-500/30 text-center space-y-4">
          <div className="h-14 w-14 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
            <Lock className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-bold text-white">Audit Trail Access Restricted</h2>
          <p className="text-xs text-slate-300 max-w-lg mx-auto leading-relaxed">
            Immutable workspace audit records and security event logs are restricted to authorized
            Project Leads, Administrators, and Knowledge Contributors.
          </p>
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-400 max-w-md mx-auto">
            Your current active role is <strong className="text-white capitalize">{currentRole.replace('_', ' ')}</strong>,
            which does not possess <span className="font-mono text-brand-400 font-semibold">VIEW_AUDIT_LOGS</span> privilege.
          </div>
          <div className="pt-2 flex items-center justify-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(id ? `/projects/${id}` : '/dashboard')}
            >
              Return to Workspace
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const projectKey = project?.key || id || 'GLOBAL';

  // Metrics collation
  const permissionEventsCount = logs.filter((l) => l.action.includes('permission') || l.action.includes('access') || l.action.includes('member')).length;
  const documentEventsCount = logs.filter((l) => l.action.includes('document')).length;
  const handoverEventsCount = logs.filter((l) => l.action.includes('handover') || l.action.includes('version') || l.action.includes('conflict')).length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Breadcrumb Header */}
      <div className="flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
          {id ? (
            <>
              <Link
                to="/projects"
                className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>Projects</span>
              </Link>
              <span>/</span>
              <Link
                to={`/projects/${id}`}
                className="font-mono text-brand-400 font-bold hover:underline"
              >
                {projectKey}
              </Link>
              <span>/</span>
              <span className="text-white font-medium">Audit Trail & Compliance Log</span>
            </>
          ) : (
            <>
              <Link
                to="/dashboard"
                className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>Dashboard</span>
              </Link>
              <span>/</span>
              <span className="text-white font-medium">Enterprise Audit Trail</span>
            </>
          )}
        </div>

        {id && (
          <div className="flex items-center gap-2">
            <Link
              to={`/projects/${id}/members`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 transition-colors"
            >
              <Users className="h-3.5 w-3.5 text-indigo-400" />
              <span>Project Members & RBAC</span>
            </Link>
            <Link
              to={`/projects/${id}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 transition-colors"
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Workspace Overview</span>
            </Link>
          </div>
        )}
      </div>

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
              <Clock className="h-4 w-4" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              {id ? `Workspace Audit Trail: ${projectKey}` : 'Enterprise Activity & Audit Trail'}
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Immutable, server-side compliance log capturing authentication, knowledge changes, role edits, and sign-offs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            onClick={fetchLogs}
            disabled={isLoading}
            className="text-xs"
          >
            Refresh Logs
          </Button>
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('timeline')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                viewMode === 'timeline'
                  ? 'bg-brand-500 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Timeline
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                viewMode === 'table'
                  ? 'bg-brand-500 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Table View
            </button>
          </div>
        </div>
      </div>

      {/* Summary KPI Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-4 bg-[#0F172A] border-slate-800">
          <div className="text-[11px] text-slate-400 font-medium">Total Logged Activities</div>
          <div className="text-xl font-bold font-mono text-white mt-1">{totalCount}</div>
        </Card>
        <Card className="p-4 bg-[#0F172A] border-slate-800">
          <div className="text-[11px] text-indigo-400 font-medium">Security & Role Changes</div>
          <div className="text-xl font-bold font-mono text-indigo-300 mt-1">{permissionEventsCount}</div>
        </Card>
        <Card className="p-4 bg-[#0F172A] border-slate-800">
          <div className="text-[11px] text-emerald-400 font-medium">Handover & Synthesis</div>
          <div className="text-xl font-bold font-mono text-emerald-300 mt-1">{handoverEventsCount}</div>
        </Card>
        <Card className="p-4 bg-[#0F172A] border-slate-800">
          <div className="text-[11px] text-brand-400 font-medium">Knowledge & Documents</div>
          <div className="text-xl font-bold font-mono text-brand-300 mt-1">{documentEventsCount}</div>
        </Card>
      </div>

      {/* Filters Bar */}
      <Card className="p-4 bg-[#0F172A] border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Filter className="h-3.5 w-3.5 text-brand-400" />
            <span>Audit Trail Query Filters</span>
          </div>
          {(selectedAction || selectedUser || startDate || endDate) && (
            <button
              onClick={handleClearFilters}
              className="text-xs text-brand-400 hover:text-brand-300 underline"
            >
              Clear All Filters
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          {/* Action Type Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              Action Type
            </label>
            <select
              value={selectedAction}
              onChange={(e) => setSelectedAction(e.target.value)}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2 text-slate-200 text-xs focus:outline-none focus:border-brand-500"
            >
              <option value="">All Action Types</option>
              <option value="user_login">User Login</option>
              <option value="user_logout">User Logout</option>
              <option value="project_created">Project Created</option>
              <option value="project_updated">Project Updated</option>
              <option value="document_uploaded">Document Uploaded</option>
              <option value="document_deleted">Document Deleted</option>
              <option value="handover_generated">Handover Generated</option>
              <option value="handover_modified">Handover Modified</option>
              <option value="handover_approved">Handover Approved</option>
              <option value="handover_rejected">Handover Rejected</option>
              <option value="handover_shared">Handover Shared</option>
              <option value="version_restored">Version Restored</option>
              <option value="permission_changed">Permission Changed</option>
              <option value="member_invited">Member Invited</option>
              <option value="access_revoked">Access Revoked</option>
              <option value="conflict_resolved">Conflict Resolved</option>
            </select>
          </div>

          {/* User Search / Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              Acting User Email or ID
            </label>
            <div className="relative">
              <UserIcon className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Filter by email or name..."
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 pl-8 pr-3 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-brand-500"
              />
            </div>
          </div>

          {/* Start Date */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              From Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-1.5 text-slate-200 text-xs focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* End Date */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              To Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-1.5 text-slate-200 text-xs focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        {/* Quick Date Presets */}
        <div className="flex items-center gap-2 pt-1">
          <span className="text-[11px] text-slate-500">Quick Range:</span>
          <button
            onClick={() => applyDatePreset('24h')}
            className="text-[11px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
          >
            Last 24 Hours
          </button>
          <button
            onClick={() => applyDatePreset('7d')}
            className="text-[11px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
          >
            Last 7 Days
          </button>
          <button
            onClick={() => applyDatePreset('30d')}
            className="text-[11px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
          >
            Last 30 Days
          </button>
        </div>
      </Card>

      {/* Main Content: Timeline View or Table View */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <div className="flex items-center gap-2.5">
            <div className="h-5 w-5 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            <span className="text-sm">Fetching immutable audit logs...</span>
          </div>
        </div>
      ) : logs.length === 0 ? (
        <Card className="p-12 text-center bg-[#0F172A] border-slate-800">
          <Clock className="h-10 w-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No Audit Records Found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
            No activity matches the selected filter parameters. Adjust your filters or query range.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearFilters}
            className="mt-4 text-xs"
          >
            Reset Filters
          </Button>
        </Card>
      ) : viewMode === 'timeline' ? (
        /* TIMELINE VIEW */
        <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
          {logs.map((record) => {
            const time = formatTimestamp(record.timestamp);
            const badge = getActionBadge(record.action);

            return (
              <div key={record.id} className="relative group">
                {/* Timeline Bullet Node */}
                <div className="absolute -left-6 sm:-left-8 top-1.5 h-3 w-3 rounded-full bg-slate-900 border-2 border-brand-500 group-hover:scale-125 transition-transform" />

                <Card className="p-4 bg-[#0F172A] border-slate-800 hover:border-slate-700 transition-colors">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={badge.variant} size="sm">
                          {badge.label.toUpperCase()}
                        </Badge>
                        <span className="font-mono text-xs text-slate-400">
                          {record.entity_type} {record.entity_id ? `(${record.entity_id})` : ''}
                        </span>
                        <span className="text-slate-600">·</span>
                        <span className="text-[11px] text-slate-500 font-mono">
                          {time.relative} ({time.formatted})
                        </span>
                      </div>

                      {/* Acting User Information */}
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 pt-0.5 text-xs">
                        <span className="text-slate-400">Performed by:</span>
                        <span className="font-semibold text-white">
                          {record.user_name || record.user_email || 'System Server'}
                        </span>
                        {record.user_email && (
                          <span className="text-[11px] text-slate-400 font-mono break-all">
                            &lt;{record.user_email}&gt;
                          </span>
                        )}
                      </div>

                      {/* Relevant Change Metadata Inline Highlights */}
                      <div className="pt-2">
                        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-300 font-mono overflow-x-auto">
                          {Object.entries(record.change_metadata || {}).map(([key, val]) => (
                            <div key={key} className="flex items-baseline gap-2 py-0.5">
                              <span className="text-brand-400 font-semibold">{key}:</span>
                              <span className="text-slate-200">
                                {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      leftIcon={<Eye className="h-3.5 w-3.5" />}
                      onClick={() => setSelectedRecord(record)}
                      className="text-xs text-slate-400 hover:text-white shrink-0 self-start sm:self-center"
                    >
                      Inspect Context
                    </Button>
                  </div>
                </Card>
              </div>
            );
          })}
        </div>
      ) : (
        /* TABLE VIEW */
        <Card className="bg-[#0F172A] border-slate-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/50 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Timestamp (UTC)</th>
                  <th className="py-3 px-4">Action Type</th>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Entity</th>
                  <th className="py-3 px-4">Change Details</th>
                  <th className="py-3 px-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-xs">
                {logs.map((record) => {
                  const time = formatTimestamp(record.timestamp);
                  const badge = getActionBadge(record.action);

                  return (
                    <tr key={record.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-3 px-4 whitespace-nowrap font-mono text-[11px] text-slate-300">
                        <div>{time.formatted}</div>
                        <div className="text-[10px] text-slate-500">{time.relative}</div>
                      </td>

                      <td className="py-3 px-4">
                        <Badge variant={badge.variant} size="sm">
                          {badge.label}
                        </Badge>
                      </td>

                      <td className="py-3 px-4">
                        <div className="font-medium text-white truncate max-w-[160px]">
                          {record.user_name || record.user_email || 'System Service'}
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono truncate max-w-[160px]">
                          {record.user_email}
                        </div>
                      </td>

                      <td className="py-3 px-4 font-mono text-[11px] text-slate-300">
                        <span className="text-brand-400">{record.entity_type}</span>
                        {record.entity_id && (
                          <span className="block text-[10px] text-slate-500 truncate max-w-[120px]">
                            {record.entity_id}
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-4 max-w-xs truncate text-[11px] text-slate-400 font-mono">
                        {JSON.stringify(record.change_metadata)}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          leftIcon={<Eye className="h-3.5 w-3.5" />}
                          onClick={() => setSelectedRecord(record)}
                          className="text-xs text-slate-400 hover:text-white"
                        >
                          Inspect
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Record Inspection Modal */}
      <Modal
        isOpen={Boolean(selectedRecord)}
        onClose={() => setSelectedRecord(null)}
        maxWidth="xl"
        title="Audit Trail Event Details"
        description="Immutable record verification metadata and HTTP request telemetry context."
        footer={
          <div className="flex items-center justify-between w-full">
            <Button
              variant="outline"
              size="sm"
              leftIcon={copiedKey ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              onClick={handleCopyMetadata}
              className="text-xs"
            >
              {copiedKey ? 'Copied' : 'Copy JSON'}
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setSelectedRecord(null)}
            >
              Close
            </Button>
          </div>
        }
      >
        {selectedRecord && (
          <div className="space-y-4 text-xs">
            {/* Top Info */}
            <div className="grid grid-cols-2 gap-3 p-3.5 rounded-xl bg-slate-900 border border-slate-800">
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-500">Audit ID</span>
                <div className="font-mono text-white select-all">{selectedRecord.audit_id || selectedRecord.id}</div>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-500">Action</span>
                <div className="font-semibold text-brand-400">{selectedRecord.action}</div>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-500">Timestamp</span>
                <div className="font-mono text-slate-300">{selectedRecord.timestamp}</div>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-500">Project Target</span>
                <div className="font-mono text-slate-300">{selectedRecord.project_id || 'System / Global'}</div>
              </div>
            </div>

            {/* Change Metadata */}
            <div>
              <h4 className="text-xs font-semibold text-white mb-1.5 flex items-center gap-1.5">
                <Code2 className="h-3.5 w-3.5 text-brand-400" />
                <span>Change Metadata (Scrubbed Server-Side)</span>
              </h4>
              <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-300 font-mono overflow-x-auto max-h-48">
                {JSON.stringify(selectedRecord.change_metadata, null, 2)}
              </pre>
            </div>

            {/* Request Context */}
            {selectedRecord.request_context && Object.keys(selectedRecord.request_context).length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-white mb-1.5 flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-indigo-400" />
                  <span>Request Context & Telemetry</span>
                </h4>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1 font-mono text-[11px] text-slate-300">
                  {selectedRecord.request_context.ip_address && (
                    <div className="flex justify-between">
                      <span className="text-slate-500">Client IP:</span>
                      <span className="text-slate-200">{selectedRecord.request_context.ip_address}</span>
                    </div>
                  )}
                  {selectedRecord.request_context.method && (
                    <div className="flex justify-between">
                      <span className="text-slate-500">Method & Path:</span>
                      <span className="text-slate-200">
                        {selectedRecord.request_context.method} {selectedRecord.request_context.path}
                      </span>
                    </div>
                  )}
                  {selectedRecord.request_context.request_id && (
                    <div className="flex justify-between">
                      <span className="text-slate-500">Request ID:</span>
                      <span className="text-slate-200">{selectedRecord.request_context.request_id}</span>
                    </div>
                  )}
                  {selectedRecord.request_context.user_agent && (
                    <div className="pt-1 text-[10px] text-slate-400 break-all">
                      <span className="text-slate-500 block">User Agent:</span>
                      {selectedRecord.request_context.user_agent}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

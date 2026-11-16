import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Users,
  UserPlus,
  ShieldCheck,
  ShieldAlert,
  ArrowLeft,
  Mail,
  Search,
  MoreVertical,
  Edit2,
  Trash2,
  UserX,
  UserCheck,
  Lock,
  ExternalLink,
  Clock,
  Sparkles,
  FileText,
  Layers,
  Sliders,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { Modal } from '../../components/common/Modal';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { PermissionsManagementModal } from '../../components/members/PermissionsManagementModal';
import { useToast } from '../../hooks/useToast';
import { useRole } from '../../context/RoleContext';
import { projectService } from '../../services/projectService';
import { memberService } from '../../services/memberService';
import { Project } from '../../types/project';
import {
  ProjectMember,
  ProjectMemberRole,
  ROLE_DISPLAY_NAMES,
} from '../../types/member';

export const ProjectMembersPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentRole, permissions } = useRole();
  const { success, error, info } = useToast();

  const [project, setProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'invited' | 'revoked'>('all');

  // Modals state
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isEditRoleModalOpen, setIsEditRoleModalOpen] = useState(false);
  const [isPermissionsModalOpen, setIsPermissionsModalOpen] = useState(false);
  const [memberToEdit, setMemberToEdit] = useState<ProjectMember | null>(null);
  const [memberToRemove, setMemberToRemove] = useState<ProjectMember | null>(null);
  const [memberToRevoke, setMemberToRevoke] = useState<ProjectMember | null>(null);

  // Invite Form State
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<ProjectMemberRole>('INCOMING');
  const [inviteStatus, setInviteStatus] = useState<'invited' | 'active'>('invited');
  const [isInviting, setIsInviting] = useState(false);

  // Edit Role Form State
  const [newRole, setNewRole] = useState<ProjectMemberRole>('INCOMING');
  const [newStatus, setNewStatus] = useState<string>('active');
  const [isUpdatingRole, setIsUpdatingRole] = useState(false);

  // Check if current active user is authorized to manage members/permissions
  const isAuthorized = permissions.canManagePermissions || permissions.canManageProject || currentRole === 'project_lead';

  const loadData = async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      // Load project details
      const projRes = await projectService.getById(id);
      if (projRes.data) {
        setProject(projRes.data);
      }

      // Load members
      const membersRes = await memberService.listMembers(id);
      if (membersRes.data) {
        setMembers(membersRes.data);
      }
    } catch (err: any) {
      console.error('Failed to load project members data:', err);
      error('Failed to Load', err.message || 'Could not load project members.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  // Handle Invite
  const handleOpenInvite = () => {
    if (!isAuthorized) {
      info(
        'Access Restricted',
        'Only Project Owners and Admins have permission to invite project members.'
      );
      return;
    }
    setInviteEmail('');
    setInviteRole('INCOMING');
    setInviteStatus('invited');
    setIsInviteModalOpen(true);
  };

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !inviteEmail.trim() || !inviteEmail.includes('@')) {
      error('Invalid Email', 'Please provide a valid corporate email address.');
      return;
    }

    setIsInviting(true);
    try {
      const res = await memberService.addMember(id, {
        email: inviteEmail.trim(),
        role: inviteRole,
        status: inviteStatus,
      });

      success('Member Added', res.message || `Invitation sent to ${inviteEmail}.`);
      setIsInviteModalOpen(false);
      setInviteEmail('');
      await loadData();
    } catch (err: any) {
      error('Invitation Failed', err.message || 'Could not invite member.');
    } finally {
      setIsInviting(false);
    }
  };

  // Handle Edit Role
  const handleOpenEditRole = (m: ProjectMember) => {
    if (!isAuthorized) {
      info('Access Restricted', 'Only Project Owners and Admins can update roles.');
      return;
    }
    setMemberToEdit(m);
    setNewRole((m.role as ProjectMemberRole) || 'INCOMING');
    setNewStatus(m.status || 'active');
    setIsEditRoleModalOpen(true);
  };

  const handleUpdateRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !memberToEdit) return;

    setIsUpdatingRole(true);
    try {
      const res = await memberService.updateMemberRole(id, memberToEdit.id, {
        role: newRole,
        status: newStatus,
      });

      success('Role Updated', res.message || `Member role updated to ${ROLE_DISPLAY_NAMES[newRole]}.`);
      setIsEditRoleModalOpen(false);
      setMemberToEdit(null);
      await loadData();
    } catch (err: any) {
      error('Update Failed', err.message || 'Failed to update member role.');
    } finally {
      setIsUpdatingRole(false);
    }
  };

  // Handle Permissions Modal
  const handleOpenPermissions = (m: ProjectMember) => {
    setMemberToEdit(m);
    setIsPermissionsModalOpen(true);
  };

  const handleSavePermissions = async (memberId: string, customPermissions: string[]) => {
    if (!id || !memberToEdit) return;
    try {
      await memberService.updateMemberRole(id, memberId, {
        role: memberToEdit.role as ProjectMemberRole,
        custom_permissions: customPermissions,
      });
      success(
        'Permissions Configured',
        `Custom permission matrix applied for ${memberToEdit.full_name}.`
      );
      await loadData();
    } catch (err: any) {
      error('Permissions Update Failed', err.message || 'Failed to update custom permissions.');
      throw err;
    }
  };

  // Handle Revoke Access
  const handleRevoke = async () => {
    if (!id || !memberToRevoke) return;
    try {
      const res = await memberService.revokeMember(id, memberToRevoke.id);
      success('Access Revoked', res.data?.message || 'Member access revoked successfully.');
      setMemberToRevoke(null);
      await loadData();
    } catch (err: any) {
      error('Revocation Failed', err.message || 'Could not revoke member access.');
    }
  };

  // Handle Remove Member
  const handleRemove = async () => {
    if (!id || !memberToRemove) return;
    try {
      await memberService.removeMember(id, memberToRemove.id);
      success('Member Removed', `${memberToRemove.full_name} has been removed from the project.`);
      setMemberToRemove(null);
      await loadData();
    } catch (err: any) {
      error('Removal Failed', err.message || 'Could not remove member.');
    }
  };

  // Filtered members list
  const filteredMembers = members.filter((m) => {
    const matchesQuery =
      m.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.role_display_name.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === 'all' || m.status === statusFilter;

    return matchesQuery && matchesStatus;
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[55vh] text-slate-400">
        <div className="flex items-center gap-2.5">
          <div className="h-5 w-5 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          <span className="text-sm">Loading Project Members & RBAC Matrix...</span>
        </div>
      </div>
    );
  }

  const projectKey = project?.key || id || 'PROJECT';

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Breadcrumb Header */}
      <div className="flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
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
          <span className="text-white font-medium">Members & Access Governance</span>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to={`/projects/${id}/audit`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 transition-colors"
          >
            <Clock className="h-3.5 w-3.5 text-brand-400" />
            <span>Workspace Audit Trail</span>
          </Link>
          <Link
            to={`/projects/${id}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 transition-colors"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Workspace Overview</span>
          </Link>
        </div>
      </div>

      {/* Page Title & Invite Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Project Members & Role Governance
            </h1>
            <Badge variant="neutral" size="sm">
              {members.length} Total
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Manage authorized collaborators, role assignments, status lifecycle, and granular permission overrides.
          </p>
        </div>

        {isAuthorized && (
          <Button
            variant="primary"
            size="sm"
            leftIcon={<UserPlus className="h-4 w-4" />}
            onClick={handleOpenInvite}
            className="shrink-0"
          >
            Invite Member
          </Button>
        )}
      </div>

      {/* RBAC Authority Notice */}
      <Card
        className={`p-4 border ${
          isAuthorized
            ? 'bg-slate-900/60 border-indigo-500/30'
            : 'bg-slate-900/40 border-slate-800'
        }`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div
              className={`p-2 rounded-lg border shrink-0 ${
                isAuthorized
                  ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400'
                  : 'bg-slate-800 border-slate-700 text-slate-400'
              }`}
            >
              {isAuthorized ? <ShieldCheck className="h-5 w-5" /> : <Lock className="h-5 w-5" />}
            </div>
            <div>
              <div className="text-xs font-semibold text-white flex items-center gap-2">
                <span>
                  {isAuthorized
                    ? 'Authorized Administrative Governance Active'
                    : 'Standard Member Access (Read-Only Mode)'}
                </span>
                <Badge variant={isAuthorized ? 'accent' : 'neutral'} size="sm">
                  Active Role: {currentRole.replace('_', ' ').toUpperCase()}
                </Badge>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                {isAuthorized
                  ? 'You possess full authority to invite contributors, change assigned roles, revoke workspace credentials, and configure granular permission overrides.'
                  : 'You have read-only visibility over active project members. Administrative operations such as role assignments and membership revocations require Project Lead or Owner privileges.'}
              </p>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-2 shrink-0">
            <span className="text-[11px] font-mono text-slate-400">
              Active: {members.filter((m) => m.status === 'active').length} | Invited:{' '}
              {members.filter((m) => m.status === 'invited').length} | Revoked:{' '}
              {members.filter((m) => m.status === 'revoked').length}
            </span>
          </div>
        </div>
      </Card>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Status Filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {(
            [
              { id: 'all', label: 'All Members', count: members.length },
              {
                id: 'active',
                label: 'Active',
                count: members.filter((m) => m.status === 'active').length,
              },
              {
                id: 'invited',
                label: 'Invited / Pending',
                count: members.filter((m) => m.status === 'invited').length,
              },
              {
                id: 'revoked',
                label: 'Revoked',
                count: members.filter((m) => m.status === 'revoked').length,
              },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 shrink-0 ${
                statusFilter === tab.id
                  ? 'bg-brand-500/15 text-brand-400 border border-brand-500/30'
                  : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <span>{tab.label}</span>
              <span className="font-mono text-[10px] opacity-70">({tab.count})</span>
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search by name, email, or role..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg bg-slate-900 border border-slate-800 pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>
      </div>

      {/* Members Table */}
      <Card className="bg-[#0F172A] border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/50 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Member Name & Email</th>
                <th className="py-3 px-4">Assigned Role</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Custom Overrides</th>
                <th className="py-3 px-4">Joined / Invited</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-xs">
              {filteredMembers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <Users className="h-8 w-8 mx-auto mb-2 opacity-40" />
                    <p className="text-sm font-medium text-slate-400">No project members match your search criteria</p>
                    <p className="text-xs text-slate-600 mt-1">Try resetting the status filter or clearing your search query.</p>
                  </td>
                </tr>
              ) : (
                filteredMembers.map((m) => {
                  const hasCustomOverrides =
                    m.custom_permissions && m.custom_permissions.length > 0;

                  return (
                    <tr
                      key={m.id}
                      className="hover:bg-slate-900/40 transition-colors group"
                    >
                      {/* Name & Email */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <img
                            src={
                              m.profile_image ||
                              'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'
                            }
                            alt={m.full_name}
                            className="h-9 w-9 rounded-full object-cover border border-slate-700 shrink-0"
                          />
                          <div className="min-w-0">
                            <div className="font-semibold text-white truncate flex items-center gap-2">
                              <span>{m.full_name}</span>
                              {m.role === 'PROJECT_OWNER' && (
                                <Badge variant="accent" size="sm">Owner</Badge>
                              )}
                            </div>
                            <div className="text-[11px] text-slate-400 font-mono truncate">
                              {m.email}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Role Badge */}
                      <td className="py-3.5 px-4">
                        <Badge
                          variant={
                            m.role === 'ADMIN' || m.role === 'PROJECT_OWNER'
                              ? 'accent'
                              : m.role === 'OUTGOING'
                              ? 'warning'
                              : m.role === 'INCOMING'
                              ? 'ai'
                              : 'neutral'
                          }
                          size="sm"
                        >
                          {m.role_display_name || m.role}
                        </Badge>
                      </td>

                      {/* Membership Status */}
                      <td className="py-3.5 px-4">
                        <Badge
                          variant={
                            m.status === 'active'
                              ? 'success'
                              : m.status === 'invited'
                              ? 'warning'
                              : 'danger'
                          }
                          size="sm"
                          dot
                        >
                          {m.status === 'active'
                            ? 'Active Member'
                            : m.status === 'invited'
                            ? 'Invited (Pending)'
                            : 'Access Revoked'}
                        </Badge>
                      </td>

                      {/* Custom Permissions Overrides */}
                      <td className="py-3.5 px-4">
                        {hasCustomOverrides ? (
                          <button
                            onClick={() => handleOpenPermissions(m)}
                            className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-brand-500/10 border border-brand-500/30 text-[11px] text-brand-300 hover:bg-brand-500/20 transition-colors"
                          >
                            <Sliders className="h-3 w-3" />
                            <span>{m.custom_permissions?.length} Overrides</span>
                          </button>
                        ) : (
                          <span className="text-[11px] text-slate-500 font-mono">
                            Role Defaults
                          </span>
                        )}
                      </td>

                      {/* Joined / Invited Date */}
                      <td className="py-3.5 px-4">
                        <span className="text-[11px] text-slate-400 font-mono">
                          {m.joined_at
                            ? new Date(m.joined_at).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                              })
                            : 'Recent'}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right">
                        {isAuthorized ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="ghost"
                              size="sm"
                              leftIcon={<Sliders className="h-3.5 w-3.5" />}
                              onClick={() => handleOpenPermissions(m)}
                              className="text-xs text-slate-300 hover:text-white"
                              title="Permissions Management"
                            >
                              Permissions
                            </Button>

                            <Button
                              variant="ghost"
                              size="sm"
                              leftIcon={<Edit2 className="h-3.5 w-3.5" />}
                              onClick={() => handleOpenEditRole(m)}
                              className="text-xs text-slate-300 hover:text-white"
                              title="Edit Role"
                            >
                              Role
                            </Button>

                            {m.status !== 'revoked' ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                leftIcon={<UserX className="h-3.5 w-3.5 text-amber-400" />}
                                onClick={() => setMemberToRevoke(m)}
                                className="text-xs text-amber-400 hover:text-amber-300 hover:bg-amber-500/10"
                                title="Revoke Access"
                              >
                                Revoke
                              </Button>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                leftIcon={<UserCheck className="h-3.5 w-3.5 text-emerald-400" />}
                                onClick={() => handleOpenEditRole(m)}
                                className="text-xs text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10"
                                title="Reactivate Access"
                              >
                                Reactivate
                              </Button>
                            )}

                            <Button
                              variant="ghost"
                              size="sm"
                              leftIcon={<Trash2 className="h-3.5 w-3.5 text-rose-400" />}
                              onClick={() => setMemberToRemove(m)}
                              className="text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                              title="Remove from Project"
                            >
                              Remove
                            </Button>
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-500 italic">
                            Protected
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Invite Member Modal */}
      <Modal
        isOpen={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
        title="Invite Member to Project Workspace"
        description="Grant an engineer access to this project repository, runbooks, and handover sessions."
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsInviteModalOpen(false)}
              disabled={isInviting}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<UserPlus className="h-4 w-4" />}
              onClick={handleSendInvite}
              isLoading={isInviting}
            >
              Send Workspace Invite
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSendInvite} className="space-y-4 text-xs">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Engineer Corporate Email *
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="email"
                placeholder="colleague@techfrontier.io"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                required
                className="w-full rounded-lg bg-slate-900 border border-slate-700 pl-9 pr-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-brand-500"
              />
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              User must be registered with TechFrontier or will receive an onboarding invite link.
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Assigned Workspace Role *
            </label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as ProjectMemberRole)}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2 text-slate-200 text-xs focus:outline-none focus:border-brand-500"
            >
              <option value="INCOMING">Incoming Member (Successor — View & Acknowledge)</option>
              <option value="OUTGOING">Outgoing Member (Contributor — Upload & Draft)</option>
              <option value="REVIEWER">Reviewer (Architecture Review & Approval)</option>
              <option value="LEAD">Project Lead (Workspace Administration & Sign-off)</option>
              <option value="PROJECT_OWNER">Project Owner (Full Authority & RBAC)</option>
              <option value="ADMIN">Admin (Full System Privileges)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Initial Membership Status
            </label>
            <select
              value={inviteStatus}
              onChange={(e) => setInviteStatus(e.target.value as 'invited' | 'active')}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2 text-slate-200 text-xs focus:outline-none focus:border-brand-500"
            >
              <option value="invited">Invited (Requires user confirmation)</option>
              <option value="active">Active Immediately (Pre-approved)</option>
            </select>
          </div>
        </form>
      </Modal>

      {/* Edit Role Modal */}
      <Modal
        isOpen={isEditRoleModalOpen}
        onClose={() => setIsEditRoleModalOpen(false)}
        title="Edit Member Role & Status"
        description="Modify assigned role credentials or re-activate access for this project member."
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEditRoleModalOpen(false)}
              disabled={isUpdatingRole}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<ShieldCheck className="h-4 w-4" />}
              onClick={handleUpdateRole}
              isLoading={isUpdatingRole}
            >
              Update Member Role
            </Button>
          </div>
        }
      >
        {memberToEdit && (
          <form onSubmit={handleUpdateRole} className="space-y-4 text-xs">
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-3">
              <img
                src={
                  memberToEdit.profile_image ||
                  'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'
                }
                alt={memberToEdit.full_name}
                className="h-8 w-8 rounded-full object-cover border border-slate-700"
              />
              <div>
                <div className="font-semibold text-white">{memberToEdit.full_name}</div>
                <div className="text-[11px] text-slate-400 font-mono">{memberToEdit.email}</div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                New Assigned Role *
              </label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as ProjectMemberRole)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2 text-slate-200 text-xs focus:outline-none focus:border-brand-500"
              >
                <option value="INCOMING">Incoming Member</option>
                <option value="OUTGOING">Outgoing Member</option>
                <option value="REVIEWER">Reviewer</option>
                <option value="LEAD">Project Lead</option>
                <option value="PROJECT_OWNER">Project Owner</option>
                <option value="ADMIN">Admin</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Membership Status *
              </label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2 text-slate-200 text-xs focus:outline-none focus:border-brand-500"
              >
                <option value="active">Active</option>
                <option value="invited">Invited (Pending Confirmation)</option>
                <option value="revoked">Revoked (Access Blocked)</option>
              </select>
            </div>

            <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>
                Role modifications take effect immediately. Project workspaces must always retain at least one active Admin or Project Owner.
              </span>
            </div>
          </form>
        )}
      </Modal>

      {/* Permissions Management Modal */}
      <PermissionsManagementModal
        isOpen={isPermissionsModalOpen}
        onClose={() => {
          setIsPermissionsModalOpen(false);
          setMemberToEdit(null);
        }}
        member={memberToEdit}
        onSavePermissions={handleSavePermissions}
        isAuthorized={isAuthorized}
      />

      {/* Revoke Access Confirm Dialog */}
      <ConfirmDialog
        isOpen={Boolean(memberToRevoke)}
        onClose={() => setMemberToRevoke(null)}
        onConfirm={handleRevoke}
        variant="warning"
        title="Revoke Project Access"
        message={`Are you sure you want to revoke access privileges for "${memberToRevoke?.full_name}" (${memberToRevoke?.email})? They will immediately lose access to repository runbooks and handover reviews.`}
        confirmLabel="Revoke Access"
      />

      {/* Remove Member Confirm Dialog */}
      <ConfirmDialog
        isOpen={Boolean(memberToRemove)}
        onClose={() => setMemberToRemove(null)}
        onConfirm={handleRemove}
        variant="danger"
        title="Remove Member from Project"
        message={`Are you sure you want to permanently remove "${memberToRemove?.full_name}" from this project workspace? This will remove all assigned roles and cannot be undone.`}
        confirmLabel="Remove Member"
      />
    </div>
  );
};

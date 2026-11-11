import React, { useState, useEffect } from 'react';
import {
  Users,
  Mail,
  ShieldCheck,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  UserX,
  UserCheck,
  FolderGit2,
  MoreVertical,
  ExternalLink,
  Send,
  Building,
  Briefcase,
  AlertCircle,
  LayoutGrid,
  List as ListIcon,
  ShieldAlert,
  ArrowRightLeft,
  Sparkles,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/common/Card';
import { Modal } from '../../components/common/Modal';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { useToast } from '../../hooks/useToast';
import { useRole, HandoverAppRole } from '../../context/RoleContext';
import { teamService } from '../../services/teamService';
import { TeamMember, TeamMemberStatus, InviteMemberPayload } from '../../types/team';
import { mockProjects } from '../../data/mockData';

export const TeamMembersPage: React.FC = () => {
  const { currentRole, permissions } = useRole();
  const { success, error, info } = useToast();

  const [members, setMembers] = useState<TeamMember[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRole, setSelectedRole] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedProject, setSelectedProject] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Modals state
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null);
  const [assigningMember, setAssigningMember] = useState<TeamMember | null>(null);
  const [memberToRemove, setMemberToRemove] = useState<TeamMember | null>(null);

  // Invite Form state
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [inviteRole, setInviteRole] = useState<HandoverAppRole>('outgoing_member');
  const [inviteRoleTitle, setInviteRoleTitle] = useState('');
  const [inviteDepartment, setInviteDepartment] = useState('Core Engineering');
  const [inviteProjectIds, setInviteProjectIds] = useState<string[]>([]);
  const [inviteStatus, setInviteStatus] = useState<TeamMemberStatus>('pending_invite');

  // Assign Projects state
  const [selectedProjectIdsForAssign, setSelectedProjectIdsForAssign] = useState<string[]>([]);

  // Edit Role state
  const [newRoleForEdit, setNewRoleForEdit] = useState<HandoverAppRole>('outgoing_member');
  const [newRoleTitleForEdit, setNewRoleTitleForEdit] = useState('');

  const refreshMembers = () => {
    setMembers(teamService.getMembers());
  };

  useEffect(() => {
    refreshMembers();
  }, []);

  const handleOpenInvite = () => {
    if (!permissions.canManagePermissions) {
      info(
        'Permission Restricted',
        'Only Project Leads have administrative authority to invite members or configure role access.'
      );
      return;
    }
    setInviteEmail('');
    setInviteName('');
    setInviteRole('outgoing_member');
    setInviteRoleTitle('');
    setInviteDepartment('Core Engineering');
    setInviteProjectIds(mockProjects.slice(0, 1).map((p) => p.id));
    setInviteStatus('pending_invite');
    setIsInviteModalOpen(true);
  };

  const handleSendInvite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail || !inviteEmail.includes('@')) {
      error('Invalid Email', 'Please enter a valid engineering email address.');
      return;
    }

    try {
      const payload: InviteMemberPayload = {
        email: inviteEmail,
        name: inviteName,
        role: inviteRole,
        roleTitle: inviteRoleTitle,
        department: inviteDepartment,
        projectIds: inviteProjectIds,
        status: inviteStatus,
      };

      const created = teamService.inviteMember(payload);
      refreshMembers();
      setIsInviteModalOpen(false);
      success(
        'Team Member Invited',
        `${created.name} (${created.email}) has been invited as ${created.role.replace('_', ' ')}.`
      );
    } catch {
      error('Invitation Failed', 'Could not save new member. Please retry.');
    }
  };

  const handleToggleProjectSelection = (projectId: string) => {
    setInviteProjectIds((prev) =>
      prev.includes(projectId) ? prev.filter((id) => id !== projectId) : [...prev, projectId]
    );
  };

  const handleResendInvite = (member: TeamMember) => {
    teamService.resendInvite(member.id);
    refreshMembers();
    success('Invitation Resent', `A fresh handover access token was dispatched to ${member.email}`);
  };

  const handleOpenEditRole = (member: TeamMember) => {
    if (!permissions.canManagePermissions) {
      info('Permission Restricted', 'Switch to Project Lead to modify teammate roles.');
      return;
    }
    setEditingMember(member);
    setNewRoleForEdit(member.role);
    setNewRoleTitleForEdit(member.roleTitle);
  };

  const handleSaveRole = () => {
    if (!editingMember) return;
    teamService.updateMemberRole(editingMember.id, newRoleForEdit, newRoleTitleForEdit);
    refreshMembers();
    setEditingMember(null);
    success('Role Updated', `${editingMember.name}'s role was set to ${newRoleForEdit.replace('_', ' ')}`);
  };

  const handleOpenAssignProjects = (member: TeamMember) => {
    if (!permissions.canManagePermissions) {
      info('Permission Restricted', 'Switch to Project Lead to modify project assignments.');
      return;
    }
    setAssigningMember(member);
    setSelectedProjectIdsForAssign(member.assignedProjects.map((p) => p.projectId));
  };

  const handleSaveAssignedProjects = () => {
    if (!assigningMember) return;
    teamService.assignProjects(assigningMember.id, selectedProjectIdsForAssign);
    refreshMembers();
    setAssigningMember(null);
    success('Assignments Updated', `Updated project assignments for ${assigningMember.name}.`);
  };

  const handleToggleStatus = (member: TeamMember) => {
    if (!permissions.canManagePermissions) {
      info('Permission Restricted', 'Switch to Project Lead to alter member activity status.');
      return;
    }
    const nextStatus: TeamMemberStatus =
      member.status === 'active' ? 'inactive' : 'active';
    teamService.updateMemberStatus(member.id, nextStatus);
    refreshMembers();
    info('Status Changed', `${member.name} is now ${nextStatus}.`);
  };

  const handleRemoveMember = (member: TeamMember) => {
    if (!permissions.canManagePermissions) {
      info('Permission Restricted', 'Switch to Project Lead to remove members.');
      return;
    }
    setMemberToRemove(member);
  };

  const handleConfirmRemove = () => {
    if (!memberToRemove) return;
    teamService.removeMember(memberToRemove.id);
    refreshMembers();
    success('Member Removed', `${memberToRemove.name} has been removed from workspace projects.`);
    setMemberToRemove(null);
  };

  // Filter logic
  const filteredMembers = members.filter((m) => {
    const matchesSearch =
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.roleTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.department.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.assignedProjects.some((p) =>
        p.projectTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.projectKey.toLowerCase().includes(searchQuery.toLowerCase())
      );

    const matchesRole = selectedRole === 'all' || m.role === selectedRole;
    const matchesStatus = selectedStatus === 'all' || m.status === selectedStatus;
    const matchesProject =
      selectedProject === 'all' || m.assignedProjects.some((p) => p.projectId === selectedProject);

    return matchesSearch && matchesRole && matchesStatus && matchesProject;
  });

  // Metrics
  const totalCount = members.length;
  const activeCount = members.filter((m) => m.status === 'active').length;
  const pendingCount = members.filter((m) => m.status === 'pending_invite').length;
  const leadsCount = members.filter((m) => m.role === 'project_lead').length;
  const outgoingCount = members.filter((m) => m.role === 'outgoing_member').length;
  const incomingCount = members.filter((m) => m.role === 'incoming_member').length;

  const getRoleBadge = (role: HandoverAppRole) => {
    switch (role) {
      case 'project_lead':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-violet-500/10 text-violet-400 border border-violet-500/30">
            <ShieldCheck className="h-3 w-3" />
            Project Lead
          </span>
        );
      case 'outgoing_member':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <ArrowRightLeft className="h-3 w-3" />
            Outgoing Member
          </span>
        );
      case 'incoming_member':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <Sparkles className="h-3 w-3" />
            Incoming Member
          </span>
        );
    }
  };

  const getStatusBadge = (status: TeamMemberStatus) => {
    switch (status) {
      case 'active':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Active
          </span>
        );
      case 'pending_invite':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="h-2.5 w-2.5" />
            Pending Invite
          </span>
        );
      case 'inactive':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
            Inactive
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Role Permission Banner if not Lead */}
      {!permissions.canManagePermissions && (
        <div className="flex items-center justify-between p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs">
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="h-4 w-4 text-amber-400 shrink-0" />
            <span>
              <strong>Read-Only Team Directory:</strong> You are logged in with the <strong>{currentRole.replace('_', ' ')}</strong> role. Administrative actions (inviting teammates, altering roles, changing project assignments) require <strong>Project Lead</strong> permissions.
            </span>
          </div>
          <span className="text-[11px] text-amber-300 font-medium underline cursor-pointer hover:text-white ml-3 shrink-0">
            Use Role Switcher in Top Bar
          </span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Team Management</h1>
            <Badge variant="accent" size="sm">
              {totalCount} Members
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Engineers, system owners, and architecture reviewers participating in knowledge continuity
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="flex items-center bg-[#0F172A] border border-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded text-xs transition-colors ${
                viewMode === 'grid' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Grid View (Profile Cards)"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded text-xs transition-colors ${
                viewMode === 'table' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Table List View"
            >
              <ListIcon className="h-4 w-4" />
            </button>
          </div>

          <Button
            variant="primary"
            size="sm"
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={handleOpenInvite}
            disabled={!permissions.canManagePermissions}
          >
            Invite Member
          </Button>
        </div>
      </div>

      {/* Summary Stats Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
          <div className="text-[11px] font-medium text-slate-400">Total Members</div>
          <div className="text-xl font-bold text-white mt-1">{totalCount}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
          <div className="text-[11px] font-medium text-emerald-400">Active Now</div>
          <div className="text-xl font-bold text-emerald-400 mt-1">{activeCount}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
          <div className="text-[11px] font-medium text-amber-400">Pending Invites</div>
          <div className="text-xl font-bold text-amber-400 mt-1">{pendingCount}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
          <div className="text-[11px] font-medium text-violet-400">Project Leads</div>
          <div className="text-xl font-bold text-violet-400 mt-1">{leadsCount}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
          <div className="text-[11px] font-medium text-amber-300">Outgoing Members</div>
          <div className="text-xl font-bold text-amber-300 mt-1">{outgoingCount}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
          <div className="text-[11px] font-medium text-cyan-400">Incoming Members</div>
          <div className="text-xl font-bold text-cyan-400 mt-1">{incomingCount}</div>
        </div>
      </div>

      {/* Toolbar: Search & Filters */}
      <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search by name, email, department, or project..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Role Filter */}
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="px-2.5 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="all">All Roles</option>
            <option value="project_lead">Project Lead</option>
            <option value="outgoing_member">Outgoing Member</option>
            <option value="incoming_member">Incoming Member</option>
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-2.5 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="pending_invite">Pending Invite</option>
            <option value="inactive">Inactive</option>
          </select>

          {/* Project Filter */}
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

          {(searchQuery || selectedRole !== 'all' || selectedStatus !== 'all' || selectedProject !== 'all') && (
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedRole('all');
                setSelectedStatus('all');
                setSelectedProject('all');
              }}
              className="px-2.5 py-2 text-xs text-slate-400 hover:text-white underline"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Member Cards / Table */}
      {filteredMembers.length === 0 ? (
        <Card className="p-12 text-center bg-[#0F172A] border-slate-800">
          <Users className="h-10 w-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No team members found</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            Try adjusting your search query or filters to locate specific teammates.
          </p>
        </Card>
      ) : viewMode === 'grid' ? (
        /* Grid Profile Cards */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredMembers.map((member) => (
            <Card
              key={member.id}
              className="p-5 bg-[#0F172A] border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between group"
            >
              <div>
                {/* Top Row: Avatar + Info + Status */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <img
                      src={member.avatarUrl}
                      alt={member.name}
                      className="h-12 w-12 rounded-full border border-slate-700 object-cover shrink-0"
                    />
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <h3 className="text-sm font-semibold text-white truncate">{member.name}</h3>
                      </div>
                      <p className="text-xs text-slate-400 truncate mt-0.5">{member.roleTitle}</p>
                      <div className="flex items-center gap-1 text-[11px] text-slate-500 mt-0.5">
                        <Building className="h-3 w-3 text-slate-500 shrink-0" />
                        <span className="truncate">{member.department}</span>
                      </div>
                    </div>
                  </div>
                  <div className="shrink-0">{getStatusBadge(member.status)}</div>
                </div>

                {/* Role Pill */}
                <div className="mt-3.5 flex items-center justify-between">
                  <div>{getRoleBadge(member.role)}</div>
                  <span className="text-[11px] text-slate-500">{member.lastActive}</span>
                </div>

                {/* Email */}
                <div className="mt-2.5 text-xs text-slate-400 flex items-center gap-1.5">
                  <Mail className="h-3 w-3 text-slate-500 shrink-0" />
                  <span className="truncate font-mono text-[11px]">{member.email}</span>
                </div>

                {/* Assigned Projects */}
                <div className="mt-4 pt-3 border-t border-slate-800/80">
                  <div className="text-[11px] font-medium text-slate-400 mb-2 flex items-center gap-1.5">
                    <FolderGit2 className="h-3 w-3 text-slate-500" />
                    <span>Assigned Workspaces ({member.assignedProjects.length})</span>
                  </div>
                  {member.assignedProjects.length === 0 ? (
                    <span className="text-[11px] text-slate-500 italic">No active project assignments</span>
                  ) : (
                    <div className="flex flex-wrap gap-1.5">
                      {member.assignedProjects.map((p) => (
                        <span
                          key={p.projectId}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-slate-900 border border-slate-800 text-slate-300 font-mono"
                          title={`${p.projectKey}: ${p.projectTitle} (${p.roleInProject})`}
                        >
                          <span className="text-brand-400 font-bold">{p.projectKey}</span>
                          <span className="text-slate-500">·</span>
                          <span className="text-slate-400 truncate max-w-[100px]">{p.roleInProject}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Card Footer Actions */}
              <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                {member.status === 'pending_invite' ? (
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<Send className="h-3 w-3 text-amber-400" />}
                    onClick={() => handleResendInvite(member)}
                    className="text-amber-300 border-amber-500/30 hover:bg-amber-500/10"
                  >
                    Resend Invite
                  </Button>
                ) : (
                  <span className="text-[11px] text-slate-500">
                    {member.status === 'active' ? 'Active Contributor' : 'Suspended'}
                  </span>
                )}

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleOpenAssignProjects(member)}
                    className="px-2 py-1 text-[11px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                    title="Assign Projects"
                  >
                    Assign
                  </button>
                  <button
                    onClick={() => handleOpenEditRole(member)}
                    className="px-2 py-1 text-[11px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                    title="Change Role"
                  >
                    Role
                  </button>
                  <button
                    onClick={() => handleToggleStatus(member)}
                    className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800"
                    title={member.status === 'active' ? 'Deactivate' : 'Activate'}
                  >
                    {member.status === 'active' ? <UserX className="h-3.5 w-3.5" /> : <UserCheck className="h-3.5 w-3.5 text-emerald-400" />}
                  </button>
                  <button
                    onClick={() => handleRemoveMember(member)}
                    className="p-1 text-slate-400 hover:text-red-400 rounded hover:bg-slate-800"
                    title="Remove from Workspace"
                  >
                    <AlertCircle className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        /* Table View */
        <Card className="bg-[#0F172A] border-slate-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-3 px-4">Member</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Assigned Projects</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Last Activity</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {filteredMembers.map((member) => (
                  <tr key={member.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        <img
                          src={member.avatarUrl}
                          alt={member.name}
                          className="h-8 w-8 rounded-full border border-slate-700 object-cover shrink-0"
                        />
                        <div>
                          <div className="font-semibold text-white">{member.name}</div>
                          <div className="text-[11px] text-slate-400 font-mono">{member.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">{getRoleBadge(member.role)}</td>
                    <td className="py-3 px-4 text-slate-300">{member.department}</td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1 max-w-[200px]">
                        {member.assignedProjects.map((p) => (
                          <span
                            key={p.projectId}
                            className="px-1.5 py-0.5 rounded text-[10px] bg-slate-900 border border-slate-800 text-slate-300 font-mono"
                          >
                            {p.projectKey}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-4">{getStatusBadge(member.status)}</td>
                    <td className="py-3 px-4 text-slate-400">{member.lastActive}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenAssignProjects(member)}
                        >
                          Projects
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenEditRole(member)}
                        >
                          Role
                        </Button>
                        {member.status === 'pending_invite' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleResendInvite(member)}
                            className="text-amber-400"
                          >
                            Resend
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* INVITE MEMBER MODAL */}
      <Modal
        isOpen={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
        maxWidth="lg"
        title="Invite Team Member"
      >
        <form onSubmit={handleSendInvite} className="space-y-4">
          <p className="text-xs text-slate-400">
            Grant workspace access and assign handover responsibilities according to engineering roles.
          </p>

          {/* Email Field (Required) */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Work Email Address <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="email"
                required
                placeholder="developer@techfrontier.io"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>
          </div>

          {/* Full Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
            <input
              type="text"
              placeholder="e.g. Alex Mercer"
              value={inviteName}
              onChange={(e) => setInviteName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* Role Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Role Selection <span className="text-red-400">*</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {/* Outgoing Member */}
              <div
                onClick={() => setInviteRole('outgoing_member')}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  inviteRole === 'outgoing_member'
                    ? 'bg-amber-500/10 border-amber-500/60 ring-1 ring-amber-500/40'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-1.5 font-semibold text-xs text-amber-300">
                  <ArrowRightLeft className="h-3.5 w-3.5" />
                  <span>Outgoing Member</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Uploads docs, runs AI generation, drafts handovers.
                </p>
              </div>

              {/* Incoming Member */}
              <div
                onClick={() => setInviteRole('incoming_member')}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  inviteRole === 'incoming_member'
                    ? 'bg-emerald-500/10 border-emerald-500/60 ring-1 ring-emerald-500/40'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-1.5 font-semibold text-xs text-emerald-300">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>Incoming Member</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Inspects approved handovers, acknowledges, executes tasks.
                </p>
              </div>

              {/* Project Lead */}
              <div
                onClick={() => setInviteRole('project_lead')}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  inviteRole === 'project_lead'
                    ? 'bg-violet-500/10 border-violet-500/60 ring-1 ring-violet-500/40'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-1.5 font-semibold text-xs text-violet-300">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Project Lead</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Manages project, reviews handovers, approves & shares.
                </p>
              </div>
            </div>
          </div>

          {/* Department & Job Title */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Job Title</label>
              <input
                type="text"
                placeholder="e.g. Senior Backend Engineer"
                value={inviteRoleTitle}
                onChange={(e) => setInviteRoleTitle(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Department</label>
              <input
                type="text"
                placeholder="e.g. Core Infrastructure"
                value={inviteDepartment}
                onChange={(e) => setInviteDepartment(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>
          </div>

          {/* Project Assignment */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Assign to Initial Projects
            </label>
            <div className="space-y-1.5 max-h-36 overflow-y-auto p-2 bg-slate-900/80 border border-slate-800 rounded-lg">
              {mockProjects.map((p) => {
                const isChecked = inviteProjectIds.includes(p.id);
                return (
                  <label
                    key={p.id}
                    className="flex items-center gap-2 p-1.5 rounded hover:bg-slate-800/60 cursor-pointer text-xs text-slate-300"
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => handleToggleProjectSelection(p.id)}
                      className="rounded border-slate-700 text-brand-500 focus:ring-0 bg-slate-800"
                    />
                    <span className="font-mono text-brand-400 font-bold">{p.key}</span>
                    <span className="truncate">{p.title}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Member Status */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Initial Status</label>
            <div className="flex items-center gap-4 text-xs text-slate-300">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="status"
                  value="pending_invite"
                  checked={inviteStatus === 'pending_invite'}
                  onChange={() => setInviteStatus('pending_invite')}
                  className="text-brand-500"
                />
                <span>Pending Invitation (Email link required)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="status"
                  value="active"
                  checked={inviteStatus === 'active'}
                  onChange={() => setInviteStatus('active')}
                  className="text-brand-500"
                />
                <span>Activate Immediately</span>
              </label>
            </div>
          </div>

          {/* Buttons */}
          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2">
            <Button variant="ghost" size="sm" type="button" onClick={() => setIsInviteModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit" leftIcon={<Send className="h-3.5 w-3.5" />}>
              Dispatch Invitation
            </Button>
          </div>
        </form>
      </Modal>

      {/* EDIT ROLE MODAL */}
      <Modal
        isOpen={!!editingMember}
        onClose={() => setEditingMember(null)}
        maxWidth="md"
        title={`Change Role: ${editingMember?.name}`}
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-400">
            Select the new permission level for this engineer. Permissions take effect immediately across all project workspaces.
          </p>

          <div className="space-y-2">
            {[
              {
                role: 'project_lead' as HandoverAppRole,
                label: 'Project Lead',
                desc: 'Manage projects, review handovers, approve & share, manage team permissions.',
              },
              {
                role: 'outgoing_member' as HandoverAppRole,
                label: 'Outgoing Member',
                desc: 'Create project, upload documents, generate AI handover, edit drafts.',
              },
              {
                role: 'incoming_member' as HandoverAppRole,
                label: 'Incoming Member',
                desc: 'View approved handovers, acknowledge receipt, execute assigned continuation tasks.',
              },
            ].map((r) => (
              <div
                key={r.role}
                onClick={() => setNewRoleForEdit(r.role)}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  newRoleForEdit === r.role
                    ? 'bg-brand-500/10 border-brand-500/50 ring-1 ring-brand-500/30'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white">{r.label}</span>
                  {newRoleForEdit === r.role && <CheckCircle2 className="h-4 w-4 text-brand-400" />}
                </div>
                <p className="text-[11px] text-slate-400 mt-1">{r.desc}</p>
              </div>
            ))}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Custom Role Title</label>
            <input
              type="text"
              value={newRoleTitleForEdit}
              onChange={(e) => setNewRoleTitleForEdit(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
            />
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setEditingMember(null)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleSaveRole}>
              Save Role Changes
            </Button>
          </div>
        </div>
      </Modal>

      {/* ASSIGN PROJECTS MODAL */}
      <Modal
        isOpen={!!assigningMember}
        onClose={() => setAssigningMember(null)}
        maxWidth="md"
        title={`Project Assignments: ${assigningMember?.name}`}
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-400">
            Check the project workspaces this team member has authorization to access.
          </p>

          <div className="space-y-2 max-h-64 overflow-y-auto p-2 bg-slate-900/60 border border-slate-800 rounded-lg">
            {mockProjects.map((p) => {
              const isChecked = selectedProjectIdsForAssign.includes(p.id);
              return (
                <label
                  key={p.id}
                  className="flex items-center justify-between p-2 rounded hover:bg-slate-800/60 cursor-pointer text-xs"
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() =>
                        setSelectedProjectIdsForAssign((prev) =>
                          prev.includes(p.id) ? prev.filter((id) => id !== p.id) : [...prev, p.id]
                        )
                      }
                      className="rounded border-slate-700 text-brand-500 focus:ring-0 bg-slate-800"
                    />
                    <div>
                      <span className="font-mono text-brand-400 font-bold mr-2">{p.key}</span>
                      <span className="text-white font-medium">{p.title}</span>
                    </div>
                  </div>
                  <span className="text-[10px] text-slate-400 uppercase">{p.status.replace('_', ' ')}</span>
                </label>
              );
            })}
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setAssigningMember(null)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleSaveAssignedProjects}>
              Update Assignments
            </Button>
          </div>
        </div>
      </Modal>

      {/* CONFIRM REMOVE MEMBER DIALOG */}
      <ConfirmDialog
        isOpen={!!memberToRemove}
        onClose={() => setMemberToRemove(null)}
        onConfirm={handleConfirmRemove}
        title="Remove Team Member"
        message={`Are you sure you want to remove ${memberToRemove?.name} (${memberToRemove?.email}) from the workspace? They will lose access to all assigned project workspaces.`}
        confirmLabel="Remove Member"
        variant="danger"
      />
    </div>
  );
};

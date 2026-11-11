import { TeamMember, InviteMemberPayload, TeamMemberStatus } from '../types/team';
import { HandoverAppRole } from '../context/RoleContext';
import { mockProjects } from '../data/mockData';

const STORAGE_KEY = 'kh_team_members_v1';

const initialTeamMembers: TeamMember[] = [
  {
    id: 'usr-1',
    name: 'Elena Rostova',
    email: 'elena.rostova@techfrontier.io',
    role: 'project_lead',
    roleTitle: 'Staff Platform Architect & Lead',
    department: 'Distributed Systems',
    avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    status: 'active',
    lastActive: '5m ago',
    bio: 'Oversees multi-region service resilience, zero-downtime database transitions, and knowledge handovers.',
    assignedProjects: [
      {
        projectId: 'proj-1',
        projectKey: 'PAY-V2',
        projectTitle: 'Global Payment Orchestration & Multi-PSP Engine',
        roleInProject: 'Project Lead',
      },
      {
        projectId: 'proj-2',
        projectKey: 'DB-SYNC',
        projectTitle: 'Distributed CockroachDB & Event Replicator',
        roleInProject: 'Architecture Reviewer',
      },
    ],
  },
  {
    id: 'usr-2',
    name: 'David Chen',
    email: 'david.chen@techfrontier.io',
    role: 'incoming_member',
    roleTitle: 'Senior Infrastructure Engineer',
    department: 'Core Infrastructure',
    avatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
    status: 'active',
    lastActive: '12m ago',
    bio: 'Successor for Payment Engine routing, Stripe/Adyen failover matrices, and Kubernetes ingress clusters.',
    assignedProjects: [
      {
        projectId: 'proj-1',
        projectKey: 'PAY-V2',
        projectTitle: 'Global Payment Orchestration & Multi-PSP Engine',
        roleInProject: 'Incoming Successor',
      },
    ],
  },
  {
    id: 'usr-3',
    name: 'Sarah Jenkins',
    email: 'sarah.jenkins@techfrontier.io',
    role: 'outgoing_member',
    roleTitle: 'Principal Identity Architect',
    department: 'Platform Architecture',
    avatarUrl: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80',
    status: 'active',
    lastActive: '1h ago',
    bio: 'Author of Passkey WebAuthn implementation and PostgreSQL 16 schema partition cutover runbooks.',
    assignedProjects: [
      {
        projectId: 'proj-3',
        projectKey: 'AUTH-ZERO',
        projectTitle: 'Customer Identity & Passkey Migration',
        roleInProject: 'Outgoing Author',
      },
    ],
  },
  {
    id: 'usr-4',
    name: 'Marcus Vance',
    email: 'marcus.v@techfrontier.io',
    role: 'project_lead',
    roleTitle: 'VP of Engineering & Lead Reviewer',
    department: 'Engineering Leadership',
    avatarUrl: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80',
    status: 'active',
    lastActive: '2h ago',
    bio: 'Responsible for executive sign-offs, risk certifications, and architectural governance.',
    assignedProjects: [
      {
        projectId: 'proj-3',
        projectKey: 'AUTH-ZERO',
        projectTitle: 'Customer Identity & Passkey Migration',
        roleInProject: 'Project Lead',
      },
      {
        projectId: 'proj-1',
        projectKey: 'PAY-V2',
        projectTitle: 'Global Payment Orchestration & Multi-PSP Engine',
        roleInProject: 'Executive Reviewer',
      },
    ],
  },
  {
    id: 'usr-5',
    name: 'Kavita Patel',
    email: 'kavita.p@techfrontier.io',
    role: 'incoming_member',
    roleTitle: 'Staff Security Engineer',
    department: 'Security & Identity',
    avatarUrl: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
    status: 'active',
    lastActive: '3h ago',
    bio: 'Taking ownership of cryptographic key rotation, HSM key ceremonies, and zero-trust policies.',
    assignedProjects: [
      {
        projectId: 'proj-3',
        projectKey: 'AUTH-ZERO',
        projectTitle: 'Customer Identity & Passkey Migration',
        roleInProject: 'Incoming Successor',
      },
    ],
  },
  {
    id: 'usr-6',
    name: 'Alex Mercer',
    email: 'alex.mercer@fintechgroup.corp',
    role: 'outgoing_member',
    roleTitle: 'Lead Data Pipeline Engineer',
    department: 'Data Platform',
    avatarUrl: 'https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=150&auto=format&fit=crop&q=80',
    status: 'pending_invite',
    lastActive: 'Never (Invited)',
    invitedAt: '2026-11-08T14:30:00Z',
    bio: 'Transitioning Kafka data pipeline compaction runbooks to successor.',
    assignedProjects: [
      {
        projectId: 'proj-2',
        projectKey: 'DB-SYNC',
        projectTitle: 'Distributed CockroachDB & Event Replicator',
        roleInProject: 'Outgoing Author',
      },
    ],
  },
  {
    id: 'usr-7',
    name: 'Maya Lin',
    email: 'maya.lin@enterprisecloud.dev',
    role: 'incoming_member',
    roleTitle: 'Cloud Infrastructure Specialist',
    department: 'Core Infrastructure',
    avatarUrl: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80',
    status: 'inactive',
    lastActive: '5 days ago',
    bio: 'On scheduled rotation; scheduled to reactivate for Q1 Cloud Migration wave.',
    assignedProjects: [],
  },
];

class TeamService {
  private load(): TeamMember[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(initialTeamMembers));
        return [...initialTeamMembers];
      }
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) && parsed.length > 0 ? parsed : [...initialTeamMembers];
    } catch {
      return [...initialTeamMembers];
    }
  }

  private save(members: TeamMember[]): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(members));
    } catch (err) {
      console.warn('Failed to save team members to storage:', err);
    }
  }

  getMembers(): TeamMember[] {
    return this.load();
  }

  getMemberById(id: string): TeamMember | undefined {
    return this.load().find((m) => m.id === id);
  }

  inviteMember(payload: InviteMemberPayload): TeamMember {
    const members = this.load();

    const assignedProjects: TeamMember['assignedProjects'] = payload.projectIds.map((pid) => {
      const project = mockProjects.find((p) => p.id === pid);
      return {
        projectId: pid,
        projectKey: project?.key || 'PROJ',
        projectTitle: project?.title || 'Assigned Project',
        roleInProject:
          payload.role === 'project_lead'
            ? 'Project Lead'
            : payload.role === 'outgoing_member'
            ? 'Outgoing Author'
            : 'Incoming Successor',
      };
    });

    const displayName = payload.name && payload.name.trim().length > 0
      ? payload.name
      : payload.email.split('@')[0].replace('.', ' ').replace(/\b\w/g, (c) => c.toUpperCase());

    const newMember: TeamMember = {
      id: `usr-${Date.now()}`,
      name: displayName,
      email: payload.email.trim().toLowerCase(),
      role: payload.role,
      roleTitle: payload.roleTitle || (payload.role === 'project_lead' ? 'Project Lead' : payload.role === 'outgoing_member' ? 'Senior Engineer' : 'Incoming Successor'),
      department: payload.department || 'Engineering',
      avatarUrl: `https://images.unsplash.com/photo-${1534528741775 + (members.length % 5) * 1000}?w=150&auto=format&fit=crop&q=80`,
      status: payload.status || 'pending_invite',
      lastActive: payload.status === 'active' ? 'Just now' : 'Never (Invited)',
      invitedAt: new Date().toISOString(),
      assignedProjects,
      bio: `Handover team member assigned to ${assignedProjects.length} project(s).`,
    };

    members.unshift(newMember);
    this.save(members);
    return newMember;
  }

  updateMemberRole(memberId: string, role: HandoverAppRole, roleTitle?: string): TeamMember | null {
    const members = this.load();
    const index = members.findIndex((m) => m.id === memberId);
    if (index === -1) return null;

    members[index].role = role;
    if (roleTitle) members[index].roleTitle = roleTitle;

    // Also update project roles
    members[index].assignedProjects = members[index].assignedProjects.map((p) => ({
      ...p,
      roleInProject:
        role === 'project_lead'
          ? 'Project Lead'
          : role === 'outgoing_member'
          ? 'Outgoing Author'
          : 'Incoming Successor',
    }));

    this.save(members);
    return members[index];
  }

  updateMemberStatus(memberId: string, status: TeamMemberStatus): TeamMember | null {
    const members = this.load();
    const index = members.findIndex((m) => m.id === memberId);
    if (index === -1) return null;

    members[index].status = status;
    if (status === 'active' && members[index].lastActive.includes('Never')) {
      members[index].lastActive = 'Active now';
    }
    this.save(members);
    return members[index];
  }

  assignProjects(memberId: string, projectIds: string[]): TeamMember | null {
    const members = this.load();
    const index = members.findIndex((m) => m.id === memberId);
    if (index === -1) return null;

    const assignedProjects: TeamMember['assignedProjects'] = projectIds.map((pid) => {
      const project = mockProjects.find((p) => p.id === pid);
      return {
        projectId: pid,
        projectKey: project?.key || 'PROJ',
        projectTitle: project?.title || 'Assigned Project',
        roleInProject:
          members[index].role === 'project_lead'
            ? 'Project Lead'
            : members[index].role === 'outgoing_member'
            ? 'Outgoing Author'
            : 'Incoming Successor',
      };
    });

    members[index].assignedProjects = assignedProjects;
    this.save(members);
    return members[index];
  }

  removeMember(memberId: string): boolean {
    const members = this.load();
    const filtered = members.filter((m) => m.id !== memberId);
    if (filtered.length === members.length) return false;
    this.save(filtered);
    return true;
  }

  resendInvite(memberId: string): boolean {
    const members = this.load();
    const member = members.find((m) => m.id === memberId);
    if (!member) return false;
    member.invitedAt = new Date().toISOString();
    this.save(members);
    return true;
  }
}

export const teamService = new TeamService();

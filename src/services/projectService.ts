import { apiClient, ApiResponse } from './apiClient';
import { Project, CreateProjectFormData } from '../types/project';
import { mockProjects, mockUsers } from '../data/mockData';

const STORAGE_KEY = 'kh_projects_store';

function loadProjectsFromStorage(): Project[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(mockProjects));
      return [...mockProjects];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : [...mockProjects];
  } catch {
    return [...mockProjects];
  }
}

function saveProjectsToStorage(projects: Project[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(projects));
  } catch (err) {
    console.warn('Failed to persist projects to storage:', err);
  }
}

class ProjectService {
  async getAll(): Promise<ApiResponse<Project[]>> {
    return apiClient.executeMock(() => {
      return loadProjectsFromStorage();
    });
  }

  async getById(id: string): Promise<ApiResponse<Project | undefined>> {
    return apiClient.executeMock(() => {
      const projects = loadProjectsFromStorage();
      return projects.find((p) => p.id === id || p.key.toLowerCase() === id.toLowerCase());
    });
  }

  async create(formData: CreateProjectFormData): Promise<ApiResponse<Project>> {
    return apiClient.executeMock(() => {
      const projects = loadProjectsFromStorage();

      // Find selected users
      const outgoingUser = mockUsers.find((u) => u.id === formData.outgoingMemberId) || mockUsers[0];
      const incomingUser = mockUsers.find((u) => u.id === formData.incomingMemberId) || mockUsers[1];
      const leadUser = mockUsers.find((u) => u.id === formData.projectLeadId) || outgoingUser;

      // Collect authorized members
      const memberList = mockUsers.filter((u) =>
        formData.authorizedMemberIds.includes(u.id) ||
        u.id === outgoingUser.id ||
        u.id === incomingUser.id ||
        u.id === leadUser.id
      );

      const newProject: Project = {
        id: `proj-${Date.now()}`,
        key: formData.key.toUpperCase(),
        title: formData.title,
        description: formData.description,
        category: formData.category || 'General',
        status: formData.status || 'in_progress',
        owner: leadUser,
        successor: incomingUser,
        outgoingMember: outgoingUser,
        incomingMember: incomingUser,
        projectLead: leadUser,
        incomingRole: formData.incomingRole,
        handoverPurpose: formData.handoverPurpose,
        startDate: formData.startDate || new Date().toISOString().split('T')[0],
        expectedDeadline: formData.expectedDeadline || new Date(Date.now() + 60 * 86400000).toISOString().split('T')[0],
        createdAt: new Date().toISOString().split('T')[0],
        knowledgeHealthScore: 100,
        lastAuditDate: new Date().toISOString().split('T')[0],
        handoverDueDate: formData.handoverDeadline || formData.expectedDeadline,
        totalDocuments: 1, // starter readme
        totalDecisions: 0,
        unresolvedGaps: 0,
        tags: [formData.category, 'Active Handover'],
        membersCount: memberList.length,
        members: memberList,
        lastUpdatedText: 'Just created',
        handoverProgress: 15,
        repoUrl: `https://github.com/techfrontier/${formData.key.toLowerCase()}`,
        permissions: {
          uploadDocs: formData.uploadDocs,
          reviewApprove: formData.reviewApprove,
          incomingAccess: formData.incomingAccess,
          authorizedMemberIds: formData.authorizedMemberIds,
        },
      };

      projects.unshift(newProject);
      saveProjectsToStorage(projects);

      return newProject;
    });
  }

  async update(id: string, updates: Partial<Project>): Promise<ApiResponse<Project>> {
    return apiClient.executeMock(() => {
      const projects = loadProjectsFromStorage();
      const index = projects.findIndex((p) => p.id === id || p.key === id);
      if (index === -1) {
        throw new Error('Project not found');
      }

      const updated = {
        ...projects[index],
        ...updates,
        lastUpdatedText: 'Updated just now',
      };

      projects[index] = updated;
      saveProjectsToStorage(projects);

      return updated;
    });
  }
}

export const projectService = new ProjectService();

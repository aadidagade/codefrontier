import React, { createContext, useContext, useState, useEffect } from 'react';
import { useToast } from '../hooks/useToast';

export type HandoverAppRole = 'project_lead' | 'outgoing_member' | 'incoming_member';

export interface RolePermissions {
  // Outgoing member capabilities
  canCreateProject: boolean;
  canUploadDocs: boolean;
  canGenerateHandover: boolean;
  canEditDraft: boolean;

  // Project lead capabilities
  canManageProject: boolean;
  canReviewHandovers: boolean;
  canApproveAndShare: boolean;
  canManagePermissions: boolean;

  // Incoming member capabilities
  canViewApprovedHandovers: boolean;
  canAcknowledgeHandover: boolean;
  canContinueTasks: boolean;
}

interface RoleContextType {
  currentRole: HandoverAppRole;
  roleLabel: string;
  roleDescription: string;
  permissions: RolePermissions;
  setRole: (role: HandoverAppRole) => void;
}

const ROLE_STORAGE_KEY = 'kh_active_app_role';

const permissionsMap: Record<HandoverAppRole, RolePermissions> = {
  project_lead: {
    canCreateProject: true,
    canUploadDocs: true,
    canGenerateHandover: true,
    canEditDraft: true,
    canManageProject: true,
    canReviewHandovers: true,
    canApproveAndShare: true,
    canManagePermissions: true,
    canViewApprovedHandovers: true,
    canAcknowledgeHandover: false,
    canContinueTasks: true,
  },
  outgoing_member: {
    canCreateProject: true,
    canUploadDocs: true,
    canGenerateHandover: true,
    canEditDraft: true,
    canManageProject: false,
    canReviewHandovers: false,
    canApproveAndShare: false,
    canManagePermissions: false,
    canViewApprovedHandovers: false,
    canAcknowledgeHandover: false,
    canContinueTasks: false,
  },
  incoming_member: {
    canCreateProject: false,
    canUploadDocs: false,
    canGenerateHandover: false,
    canEditDraft: false,
    canManageProject: false,
    canReviewHandovers: false,
    canApproveAndShare: false,
    canManagePermissions: false,
    canViewApprovedHandovers: true,
    canAcknowledgeHandover: true,
    canContinueTasks: true,
  },
};

const roleMetadata: Record<HandoverAppRole, { label: string; description: string }> = {
  project_lead: {
    label: 'Project Lead',
    description: 'Full administrative authority: manage projects, review handovers, certify approvals, and configure team permissions.',
  },
  outgoing_member: {
    label: 'Outgoing Member',
    description: 'Knowledge contributor: upload project documents, run AI generation, and draft handover briefs.',
  },
  incoming_member: {
    label: 'Incoming Member',
    description: 'Successor: inspect approved handovers, acknowledge receipt, and track continuation responsibilities.',
  },
};

const RoleContext = createContext<RoleContextType | undefined>(undefined);

export const RoleProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { info } = useToast();
  const [currentRole, setCurrentRoleState] = useState<HandoverAppRole>(() => {
    const saved = localStorage.getItem(ROLE_STORAGE_KEY) as HandoverAppRole;
    return saved || 'project_lead';
  });

  const setRole = (role: HandoverAppRole) => {
    setCurrentRoleState(role);
    localStorage.setItem(ROLE_STORAGE_KEY, role);
    info(
      `Switched Active Role: ${roleMetadata[role].label}`,
      `Navigation and operational permissions updated for ${roleMetadata[role].label}.`
    );
  };

  return (
    <RoleContext.Provider
      value={{
        currentRole,
        roleLabel: roleMetadata[currentRole].label,
        roleDescription: roleMetadata[currentRole].description,
        permissions: permissionsMap[currentRole],
        setRole,
      }}
    >
      {children}
    </RoleContext.Provider>
  );
};

export const useRole = (): RoleContextType => {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error('useRole must be used within a RoleProvider');
  }
  return context;
};

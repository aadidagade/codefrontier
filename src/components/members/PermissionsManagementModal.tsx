import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Sparkles,
} from 'lucide-react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import {
  ProjectMember,
  AVAILABLE_PERMISSIONS,
  ROLE_DEFAULT_PERMISSIONS,
  PermissionDefinition,
} from '../../types/member';

export interface PermissionsManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  member: ProjectMember | null;
  onSavePermissions: (memberId: string, customPermissions: string[]) => Promise<void>;
  isAuthorized: boolean;
}

export const PermissionsManagementModal: React.FC<PermissionsManagementModalProps> = ({
  isOpen,
  onClose,
  member,
  onSavePermissions,
  isAuthorized,
}) => {
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>('all');

  useEffect(() => {
    if (member) {
      if (member.custom_permissions && Array.isArray(member.custom_permissions)) {
        setSelectedPermissions([...member.custom_permissions]);
      } else {
        const defaultRolePerms = ROLE_DEFAULT_PERMISSIONS[member.role] || [];
        setSelectedPermissions([...defaultRolePerms]);
      }
    }
  }, [member, isOpen]);

  if (!member) return null;

  const defaultRolePerms = ROLE_DEFAULT_PERMISSIONS[member.role] || [];

  const handleToggle = (key: string) => {
    if (!isAuthorized) return;
    setSelectedPermissions((prev) =>
      prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key]
    );
  };

  const handleResetToDefaults = () => {
    setSelectedPermissions([...defaultRolePerms]);
  };

  const handleSave = async () => {
    if (!isAuthorized) return;
    setIsSaving(true);
    try {
      await onSavePermissions(member.id, selectedPermissions);
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  const categories = [
    { id: 'all', label: 'All Permissions' },
    { id: 'workspace', label: 'Workspace' },
    { id: 'documents', label: 'Documents' },
    { id: 'handover', label: 'Handover Synthesis' },
    { id: 'governance', label: 'Governance & Security' },
  ];

  const filteredPermissions =
    activeCategory === 'all'
      ? AVAILABLE_PERMISSIONS
      : AVAILABLE_PERMISSIONS.filter((p) => p.category === activeCategory);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="2xl"
      title="Permissions Management"
      description="Configure granular role capabilities and explicit permission overrides for this project member."
      footer={
        <div className="flex flex-col sm:flex-row items-center justify-between w-full gap-3">
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            onClick={handleResetToDefaults}
            disabled={!isAuthorized || isSaving}
            className="text-xs text-slate-400 hover:text-white"
          >
            Reset to Role Defaults
          </Button>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onClose} disabled={isSaving}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<ShieldCheck className="h-4 w-4" />}
              onClick={handleSave}
              isLoading={isSaving}
              disabled={!isAuthorized}
            >
              Save Permission Matrix
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-5">
        {/* Member Profile Summary */}
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center gap-3">
            <img
              src={
                member.profile_image ||
                'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'
              }
              alt={member.full_name}
              className="h-10 w-10 rounded-full object-cover border border-slate-700"
            />
            <div>
              <div className="text-sm font-semibold text-white flex items-center gap-2">
                <span>{member.full_name}</span>
                <Badge variant="accent" size="sm">
                  {member.role_display_name}
                </Badge>
              </div>
              <div className="text-xs text-slate-400 font-mono mt-0.5">{member.email}</div>
            </div>
          </div>

          <div className="text-right hidden sm:block">
            <div className="text-[11px] text-slate-500 font-medium">Effective Privileges</div>
            <div className="text-xs font-mono font-bold text-brand-400">
              {selectedPermissions.length} / {AVAILABLE_PERMISSIONS.length} Granted
            </div>
          </div>
        </div>

        {/* Authorization Note */}
        {!isAuthorized ? (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2.5 text-xs text-amber-300">
            <Lock className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Read-Only Mode: </span>
              Only authorized Project Owners and Administrators can modify granular permission overrides.
            </div>
          </div>
        ) : (
          <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-start gap-2.5 text-xs text-indigo-300">
            <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5 text-indigo-400" />
            <div>
              <span className="font-semibold">Audit Enforced: </span>
              All permission modifications take effect immediately and are permanently recorded in the
              workspace Audit Trail.
            </div>
          </div>
        )}

        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-slate-800">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                activeCategory === cat.id
                  ? 'bg-brand-500/15 text-brand-400 border border-brand-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Permission Toggles List */}
        <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
          {filteredPermissions.map((perm) => {
            const isGranted = selectedPermissions.includes(perm.key);
            const isRoleDefault = defaultRolePerms.includes(perm.key);
            const isCustomOverride = isGranted !== isRoleDefault;

            return (
              <div
                key={perm.key}
                onClick={() => handleToggle(perm.key)}
                className={`p-3 rounded-xl border transition-all text-xs flex items-center justify-between gap-3 ${
                  isAuthorized ? 'cursor-pointer' : 'cursor-default'
                } ${
                  isGranted
                    ? 'bg-slate-900/90 border-brand-500/30 hover:border-brand-500/50'
                    : 'bg-slate-950/40 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start gap-3 min-w-0">
                  <input
                    type="checkbox"
                    checked={isGranted}
                    onChange={() => handleToggle(perm.key)}
                    disabled={!isAuthorized}
                    className="mt-0.5 rounded border-slate-700 bg-slate-800 text-brand-600 focus:ring-brand-500 h-4 w-4 cursor-pointer disabled:cursor-not-allowed"
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`font-semibold ${isGranted ? 'text-white' : 'text-slate-400'}`}>
                        {perm.label}
                      </span>
                      <span className="font-mono text-[10px] text-slate-500">({perm.key})</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                      {perm.description}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {isCustomOverride && (
                    <Badge variant={isGranted ? 'success' : 'danger'} size="sm">
                      {isGranted ? 'Override (+)' : 'Denied (-)'}
                    </Badge>
                  )}
                  {isRoleDefault && !isCustomOverride && (
                    <Badge variant="neutral" size="sm">
                      Role Default
                    </Badge>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Modal>
  );
};

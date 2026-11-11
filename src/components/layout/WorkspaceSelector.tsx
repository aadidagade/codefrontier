import React, { useState } from 'react';
import { ChevronDown, Check, Plus, Layers, Building2 } from 'lucide-react';
import { Dropdown, DropdownItem } from '../common/Dropdown';
import { useToast } from '../../hooks/useToast';
import { mockWorkspaces } from '../../data/mockData';
import { Workspace } from '../../types/dashboard';

export const WorkspaceSelector: React.FC = () => {
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace>(mockWorkspaces[0]);
  const { success, info } = useToast();

  const handleSelect = (ws: Workspace) => {
    setCurrentWorkspace(ws);
    success('Workspace Switched', `Active workspace set to ${ws.name}`);
  };

  const items: DropdownItem[] = [
    {
      id: 'header-ws',
      label: 'Switch Workspace',
      disabled: true,
    },
    {
      id: 'div-ws-0',
      label: '',
      divider: true,
    },
    ...mockWorkspaces.map((ws) => ({
      id: ws.id,
      label: `${ws.name} (${ws.plan})`,
      icon: (
        <span className="flex items-center gap-1.5">
          {ws.id === currentWorkspace.id ? (
            <Check className="h-3.5 w-3.5 text-brand-400" />
          ) : (
            <Building2 className="h-3.5 w-3.5 text-slate-500" />
          )}
        </span>
      ),
      onClick: () => handleSelect(ws),
    })),
    {
      id: 'div-ws-1',
      label: '',
      divider: true,
    },
    {
      id: 'new-workspace',
      label: 'Create Workspace...',
      icon: <Plus className="h-3.5 w-3.5 text-brand-400" />,
      onClick: () => info('Create Workspace', 'Workspace provision wizard opening.'),
    },
  ];

  return (
    <Dropdown
      trigger={
        <button
          type="button"
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 text-xs text-slate-200 hover:text-white transition-all duration-150"
        >
          <div className="h-5 w-5 rounded-md bg-brand-500/20 text-brand-400 flex items-center justify-center shrink-0">
            <Building2 className="h-3.5 w-3.5" />
          </div>
          <span className="font-semibold text-xs truncate max-w-[140px] sm:max-w-[180px]">
            {currentWorkspace.name}
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-slate-400 shrink-0 ml-0.5" />
        </button>
      }
      items={items}
      align="left"
    />
  );
};

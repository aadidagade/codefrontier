import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderGit2,
  FileText,
  ArrowRightLeft,
  CheckSquare,
  ListTodo,
  Users,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Layers,
  Database,
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { UserMenu } from './UserMenu';
import { mockHandovers } from '../../data/mockData';
import { useRole } from '../../context/RoleContext';

export interface SidebarProps {
  isOpen: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { currentRole, roleLabel } = useRole();

  // Role-adapted Sidebar navigation items
  const getNavItems = () => {
    if (currentRole === 'outgoing_member') {
      return [
        { label: 'Overview', path: '/dashboard', icon: LayoutDashboard },
        { label: 'My Projects', path: '/projects', icon: FolderGit2, badge: '2' },
        { label: 'Knowledge Sources', path: '/knowledge-sources', icon: Database, badge: '14' },
        { label: 'Generate Handover', path: '/handover/generate', icon: Sparkles, badge: 'AI' },
        { label: 'Handover Drafts', path: '/handover', icon: ArrowRightLeft, badge: '2' },
        { label: 'My Tasks', path: '/tasks', icon: ListTodo },
        { label: 'Team Directory', path: '/team', icon: Users },
        { label: 'Settings', path: '/settings', icon: Settings },
      ];
    }

    if (currentRole === 'incoming_member') {
      return [
        { label: 'Overview', path: '/dashboard', icon: LayoutDashboard },
        { label: 'My Handovers', path: '/my-handovers', icon: ArrowRightLeft, badge: '3' },
        { label: 'Continuation Tasks', path: '/tasks', icon: ListTodo, badge: '4' },
        { label: 'Approved Sources', path: '/knowledge-sources', icon: Database, badge: 'Verified' },
        { label: 'Team Directory', path: '/team', icon: Users },
        { label: 'Settings', path: '/settings', icon: Settings },
      ];
    }

    // Default: Project Lead
    return [
      { label: 'Overview', path: '/dashboard', icon: LayoutDashboard },
      { label: 'My Projects', path: '/projects', icon: FolderGit2, badge: '6' },
      { label: 'Knowledge Sources', path: '/knowledge-sources', icon: Database, badge: '34' },
      { label: 'Handovers', path: '/handover', icon: ArrowRightLeft, badge: '4' },
      { label: 'Pending Reviews', path: '/review', icon: CheckSquare, badge: '3' },
      { label: 'My Tasks', path: '/tasks', icon: ListTodo, badge: '4' },
      { label: 'Team Management', path: '/team', icon: Users, badge: 'Admin' },
      { label: 'Settings', path: '/settings', icon: Settings },
    ];
  };

  const navItems = getNavItems();

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex flex-col border-r border-slate-800 bg-[#080C14] transition-all duration-300 lg:static shrink-0 select-none',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
          isCollapsed ? 'w-16' : 'w-64'
        )}
      >
        {/* Workspace Brand Header */}
        <div className="flex h-14 items-center justify-between px-3.5 border-b border-slate-800">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-brand-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-glow shrink-0">
              <Layers className="h-4 w-4 text-white" />
            </div>
            {!isCollapsed && (
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-bold tracking-tight text-white truncate">
                  Knowledge Handover
                </span>
                <span className="text-[10px] text-brand-400 font-mono truncate">
                  TechFrontier · Enterprise
                </span>
              </div>
            )}
          </div>

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden lg:flex p-1 rounded-md text-slate-500 hover:text-slate-300 hover:bg-slate-800/80 transition-colors"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
          </button>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
          {!isCollapsed && (
            <div className="px-2 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              Workspace Navigation
            </div>
          )}

          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'group relative flex items-center gap-3 px-2.5 py-2 rounded-lg text-xs font-medium transition-all duration-150',
                    isActive
                      ? 'bg-brand-500/15 text-white font-semibold shadow-subtle border border-brand-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={cn(
                        'h-4 w-4 shrink-0 transition-colors',
                        isActive ? 'text-brand-400' : 'text-slate-400 group-hover:text-slate-200'
                      )}
                    />
                    {!isCollapsed && (
                      <span className="flex-1 truncate">{item.label}</span>
                    )}
                    {!isCollapsed && item.badge && (
                      <span
                        className={cn(
                          'text-[10px] font-mono px-1.5 py-0.2 rounded-full',
                          isActive ? 'bg-brand-500/25 text-brand-300' : 'bg-slate-800 text-slate-400'
                        )}
                      >
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}

          {/* Active Handover Section */}
          {!isCollapsed && (
            <div className="pt-4 mt-4 border-t border-slate-850">
              <div className="flex items-center justify-between px-2 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                <span>Active Handovers</span>
                <span className="text-[10px] text-brand-400 font-mono">Live</span>
              </div>
              <div className="mt-1 space-y-1">
                {mockHandovers.map((h) => (
                  <NavLink
                    key={h.id}
                    to="/handover"
                    className="flex flex-col gap-1 p-2 rounded-lg bg-slate-900/50 border border-slate-800/60 hover:border-slate-700 transition-colors text-left"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-slate-200 truncate">
                        {h.projectKey}
                      </span>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                        {h.progressPercentage}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
                      <div
                        className="bg-brand-500 h-full rounded-full transition-all duration-300"
                        style={{ width: `${h.progressPercentage}%` }}
                      />
                    </div>
                  </NavLink>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* AI Continuity Health Widget */}
        {!isCollapsed && (
          <div className="p-3 mx-2 my-2 rounded-xl bg-gradient-to-b from-brand-950/40 to-slate-900/60 border border-brand-500/20">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
              <Sparkles className="h-3.5 w-3.5 text-brand-400" />
              <span>Continuity Shield</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400 leading-tight">
              AI verified 94% of decisions across repositories.
            </p>
          </div>
        )}

        {/* User Menu Footer */}
        <div className="p-2 border-t border-slate-800">
          <UserMenu compact={isCollapsed} />
        </div>
      </aside>
    </>
  );
};

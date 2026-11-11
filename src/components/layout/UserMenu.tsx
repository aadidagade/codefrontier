import React from 'react';
import { useNavigate } from 'react-router-dom';
import { User, LogOut, Settings, ShieldCheck, Sparkles } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { Dropdown, DropdownItem } from '../common/Dropdown';

export const UserMenu: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { info } = useToast();

  const handleLogout = async () => {
    await logout();
    info('Logged out', 'You have been signed out of your session.');
    navigate('/login');
  };

  const menuItems: DropdownItem[] = [
    {
      id: 'profile',
      label: 'Profile & Credentials',
      icon: <User className="h-4 w-4" />,
      onClick: () => navigate('/settings'),
    },
    {
      id: 'workspace',
      label: 'Workspace Security',
      icon: <ShieldCheck className="h-4 w-4" />,
      onClick: () => navigate('/settings'),
    },
    {
      id: 'ai-audit',
      label: 'AI Audit Settings',
      icon: <Sparkles className="h-4 w-4 text-brand-400" />,
      onClick: () => navigate('/settings'),
    },
    {
      id: 'settings',
      label: 'Preferences',
      icon: <Settings className="h-4 w-4" />,
      onClick: () => navigate('/settings'),
    },
    {
      id: 'div-1',
      label: '',
      divider: true,
    },
    {
      id: 'logout',
      label: 'Sign Out',
      danger: true,
      icon: <LogOut className="h-4 w-4" />,
      onClick: handleLogout,
    },
  ];

  if (!user) return null;

  return (
    <Dropdown
      trigger={
        compact ? (
          <div className="relative group cursor-pointer">
            <img
              src={user.avatarUrl || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'}
              alt={user.name}
              className="h-8 w-8 rounded-full border border-slate-700/80 group-hover:border-brand-500/80 transition-colors object-cover"
            />
            <span className="absolute bottom-0 right-0 h-2 w-2 rounded-full bg-emerald-400 border border-[#0F172A]" />
          </div>
        ) : (
          <div className="flex items-center gap-2.5 p-1.5 rounded-lg hover:bg-slate-800/60 transition-colors cursor-pointer w-full text-left">
            <div className="relative shrink-0">
              <img
                src={user.avatarUrl || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'}
                alt={user.name}
                className="h-8 w-8 rounded-full border border-slate-700 object-cover"
              />
              <span className="absolute bottom-0 right-0 h-2 w-2 rounded-full bg-emerald-400 border border-[#0F172A]" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-slate-200 truncate">{user.name}</div>
              <div className="text-[11px] text-slate-400 truncate capitalize">{user.role.replace('_', ' ')}</div>
            </div>
          </div>
        )
      }
      items={menuItems}
      align="right"
    />
  );
};

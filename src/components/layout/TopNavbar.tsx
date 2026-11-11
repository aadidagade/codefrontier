import React, { useState, useEffect } from 'react';
import { Menu, Search, Sparkles, SlidersHorizontal } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Breadcrumbs } from './Breadcrumbs';
import { WorkspaceSelector } from './WorkspaceSelector';
import { ThemeToggle } from './ThemeToggle';
import { NotificationsDropdown } from './NotificationsDropdown';
import { UserMenu } from './UserMenu';
import { CommandPalette } from './CommandPalette';
import { RoleSwitcher } from './RoleSwitcher';
import { Button } from '../common/Button';

export interface TopNavbarProps {
  onToggleSidebar?: () => void;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({ onToggleSidebar }) => {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-800 bg-[#080C14]/90 backdrop-blur-md px-3 sm:px-6">
        {/* Left: Hamburger + Workspace Selector + Breadcrumbs */}
        <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              aria-label="Toggle Navigation"
            >
              <Menu className="h-5 w-5" />
            </button>
          )}
          <WorkspaceSelector />
          <div className="hidden xl:flex items-center pl-2 border-l border-slate-800">
            <Breadcrumbs />
          </div>
        </div>

        {/* Center: Global Search Command Palette Trigger */}
        <div className="hidden md:flex items-center flex-1 max-w-sm lg:max-w-md mx-4">
          <button
            onClick={() => setIsCommandPaletteOpen(true)}
            className="w-full flex items-center justify-between px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 text-xs text-slate-400 hover:text-slate-300 transition-all duration-150 shadow-sm"
          >
            <div className="flex items-center gap-2">
              <Search className="h-3.5 w-3.5 text-slate-500" />
              <span>Global search (projects, handovers, runbooks)...</span>
            </div>
            <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-800 border border-slate-700 rounded">
              ⌘K
            </kbd>
          </button>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <span
            className="hidden 2xl:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-mono text-slate-400 bg-slate-900/80 border border-slate-800 select-none"
            title="All architecture artifacts, conflict pairs, and evidence traces are realistic synthetic demonstrations for prototype evaluation."
          >
            <span className="h-1.5 w-1.5 rounded-full bg-violet-400" />
            <span>Synthetic Demo Data</span>
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/design-system')}
            className="hidden sm:flex text-slate-400 hover:text-slate-200 text-xs gap-1.5 h-8 px-2.5"
            leftIcon={<SlidersHorizontal className="h-3.5 w-3.5 text-brand-400" />}
          >
            UI Kit
          </Button>

          <Button
            variant="ai"
            size="sm"
            onClick={() => setIsCommandPaletteOpen(true)}
            leftIcon={<Sparkles className="h-3.5 w-3.5" />}
            className="hidden sm:flex text-xs h-8 px-3"
          >
            Ask AI Handover
          </Button>

          <RoleSwitcher />
          <NotificationsDropdown />
          <ThemeToggle />
          <div className="h-4 w-px bg-slate-800 mx-1" />
          <UserMenu compact />
        </div>
      </header>

      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
    </>
  );
};

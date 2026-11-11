import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';
import { Tooltip } from '../common/Tooltip';

export const ThemeToggle: React.FC<{ className?: string }> = ({ className }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <Tooltip content={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
      <button
        onClick={toggleTheme}
        className={`p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors ${className || ''}`}
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? (
          <Sun className="h-4 w-4 text-amber-400/90" />
        ) : (
          <Moon className="h-4 w-4 text-slate-300" />
        )}
      </button>
    </Tooltip>
  );
};

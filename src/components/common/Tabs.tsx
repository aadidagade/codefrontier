import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  icon?: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  variant?: 'pill' | 'underline';
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  variant = 'pill',
  className,
}) => {
  return (
    <div
      className={cn(
        'flex items-center',
        variant === 'pill'
          ? 'p-1 rounded-xl bg-slate-900/80 border border-slate-800/80'
          : 'border-b border-slate-800 gap-6',
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;

        if (variant === 'pill') {
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className={cn(
                'relative flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors select-none',
                isActive ? 'text-white' : 'text-slate-400 hover:text-slate-200'
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="activePillTab"
                  className="absolute inset-0 bg-slate-800 border border-slate-700/60 rounded-lg shadow-sm"
                  transition={{ type: 'spring', duration: 0.35, bounce: 0.15 }}
                />
              )}
              <span className="relative z-10 flex items-center gap-1.5">
                {tab.icon && <span className="h-3.5 w-3.5">{tab.icon}</span>}
                <span>{tab.label}</span>
                {typeof tab.count !== 'undefined' && (
                  <span
                    className={cn(
                      'text-[10px] px-1.5 py-0.2 rounded-full font-mono',
                      isActive ? 'bg-brand-500/20 text-brand-300' : 'bg-slate-800 text-slate-400'
                    )}
                  >
                    {tab.count}
                  </span>
                )}
              </span>
            </button>
          );
        }

        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              'relative pb-2.5 pt-1 text-xs font-medium transition-colors select-none flex items-center gap-1.5',
              isActive ? 'text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            {tab.icon && <span className="h-3.5 w-3.5">{tab.icon}</span>}
            <span>{tab.label}</span>
            {typeof tab.count !== 'undefined' && (
              <span
                className={cn(
                  'text-[10px] px-1.5 py-0.2 rounded-full font-mono',
                  isActive ? 'bg-brand-500/20 text-brand-300' : 'bg-slate-800 text-slate-400'
                )}
              >
                {tab.count}
              </span>
            )}
            {isActive && (
              <motion.div
                layoutId="activeUnderlineTab"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-500 rounded-full"
                transition={{ type: 'spring', duration: 0.35, bounce: 0.15 }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
};

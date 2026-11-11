import React, { useState, useRef, useEffect } from 'react';
import { ShieldCheck, ChevronDown, Check, UserCheck, ArrowRightLeft, UserPlus } from 'lucide-react';
import { useRole, HandoverAppRole } from '../../context/RoleContext';
import { cn } from '../../utils/cn';

export const RoleSwitcher: React.FC = () => {
  const { currentRole, roleLabel, setRole } = useRole();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const roles: { id: HandoverAppRole; label: string; desc: string; color: string }[] = [
    {
      id: 'project_lead',
      label: 'Project Lead',
      desc: 'Review & approve handovers, manage team & permissions',
      color: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
    },
    {
      id: 'outgoing_member',
      label: 'Outgoing Member',
      desc: 'Upload documentation, generate handovers, edit drafts',
      color: 'text-brand-400 bg-brand-500/10 border-brand-500/30',
    },
    {
      id: 'incoming_member',
      label: 'Incoming Member',
      desc: 'View approved handovers, acknowledge receipt, track tasks',
      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    },
  ];

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all duration-150',
          currentRole === 'project_lead'
            ? 'bg-purple-950/40 text-purple-300 border-purple-500/30 hover:border-purple-400'
            : currentRole === 'outgoing_member'
            ? 'bg-brand-950/40 text-brand-300 border-brand-500/30 hover:border-brand-400'
            : 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30 hover:border-emerald-400'
        )}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
        <span className="hidden sm:inline font-mono text-[10px] uppercase opacity-75">Role:</span>
        <span>{roleLabel}</span>
        <ChevronDown className="h-3 w-3 opacity-60" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 rounded-xl bg-[#090D16] border border-slate-800 shadow-2xl p-2 z-50 space-y-1">
          <div className="px-2.5 py-1.5 text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800">
            Switch Simulated Handover Role
          </div>

          {roles.map((r) => {
            const isSelected = currentRole === r.id;
            return (
              <button
                key={r.id}
                onClick={() => {
                  setRole(r.id);
                  setIsOpen(false);
                }}
                className={cn(
                  'w-full flex items-start gap-2.5 p-2 rounded-lg text-left text-xs transition-colors',
                  isSelected ? 'bg-slate-800 text-white' : 'hover:bg-slate-900 text-slate-300'
                )}
              >
                <div className={cn('h-5 w-5 rounded-md flex items-center justify-center shrink-0 mt-0.5 border', r.color)}>
                  {isSelected ? <Check className="h-3.5 w-3.5" /> : null}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold">{r.label}</div>
                  <p className="text-[10px] text-slate-400 leading-tight mt-0.5">{r.desc}</p>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

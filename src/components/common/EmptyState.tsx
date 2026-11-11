import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';
import { Button } from './Button';
import { cn } from '../../utils/cn';

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  actionIcon?: React.ReactNode;
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  actionLabel,
  onAction,
  actionIcon,
  secondaryActionLabel,
  onSecondaryAction,
  className,
}) => {
  return (
    <div
      className={cn(
        'p-10 sm:p-12 text-center rounded-2xl border border-slate-800 bg-[#0F172A]/70 flex flex-col items-center justify-center',
        className
      )}
    >
      <div className="h-12 w-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mb-3 text-slate-500 shadow-inner">
        <Icon className="h-6 w-6 text-slate-400" />
      </div>

      <h3 className="text-base font-semibold text-white tracking-tight">{title}</h3>
      <p className="text-xs text-slate-400 mt-1.5 max-w-md leading-relaxed">{description}</p>

      {(actionLabel || secondaryActionLabel) && (
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2.5">
          {actionLabel && onAction && (
            <Button
              variant="primary"
              size="sm"
              leftIcon={actionIcon}
              onClick={onAction}
            >
              {actionLabel}
            </Button>
          )}

          {secondaryActionLabel && onSecondaryAction && (
            <Button
              variant="outline"
              size="sm"
              onClick={onSecondaryAction}
            >
              {secondaryActionLabel}
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

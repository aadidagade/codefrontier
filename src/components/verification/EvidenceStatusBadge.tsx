import React from 'react';
import { CheckCircle2, AlertCircle, XCircle } from 'lucide-react';
import { EvidenceStatus } from '../../types/verification';
import { cn } from '../../utils/cn';

interface EvidenceStatusBadgeProps {
  status: EvidenceStatus;
  size?: 'sm' | 'md';
  className?: string;
}

export const EvidenceStatusBadge: React.FC<EvidenceStatusBadgeProps> = ({
  status,
  size = 'md',
  className,
}) => {
  if (status === 'supported') {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 font-semibold rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
          size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs',
          className
        )}
      >
        <CheckCircle2 className={size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'} />
        <span>Supported</span>
      </span>
    );
  }

  if (status === 'partially_supported') {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 font-semibold rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20',
          size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs',
          className
        )}
      >
        <AlertCircle className={size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'} />
        <span>Partially Supported</span>
      </span>
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 font-semibold rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20',
        size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs',
        className
      )}
    >
      <XCircle className={size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'} />
      <span>Unsupported</span>
    </span>
  );
};

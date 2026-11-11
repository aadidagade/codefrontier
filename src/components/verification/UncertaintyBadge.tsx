import React from 'react';
import {
  AlertTriangle,
  HelpCircle,
  GitCompare,
  Clock,
  ShieldAlert,
  Info,
} from 'lucide-react';
import { UncertaintyType } from '../../types/verification';
import { Tooltip } from '../common/Tooltip';
import { cn } from '../../utils/cn';

interface UncertaintyBadgeProps {
  type: UncertaintyType;
  showLabel?: boolean;
  className?: string;
}

const config: Record<
  UncertaintyType,
  {
    label: string;
    description: string;
    icon: React.ElementType;
    bgClass: string;
    textClass: string;
    borderClass: string;
  }
> = {
  missing_evidence: {
    label: 'Missing Evidence',
    description: 'No primary document or code repository found backing this claim.',
    icon: AlertTriangle,
    bgClass: 'bg-rose-500/10',
    textClass: 'text-rose-400',
    borderClass: 'border-rose-500/20',
  },
  unclear_ownership: {
    label: 'Unclear Ownership',
    description: 'Multiple conflicting individuals or unassigned teams claimed ownership.',
    icon: HelpCircle,
    bgClass: 'bg-amber-500/10',
    textClass: 'text-amber-400',
    borderClass: 'border-amber-500/20',
  },
  contradictory: {
    label: 'Contradictory Info',
    description: 'Passages in two separate documents provide conflicting dates, owners, or specs.',
    icon: GitCompare,
    bgClass: 'bg-red-500/10',
    textClass: 'text-red-400',
    borderClass: 'border-red-500/25',
  },
  outdated: {
    label: 'Potentially Outdated',
    description: 'Source document is older than 6 months or superseded by a newer architecture record.',
    icon: Clock,
    bgClass: 'bg-yellow-500/10',
    textClass: 'text-yellow-400',
    borderClass: 'border-yellow-500/20',
  },
  unsupported_statement: {
    label: 'Unsupported Statement',
    description: 'AI model synthesized this statement without sufficient verbatim citation.',
    icon: ShieldAlert,
    bgClass: 'bg-purple-500/10',
    textClass: 'text-purple-400',
    borderClass: 'border-purple-500/20',
  },
};

export const UncertaintyBadge: React.FC<UncertaintyBadgeProps> = ({
  type,
  showLabel = true,
  className,
}) => {
  const item = config[type] || {
    label: 'Uncertain Flag',
    description: 'Flagged for reviewer verification.',
    icon: Info,
    bgClass: 'bg-slate-800',
    textClass: 'text-slate-300',
    borderClass: 'border-slate-700',
  };

  const Icon = item.icon;

  const content = (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium border transition-colors',
        item.bgClass,
        item.textClass,
        item.borderClass,
        className
      )}
    >
      <Icon className="h-3 w-3 shrink-0" />
      {showLabel && <span>{item.label}</span>}
    </span>
  );

  return <Tooltip content={item.description}>{content}</Tooltip>;
};

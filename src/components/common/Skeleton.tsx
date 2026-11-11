import React from 'react';
import { cn } from '../../utils/cn';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular' | 'card';
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'text',
  width,
  height,
  style,
  ...props
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'circular':
        return 'rounded-full';
      case 'rectangular':
        return 'rounded-lg';
      case 'card':
        return 'rounded-xl p-5 border border-slate-800 bg-[#0F172A]';
      case 'text':
      default:
        return 'rounded h-3.5';
    }
  };

  return (
    <div
      className={cn(
        'animate-pulse bg-slate-800/80',
        getVariantStyles(),
        className
      )}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
        ...style,
      }}
      aria-hidden="true"
      {...props}
    />
  );
};

export const SkeletonCard: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('p-5 rounded-xl border border-slate-800 bg-[#0F172A] space-y-4', className)}>
    <div className="flex items-center justify-between">
      <Skeleton variant="rectangular" width={70} height={20} />
      <Skeleton variant="circular" width={28} height={28} />
    </div>
    <div className="space-y-2">
      <Skeleton variant="text" width="85%" height={16} />
      <Skeleton variant="text" width="65%" height={12} />
    </div>
    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Skeleton variant="circular" width={22} height={22} />
        <Skeleton variant="text" width={80} height={12} />
      </div>
      <Skeleton variant="rectangular" width={60} height={18} />
    </div>
  </div>
);

export const SkeletonTableRows: React.FC<{ rows?: number; columns?: number }> = ({
  rows = 4,
  columns = 5,
}) => (
  <div className="divide-y divide-slate-800">
    {Array.from({ length: rows }).map((_, rIdx) => (
      <div key={rIdx} className="p-4 flex items-center justify-between gap-4">
        {Array.from({ length: columns }).map((_, cIdx) => (
          <Skeleton
            key={cIdx}
            variant="text"
            className={cIdx === 0 ? 'w-1/3' : 'w-1/6'}
            height={14}
          />
        ))}
      </div>
    ))}
  </div>
);

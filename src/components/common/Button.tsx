import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'ai';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]';

    const variants = {
      primary:
        'bg-brand-600 hover:bg-brand-500 text-white shadow-subtle hover:shadow-glow focus:ring-brand-500 focus:ring-offset-[#080C14] border border-brand-500/30',
      secondary:
        'bg-slate-800/80 hover:bg-slate-700/80 text-slate-100 hover:text-white border border-slate-700/60 focus:ring-slate-500 focus:ring-offset-[#080C14] dark:bg-surface-elevated dark:hover:bg-surface-hover dark:border-border',
      outline:
        'bg-transparent hover:bg-slate-800/50 text-slate-300 hover:text-white border border-slate-700/80 focus:ring-slate-500 dark:border-slate-800 dark:hover:bg-slate-850',
      ghost:
        'bg-transparent hover:bg-slate-800/40 text-slate-300 hover:text-white border border-transparent focus:ring-slate-500',
      danger:
        'bg-red-600/90 hover:bg-red-600 text-white shadow-subtle hover:shadow-[0_0_20px_rgba(239,68,68,0.25)] border border-red-500/40 focus:ring-red-500',
      ai:
        'bg-gradient-to-r from-brand-600 via-indigo-600 to-brand-accent hover:from-brand-500 hover:to-purple-500 text-white shadow-glow hover:shadow-glow-accent border border-indigo-400/30 focus:ring-brand-accent',
    };

    const sizes = {
      sm: 'text-xs px-2.5 py-1.5 gap-1.5 h-8',
      md: 'text-sm px-4 py-2 gap-2 h-10',
      lg: 'text-base px-5 py-2.5 gap-2.5 h-12',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-current" />
        ) : (
          leftIcon && <span className="inline-flex shrink-0 items-center">{leftIcon}</span>
        )}
        <span>{children}</span>
        {!isLoading && rightIcon && (
          <span className="inline-flex shrink-0 items-center">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

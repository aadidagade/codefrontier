import React from 'react';
import { cn } from '../../utils/cn';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helperText, id, disabled, rows = 4, ...props }, ref) => {
    const generatedId = React.useId();
    const textareaId = id || generatedId;

    return (
      <div className="w-full text-left">
        {label && (
          <label htmlFor={textareaId} className="block text-xs font-medium text-slate-300 mb-1.5">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          rows={rows}
          disabled={disabled}
          className={cn(
            'w-full rounded-lg bg-slate-900/90 dark:bg-[#0B101D] text-slate-100 text-sm placeholder-slate-500',
            'border border-slate-700/80 dark:border-slate-800 transition-all duration-150',
            'focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500',
            'disabled:opacity-50 disabled:cursor-not-allowed p-3',
            error && 'border-red-500/80 focus:border-red-500 focus:ring-red-500',
            className
          )}
          {...props}
        />
        {error && <p className="mt-1 text-xs text-red-400">• {error}</p>}
        {!error && helperText && <p className="mt-1 text-xs text-slate-400">{helperText}</p>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

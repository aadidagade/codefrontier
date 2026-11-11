import React from 'react';
import { cn } from '../../utils/cn';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  shortcut?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      type = 'text',
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      shortcut,
      id,
      disabled,
      ...props
    },
    ref
  ) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;

    return (
      <div className="w-full text-left">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-medium text-slate-300 dark:text-slate-300 mb-1.5"
          >
            {label}
          </label>
        )}

        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3 flex items-center pointer-events-none text-slate-400">
              {leftIcon}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            type={type}
            disabled={disabled}
            className={cn(
              'w-full rounded-lg bg-slate-900/90 dark:bg-[#0B101D] text-slate-100 text-sm placeholder-slate-500',
              'border border-slate-700/80 dark:border-slate-800 transition-all duration-150',
              'focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'h-10 px-3',
              leftIcon ? 'pl-9' : 'pl-3',
              rightIcon || shortcut ? 'pr-10' : 'pr-3',
              error && 'border-red-500/80 focus:border-red-500 focus:ring-red-500',
              className
            )}
            {...props}
          />

          {shortcut && !rightIcon && (
            <div className="absolute right-2.5 pointer-events-none">
              <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-800 border border-slate-700 rounded shadow-sm">
                {shortcut}
              </kbd>
            </div>
          )}

          {rightIcon && (
            <div className="absolute right-2.5 flex items-center text-slate-400">
              {rightIcon}
            </div>
          )}
        </div>

        {error && (
          <p className="mt-1 text-xs text-red-400 flex items-center gap-1">
            <span>•</span>
            {error}
          </p>
        )}

        {!error && helperText && (
          <p className="mt-1 text-xs text-slate-400">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

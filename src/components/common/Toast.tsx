import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, Sparkles, X } from 'lucide-react';
import { useToast, ToastItem } from '../../context/ToastContext';
import { cn } from '../../utils/cn';

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useToast();

  const icons = {
    success: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
    error: <AlertCircle className="h-4 w-4 text-rose-400" />,
    warning: <AlertTriangle className="h-4 w-4 text-amber-400" />,
    info: <Info className="h-4 w-4 text-brand-400" />,
    ai: <Sparkles className="h-4 w-4 text-brand-accent animate-pulse" />,
  };

  const borders = {
    success: 'border-emerald-500/30',
    error: 'border-rose-500/30',
    warning: 'border-amber-500/30',
    info: 'border-brand-500/30',
    ai: 'border-brand-accent/40 shadow-glow-accent',
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none p-2">
      <AnimatePresence>
        {toasts.map((toast: ToastItem) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 16, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.94, transition: { duration: 0.15 } }}
            className={cn(
              'pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl bg-[#0F172A] border shadow-2xl backdrop-blur-md text-slate-100',
              borders[toast.type]
            )}
          >
            <div className="mt-0.5 shrink-0">{icons[toast.type]}</div>
            <div className="flex-1 min-w-0">
              <h4 className="text-xs font-semibold leading-tight">{toast.title}</h4>
              {toast.message && (
                <p className="mt-1 text-[11px] text-slate-400 leading-snug break-words">
                  {toast.message}
                </p>
              )}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="shrink-0 rounded-md p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

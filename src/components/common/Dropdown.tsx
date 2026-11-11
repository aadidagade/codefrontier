import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../../utils/cn';

export interface DropdownItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  danger?: boolean;
  disabled?: boolean;
  divider?: boolean;
}

export interface DropdownProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
  className?: string;
}

export const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  items,
  align = 'right',
  className,
}) => {
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

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      <div onClick={() => setIsOpen((prev) => !prev)} className="cursor-pointer">
        {trigger}
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -4 }}
            transition={{ duration: 0.12 }}
            className={cn(
              'absolute z-50 mt-1.5 w-52 rounded-xl bg-[#0F172A] border border-slate-800 shadow-xl py-1.5 focus:outline-none backdrop-blur-md',
              align === 'right' ? 'right-0' : 'left-0',
              className
            )}
          >
            {items.map((item) => {
              if (item.divider) {
                return <div key={item.id} className="h-px bg-slate-800 my-1" />;
              }

              return (
                <button
                  key={item.id}
                  disabled={item.disabled}
                  onClick={() => {
                    item.onClick?.();
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium transition-colors text-left',
                    item.danger
                      ? 'text-red-400 hover:bg-red-500/10 hover:text-red-300'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white',
                    item.disabled && 'opacity-40 cursor-not-allowed'
                  )}
                >
                  {item.icon && <span className="h-4 w-4 shrink-0">{item.icon}</span>}
                  <span>{item.label}</span>
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  ArrowRightLeft,
  FileText,
  Clock,
  ShieldCheck,
  AlertCircle,
  Check,
  Trash2,
  ExternalLink,
  ChevronRight,
  Filter,
} from 'lucide-react';
import { notificationService } from '../../services/notificationService';
import { NotificationItem, NotificationEventType, NotificationCategory } from '../../types/notification';
import { Badge } from '../common/Badge';

export const NotificationsDropdown: React.FC = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [category, setCategory] = useState<NotificationCategory>('all');
  const [showSimulateMenu, setShowSimulateMenu] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  const refresh = () => {
    setNotifications(notificationService.getNotifications());
    setUnreadCount(notificationService.getUnreadCount());
  };

  useEffect(() => {
    refresh();
    const unsubscribe = notificationService.subscribe(refresh);
    return () => unsubscribe();
  }, []);

  // Close when clicked outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setShowSimulateMenu(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleItemClick = (item: NotificationItem) => {
    notificationService.markAsRead(item.id);
    refresh();
    setIsOpen(false);
    navigate(item.targetUrl);
  };

  const handleMarkAllRead = (e: React.MouseEvent) => {
    e.stopPropagation();
    notificationService.markAllAsRead();
    refresh();
  };

  const handleDeleteItem = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    notificationService.deleteNotification(id);
    refresh();
  };

  const handleTriggerSimulate = (type: NotificationEventType) => {
    notificationService.triggerSampleNotification(type);
    refresh();
    setShowSimulateMenu(false);
  };

  // Filter logic
  const filteredNotifications = notifications.filter((n) => {
    if (category === 'unread') return !n.read;
    if (category === 'handovers')
      return n.type === 'new_handover_received' || n.type === 'incoming_member_acknowledged';
    if (category === 'reviews')
      return n.type === 'review_requested' || n.type === 'handover_approved' || n.type === 'changes_requested';
    if (category === 'conflicts') return n.type === 'conflict_detected';
    if (category === 'documents') return n.type === 'document_uploaded';
    return true;
  });

  const getEventIcon = (type: NotificationEventType) => {
    switch (type) {
      case 'new_handover_received':
        return <Sparkles className="h-4 w-4 text-violet-400" />;
      case 'review_requested':
        return <Clock className="h-4 w-4 text-amber-400" />;
      case 'handover_approved':
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case 'changes_requested':
        return <AlertCircle className="h-4 w-4 text-amber-400" />;
      case 'document_uploaded':
        return <FileText className="h-4 w-4 text-cyan-400" />;
      case 'conflict_detected':
        return <AlertTriangle className="h-4 w-4 text-rose-400" />;
      case 'incoming_member_acknowledged':
        return <ShieldCheck className="h-4 w-4 text-emerald-400" />;
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors focus:outline-none"
        title="Notifications Center"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 min-w-4 px-1 items-center justify-center rounded-full bg-violet-600 text-[10px] font-bold text-white ring-2 ring-[#080C14] animate-pulse">
            {unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 sm:w-[440px] rounded-xl bg-[#0B1120] border border-slate-800 shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          {/* Header */}
          <div className="p-3.5 border-b border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-white">Notifications</span>
              {unreadCount > 0 ? (
                <span className="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-violet-500/20 text-violet-300 border border-violet-500/30">
                  {unreadCount} new
                </span>
              ) : (
                <span className="text-[11px] text-slate-500">All caught up</span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSimulateMenu(!showSimulateMenu)}
                className="text-[11px] text-brand-400 hover:text-brand-300 font-medium transition-colors"
                title="Test trigger one of the 7 notification types"
              >
                + Test Event
              </button>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
                >
                  <Check className="h-3 w-3" />
                  <span>Mark all read</span>
                </button>
              )}
            </div>
          </div>

          {/* Test Event Simulator Menu */}
          {showSimulateMenu && (
            <div className="p-2.5 bg-slate-900 border-b border-slate-800 text-xs space-y-1">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Dispatch Test Event:
              </div>
              <div className="grid grid-cols-2 gap-1 text-[11px]">
                <button
                  onClick={() => handleTriggerSimulate('new_handover_received')}
                  className="px-2 py-1 text-left rounded bg-slate-800 hover:bg-slate-700 text-slate-200 truncate"
                >
                  ⚡ New Handover
                </button>
                <button
                  onClick={() => handleTriggerSimulate('review_requested')}
                  className="px-2 py-1 text-left rounded bg-slate-800 hover:bg-slate-700 text-slate-200 truncate"
                >
                  🔍 Review Requested
                </button>
                <button
                  onClick={() => handleTriggerSimulate('handover_approved')}
                  className="px-2 py-1 text-left rounded bg-slate-800 hover:bg-slate-700 text-slate-200 truncate"
                >
                  ✅ Handover Approved
                </button>
                <button
                  onClick={() => handleTriggerSimulate('changes_requested')}
                  className="px-2 py-1 text-left rounded bg-slate-800 hover:bg-slate-700 text-slate-200 truncate"
                >
                  ⚠️ Changes Requested
                </button>
                <button
                  onClick={() => handleTriggerSimulate('document_uploaded')}
                  className="px-2 py-1 text-left rounded bg-slate-800 hover:bg-slate-700 text-slate-200 truncate"
                >
                  📄 Doc Uploaded
                </button>
                <button
                  onClick={() => handleTriggerSimulate('conflict_detected')}
                  className="px-2 py-1 text-left rounded bg-slate-800 hover:bg-slate-700 text-slate-200 truncate"
                >
                  ⚡ Conflict Detected
                </button>
                <button
                  onClick={() => handleTriggerSimulate('incoming_member_acknowledged')}
                  className="col-span-2 px-2 py-1 text-left rounded bg-slate-800 hover:bg-slate-700 text-slate-200 truncate"
                >
                  🤝 Incoming Member Acknowledged
                </button>
              </div>
            </div>
          )}

          {/* Category Filter Pills */}
          <div className="px-3 py-2 border-b border-slate-800/60 bg-slate-900/30 flex items-center gap-1.5 overflow-x-auto text-[11px]">
            <button
              onClick={() => setCategory('all')}
              className={`px-2 py-0.5 rounded-full whitespace-nowrap transition-colors ${
                category === 'all'
                  ? 'bg-slate-800 text-white font-medium'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setCategory('unread')}
              className={`px-2 py-0.5 rounded-full whitespace-nowrap transition-colors ${
                category === 'unread'
                  ? 'bg-violet-600/30 text-violet-300 font-medium'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Unread ({unreadCount})
            </button>
            <button
              onClick={() => setCategory('handovers')}
              className={`px-2 py-0.5 rounded-full whitespace-nowrap transition-colors ${
                category === 'handovers'
                  ? 'bg-slate-800 text-white font-medium'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Handovers
            </button>
            <button
              onClick={() => setCategory('reviews')}
              className={`px-2 py-0.5 rounded-full whitespace-nowrap transition-colors ${
                category === 'reviews'
                  ? 'bg-slate-800 text-white font-medium'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Reviews
            </button>
            <button
              onClick={() => setCategory('conflicts')}
              className={`px-2 py-0.5 rounded-full whitespace-nowrap transition-colors ${
                category === 'conflicts'
                  ? 'bg-rose-500/20 text-rose-300 font-medium'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Conflicts
            </button>
            <button
              onClick={() => setCategory('documents')}
              className={`px-2 py-0.5 rounded-full whitespace-nowrap transition-colors ${
                category === 'documents'
                  ? 'bg-slate-800 text-white font-medium'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Docs
            </button>
          </div>

          {/* Notifications List */}
          <div className="max-h-[380px] overflow-y-auto divide-y divide-slate-800/50">
            {filteredNotifications.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">
                <Bell className="h-7 w-7 text-slate-600 mx-auto mb-2 opacity-50" />
                No notifications in this filter category
              </div>
            ) : (
              filteredNotifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => handleItemClick(n)}
                  className={`p-3.5 flex items-start gap-3 transition-colors cursor-pointer group ${
                    n.read ? 'hover:bg-slate-900/50 opacity-80' : 'bg-slate-900/40 hover:bg-slate-900/80'
                  }`}
                >
                  {/* Icon Badge */}
                  <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 shrink-0 mt-0.5">
                    {getEventIcon(n.type)}
                  </div>

                  {/* Body */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="text-xs font-semibold text-white truncate">{n.title}</span>
                        {!n.read && (
                          <span className="h-1.5 w-1.5 rounded-full bg-violet-400 shrink-0" />
                        )}
                      </div>
                      <span className="text-[10px] text-slate-500 shrink-0">{n.timestamp}</span>
                    </div>

                    <p className="text-[11px] text-slate-300 mt-1 line-clamp-2 leading-relaxed">
                      {n.message}
                    </p>

                    <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                      <span className="font-mono text-brand-400 font-semibold">{n.projectKey}</span>
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <span className="text-slate-300 flex items-center gap-1 hover:underline">
                          View details <ExternalLink className="h-2.5 w-2.5" />
                        </span>
                        <button
                          onClick={(e) => handleDeleteItem(e, n.id)}
                          className="p-1 hover:text-red-400"
                          title="Dismiss"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-2.5 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between text-[11px] text-slate-400 px-3">
            <span>{notifications.length} total notifications recorded</span>
            <button
              onClick={() => {
                notificationService.clearAll();
                refresh();
              }}
              className="text-slate-500 hover:text-red-400 transition-colors"
            >
              Clear history
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

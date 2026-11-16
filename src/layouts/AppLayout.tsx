import React, { useState } from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { Sidebar } from '../components/layout/Sidebar';
import { TopNavbar } from '../components/layout/TopNavbar';
import { ToastContainer } from '../components/common/Toast';
import { useAuth } from '../hooks/useAuth';

export const AppLayout: React.FC = () => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // While checking stored session from localStorage / cookies
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#080C14] text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          <span className="text-xs font-mono text-slate-400">Verifying session...</span>
        </div>
      </div>
    );
  }

  // Enforce authentication on all app workspace routes
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <div className="flex h-screen bg-[#080C14] text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <TopNavbar onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-grid-pattern relative">
          <Outlet />
        </main>
      </div>

      {/* Stacked Toasts */}
      <ToastContainer />
    </div>
  );
};

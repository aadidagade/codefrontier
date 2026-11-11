import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/layout/Sidebar';
import { TopNavbar } from '../components/layout/TopNavbar';
import { ToastContainer } from '../components/common/Toast';

export const AppLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

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

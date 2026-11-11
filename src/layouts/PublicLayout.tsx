import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { Layers, ArrowRight } from 'lucide-react';
import { Button } from '../components/common/Button';
import { ThemeToggle } from '../components/layout/ThemeToggle';
import { ToastContainer } from '../components/common/Toast';

export const PublicLayout: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#080C14] text-slate-100 flex flex-col font-sans selection:bg-brand-500 selection:text-white">
      {/* Public Navbar */}
      <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-[#080C14]/85 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-glow group-hover:shadow-glow-accent transition-all duration-200">
              <Layers className="h-5 w-5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight text-white group-hover:text-brand-300 transition-colors">
                Knowledge Handover
              </span>
              <span className="text-[10px] text-slate-400 font-mono tracking-wider">
                AI CONTINUITY PLATFORM
              </span>
            </div>
          </Link>

          {/* Nav links */}
          <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-slate-400">
            <a href="#problem" className="hover:text-slate-100 transition-colors">
              The Problem
            </a>
            <a href="#how-it-works" className="hover:text-slate-100 transition-colors">
              How It Works
            </a>
            <a href="#capabilities" className="hover:text-slate-100 transition-colors">
              Capabilities
            </a>
            <a href="#workflow" className="hover:text-slate-100 transition-colors">
              Workflow
            </a>
            <Link to="/design-system" className="hover:text-brand-300 transition-colors">
              UI System
            </Link>
          </nav>

          {/* Action CTAs */}
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/login')}
              className="text-xs text-slate-300 hover:text-white"
            >
              Sign In
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate('/register')}
              rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
              className="text-xs"
            >
              Get Started
            </Button>
          </div>
        </div>
      </header>

      {/* Main Public Body */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Stacked Toasts */}
      <ToastContainer />
    </div>
  );
};

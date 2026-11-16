import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, Eye, EyeOff, ArrowRight, ShieldCheck, Sparkles, CheckCircle2 } from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';

interface DemoAccount {
  role: string;
  name: string;
  email: string;
  password: string;
  badge: string;
  badgeColor: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    role: 'Lead Engineer',
    name: 'Elena Rostova',
    email: 'elena.rostova@techfrontier.io',
    password: 'continuity2026',
    badge: 'Lead / Admin',
    badgeColor: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
  },
  {
    role: 'Outgoing Lead',
    name: 'Sarah Chen',
    email: 'sarah.chen@apex-pay.io',
    password: 'Password123!',
    badge: 'Author',
    badgeColor: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
  },
  {
    role: 'Project Owner',
    name: 'Marcus Vance',
    email: 'marcus.vance@apex-pay.io',
    password: 'Password123!',
    badge: 'Reviewer',
    badgeColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  },
  {
    role: 'Incoming Member',
    name: 'Alex Rivera',
    email: 'alex.rivera@apex-pay.io',
    password: 'Password123!',
    badge: 'Continuity',
    badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  },
];

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { success, error: toastError } = useToast();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string; general?: string }>({});

  const validate = (): boolean => {
    const errs: { email?: string; password?: string } = {};
    if (!email) {
      errs.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errs.email = 'Please enter a valid email address';
    }

    if (!password) {
      errs.password = 'Password is required';
    } else if (password.length < 6) {
      errs.password = 'Password must be at least 6 characters';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);
    setErrors({});

    try {
      await login({ email, password, rememberMe });
      success('Welcome back!', 'Authenticated into Knowledge Handover workspace.');
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid login credentials';
      setErrors({ general: msg });
      toastError('Login Failed', msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFillAccount = (account: DemoAccount) => {
    setEmail(account.email);
    setPassword(account.password);
    setErrors({});
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8 bg-grid-pattern relative">
      {/* Background soft glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-brand-500/10 blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="relative w-full max-w-lg rounded-2xl bg-[#0F172A] border border-slate-800 shadow-2xl p-6 sm:p-8"
      >
        <div className="text-center mb-5">
          <div className="inline-flex items-center justify-center h-11 w-11 rounded-xl bg-gradient-to-tr from-brand-600 to-purple-600 text-white shadow-glow mb-3">
            <Sparkles className="h-5 w-5" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Sign in to your workspace</h2>
          <p className="text-xs text-slate-400 mt-1">
            Access your AI-verified project handovers and evidence graphs
          </p>
        </div>

        {/* Demo Accounts & Credentials Section */}
        <div className="mb-5 rounded-xl bg-slate-900/90 border border-brand-500/30 overflow-hidden shadow-sm">
          {/* Header & Primary Auto Fill */}
          <div className="p-3 bg-brand-500/10 border-b border-brand-500/20 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-brand-400 shrink-0" />
              <span className="text-xs font-semibold text-brand-200">Demo Accounts & Credentials</span>
            </div>
            <button
              type="button"
              onClick={() => handleFillAccount(DEMO_ACCOUNTS[0])}
              className="text-[11px] font-semibold text-brand-400 hover:text-brand-300 bg-brand-500/20 hover:bg-brand-500/30 px-2.5 py-1 rounded transition-colors"
            >
              Auto Fill
            </button>
          </div>

          {/* Credentials Display List */}
          <div className="p-2.5 space-y-2">
            <div className="text-[11px] text-slate-400 px-1 flex items-center justify-between">
              <span>Click any demo account to populate credentials:</span>
            </div>

            <div className="grid grid-cols-1 gap-1.5 max-h-52 overflow-y-auto pr-0.5">
              {DEMO_ACCOUNTS.map((acc) => (
                <div
                  key={acc.email}
                  onClick={() => handleFillAccount(acc)}
                  className={`p-2 rounded-lg border text-left cursor-pointer transition-all flex items-center justify-between ${
                    email === acc.email
                      ? 'bg-brand-500/15 border-brand-500/50 text-white'
                      : 'bg-slate-800/60 hover:bg-slate-800 border-slate-700/60 text-slate-300'
                  }`}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleFillAccount(acc);
                    }
                  }}
                >
                  <div className="min-w-0 flex-1 mr-2">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-medium text-white truncate">{acc.role}</span>
                      <span className={`text-[10px] px-1.5 py-0.2 rounded border font-mono ${acc.badgeColor}`}>
                        {acc.badge}
                      </span>
                    </div>
                    <div className="mt-0.5 font-mono text-[11px] text-slate-400 flex flex-wrap gap-x-2">
                      <span>email: <strong className="text-slate-200 font-mono">{acc.email}</strong></span>
                      <span>password: <strong className="text-brand-300 font-mono">{acc.password}</strong></span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleFillAccount(acc);
                    }}
                    className="text-[10px] shrink-0 font-medium px-2 py-0.5 rounded bg-slate-700/70 hover:bg-brand-600 text-slate-300 hover:text-white transition-colors"
                  >
                    Use
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {errors.general && (
          <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
            <span>•</span>
            <span>{errors.general}</span>
          </div>
        )}

        <form noValidate onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Work or University Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="elena.rostova@techfrontier.io"
            leftIcon={<Mail className="h-4 w-4" />}
            error={errors.email}
            disabled={isLoading}
            autoComplete="email"
          />

          <div>
            <div className="relative">
              <Input
                label="Password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                leftIcon={<Lock className="h-4 w-4" />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="hover:text-slate-200 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
                error={errors.password}
                disabled={isLoading}
                autoComplete="current-password"
              />
            </div>
          </div>

          <div className="flex items-center justify-between text-xs pt-1">
            <label className="flex items-center gap-2 cursor-pointer text-slate-300 select-none">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="rounded border-slate-700 bg-slate-800 text-brand-600 focus:ring-brand-500 h-3.5 w-3.5"
              />
              <span>Remember me for 30 days</span>
            </label>

            <Link
              to="/forgot-password"
              className="text-brand-400 hover:text-brand-300 transition-colors font-medium"
            >
              Forgot password?
            </Link>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="md"
            isLoading={isLoading}
            rightIcon={<ArrowRight className="h-4 w-4" />}
            className="w-full mt-2 font-semibold"
          >
            Sign In
          </Button>
        </form>

        <div className="mt-6 pt-5 border-t border-slate-800/80 text-center text-xs text-slate-400">
          Don't have an account yet?{' '}
          <Link to="/register" className="text-brand-400 hover:text-brand-300 font-semibold ml-1">
            Create an account
          </Link>
        </div>
      </motion.div>
    </div>
  );
};

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { User as UserIcon, Mail, Lock, Eye, EyeOff, ArrowRight, Sparkles, Building2 } from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const { success, error: toastError } = useToast();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [organization, setOrganization] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const errs: Record<string, string> = {};

    if (!fullName.trim()) {
      errs.fullName = 'Full name is required';
    }

    if (!email.trim()) {
      errs.email = 'Work or college email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errs.email = 'Please provide a valid email format';
    }

    if (!password) {
      errs.password = 'Password is required';
    } else if (password.length < 8) {
      errs.password = 'Password must be at least 8 characters';
    }

    if (!confirmPassword) {
      errs.confirmPassword = 'Confirm your password';
    } else if (password !== confirmPassword) {
      errs.confirmPassword = 'Passwords do not match';
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
      await register({
        fullName,
        email,
        password,
        confirmPassword,
        organization: organization || 'Engineering Org',
      });
      success('Account created!', 'Welcome to Knowledge Handover. Workspace initialized.');
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed';
      setErrors({ general: msg });
      toastError('Registration Error', msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8 bg-grid-pattern relative">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-brand-accent/10 blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="relative w-full max-w-md rounded-2xl bg-[#0F172A] border border-slate-800 shadow-2xl p-6 sm:p-8"
      >
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center h-11 w-11 rounded-xl bg-gradient-to-tr from-brand-accent to-indigo-600 text-white shadow-glow-accent mb-3">
            <Sparkles className="h-5 w-5" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Create your account</h2>
          <p className="text-xs text-slate-400 mt-1">
            Safeguard your team's codebases with evidence-linked AI handovers
          </p>
        </div>

        {errors.general && (
          <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
            <span>•</span>
            <span>{errors.general}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5">
          <Input
            label="Full Name"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Alex Mercer"
            leftIcon={<UserIcon className="h-4 w-4" />}
            error={errors.fullName}
            disabled={isLoading}
            autoComplete="name"
          />

          <Input
            label="Work or College Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="alex.m@organization.io"
            leftIcon={<Mail className="h-4 w-4" />}
            error={errors.email}
            disabled={isLoading}
            autoComplete="email"
          />

          <Input
            label="Organization or Team (Optional)"
            type="text"
            value={organization}
            onChange={(e) => setOrganization(e.target.value)}
            placeholder="Core Infrastructure Team"
            leftIcon={<Building2 className="h-4 w-4" />}
            disabled={isLoading}
          />

          <Input
            label="Password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Minimum 8 characters"
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
            autoComplete="new-password"
          />

          <Input
            label="Confirm Password"
            type={showPassword ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Re-enter password"
            leftIcon={<Lock className="h-4 w-4" />}
            error={errors.confirmPassword}
            disabled={isLoading}
            autoComplete="new-password"
          />

          <Button
            type="submit"
            variant="ai"
            size="md"
            isLoading={isLoading}
            rightIcon={<ArrowRight className="h-4 w-4" />}
            className="w-full mt-2 font-semibold"
          >
            Create Account
          </Button>
        </form>

        <p className="mt-4 text-[11px] text-slate-400 text-center leading-relaxed">
          By signing up, you agree to our Terms of Service and Privacy Policy. All code analysis is processed in isolated SOC2 containers.
        </p>

        <div className="mt-5 pt-4 border-t border-slate-800/80 text-center text-xs text-slate-400">
          Already have an account?{' '}
          <Link to="/login" className="text-brand-400 hover:text-brand-300 font-semibold ml-1">
            Sign In
          </Link>
        </div>
      </motion.div>
    </div>
  );
};

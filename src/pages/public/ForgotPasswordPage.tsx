import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, ArrowLeft, ArrowRight, CheckCircle2, KeyRound } from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';

export const ForgotPasswordPage: React.FC = () => {
  const { forgotPassword } = useAuth();
  const { success: toastSuccess, error: toastError } = useToast();

  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError('Please provide your account email');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please provide a valid email format');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await forgotPassword(email);
      setIsSubmitted(true);
      toastSuccess('Instructions Dispatched', `Password reset link sent to ${email}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send reset link';
      setError(msg);
      toastError('Request Failed', msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8 bg-grid-pattern relative">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[350px] bg-brand-500/10 blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="relative w-full max-w-md rounded-2xl bg-[#0F172A] border border-slate-800 shadow-2xl p-6 sm:p-8"
      >
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center h-11 w-11 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 text-white shadow-glow mb-3">
            <KeyRound className="h-5 w-5" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Reset your password</h2>
          <p className="text-xs text-slate-400 mt-1">
            We will send you a secure verification link to regain access
          </p>
        </div>

        {isSubmitted ? (
          <div className="space-y-5 text-center">
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex flex-col items-center gap-2">
              <CheckCircle2 className="h-8 w-8 text-emerald-400" />
              <div className="font-semibold text-sm text-white">Reset Link Dispatched</div>
              <p className="text-slate-300 text-xs">
                We've sent recovery instructions to <strong className="text-white">{email}</strong>.
                The link is valid for 15 minutes.
              </p>
            </div>

            <Button
              variant="outline"
              size="md"
              onClick={() => setIsSubmitted(false)}
              className="w-full text-xs"
            >
              Didn't receive email? Try again
            </Button>

            <div className="pt-2">
              <Link
                to="/login"
                className="inline-flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 font-semibold"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>Return to sign in</span>
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Account Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="elena.rostova@techfrontier.io"
              leftIcon={<Mail className="h-4 w-4" />}
              error={error || undefined}
              disabled={isLoading}
              autoComplete="email"
            />

            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isLoading}
              rightIcon={<ArrowRight className="h-4 w-4" />}
              className="w-full mt-2 font-semibold"
            >
              Send Reset Link
            </Button>

            <div className="pt-4 text-center">
              <Link
                to="/login"
                className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>Back to sign in</span>
              </Link>
            </div>
          </form>
        )}
      </motion.div>
    </div>
  );
};

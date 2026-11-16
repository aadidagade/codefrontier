import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ShieldCheck, BadgeCheck } from 'lucide-react';
import { Badge } from '../../components/common/Badge';
import { EvidenceVerificationDashboard } from '../../components/verification/EvidenceVerificationDashboard';

export const EvidenceVerificationPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Breadcrumb Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate(-1)}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-mono transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </button>
            <span className="text-slate-600">·</span>
            <Badge variant="ai" size="sm">
              Section-by-Section Evidence Grounding
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
            Evidence Verification Dashboard
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            Audit handover assertions against retrieved source document chunks, verify factual support, and inspect source document excerpts.
          </p>
        </div>
      </div>

      {/* Main Dashboard */}
      <EvidenceVerificationDashboard />
    </div>
  );
};

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, GitCompare } from 'lucide-react';
import { Badge } from '../../components/common/Badge';
import { ContradictionDashboard } from '../../components/verification/ContradictionDashboard';

export const ConflictsPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Navigation Header */}
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
              Cross-Document Contradiction Engine
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
            Knowledge Conflicts & Contradictions
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            Detect and arbitrate conflicting information across project documents, architecture records, runbooks, and audit specifications.
          </p>
        </div>
      </div>

      {/* Main Contradiction Dashboard */}
      <ContradictionDashboard />
    </div>
  );
};

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRightLeft, Sparkles, CheckCircle2, Clock, AlertTriangle, Plus, ChevronRight, FileText } from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/common/Card';
import { mockHandovers } from '../../data/mockData';
import { useToast } from '../../hooks/useToast';

export const HandoverSessionsPage: React.FC = () => {
  const navigate = useNavigate();
  const { info } = useToast();

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-brand-400 uppercase tracking-wider font-mono">
              Knowledge Continuity Transfers
            </span>
            <Badge variant="ai" size="sm">
              AI Powered
            </Badge>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1">
            Handover Sessions
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Active and archived engineer knowledge transfers, checklists, and evidence sign-offs
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="md"
            onClick={() => navigate('/my-handovers')}
            className="text-xs font-semibold"
          >
            My Incoming Handovers (3)
          </Button>
          <Button
            variant="ai"
            size="md"
            leftIcon={<Sparkles className="h-4 w-4" />}
            onClick={() => navigate('/handover/generate')}
            className="text-xs font-semibold"
          >
            Reconstruct Knowledge (AI)
          </Button>
        </div>
      </div>

      {/* Featured Callout Banner for AI Generation */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-brand-950/80 via-slate-900 to-indigo-950/70 border border-brand-500/25 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-card">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-semibold text-brand-300">
            <Sparkles className="h-4 w-4 text-brand-400" />
            <span>Automated AI Knowledge Reconstruction</span>
          </div>
          <h3 className="text-base font-bold text-white">
            Have processed project documents? Let AI connect the dots.
          </h3>
          <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
            Select verified documents to extract architecture decisions, tasks, dependencies, risks, and unresolved questions into a structured handover brief.
          </p>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={() => navigate('/handover/generate')}
          rightIcon={<ChevronRight className="h-4 w-4" />}
          className="text-xs shrink-0"
        >
          Generate Handover Draft
        </Button>
      </div>

      {/* Sessions List */}
      <div className="space-y-4">
        {mockHandovers.map((h) => (
          <Card key={h.id} className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
                  <ArrowRightLeft className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-brand-400">{h.projectKey}</span>
                    <Badge variant="success" size="sm" dot>
                      Stage: {h.currentStage.toUpperCase()}
                    </Badge>
                  </div>
                  <h3 className="text-base font-semibold text-white mt-0.5">{h.projectTitle}</h3>
                </div>
              </div>

              <div className="flex items-center gap-6 text-xs text-slate-400">
                <div>
                  <div className="text-[10px] uppercase font-mono">Lead / Outgoing</div>
                  <div className="font-medium text-slate-200">{h.initiator.name}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase font-mono">Successor</div>
                  <div className="font-medium text-slate-200">{h.recipient.name}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase font-mono">Target Date</div>
                  <div className="font-medium text-slate-200">{h.targetCompletionDate}</div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                <span className="text-slate-400">Checklist Items:</span>
                <span className="ml-2 font-semibold text-white">
                  {h.checklist.filter((c) => c.completed).length} of {h.checklist.length} Verified
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                <span className="text-slate-400">Flagged Conflicts:</span>
                <span className="ml-2 font-semibold text-amber-300">{h.conflictsDetected} Active</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                <span className="text-slate-400">AI Readiness Score:</span>
                <span className="ml-2 font-semibold text-emerald-400">{h.aiReadinessScore}%</span>
              </div>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-slate-800/80 text-xs">
              <span className="text-slate-400">
                Status: Handover verification active in staging environment
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate('/handover/generate')}
                  className="text-xs"
                >
                  Inspect AI Brief
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => navigate('/review/rev-auth-zero')}
                  rightIcon={<ChevronRight className="h-3.5 w-3.5" />}
                  className="text-xs"
                >
                  Review & Approve
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

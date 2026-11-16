import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  GitBranch,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { VersionHistorySection } from '../../components/handover/VersionHistorySection';
import { reviewService } from '../../services/reviewService';
import { incomingService } from '../../services/incomingService';

export const HandoverVersionsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [handoverTitle, setHandoverTitle] = useState<string>('Knowledge Handover');
  const [projectKey, setProjectKey] = useState<string>('HANDOVER');
  const [currentVersion, setCurrentVersion] = useState<string>('v1.0');
  const [loading, setLoading] = useState<boolean>(true);

  const targetId = id || 'rev-auth-zero';

  useEffect(() => {
    const loadInfo = async () => {
      setLoading(true);
      try {
        const rev = await reviewService.getHandoverById(targetId);
        if (rev) {
          setHandoverTitle(rev.projectName);
          setProjectKey(rev.projectKey);
          setCurrentVersion(rev.version);
        } else {
          const inc = await incomingService.getIncomingHandoverById(targetId);
          if (inc) {
            setHandoverTitle(inc.projectName);
            setProjectKey(inc.projectKey);
            setCurrentVersion(inc.version);
          }
        }
      } catch (err) {
        console.warn('Failed to load handover title:', err);
      } finally {
        setLoading(false);
      }
    };

    loadInfo();
  }, [targetId]);

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Top Breadcrumb & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate(-1)}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-mono transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </button>
            <span className="text-slate-600">·</span>
            <span className="font-mono text-xs font-bold text-brand-400">
              {projectKey}
            </span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              {currentVersion}
            </span>
          </div>

          <h1 className="text-2xl font-bold text-white tracking-tight">
            Handover Version Management
          </h1>
          <p className="text-xs text-slate-400">
            {handoverTitle} &mdash; Immutable snapshots, chapter diffs, and non-destructive version restoration
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/review/${targetId}`)}
            className="text-xs font-semibold"
          >
            Open Review Workspace
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/my-handovers/${targetId}`)}
            className="text-xs font-semibold"
          >
            Open Incoming Dashboard
          </Button>
        </div>
      </div>

      {/* Security & Immutability Guarantee Banner */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-start gap-3">
        <ShieldCheck className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5 text-xs">
          <strong className="text-white">Enterprise Versioning & Immutability Guarantee:</strong>
          <p className="text-slate-400 leading-relaxed">
            Every approved version and revision snapshot is stored as an immutable historical record.
            When regenerating or restoring a prior version, a new revision is created rather than overwriting existing data.
            All diffs use pure stored snapshot data rather than AI regeneration.
          </p>
        </div>
      </div>

      {/* Main Version History & Comparator Component */}
      <Card className="bg-[#0F172A] border-slate-800 p-6 shadow-card">
        <VersionHistorySection
          handoverId={targetId}
          currentVersionNumber={currentVersion}
          onVersionRestored={(newVer) => {
            if (newVer?.version_number) {
              setCurrentVersion(newVer.version_number);
            }
          }}
        />
      </Card>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  XCircle,
  HelpCircle,
  Sparkles,
  RotateCcw,
  Layers,
  ArrowRight,
  TrendingUp,
  FileCheck,
  ChevronDown,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { Skeleton } from '../common/Skeleton';
import { EmptyState } from '../common/EmptyState';
import { useToast } from '../../hooks/useToast';
import { verificationService } from '../../services/verificationService';
import {
  AdvancedHandoverVerificationReport,
  ClaimVerificationRecord,
} from '../../types/verification';
import { EvidenceDetailsTable } from './EvidenceDetailsTable';
import { SourceDocumentModal } from './SourceDocumentModal';

interface EvidenceVerificationDashboardProps {
  initialHandoverId?: string;
}

export const EvidenceVerificationDashboard: React.FC<EvidenceVerificationDashboardProps> = ({
  initialHandoverId,
}) => {
  const { success, error, info } = useToast();

  const [handovers, setHandovers] = useState<any[]>([]);
  const [selectedHandoverId, setSelectedHandoverId] = useState<string>(initialHandoverId || '');
  const [report, setReport] = useState<AdvancedHandoverVerificationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedClaimForModal, setSelectedClaimForModal] = useState<ClaimVerificationRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  // 1. Fetch available handovers on mount
  useEffect(() => {
    const fetchHandovers = async () => {
      try {
        const list = await verificationService.getHandovers();
        setHandovers(list);
        if (list.length > 0 && !selectedHandoverId) {
          setSelectedHandoverId(list[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load handovers:', err);
      }
    };
    fetchHandovers();
  }, []);

  // 2. Fetch verification report when selectedHandoverId changes
  const fetchReport = async (handoverId: string) => {
    if (!handoverId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await verificationService.getHandoverVerificationResults(handoverId);
      setReport(data);
    } catch (err: any) {
      // If no verification has been run yet for this handover, report will be empty
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedHandoverId) {
      fetchReport(selectedHandoverId);
    }
  }, [selectedHandoverId]);

  // 3. Trigger Gemini Evidence Verification Engine
  const handleRunVerification = async () => {
    if (!selectedHandoverId) {
      error('No Handover Selected', 'Please select a handover to analyze.');
      return;
    }
    setVerifying(true);
    info('Verification Started', 'Gemini is retrieving source chunks and verifying claims...');
    try {
      const updatedReport = await verificationService.triggerHandoverVerification(
        selectedHandoverId
      );
      setReport(updatedReport);
      success(
        'Evidence Verification Complete',
        `Analyzed ${updatedReport.total_claims} claims: ${updatedReport.supported_claims} supported.`
      );
    } catch (err: any) {
      error(
        'Verification Failed',
        err.message || 'Failed to verify claims against original document chunks.'
      );
    } finally {
      setVerifying(false);
    }
  };

  const handleOpenSourceModal = (claim: ClaimVerificationRecord) => {
    setSelectedClaimForModal(claim);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Selector Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl bg-gradient-to-r from-slate-900 via-[#0B132B]/80 to-slate-900 border border-slate-800 shadow-lg">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="h-4 w-4" />
            </span>
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
              Evidence Verification Engine
            </span>
            <span className="text-slate-600">·</span>
            <span className="text-xs text-slate-400 font-mono">Gemini Grounded NLI</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Handover Claim Audit & Traceability
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            Compare every AI-generated claim against its supporting source passages in original documents.
          </p>
        </div>

        {/* Handover Picker & Action */}
        <div className="flex items-center gap-3 flex-wrap">
          {handovers.length > 0 && (
            <div className="relative">
              <select
                value={selectedHandoverId}
                onChange={(e) => setSelectedHandoverId(e.target.value)}
                className="appearance-none pl-3 pr-8 py-2 text-xs sm:text-sm rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-brand-500 transition-colors font-medium cursor-pointer"
              >
                {handovers.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.title || h.projectName || `Handover ${h.id.slice(0, 8)}`}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
            </div>
          )}

          <Button
            variant="primary"
            onClick={handleRunVerification}
            isLoading={verifying}
            className="flex items-center gap-2 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-semibold text-xs sm:text-sm px-4 py-2 rounded-xl shadow-glow"
          >
            <Sparkles className="h-4 w-4" />
            <span>{verifying ? 'Analyzing Claims...' : 'Run Verification Engine'}</span>
          </Button>
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-64 rounded-xl" />
        </div>
      ) : !report || report.total_claims === 0 ? (
        /* Empty State */
        <EmptyState
          title="No verification audit yet"
          description="Click 'Run Verification Engine' above to have Gemini compare every claim against original document chunks and classify support."
          icon={ShieldCheck}
          actionLabel="Start First Verification"
          onAction={handleRunVerification}
        />
      ) : (
        /* Dashboard Metrics Cards */
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Total Claims */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Total Claims
              </span>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-extrabold text-white font-mono">
                  {report.total_claims}
                </span>
                <span className="text-xs text-slate-500 font-mono">100%</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div className="bg-brand-500 h-full w-full" />
              </div>
            </div>

            {/* Supported */}
            <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">
                  Supported
                </span>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-extrabold text-emerald-400 font-mono">
                  {report.supported_claims}
                </span>
                <span className="text-xs text-emerald-500 font-mono">
                  {Math.round((report.supported_claims / (report.total_claims || 1)) * 100)}%
                </span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-emerald-500 h-full transition-all duration-500"
                  style={{
                    width: `${(report.supported_claims / (report.total_claims || 1)) * 100}%`,
                  }}
                />
              </div>
            </div>

            {/* Partially Supported */}
            <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400">
                  Partially Supp.
                </span>
                <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-extrabold text-amber-400 font-mono">
                  {report.partially_supported_claims}
                </span>
                <span className="text-xs text-amber-500 font-mono">
                  {Math.round(
                    (report.partially_supported_claims / (report.total_claims || 1)) * 100
                  )}
                  %
                </span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-amber-500 h-full transition-all duration-500"
                  style={{
                    width: `${
                      (report.partially_supported_claims / (report.total_claims || 1)) * 100
                    }%`,
                  }}
                />
              </div>
            </div>

            {/* Unsupported */}
            <div className="p-4 rounded-xl bg-rose-500/5 border border-rose-500/20 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-rose-400">
                  Unsupported
                </span>
                <XCircle className="h-3.5 w-3.5 text-rose-400" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-extrabold text-rose-400 font-mono">
                  {report.unsupported_claims}
                </span>
                <span className="text-xs text-rose-500 font-mono">
                  {Math.round(
                    (report.unsupported_claims / (report.total_claims || 1)) * 100
                  )}
                  %
                </span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-rose-500 h-full transition-all duration-500"
                  style={{
                    width: `${
                      (report.unsupported_claims / (report.total_claims || 1)) * 100
                    }%`,
                  }}
                />
              </div>
            </div>

            {/* Conflicting */}
            <div className="p-4 rounded-xl bg-purple-500/5 border border-purple-500/20 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-purple-400">
                  Conflicting
                </span>
                <AlertCircle className="h-3.5 w-3.5 text-purple-400" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-extrabold text-purple-400 font-mono">
                  {report.conflicting_claims}
                </span>
                <span className="text-xs text-purple-500 font-mono">
                  {Math.round(
                    (report.conflicting_claims / (report.total_claims || 1)) * 100
                  )}
                  %
                </span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-purple-500 h-full transition-all duration-500"
                  style={{
                    width: `${
                      (report.conflicting_claims / (report.total_claims || 1)) * 100
                    }%`,
                  }}
                />
              </div>
            </div>

            {/* Insufficient Evidence */}
            <div className="p-4 rounded-xl bg-slate-500/5 border border-slate-500/20 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Insufficient
                </span>
                <HelpCircle className="h-3.5 w-3.5 text-slate-400" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-extrabold text-slate-400 font-mono">
                  {report.insufficient_evidence_claims}
                </span>
                <span className="text-xs text-slate-500 font-mono">
                  {Math.round(
                    (report.insufficient_evidence_claims / (report.total_claims || 1)) * 100
                  )}
                  %
                </span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-slate-500 h-full transition-all duration-500"
                  style={{
                    width: `${
                      (report.insufficient_evidence_claims / (report.total_claims || 1)) * 100
                    }%`,
                  }}
                />
              </div>
            </div>
          </div>

          {/* Evidence Details Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                  Evidence Details & Provenance
                </h3>
                <p className="text-xs text-slate-400">
                  Review original document names, page references, and supporting text excerpts for each claim.
                </p>
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Support Rate:{' '}
                <span className="text-emerald-400 font-bold">
                  {Math.round((report.overall_support_rate || 0) * 100)}%
                </span>
              </div>
            </div>

            <EvidenceDetailsTable
              claims={report.claims || []}
              onOpenSourceModal={handleOpenSourceModal}
              activeStatusFilter={statusFilter}
              onFilterChange={setStatusFilter}
            />
          </div>
        </div>
      )}

      {/* Source Document Modal */}
      <SourceDocumentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        claim={selectedClaimForModal}
      />
    </div>
  );
};

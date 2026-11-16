import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  Clock,
  User,
  ShieldCheck,
  RotateCcw,
  Eye,
  ArrowRightLeft,
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  FileText,
  ChevronRight,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { HandoverVersionItem } from '../../types/handover';
import { handoverService } from '../../services/handoverService';
import { useToast } from '../../hooks/useToast';
import { RestoreConfirmationModal } from './RestoreConfirmationModal';
import { VersionComparisonModal } from './VersionComparisonModal';
import { VersionSnapshotModal } from './VersionSnapshotModal';
import { CreateVersionModal } from './CreateVersionModal';

interface VersionHistorySectionProps {
  handoverId: string;
  currentVersionNumber?: string;
  onVersionRestored?: (newVersion: any) => void;
  className?: string;
  compact?: boolean;
}

export const VersionHistorySection: React.FC<VersionHistorySectionProps> = ({
  handoverId,
  currentVersionNumber = 'v1.0',
  onVersionRestored,
  className = '',
  compact = false,
}) => {
  const { success, error, info } = useToast();

  const [versions, setVersions] = useState<HandoverVersionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Modals state
  const [selectedSnapshotVersion, setSelectedSnapshotVersion] = useState<HandoverVersionItem | null>(null);
  const [isSnapshotModalOpen, setIsSnapshotModalOpen] = useState<boolean>(false);

  const [selectedRestoreVersion, setSelectedRestoreVersion] = useState<HandoverVersionItem | null>(null);
  const [isRestoreModalOpen, setIsRestoreModalOpen] = useState<boolean>(false);
  const [isRestoring, setIsRestoring] = useState<boolean>(false);

  const [isComparisonModalOpen, setIsComparisonModalOpen] = useState<boolean>(false);
  const [compareFromId, setCompareFromId] = useState<string | undefined>(undefined);
  const [compareToId, setCompareToId] = useState<string | undefined>(undefined);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);

  const loadVersions = async () => {
    setLoading(true);
    try {
      const res = await handoverService.listVersions(handoverId);
      if (res && res.data && Array.isArray(res.data)) {
        // Sort descending (latest on top)
        const sorted = [...res.data].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setVersions(sorted);
      } else {
        setVersions([]);
      }
    } catch (err: any) {
      console.error('Failed to load version history:', err);
      error('Failed to Load Versions', err?.message || 'Could not fetch version records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (handoverId) {
      loadVersions();
    }
  }, [handoverId]);

  // Handle View Version Snapshot
  const handleViewVersion = (ver: HandoverVersionItem) => {
    setSelectedSnapshotVersion(ver);
    setIsSnapshotModalOpen(true);
  };

  // Handle Compare Click from specific version
  const handleOpenCompare = (ver?: HandoverVersionItem) => {
    if (ver) {
      // If version is not latest, compare it against the latest
      const latest = versions.find((v) => v.is_latest) || versions[0];
      if (latest && latest.id !== ver.id) {
        setCompareFromId(ver.id);
        setCompareToId(latest.id);
      } else if (versions.length >= 2) {
        setCompareFromId(versions[1].id);
        setCompareToId(ver.id);
      } else {
        setCompareFromId(ver.id);
        setCompareToId(ver.id);
      }
    } else if (versions.length >= 2) {
      const sorted = [...versions].sort((a, b) =>
        a.version_number.localeCompare(b.version_number, undefined, { numeric: true })
      );
      setCompareFromId(sorted[0].id);
      setCompareToId(sorted[sorted.length - 1].id);
    }
    setIsComparisonModalOpen(true);
  };

  // Handle Restore Click
  const handleOpenRestore = (ver: HandoverVersionItem) => {
    setSelectedRestoreVersion(ver);
    setIsRestoreModalOpen(true);
  };

  // Execute Restore API call
  const handleConfirmRestore = async (reason: string) => {
    if (!selectedRestoreVersion) return;
    setIsRestoring(true);
    try {
      const res = await handoverService.restoreVersion(
        handoverId,
        selectedRestoreVersion.id,
        reason
      );
      success(
        'Version Restored Successfully',
        `Created new revision based on baseline ${selectedRestoreVersion.version_number}. Previous versions remain permanently preserved.`
      );
      setIsRestoreModalOpen(false);
      setSelectedRestoreVersion(null);
      await loadVersions();
      if (onVersionRestored) {
        onVersionRestored(res.data);
      }
    } catch (err: any) {
      console.error('Failed to restore version:', err);
      error('Restoration Failed', err?.message || 'Could not restore target version snapshot.');
    } finally {
      setIsRestoring(false);
    }
  };

  // Execute Create Snapshot API call
  const handleConfirmCreateSnapshot = async (description: string) => {
    try {
      const res = await handoverService.createVersion(handoverId, description);
      success(
        'Version Snapshot Created',
        `Archived version ${res.data?.version_number || 'new revision'} baseline.`
      );
      await loadVersions();
    } catch (err: any) {
      console.error('Failed to create snapshot:', err);
      error('Snapshot Creation Failed', err?.message || 'Could not archive version snapshot.');
    }
  };

  const getStatusBadgeVariant = (status: string): 'default' | 'success' | 'warning' | 'danger' | 'accent' => {
    const s = (status || '').toUpperCase();
    switch (s) {
      case 'APPROVED':
        return 'success';
      case 'IN_REVIEW':
        return 'accent';
      case 'CHANGES_REQUESTED':
        return 'warning';
      case 'REJECTED':
        return 'danger';
      case 'DRAFT':
      default:
        return 'default';
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
            <GitBranch className="h-4 w-4" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-tight">
                Version History & Snapshots
              </h3>
              <Badge variant="ai" size="sm">
                {versions.length} {versions.length === 1 ? 'Version' : 'Versions'}
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400">
              Immutable historical baselines with full audit attribution and comparison
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={loadVersions}
            isLoading={loading}
            title="Refresh Version List"
            className="p-1.5 text-slate-400 hover:text-white"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>

          {versions.length >= 2 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleOpenCompare()}
              leftIcon={<ArrowRightLeft className="h-3.5 w-3.5" />}
              className="text-xs font-semibold"
            >
              Compare Versions
            </Button>
          )}

          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsCreateModalOpen(true)}
            leftIcon={<Plus className="h-3.5 w-3.5" />}
            className="text-xs font-semibold"
          >
            Create Snapshot
          </Button>
        </div>
      </div>

      {/* Version Items List */}
      {loading && versions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-slate-400">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          <span className="text-xs">Loading immutable version records...</span>
        </div>
      ) : versions.length === 0 ? (
        <div className="p-8 rounded-xl bg-slate-900/60 border border-slate-800 text-center space-y-3">
          <GitBranch className="h-8 w-8 text-slate-600 mx-auto" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-white">No Version History Records</h4>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              This handover has not been version-snapshotted yet. When sections are modified after approval or a revision is created, versions appear here.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsCreateModalOpen(true)}
            leftIcon={<Plus className="h-3.5 w-3.5" />}
            className="text-xs"
          >
            Create First Baseline Snapshot
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {versions.map((ver, idx) => {
            const isLatest = ver.is_latest;
            const formattedDate = ver.created_at
              ? new Date(ver.created_at).toLocaleString('en-US', {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                })
              : 'Unknown date';

            return (
              <div
                key={ver.id || idx}
                className={`p-4 rounded-xl transition-all border ${
                  isLatest
                    ? 'bg-gradient-to-r from-brand-950/30 via-slate-900 to-slate-900 border-brand-500/40 shadow-sm'
                    : 'bg-[#0F172A] border-slate-800/90 hover:border-slate-700'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  {/* Left Metadata Block */}
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-bold text-white flex items-center gap-1.5">
                        {ver.version_number}
                      </span>

                      {isLatest && (
                        <Badge variant="success" size="sm" dot>
                          Latest Active
                        </Badge>
                      )}

                      <Badge variant={getStatusBadgeVariant(ver.approval_status)} size="sm">
                        {ver.approval_status}
                      </Badge>

                      {ver.parent_version_id && (
                        <span className="text-[11px] font-mono text-slate-500 flex items-center gap-1">
                          <GitBranch className="h-3 w-3" />
                          Branch revision
                        </span>
                      )}
                    </div>

                    {/* Version Description */}
                    {ver.version_description ? (
                      <p className="text-xs text-slate-300 leading-relaxed line-clamp-2">
                        {ver.version_description}
                      </p>
                    ) : (
                      <p className="text-xs text-slate-500 italic">No description provided for this revision.</p>
                    )}

                    {/* Created by & Timestamp */}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-0.5">
                      <div className="flex items-center gap-1.5">
                        <User className="h-3.5 w-3.5 text-slate-500" />
                        <span className="truncate">
                          Created by: <strong className="text-slate-300">{ver.creator_name || 'System / Outgoing Lead'}</strong>
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 font-mono text-[11px]">
                        <Clock className="h-3.5 w-3.5 text-slate-500" />
                        <span>{formattedDate}</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions Column */}
                  <div className="flex items-center gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-slate-800/80 shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewVersion(ver)}
                      leftIcon={<Eye className="h-3.5 w-3.5" />}
                      className="text-xs font-semibold"
                    >
                      View Version
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenCompare(ver)}
                      leftIcon={<ArrowRightLeft className="h-3.5 w-3.5" />}
                      className="text-xs font-semibold"
                    >
                      Compare
                    </Button>

                    {!isLatest ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleOpenRestore(ver)}
                        leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
                        className="text-xs font-semibold text-amber-300 border-amber-500/50 hover:bg-amber-500/10"
                        title="Restore this version as a new revision"
                      >
                        Restore Version
                      </Button>
                    ) : (
                      <span className="text-[11px] font-mono text-emerald-400/80 px-2.5 py-1 rounded bg-emerald-950/40 border border-emerald-500/20 select-none">
                        Current Baseline
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Snapshot Viewer Modal */}
      <VersionSnapshotModal
        isOpen={isSnapshotModalOpen}
        onClose={() => {
          setIsSnapshotModalOpen(false);
          setSelectedSnapshotVersion(null);
        }}
        version={selectedSnapshotVersion}
        onCompareClick={(v) => {
          setIsSnapshotModalOpen(false);
          handleOpenCompare(v);
        }}
        onRestoreClick={(v) => {
          setIsSnapshotModalOpen(false);
          handleOpenRestore(v);
        }}
      />

      {/* Comparison Engine Modal */}
      <VersionComparisonModal
        isOpen={isComparisonModalOpen}
        onClose={() => {
          setIsComparisonModalOpen(false);
          setCompareFromId(undefined);
          setCompareToId(undefined);
        }}
        handoverId={handoverId}
        versions={versions}
        initialFromVersionId={compareFromId}
        initialToVersionId={compareToId}
      />

      {/* Restore Confirmation Modal */}
      <RestoreConfirmationModal
        isOpen={isRestoreModalOpen}
        onClose={() => {
          setIsRestoreModalOpen(false);
          setSelectedRestoreVersion(null);
        }}
        onConfirm={handleConfirmRestore}
        version={selectedRestoreVersion}
        currentLatestVersionNumber={currentVersionNumber}
        isRestoring={isRestoring}
      />

      {/* Create Version Modal */}
      <CreateVersionModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleConfirmCreateSnapshot}
        currentVersionNumber={currentVersionNumber}
      />
    </div>
  );
};

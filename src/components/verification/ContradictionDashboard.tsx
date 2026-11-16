import React, { useState, useEffect, useMemo } from 'react';
import {
  GitCompare,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Ban,
  Sparkles,
  RotateCcw,
  FileText,
  Filter,
  Search,
  ExternalLink,
  ChevronDown,
  Quote,
  Check,
  HelpCircle,
  Eye,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Skeleton } from '../common/Skeleton';
import { EmptyState } from '../common/EmptyState';
import { useToast } from '../../hooks/useToast';
import { verificationService } from '../../services/verificationService';
import {
  ConflictResponse,
  ConflictResolutionStatusType,
} from '../../types/verification';
import { ContradictionResolutionModal } from './ContradictionResolutionModal';
import { cn } from '../../utils/cn';

interface ContradictionDashboardProps {
  initialProjectId?: string;
}

export const ContradictionDashboard: React.FC<ContradictionDashboardProps> = ({
  initialProjectId,
}) => {
  const { success, error, info } = useToast();

  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(initialProjectId || '');
  const [conflicts, setConflicts] = useState<ConflictResponse[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Resolution Modal
  const [selectedConflict, setSelectedConflict] = useState<ConflictResponse | null>(null);
  const [isResolveModalOpen, setIsResolveModalOpen] = useState(false);

  // 1. Load projects and conflict categories
  useEffect(() => {
    const init = async () => {
      try {
        const [projList, cats] = await Promise.all([
          verificationService.getProjects(),
          verificationService.getConflictCategories(),
        ]);
        setProjects(projList);
        setCategories(cats);
        if (projList.length > 0 && !selectedProjectId) {
          setSelectedProjectId(projList[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load initial data:', err);
      }
    };
    init();
  }, []);

  // 2. Fetch conflicts for selected project
  const loadConflicts = async (projectId: string) => {
    if (!projectId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await verificationService.getProjectConflicts(projectId);
      setConflicts(data);
    } catch (err: any) {
      setConflicts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedProjectId) {
      loadConflicts(selectedProjectId);
    }
  }, [selectedProjectId]);

  // 3. Trigger Contradiction Scan using backend Gemini Engine
  const handleRunScan = async () => {
    if (!selectedProjectId) {
      error('No Project Selected', 'Please select a project to scan for contradictions.');
      return;
    }
    setScanning(true);
    info(
      'Scanning Project Documents',
      'Extracting factual statements across documents and evaluating contradictions...'
    );
    try {
      const report = await verificationService.triggerContradictionDetection(selectedProjectId);
      setConflicts(report.conflicts || []);
      success(
        'Contradiction Scan Complete',
        `Analyzed ${report.documents_analyzed} documents (${report.statements_extracted} statements). Found ${report.contradictions_detected} contradiction(s).`
      );
    } catch (err: any) {
      error(
        'Scan Failed',
        err.message || 'Contradiction detection failed. Ensure documents are uploaded.'
      );
    } finally {
      setScanning(false);
    }
  };

  // 4. Update status quick-action (Under Review)
  const handleMarkUnderReview = async (conflict: ConflictResponse) => {
    try {
      await verificationService.updateConflictStatus(conflict.id, {
        status: 'Under Review',
        resolution_status: 'Under Review',
      });
      info('Status Updated', `Conflict marked as Under Review.`);
      if (selectedProjectId) loadConflicts(selectedProjectId);
    } catch (err: any) {
      error('Failed to Update Status', err.message);
    }
  };

  const handleOpenResolve = (conflict: ConflictResponse) => {
    setSelectedConflict(conflict);
    setIsResolveModalOpen(true);
  };

  // Status Badge Component
  const renderStatusBadge = (status: string) => {
    const clean = (status || 'unresolved').toLowerCase();
    if (clean.includes('resolved') && !clean.includes('un')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="h-3.5 w-3.5" />
          <span>Resolved</span>
        </span>
      );
    }
    if (clean.includes('review')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
          <Clock className="h-3.5 w-3.5" />
          <span>Under Review</span>
        </span>
      );
    }
    if (clean.includes('dismiss')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
          <Ban className="h-3.5 w-3.5" />
          <span>Dismissed</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
        <AlertTriangle className="h-3.5 w-3.5" />
        <span>Unresolved</span>
      </span>
    );
  };

  // Metric counts
  const metrics = useMemo(() => {
    let unresolved = 0;
    let underReview = 0;
    let resolved = 0;
    let dismissed = 0;

    conflicts.forEach((c) => {
      const s = (c.resolution_status || c.status || 'unresolved').toLowerCase();
      if (s.includes('resolved') && !s.includes('un')) resolved++;
      else if (s.includes('review')) underReview++;
      else if (s.includes('dismiss')) dismissed++;
      else unresolved++;
    });

    return {
      total: conflicts.length,
      unresolved,
      underReview,
      resolved,
      dismissed,
    };
  }, [conflicts]);

  // Filtered conflicts
  const filteredConflicts = useMemo(() => {
    return conflicts.filter((c) => {
      // Status filter
      if (statusFilter !== 'all') {
        const s = (c.resolution_status || c.status || 'unresolved').toLowerCase();
        if (statusFilter === 'Unresolved' && (s.includes('resolved') && !s.includes('un') || s.includes('review') || s.includes('dismiss'))) return false;
        if (statusFilter === 'Under Review' && !s.includes('review')) return false;
        if (statusFilter === 'Resolved' && (!s.includes('resolved') || s.includes('un'))) return false;
        if (statusFilter === 'Dismissed' && !s.includes('dismiss')) return false;
      }

      // Category filter
      if (categoryFilter !== 'all') {
        if (c.conflict_category !== categoryFilter && c.conflict_type !== categoryFilter) {
          return false;
        }
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const descMatch = c.description?.toLowerCase().includes(q);
        const stmtAMatch = (c.conflicting_statement_a || c.statement_a || '').toLowerCase().includes(q);
        const stmtBMatch = (c.conflicting_statement_b || c.statement_b || '').toLowerCase().includes(q);
        const docAMatch = (c.source_document_a || '').toLowerCase().includes(q);
        const docBMatch = (c.source_document_b || '').toLowerCase().includes(q);
        return descMatch || stmtAMatch || stmtBMatch || docAMatch || docBMatch;
      }

      return true;
    });
  }, [conflicts, statusFilter, categoryFilter, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Top Banner & Control Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl bg-gradient-to-r from-slate-900 via-[#130E26]/80 to-slate-900 border border-slate-800 shadow-lg">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <GitCompare className="h-4 w-4" />
            </span>
            <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">
              Contradiction Detection Engine
            </span>
            <span className="text-slate-600">·</span>
            <span className="text-xs text-slate-400 font-mono">Cross-Document Verification</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Knowledge Conflicts & Contradictions
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            Identify conflicting deadlines, architecture specs, task statuses, and team responsibilities across documents.
          </p>
        </div>

        {/* Project Selector & Scan Action */}
        <div className="flex items-center gap-3 flex-wrap">
          {projects.length > 0 && (
            <div className="relative">
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="appearance-none pl-3 pr-8 py-2 text-xs sm:text-sm rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-purple-500 transition-colors font-medium cursor-pointer"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name || p.key || `Project ${p.id.slice(0, 8)}`}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
            </div>
          )}

          <Button
            variant="primary"
            onClick={handleRunScan}
            isLoading={scanning}
            className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-xs sm:text-sm px-4 py-2 rounded-xl shadow-glow"
          >
            <Sparkles className="h-4 w-4" />
            <span>{scanning ? 'Detecting Contradictions...' : 'Run Contradiction Scan'}</span>
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {/* Total Detected */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Total Detected
          </span>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-extrabold text-white font-mono">
              {metrics.total}
            </span>
            <span className="text-xs text-slate-500 font-mono">All Time</span>
          </div>
        </div>

        {/* Unresolved */}
        <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400">
              Unresolved
            </span>
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-extrabold text-amber-400 font-mono">
              {metrics.unresolved}
            </span>
            <span className="text-xs text-amber-500 font-mono">Requires Action</span>
          </div>
        </div>

        {/* Under Review */}
        <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/20 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-400">
              Under Review
            </span>
            <Clock className="h-3.5 w-3.5 text-blue-400" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-extrabold text-blue-400 font-mono">
              {metrics.underReview}
            </span>
            <span className="text-xs text-blue-500 font-mono">In Triage</span>
          </div>
        </div>

        {/* Resolved */}
        <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">
              Resolved
            </span>
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-extrabold text-emerald-400 font-mono">
              {metrics.resolved}
            </span>
            <span className="text-xs text-emerald-500 font-mono">Authoritative</span>
          </div>
        </div>

        {/* Dismissed */}
        <div className="p-4 rounded-xl bg-slate-500/5 border border-slate-500/20 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Dismissed
            </span>
            <Ban className="h-3.5 w-3.5 text-slate-400" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-extrabold text-slate-400 font-mono">
              {metrics.dismissed}
            </span>
            <span className="text-xs text-slate-500 font-mono">Closed</span>
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conflicts, statements, or document titles..."
            className="w-full pl-9 pr-3 py-1.5 text-xs sm:text-sm rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 transition-colors"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Status Filter Chips */}
          <div className="flex items-center gap-1">
            {['all', 'Unresolved', 'Under Review', 'Resolved', 'Dismissed'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={cn(
                  'px-2.5 py-1 text-xs rounded-lg font-medium transition-all',
                  statusFilter === st
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
                )}
              >
                {st === 'all' ? 'All Statuses' : st}
              </button>
            ))}
          </div>

          {/* Category Dropdown */}
          {categories.length > 0 && (
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-2.5 py-1 text-xs rounded-lg bg-slate-950 border border-slate-700 text-slate-300 focus:outline-none focus:border-purple-500 font-medium"
            >
              <option value="all">All Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c.replace('_', ' ').toUpperCase()}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Conflicts List */}
      {loading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-44 rounded-xl" />
          ))}
        </div>
      ) : filteredConflicts.length === 0 ? (
        <EmptyState
          title={
            conflicts.length === 0
              ? 'No contradictions detected in this project'
              : 'No conflicts match the applied filters'
          }
          description={
            conflicts.length === 0
              ? 'Click "Run Contradiction Scan" to have Gemini analyze and compare factual statements across project documents.'
              : 'Try clearing your search query or changing the status/category filter.'
          }
          icon={GitCompare}
          actionLabel={conflicts.length === 0 ? 'Scan Now' : undefined}
          onAction={conflicts.length === 0 ? handleRunScan : undefined}
        />
      ) : (
        <div className="space-y-4">
          {filteredConflicts.map((conflict, idx) => {
            const statementA = conflict.conflicting_statement_a || conflict.statement_a || '';
            const statementB = conflict.conflicting_statement_b || conflict.statement_b || '';
            const docA = conflict.source_document_a || conflict.source_document_a_name || 'Document A';
            const docB = conflict.source_document_b || conflict.source_document_b_name || 'Document B';
            const excerptA = conflict.source_excerpt_a || conflict.source_a?.excerpt || '';
            const excerptB = conflict.source_excerpt_b || conflict.source_b?.excerpt || '';
            const isResolved =
              conflict.resolution_status === 'Resolved' ||
              conflict.status === 'Resolved' ||
              Boolean(conflict.resolution);

            return (
              <div
                key={conflict.id || idx}
                className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all space-y-4"
              >
                {/* Header row: Category, Status, Timestamp, Action */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    {renderStatusBadge(conflict.resolution_status || conflict.status)}
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 uppercase font-semibold">
                      {conflict.conflict_category}
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono">
                      ID: {conflict.id.slice(0, 8)}
                    </span>
                    {conflict.detection_timestamp && (
                      <span className="text-[11px] text-slate-500 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        <span>{new Date(conflict.detection_timestamp).toLocaleDateString()}</span>
                      </span>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {(!isResolved || conflict.resolution_status === 'Under Review') && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleMarkUnderReview(conflict)}
                        className="text-xs text-blue-400 border-blue-500/30 hover:bg-blue-500/10"
                      >
                        Mark Under Review
                      </Button>
                    )}

                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleOpenResolve(conflict)}
                      className={cn(
                        'text-xs flex items-center gap-1.5',
                        isResolved
                          ? 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                          : 'bg-gradient-to-r from-purple-600 to-brand-600 hover:from-purple-500 hover:to-brand-500 text-white shadow-sm'
                      )}
                    >
                      <GitCompare className="h-3.5 w-3.5" />
                      <span>{isResolved ? 'Review Decision' : 'Resolve Conflict'}</span>
                    </Button>
                  </div>
                </div>

                {/* Contradiction Description */}
                <div className="text-sm font-semibold text-white">
                  {conflict.description}
                </div>

                {/* Side-by-Side Conflicting Statements */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Statement A */}
                  <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col justify-between gap-3">
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-brand-400">
                          Conflicting Statement A
                        </span>
                        <div className="flex items-center gap-1 text-[11px] text-slate-400 truncate max-w-[200px]">
                          <FileText className="h-3 w-3 text-brand-400 shrink-0" />
                          <span className="truncate" title={docA}>
                            {docA}
                          </span>
                        </div>
                      </div>
                      <p className="font-medium text-white text-xs sm:text-sm leading-relaxed">
                        "{statementA}"
                      </p>
                    </div>

                    {excerptA && (
                      <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-850 text-xs text-slate-400 italic">
                        <Quote className="h-3 w-3 text-slate-600 mb-0.5 inline mr-1" />
                        {excerptA}
                      </div>
                    )}
                  </div>

                  {/* Statement B */}
                  <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col justify-between gap-3">
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-purple-400">
                          Conflicting Statement B
                        </span>
                        <div className="flex items-center gap-1 text-[11px] text-slate-400 truncate max-w-[200px]">
                          <FileText className="h-3 w-3 text-purple-400 shrink-0" />
                          <span className="truncate" title={docB}>
                            {docB}
                          </span>
                        </div>
                      </div>
                      <p className="font-medium text-white text-xs sm:text-sm leading-relaxed">
                        "{statementB}"
                      </p>
                    </div>

                    {excerptB && (
                      <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-850 text-xs text-slate-400 italic">
                        <Quote className="h-3 w-3 text-slate-600 mb-0.5 inline mr-1" />
                        {excerptB}
                      </div>
                    )}
                  </div>
                </div>

                {/* If Resolved: Authoritative Resolution Display */}
                {conflict.resolution && (
                  <div className="p-3.5 rounded-xl bg-emerald-500/5 border border-emerald-500/20 space-y-2">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                        <CheckCircle2 className="h-4 w-4" /> Authoritative Decision
                      </span>
                      {conflict.resolution.resolved_at && (
                        <span className="text-[11px] text-slate-500 font-mono">
                          Resolved: {new Date(conflict.resolution.resolved_at).toLocaleString()}
                        </span>
                      )}
                    </div>

                    <div className="text-xs sm:text-sm font-medium text-slate-200">
                      Authoritative Statement:{' '}
                      <span className="text-white font-semibold">
                        "{conflict.resolution.authoritative_value || conflict.resolution.chosen_value}"
                      </span>
                    </div>

                    {(conflict.resolution.explanation || conflict.resolution.resolution_notes) && (
                      <p className="text-xs text-slate-400 italic">
                        Explanation: "{conflict.resolution.explanation || conflict.resolution.resolution_notes}"
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Resolution Modal */}
      <ContradictionResolutionModal
        isOpen={isResolveModalOpen}
        onClose={() => setIsResolveModalOpen(false)}
        conflict={selectedConflict}
        onSuccess={() => {
          if (selectedProjectId) loadConflicts(selectedProjectId);
        }}
      />
    </div>
  );
};

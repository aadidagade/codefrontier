import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  FileText,
  FileCode,
  FileSpreadsheet,
  File,
  Lock,
  GitBranch,
  Clock,
  Layers,
  Users,
  CheckSquare,
  ShieldCheck,
  ExternalLink,
  ChevronRight,
  Edit2,
  RefreshCw,
  HelpCircle,
  AlertCircle,
  Copy,
  Check,
  Save,
  Share2,
  Download,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/common/Card';
import { Input } from '../../components/common/Input';
import { Textarea } from '../../components/common/Textarea';
import { Modal } from '../../components/common/Modal';
import { documentService } from '../../services/documentService';
import { handoverService, INITIAL_GENERATED_HANDOVER } from '../../services/handoverService';
import { notificationService } from '../../services/notificationService';
import { KnowledgeSourceDocument } from '../../types/document';
import {
  GenerationConfig,
  AnalysisStageInfo,
  GeneratedHandover,
  KeyDecisionItem,
  BlockerRiskItem,
  UnresolvedQuestionItem,
  RecommendedActionItem,
  EvidenceCitationItem,
} from '../../types/handover';
import { EvidenceDrawer } from '../../components/verification/EvidenceDrawer';
import { VerificationClaim } from '../../types/verification';
import { verificationService } from '../../services/verificationService';
import { useToast } from '../../hooks/useToast';
import { formatFileSize, formatDate } from '../../utils/formatters';

const ANALYSIS_STAGES: AnalysisStageInfo[] = [
  { id: 1, title: 'Retrieving relevant passages', description: 'Searching dense vector space across selected documents for high-relevance semantic chunks.', status: 'pending' },
  { id: 2, title: 'Reconstructing project overview', description: 'Synthesizing system boundaries, mission impact, architecture diagrams, and service tiers.', status: 'pending' },
  { id: 3, title: 'Extracting decisions and rationale', description: 'Codifying Architectural Decision Records (ADRs) with rationale and evidence citations.', status: 'pending' },
  { id: 4, title: 'Identifying tasks and ownership', description: 'Mapping active on-call tasks, shadow crons, and service ownership to engineers.', status: 'pending' },
  { id: 5, title: 'Detecting blockers and risks', description: 'Analyzing secret key rotation cycles, single points of failure, and unmonitored scripts.', status: 'pending' },
  { id: 6, title: 'Mapping dependencies', description: 'Connecting microservice RPCs, Redis state, and third-party banking API contracts.', status: 'pending' },
  { id: 7, title: 'Checking evidence and contradictions', description: 'Validating claims against Git commits and flagging infrastructure drift conflicts.', status: 'pending' },
  { id: 8, title: 'Preparing handover draft', description: 'Formatting structured handover brief with evidence index ready for lead sign-off.', status: 'pending' },
];

export const GenerateHandoverPage: React.FC = () => {
  const navigate = useNavigate();
  const { success, warning, info: toastInfo, error: toastError } = useToast();

  // Documents from Document Service
  const [documents, setDocuments] = useState<KnowledgeSourceDocument[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);

  // Configuration State
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [incomingRole, setIncomingRole] = useState('Staff Site Reliability Engineer / Distributed Systems');
  const [handoverScope, setHandoverScope] = useState('Full Architectural & Operational Handover');
  const [timelineScope, setTimelineScope] = useState('Last 6 Months (Recommended)');
  const [additionalInstructions, setAdditionalInstructions] = useState('');

  // Generation & Analysis Progress State
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStageId, setCurrentStageId] = useState(0);
  const [currentStageDetail, setCurrentStageDetail] = useState('');
  const [analysisStages, setAnalysisStages] = useState<AnalysisStageInfo[]>(ANALYSIS_STAGES);
  const [analysisProgress, setAnalysisProgress] = useState(0);

  // Completed Generated Handover
  const [handover, setHandover] = useState<GeneratedHandover | null>(null);

  // Section Editing Modal State
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editedOverviewPurpose, setEditedOverviewPurpose] = useState('');
  const [editedOverviewStatus, setEditedOverviewStatus] = useState('');

  // Evidence Drawer State
  const [selectedDrawerClaim, setSelectedDrawerClaim] = useState<VerificationClaim | null>(null);
  const [isEvidenceDrawerOpen, setIsEvidenceDrawerOpen] = useState(false);

  // Section Navigation active anchor
  const [activeSection, setActiveSection] = useState('overview');

  const handleOpenCitationEvidence = async (cite: EvidenceCitationItem) => {
    const claims = await verificationService.getClaims();
    const matched = claims.find(
      (c) => c.sourceDocName === cite.sourceDocName || c.claimText.includes(cite.title)
    );
    if (matched) {
      setSelectedDrawerClaim(matched);
    } else {
      setSelectedDrawerClaim({
        id: cite.id,
        projectId: handover?.projectKey || 'AUTH-ZERO',
        projectKey: handover?.projectKey || 'AUTH-ZERO',
        projectName: handover?.projectName || 'Customer Identity & Passkey Migration',
        section: 'decisions',
        claimText: cite.title,
        sourceDocId: 'doc-1',
        sourceDocName: cite.sourceDocName,
        sourceDocType: 'pdf',
        pageOrSection: 'Primary Indexed Section',
        evidenceSnippet: cite.excerpt,
        evidenceStatus: cite.isFlagged ? 'partially_supported' : 'supported',
        uncertaintyFlags: cite.isFlagged ? ['contradictory'] : [],
        confidenceScore: cite.confidence,
        isSyntheticModelOutput: true,
        verificationStatus: 'unverified',
        conflictId: cite.isFlagged ? 'conf-1' : undefined,
        createdAt: new Date().toISOString(),
      });
    }
    setIsEvidenceDrawerOpen(true);
  };

  const handleOpenDecisionEvidence = async (dec: KeyDecisionItem) => {
    const claims = await verificationService.getClaims();
    const matched = claims.find(
      (c) => c.sourceDocName.includes(dec.supportingSource) || c.claimText.includes(dec.decision.slice(0, 20))
    );
    if (matched) {
      setSelectedDrawerClaim(matched);
    } else {
      setSelectedDrawerClaim({
        id: dec.id,
        projectId: handover?.projectKey || 'AUTH-ZERO',
        projectKey: handover?.projectKey || 'AUTH-ZERO',
        projectName: handover?.projectName || 'Customer Identity & Passkey Migration',
        section: 'decisions',
        claimText: dec.decision,
        sourceDocId: dec.sourceDocId || 'doc-1',
        sourceDocName: dec.supportingSource,
        sourceDocType: 'pdf',
        pageOrSection: 'Architecture Decision Record',
        evidenceSnippet: `Rationale: ${dec.rationale}. Verified under architectural review criteria.`,
        evidenceStatus: dec.isUncertain ? 'partially_supported' : 'supported',
        uncertaintyFlags: dec.isUncertain ? ['contradictory'] : [],
        confidenceScore: dec.isUncertain ? 74 : 96,
        isSyntheticModelOutput: true,
        verificationStatus: 'unverified',
        createdAt: new Date().toISOString(),
      });
    }
    setIsEvidenceDrawerOpen(true);
  };

  // Load documents
  useEffect(() => {
    async function fetchDocs() {
      setIsLoadingDocs(true);
      const res = await documentService.getAll();
      if (res.data) {
        setDocuments(res.data);
        // Pre-select documents marked 'ready'
        const readyIds = res.data.filter((d) => d.processingStatus === 'ready').map((d) => d.id);
        setSelectedDocIds(readyIds);
      }
      setIsLoadingDocs(false);
    }
    fetchDocs();
  }, []);

  const readyDocuments = documents.filter((d) => d.processingStatus === 'ready');

  const handleToggleDoc = (doc: KnowledgeSourceDocument) => {
    if (doc.processingStatus !== 'ready') {
      warning('Document Not Ready', 'Only documents with status "Ready for analysis" can be included.');
      return;
    }
    setSelectedDocIds((prev) =>
      prev.includes(doc.id) ? prev.filter((id) => id !== doc.id) : [...prev, doc.id]
    );
  };

  const handleSelectAllReady = () => {
    setSelectedDocIds(readyDocuments.map((d) => d.id));
  };

  const handleDeselectAll = () => {
    setSelectedDocIds([]);
  };

  // Start Generation
  const handleStartGeneration = async () => {
    if (selectedDocIds.length === 0) {
      toastError('No Documents Selected', 'Please select at least one ready document to reconstruct knowledge.');
      return;
    }

    setIsGenerating(true);
    setCurrentStageId(1);
    setAnalysisProgress(10);
    setHandover(null);

    // Reset stages
    setAnalysisStages(
      ANALYSIS_STAGES.map((s, idx) => ({
        ...s,
        status: idx === 0 ? 'in_progress' : 'pending',
      }))
    );

    const config: GenerationConfig = {
      incomingRole,
      handoverScope,
      timelineScope,
      additionalInstructions,
      selectedDocumentIds: selectedDocIds,
    };

    try {
      const res = await handoverService.generateHandover(config, (stageId, detail) => {
        setCurrentStageId(stageId);
        setCurrentStageDetail(detail);
        const progressPct = Math.round((stageId / 8) * 100);
        setAnalysisProgress(progressPct);

        setAnalysisStages((prev) =>
          prev.map((s) => ({
            ...s,
            status:
              s.id < stageId
                ? 'completed'
                : s.id === stageId
                ? 'in_progress'
                : 'pending',
            detail: s.id === stageId ? detail : s.detail,
          }))
        );
      });

      if (res.data) {
        setAnalysisStages((prev) => prev.map((s) => ({ ...s, status: 'completed' })));
        setAnalysisProgress(100);
        setHandover(res.data);
        setIsGenerating(false);
        success('Handover Reconstructed', 'AI synthesis completed with 96% verified evidence link confidence.');

        // Scroll to results
        setTimeout(() => {
          document.getElementById('generated-handover-results')?.scrollIntoView({ behavior: 'smooth' });
        }, 100);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Generation failed';
      toastError('Synthesis Error', msg);
      setIsGenerating(false);
    }
  };

  const openOverviewEdit = () => {
    if (!handover) return;
    setEditedOverviewPurpose(handover.overview.purpose);
    setEditedOverviewStatus(handover.overview.currentStatus);
    setEditingSection('overview');
  };

  const handleSaveOverviewEdit = () => {
    if (!handover) return;
    const updated = {
      ...handover,
      overview: {
        ...handover.overview,
        purpose: editedOverviewPurpose,
        currentStatus: editedOverviewStatus,
      },
    };
    setHandover(updated);
    handoverService.updateGeneratedHandover(handover.id, updated);
    setEditingSection(null);
    success('Overview Updated', 'Section changes saved to handover draft.');
  };

  const getFormatIcon = (fmt: string) => {
    switch (fmt) {
      case 'pdf':
        return <FileText className="h-4 w-4 text-rose-400" />;
      case 'docx':
        return <FileSpreadsheet className="h-4 w-4 text-blue-400" />;
      case 'md':
        return <FileCode className="h-4 w-4 text-purple-400" />;
      default:
        return <File className="h-4 w-4 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-24">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Link
              to="/handover"
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="h-3 w-3" />
              <span>Handover Sessions</span>
            </Link>
            <span className="text-slate-600">/</span>
            <span className="text-xs font-semibold text-brand-400 uppercase tracking-wider font-mono">
              AI Handover Synthesizer
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
            Reconstruct Project Knowledge
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Let AI connect the dots across your project documentation.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Badge variant="ai" size="md">
            Zero-Hallucination Evidence Linked
          </Badge>
        </div>
      </div>

      {/* SECTION 1: SOURCE SELECTION */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              <span className="h-5 w-5 rounded-full bg-brand-500/20 text-brand-400 text-xs flex items-center justify-center font-mono">
                1
              </span>
              <span>Source Document Selection</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Select verified project runbooks and ADRs to feed into the AI knowledge reconstruction pipeline
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-brand-400 font-semibold bg-brand-500/10 px-2.5 py-1 rounded border border-brand-500/20">
              {selectedDocIds.length} of {readyDocuments.length} Ready Documents Selected
            </span>
            <div className="flex items-center gap-1.5 text-xs">
              <button
                type="button"
                onClick={handleSelectAllReady}
                className="text-slate-400 hover:text-white underline underline-offset-2 text-[11px]"
              >
                Select All Ready
              </button>
              <span className="text-slate-600">•</span>
              <button
                type="button"
                onClick={handleDeselectAll}
                className="text-slate-400 hover:text-white underline underline-offset-2 text-[11px]"
              >
                Deselect All
              </button>
            </div>
          </div>
        </div>

        {/* Documents Table / Card List */}
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-[#0F172A]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold text-[11px]">
                  <th className="px-4 py-3 w-10 text-center">Include</th>
                  <th className="px-4 py-3">Document Name & Format</th>
                  <th className="px-4 py-3">Workspace</th>
                  <th className="px-4 py-3">File Size</th>
                  <th className="px-4 py-3">Processing Status</th>
                  <th className="px-4 py-3 text-right">Eligibility</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {documents.map((doc) => {
                  const isReady = doc.processingStatus === 'ready';
                  const isChecked = selectedDocIds.includes(doc.id);

                  return (
                    <tr
                      key={doc.id}
                      onClick={() => handleToggleDoc(doc)}
                      className={`transition-colors cursor-pointer ${
                        isChecked
                          ? 'bg-brand-500/10 hover:bg-brand-500/15'
                          : isReady
                          ? 'hover:bg-slate-800/40'
                          : 'opacity-40 cursor-not-allowed hover:bg-transparent'
                      }`}
                    >
                      <td className="px-4 py-3.5 text-center" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          disabled={!isReady}
                          onChange={() => handleToggleDoc(doc)}
                          className="rounded border-slate-700 bg-slate-800 text-brand-600 focus:ring-brand-500 h-4 w-4 cursor-pointer disabled:cursor-not-allowed"
                        />
                      </td>

                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2.5">
                          {getFormatIcon(doc.fileFormat)}
                          <div>
                            <span className="font-semibold text-white block">{doc.fileName}</span>
                            <span className="text-[10px] text-slate-500 font-mono uppercase">
                              {doc.fileFormat} {doc.pageCount ? `· ${doc.pageCount} Pages` : ''}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-3.5 font-mono text-brand-400 font-bold">
                        {doc.projectKey}
                      </td>

                      <td className="px-4 py-3.5 font-mono text-slate-400">
                        {doc.fileSizeBytesFormatted}
                      </td>

                      <td className="px-4 py-3.5">
                        {isReady ? (
                          <Badge variant="success" size="sm" dot>
                            Ready for analysis
                          </Badge>
                        ) : doc.processingStatus === 'failed' ? (
                          <Badge variant="danger" size="sm" dot>
                            Failed
                          </Badge>
                        ) : (
                          <Badge variant="warning" size="sm" dot>
                            Processing ({doc.processingProgress}%)
                          </Badge>
                        )}
                      </td>

                      <td className="px-4 py-3.5 text-right font-mono text-[11px]">
                        {isReady ? (
                          <span className="text-emerald-400 font-semibold">Eligible</span>
                        ) : (
                          <span className="text-slate-500">Must be ready</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* SECTION 2: GENERATION CONFIGURATION */}
      <section className="space-y-4">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <span className="h-5 w-5 rounded-full bg-brand-500/20 text-brand-400 text-xs flex items-center justify-center font-mono">
              2
            </span>
            <span>Generation Configuration</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Tailor the AI synthesis to the successor's role, operational depth, and historical window
          </p>
        </div>

        <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Incoming Role */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Incoming Role & Focus *
              </label>
              <select
                value={incomingRole}
                onChange={(e) => setIncomingRole(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700/80 px-3 h-10 text-xs text-slate-200 focus:border-brand-500 focus:outline-none cursor-pointer"
              >
                <option value="Staff Site Reliability Engineer / Distributed Systems">
                  Staff Site Reliability Engineer (SRE / Infra)
                </option>
                <option value="Principal Platform Architect">
                  Principal Platform Architect (Architecture & ADRs)
                </option>
                <option value="Senior Core Backend Engineer (Go/Kafka)">
                  Senior Core Backend Engineer (Code & Pipelines)
                </option>
                <option value="Security & Compliance Engineer">
                  Security & Compliance Engineer (KMS & Secrets)
                </option>
                <option value="Engineering Manager / Director">
                  Engineering Manager (Executive & Timelines)
                </option>
              </select>
            </div>

            {/* Handover Scope */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Handover Scope
              </label>
              <select
                value={handoverScope}
                onChange={(e) => setHandoverScope(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700/80 px-3 h-10 text-xs text-slate-200 focus:border-brand-500 focus:outline-none cursor-pointer"
              >
                <option value="Full Architectural & Operational Handover">
                  Full Architectural & Operational Handover
                </option>
                <option value="Incident Runbooks & On-Call Playbooks">
                  Incident Runbooks & On-Call Focus Only
                </option>
                <option value="Security, Secrets & Bastion Access">
                  Security, Secrets & Bastion Access Focus
                </option>
                <option value="Executive Continuity Summary">
                  Executive Continuity Summary (High-Level)
                </option>
              </select>
            </div>

            {/* Relevant Timeline */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Relevant Project Timeline
              </label>
              <select
                value={timelineScope}
                onChange={(e) => setTimelineScope(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700/80 px-3 h-10 text-xs text-slate-200 focus:border-brand-500 focus:outline-none cursor-pointer"
              >
                <option value="Last 6 Months (Recommended)">
                  Last 6 Months (Recommended)
                </option>
                <option value="All Historical Context">
                  All Historical Context (Complete Lifetime)
                </option>
                <option value="Last 3 Months">
                  Last 3 Months (Recent Sprints)
                </option>
                <option value="Active Incident & Migration Window">
                  Active Incident & Migration Window (Last 30 Days)
                </option>
              </select>
            </div>
          </div>

          {/* Additional Instructions */}
          <div>
            <Textarea
              label="Optional Additional Instructions"
              placeholder="e.g. Focus on 3:00 AM banking failovers, unmonitored shadow cron jobs, and specific gotchas for Redis circuit breakers..."
              rows={2}
              value={additionalInstructions}
              onChange={(e) => setAdditionalInstructions(e.target.value)}
            />
          </div>

          {/* Action Trigger */}
          <div className="pt-2 flex items-center justify-between border-t border-slate-800/80">
            <span className="text-xs text-slate-400">
              Selected sources will be cited with line-level evidence references.
            </span>

            <Button
              variant="ai"
              size="lg"
              onClick={handleStartGeneration}
              disabled={isGenerating || selectedDocIds.length === 0}
              leftIcon={<Sparkles className="h-4 w-4" />}
              className="text-xs px-6 font-semibold"
            >
              {isGenerating ? 'Synthesizing Handover...' : 'Generate Structured Handover'}
            </Button>
          </div>
        </Card>
      </section>

      {/* SECTION 3: MULTI-STAGE ANALYSIS PROGRESS */}
      {(isGenerating || (analysisProgress > 0 && analysisProgress < 100)) && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              <span className="h-5 w-5 rounded-full bg-brand-accent/20 text-brand-accent text-xs flex items-center justify-center font-mono">
                3
              </span>
              <span>Multi-Stage Knowledge Reconstruction Progress</span>
            </h2>
            <span className="text-xs font-mono font-bold text-brand-300">
              {analysisProgress}% Complete
            </span>
          </div>

          <Card className="bg-[#0F172A] border-brand-500/30 p-6 space-y-5 shadow-glow">
            {/* Main Progress Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-slate-300 font-medium">
                <span>Active Pipeline: Stage {currentStageId} of 8</span>
                <span className="font-mono text-brand-400">{analysisProgress}%</span>
              </div>
              <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-brand-600 via-indigo-500 to-brand-accent h-full rounded-full transition-all duration-300"
                  style={{ width: `${analysisProgress}%` }}
                />
              </div>
            </div>

            {/* 8-Stage Sequential Visual Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
              {analysisStages.map((st) => (
                <div
                  key={st.id}
                  className={`p-3 rounded-xl border transition-all text-xs flex flex-col justify-between ${
                    st.status === 'completed'
                      ? 'bg-slate-900/80 border-emerald-500/30 text-slate-200'
                      : st.status === 'in_progress'
                      ? 'bg-brand-500/10 border-brand-500 text-white shadow-sm ring-1 ring-brand-500/30'
                      : 'bg-slate-900/30 border-slate-800/80 text-slate-500'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-bold">STAGE 0{st.id}</span>
                      {st.status === 'completed' ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                      ) : st.status === 'in_progress' ? (
                        <div className="h-3.5 w-3.5 rounded-full border-2 border-brand-400 border-t-transparent animate-spin shrink-0" />
                      ) : (
                        <div className="h-3 w-3 rounded-full border border-slate-700 bg-slate-800 shrink-0" />
                      )}
                    </div>
                    <div className="font-semibold text-xs leading-snug">{st.title}</div>
                    <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5 leading-snug">
                      {st.description}
                    </p>
                  </div>

                  {st.detail && st.status === 'in_progress' && (
                    <div className="mt-2 text-[10px] font-mono text-brand-300 truncate">
                      {st.detail}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      {/* SECTION 4: GENERATED HANDOVER DISPLAY */}
      {handover && !isGenerating && (
        <motion.div
          id="generated-handover-results"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="space-y-6 pt-4"
        >
          {/* Section 4 Header Banner */}
          <div className="rounded-2xl bg-gradient-to-r from-brand-950/80 via-slate-900 to-purple-950/70 border border-brand-500/30 p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-2xl">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="font-mono text-xs font-bold text-brand-400 bg-brand-500/10 px-2.5 py-0.5 rounded border border-brand-500/20">
                  {handover.projectKey}
                </span>
                <Badge variant="ai" size="sm">
                  Evidence Verified: {handover.evidenceScore}%
                </Badge>
                <Badge variant="success" size="sm" dot>
                  Draft Generated
                </Badge>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                Structured Knowledge Handover: {handover.projectName}
              </h2>
              <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                Tailored for <strong className="text-white">{handover.targetRole}</strong> · Scope: {handover.scope}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              <Button
                variant="outline"
                size="sm"
                leftIcon={<Share2 className="h-3.5 w-3.5" />}
                onClick={() => success('Share Link Generated', 'Handover review link copied.')}
                className="text-xs"
              >
                Share Draft
              </Button>
              <Button
                variant="outline"
                size="sm"
                leftIcon={<Download className="h-3.5 w-3.5" />}
                onClick={() => success('Exported', 'Handover exported as Markdown with evidence index.')}
                className="text-xs"
              >
                Export Brief
              </Button>
              <Button
                variant="primary"
                size="sm"
                leftIcon={<CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
                onClick={() => {
                  notificationService.triggerSampleNotification('review_requested');
                  success('Submitted to Review Queue', 'Handover draft transferred for Project Lead audit and sign-off.');
                  navigate('/review');
                }}
                className="text-xs font-semibold shadow-glow"
              >
                Submit for Review &rarr;
              </Button>
            </div>
          </div>

          {/* Sticky Section Jump Navigation Bar */}
          <div className="sticky top-14 z-20 bg-[#080C14]/95 backdrop-blur-md p-2 rounded-xl border border-slate-800 flex items-center gap-1.5 overflow-x-auto text-xs shadow-md">
            {[
              { id: 'overview', label: 'A. Project Overview' },
              { id: 'decisions', label: 'B. Key Decisions' },
              { id: 'tasks', label: 'C. Tasks & Ownership' },
              { id: 'risks', label: 'D. Blockers & Risks' },
              { id: 'dependencies', label: 'E. Dependencies' },
              { id: 'questions', label: 'F. Unresolved Questions' },
              { id: 'actions', label: 'G. Next Actions' },
              { id: 'evidence', label: 'Evidence Citations' },
            ].map((nav) => (
              <button
                key={nav.id}
                onClick={() => {
                  setActiveSection(nav.id);
                  document.getElementById(`sec-${nav.id}`)?.scrollIntoView({ behavior: 'smooth' });
                }}
                className={`px-3 py-1.5 rounded-lg whitespace-nowrap text-xs font-medium transition-colors ${
                  activeSection === nav.id
                    ? 'bg-brand-500/20 text-brand-300 font-semibold border border-brand-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                {nav.label}
              </button>
            ))}
          </div>

          {/* Main 2-Column Split: Content (8) + Evidence Panel (4) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column (8): Handover Sections A to G */}
            <div className="lg:col-span-8 space-y-6">
              {/* SECTION A: PROJECT OVERVIEW */}
              <Card id="sec-overview" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span className="h-5 w-5 rounded-md bg-brand-500/20 text-brand-400 text-xs flex items-center justify-center font-mono font-bold">
                      A
                    </span>
                    <span>Project Overview</span>
                  </h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={openOverviewEdit}
                    leftIcon={<Edit2 className="h-3 w-3" />}
                    className="text-xs text-brand-400 hover:text-brand-300 h-7"
                  >
                    Edit Section
                  </Button>
                </div>

                <div className="space-y-3.5 text-xs">
                  <div>
                    <span className="font-semibold text-slate-300 block mb-1">
                      Project Purpose & High-Throughput SLA Mission:
                    </span>
                    <p className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/80 text-slate-300 leading-relaxed">
                      {handover.overview.purpose}
                    </p>
                  </div>

                  <div>
                    <span className="font-semibold text-slate-300 block mb-1">
                      Current Status & Stage Readiness:
                    </span>
                    <p className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/80 text-slate-300 leading-relaxed">
                      {handover.overview.currentStatus}
                    </p>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400 font-medium">Continuity Progress:</span>
                    <div className="flex items-center gap-3">
                      <div className="w-24 bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-brand-500 h-full rounded-full"
                          style={{ width: `${handover.overview.overallProgress}%` }}
                        />
                      </div>
                      <span className="font-mono font-bold text-white">
                        {handover.overview.overallProgress}% Complete
                      </span>
                    </div>
                  </div>
                </div>
              </Card>

              {/* SECTION B: KEY DECISIONS */}
              <Card id="sec-decisions" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span className="h-5 w-5 rounded-md bg-brand-500/20 text-brand-400 text-xs flex items-center justify-center font-mono font-bold">
                      B
                    </span>
                    <span>Key Architectural Decisions (ADRs)</span>
                  </h3>
                  <Badge variant="accent" size="sm">
                    {handover.decisions.length} Decisions Documented
                  </Badge>
                </div>

                <div className="space-y-3">
                  {handover.decisions.map((dec) => (
                    <div
                      key={dec.id}
                      className={`p-4 rounded-xl border text-xs space-y-2 transition-colors ${
                        dec.isUncertain
                          ? 'bg-amber-500/5 border-amber-500/30'
                          : 'bg-slate-900/60 border-slate-800'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="font-semibold text-white text-xs flex items-center gap-2">
                          <CheckCircle2 className="h-3.5 w-3.5 text-brand-400 shrink-0" />
                          <span>{dec.decision}</span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {dec.isUncertain && (
                            <Badge variant="warning" size="sm">
                              Uncertain / Drift
                            </Badge>
                          )}
                          <span className="font-mono text-[10px] text-slate-500">{dec.date}</span>
                        </div>
                      </div>

                      <p className="text-slate-300 text-[11px] leading-relaxed">
                        <strong className="text-slate-200 font-semibold">Rationale: </strong>
                        {dec.rationale}
                      </p>

                      <div className="pt-1.5 flex items-center justify-between text-[11px] text-brand-400">
                        <button
                          type="button"
                          onClick={() => handleOpenDecisionEvidence(dec)}
                          className="font-mono hover:text-brand-300 hover:underline flex items-center gap-1.5 cursor-pointer text-left"
                        >
                          <ShieldCheck className="h-3 w-3 text-brand-400" />
                          <span>Source: {dec.supportingSource}</span>
                          <span className="text-[10px] text-slate-500 font-sans">(Click to verify evidence)</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* SECTION C: TASKS AND OWNERSHIP */}
              <Card id="sec-tasks" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span className="h-5 w-5 rounded-md bg-brand-500/20 text-brand-400 text-xs flex items-center justify-center font-mono font-bold">
                      C
                    </span>
                    <span>Tasks & System Ownership</span>
                  </h3>
                  <Badge variant="neutral" size="sm">
                    {handover.tasks.length} Assigned Items
                  </Badge>
                </div>

                <div className="overflow-hidden rounded-xl border border-slate-800">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 uppercase text-[10px] font-mono">
                        <th className="px-4 py-2.5">Task Name</th>
                        <th className="px-4 py-2.5">Owner</th>
                        <th className="px-4 py-2.5">Priority</th>
                        <th className="px-4 py-2.5">Status</th>
                        <th className="px-4 py-2.5 text-right">Due Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {handover.tasks.map((tsk) => (
                        <tr key={tsk.id} className="hover:bg-slate-850/40">
                          <td className="px-4 py-3 font-medium text-white">{tsk.taskName}</td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5">
                              <img
                                src={tsk.assignedOwner.avatarUrl}
                                alt={tsk.assignedOwner.name}
                                className="h-4 w-4 rounded-full object-cover"
                              />
                              <span>{tsk.assignedOwner.name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <Badge
                              variant={
                                tsk.priority === 'critical'
                                  ? 'danger'
                                  : tsk.priority === 'high'
                                  ? 'warning'
                                  : 'neutral'
                              }
                              size="sm"
                            >
                              {tsk.priority}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 capitalize text-slate-400">
                            {tsk.status.replace('_', ' ')}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-slate-400">
                            {tsk.dueDate || 'TBD'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* SECTION D: BLOCKERS AND RISKS */}
              <Card id="sec-risks" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span className="h-5 w-5 rounded-md bg-amber-500/20 text-amber-400 text-xs flex items-center justify-center font-mono font-bold">
                      D
                    </span>
                    <span>Blockers & Operational Risks</span>
                  </h3>
                  <Badge variant="warning" size="sm">
                    {handover.blockersAndRisks.length} Risks Flagged
                  </Badge>
                </div>

                <div className="space-y-3">
                  {handover.blockersAndRisks.map((risk) => (
                    <div
                      key={risk.id}
                      className={`p-4 rounded-xl border text-xs space-y-2 ${
                        risk.severity === 'critical'
                          ? 'bg-rose-500/5 border-rose-500/30'
                          : risk.isUncertain
                          ? 'bg-amber-500/5 border-amber-500/30'
                          : 'bg-slate-900/60 border-slate-800'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-white flex items-center gap-2">
                          <AlertTriangle
                            className={`h-4 w-4 ${
                              risk.severity === 'critical' ? 'text-rose-400' : 'text-amber-400'
                            }`}
                          />
                          <span>{risk.description}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {risk.isUncertain && (
                            <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                              Tribal Knowledge
                            </span>
                          )}
                          <Badge
                            variant={risk.severity === 'critical' ? 'danger' : 'warning'}
                            size="sm"
                          >
                            {risk.severity.toUpperCase()}
                          </Badge>
                        </div>
                      </div>

                      <p className="text-slate-300 text-[11px] leading-relaxed">
                        <strong className="text-slate-200">Impact: </strong>
                        {risk.impact}
                      </p>

                      <div className="text-[11px] text-slate-400 font-mono">
                        Supporting Evidence: {risk.supportingEvidence}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* SECTION E: DEPENDENCIES */}
              <Card id="sec-dependencies" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span className="h-5 w-5 rounded-md bg-brand-500/20 text-brand-400 text-xs flex items-center justify-center font-mono font-bold">
                      E
                    </span>
                    <span>Cross-System Dependencies</span>
                  </h3>
                  <Badge variant="neutral" size="sm">
                    {handover.dependencies.length} Systems
                  </Badge>
                </div>

                <div className="space-y-2.5">
                  {handover.dependencies.map((dep) => (
                    <div
                      key={dep.id}
                      className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-white">{dep.dependency}</span>
                        <Badge variant="success" size="sm">
                          {dep.currentStatus}
                        </Badge>
                      </div>
                      <div className="text-slate-400 text-[11px]">
                        Related Task: <span className="text-slate-200">{dep.relatedTask}</span>
                      </div>
                      <div className="text-slate-500 text-[10px]">
                        Required Resource: {dep.requiredPersonOrResource}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* SECTION F: UNRESOLVED QUESTIONS */}
              <Card id="sec-questions" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span className="h-5 w-5 rounded-md bg-purple-500/20 text-purple-400 text-xs flex items-center justify-center font-mono font-bold">
                      F
                    </span>
                    <span>Unresolved Questions</span>
                  </h3>
                  <Badge variant="ai" size="sm">
                    {handover.unresolvedQuestions.length} Items To Confirm
                  </Badge>
                </div>

                <div className="space-y-3">
                  {handover.unresolvedQuestions.map((q) => (
                    <div
                      key={q.id}
                      className="p-4 rounded-xl bg-purple-500/5 border border-purple-500/20 text-xs space-y-2"
                    >
                      <div className="font-semibold text-white flex items-start gap-2">
                        <HelpCircle className="h-4 w-4 text-brand-accent shrink-0 mt-0.5" />
                        <span>{q.question}</span>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed">
                        <strong className="text-purple-300">Why It Matters: </strong>
                        {q.whyItMatters}
                      </p>
                      <div className="text-[11px] text-brand-300 font-mono">
                        Needs Confirmation From: {q.whoNeedsToConfirm}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* SECTION G: RECOMMENDED NEXT ACTIONS */}
              <Card id="sec-actions" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span className="h-5 w-5 rounded-md bg-emerald-500/20 text-emerald-400 text-xs flex items-center justify-center font-mono font-bold">
                      G
                    </span>
                    <span>Recommended Next Actions</span>
                  </h3>
                  <Badge variant="success" size="sm">
                    {handover.recommendedNextActions.length} Action Items
                  </Badge>
                </div>

                <div className="space-y-2.5">
                  {handover.recommendedNextActions.map((act) => (
                    <div
                      key={act.id}
                      className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs flex items-start justify-between gap-3"
                    >
                      <div className="space-y-1">
                        <div className="font-semibold text-white flex items-center gap-2">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                          <span>{act.action}</span>
                        </div>
                        <p className="text-slate-400 text-[11px]">{act.reason}</p>
                        {act.suggestedOwner && (
                          <div className="text-[10px] text-slate-500">
                            Suggested Owner: <span className="text-slate-300 font-medium">{act.suggestedOwner}</span>
                          </div>
                        )}
                      </div>

                      <Badge
                        variant={act.priority === 'high' ? 'danger' : 'neutral'}
                        size="sm"
                      >
                        {act.priority.toUpperCase()}
                      </Badge>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            {/* Right Column (4): STICKY EVIDENCE & CITATION PANEL */}
            <div id="sec-evidence" className="lg:col-span-4 sticky top-28 space-y-4">
              <Card className="bg-[#0B101D] border-brand-500/30 p-5 space-y-4 shadow-xl">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                      Evidence Index
                    </h3>
                  </div>
                  <Badge variant="ai" size="sm">
                    {handover.evidenceScore}% Verified
                  </Badge>
                </div>

                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Every decision, gotcha, and risk above is linked to raw verified source passages below.
                </p>

                {/* Evidence Citations List */}
                <div className="space-y-3 pt-1">
                  {handover.evidenceCitations.map((cite) => (
                    <div
                      key={cite.id}
                      onClick={() => handleOpenCitationEvidence(cite)}
                      className={`p-3 rounded-xl border text-xs space-y-1.5 transition-all cursor-pointer hover:scale-[1.01] ${
                        cite.isFlagged
                          ? 'bg-amber-500/10 border-amber-500/40 text-amber-200 hover:border-amber-400'
                          : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:border-brand-500/50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-white text-[11px] group-hover:text-brand-300">
                          {cite.title}
                        </span>
                        <span className="font-mono text-[10px] text-brand-400 bg-brand-500/10 px-1.5 py-0.5 rounded border border-brand-500/20">
                          {cite.confidence}% Match
                        </span>
                      </div>

                      <div className="font-mono text-[10px] text-slate-400 truncate flex items-center justify-between">
                        <span>File: {cite.sourceDocName}</span>
                        <span className="text-[10px] text-brand-400 font-sans hover:underline flex items-center gap-0.5">
                          Inspect &rarr;
                        </span>
                      </div>

                      <p className="text-[10px] font-mono leading-relaxed bg-slate-950/60 p-2 rounded border border-slate-800/80 text-slate-300">
                        "{cite.excerpt}"
                      </p>

                      {cite.isFlagged && (
                        <div className="flex items-center gap-1.5 text-[10px] text-amber-400 font-semibold pt-0.5">
                          <AlertTriangle className="h-3 w-3" />
                          <span>Flagged Contradiction Detected (Click to audit)</span>
                        </div>
                      )}

                      {cite.externalLink && (
                        <div
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-[10px] text-brand-400 hover:text-brand-300 font-semibold pt-1"
                        >
                          <a
                            href={cite.externalLink}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1"
                          >
                            <span>Inspect GitHub PR #412</span>
                            <ExternalLink className="h-2.5 w-2.5" />
                          </a>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
                  <span>FastAPI Endpoints Linked</span>
                  <span className="font-mono text-emerald-400">POST /api/v1/handovers</span>
                </div>
              </Card>
            </div>
          </div>
        </motion.div>
      )}

      {/* Overview Edit Modal */}
      <Modal
        isOpen={Boolean(editingSection === 'overview')}
        onClose={() => setEditingSection(null)}
        title="Edit Project Overview Section"
        description="Update project purpose or operational summary for this handover draft"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setEditingSection(null)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleSaveOverviewEdit}>
              Save Changes
            </Button>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-slate-300 mb-1">
              Project Purpose
            </label>
            <textarea
              rows={4}
              value={editedOverviewPurpose}
              onChange={(e) => setEditedOverviewPurpose(e.target.value)}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2.5 text-slate-200 text-xs"
            />
          </div>

          <div>
            <label className="block font-medium text-slate-300 mb-1">
              Current Status Summary
            </label>
            <textarea
              rows={4}
              value={editedOverviewStatus}
              onChange={(e) => setEditedOverviewStatus(e.target.value)}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2.5 text-slate-200 text-xs"
            />
          </div>
        </div>
      </Modal>

      {/* Reusable Primary Evidence Drawer */}
      <EvidenceDrawer
        isOpen={isEvidenceDrawerOpen}
        onClose={() => {
          setIsEvidenceDrawerOpen(false);
          setSelectedDrawerClaim(null);
        }}
        claim={selectedDrawerClaim}
        onVerify={async (clm) => {
          await verificationService.verifyClaim(clm.id, {
            id: 'u-1',
            name: 'Elena Rostova',
            role: 'Lead Engineer',
          });
          const updated = await verificationService.getClaimById(clm.id);
          setSelectedDrawerClaim(updated);
        }}
        onFlag={async (clm) => {
          await verificationService.flagClaim(
            clm.id,
            { id: 'u-1', name: 'Elena Rostova' },
            'Flagged during handover generation preview'
          );
          const updated = await verificationService.getClaimById(clm.id);
          setSelectedDrawerClaim(updated);
        }}
        onOpenConflict={(conflictId) => {
          setIsEvidenceDrawerOpen(false);
          navigate(`/conflicts`);
        }}
      />
    </div>
  );
};

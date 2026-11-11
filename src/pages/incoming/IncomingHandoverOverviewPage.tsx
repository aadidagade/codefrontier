import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Printer,
  Download,
  ShieldCheck,
  Calendar,
  User,
  GitBranch,
  Flame,
  AlertTriangle,
  HelpCircle,
  Sparkles,
  FileText,
  ListTodo,
  ExternalLink,
  ChevronRight,
  Send,
  MessageSquare,
} from 'lucide-react';
import { incomingService } from '../../services/incomingService';
import { IncomingHandoverPackage } from '../../types/incoming';
import { VerificationClaim } from '../../types/verification';
import { verificationService } from '../../services/verificationService';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { Textarea } from '../../components/common/Textarea';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { cn } from '../../utils/cn';

import { ContinuationTracker } from '../../components/incoming/ContinuationTracker';
import { AcknowledgementModal } from '../../components/incoming/AcknowledgementModal';
import { HandoverPrintableView } from '../../components/incoming/HandoverPrintableView';
import { EvidenceDrawer } from '../../components/verification/EvidenceDrawer';

export const IncomingHandoverOverviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, info } = useToast();

  const [packageData, setPackageData] = useState<IncomingHandoverPackage | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'all' | 'intro' | 'decisions' | 'tasks' | 'blockers' | 'deps' | 'actions' | 'questions'>('all');

  // Modals & Drawers
  const [isAckModalOpen, setIsAckModalOpen] = useState(false);
  const [isPrintViewOpen, setIsPrintViewOpen] = useState(false);

  // Evidence Drawer
  const [selectedDrawerClaim, setSelectedDrawerClaim] = useState<VerificationClaim | null>(null);
  const [isEvidenceDrawerOpen, setIsEvidenceDrawerOpen] = useState(false);

  // Ask question / Clarification state
  const [questionInput, setQuestionInput] = useState<{ [qId: string]: string }>({});

  const loadData = async () => {
    setLoading(true);
    try {
      const targetId = id || 'inc-auth-zero';
      const record = await incomingService.getIncomingHandoverById(targetId);
      if (record) {
        setPackageData(record);
      } else {
        const all = await incomingService.getMyIncomingHandovers();
        if (all.length > 0) setPackageData(all[0]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  if (loading || !packageData) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          <span className="text-xs text-slate-400">Loading Handover Overview...</span>
        </div>
      </div>
    );
  }

  // If printable view requested
  if (isPrintViewOpen) {
    return (
      <HandoverPrintableView
        packageData={packageData}
        onClose={() => setIsPrintViewOpen(false)}
      />
    );
  }

  // Acknowledgement confirmation
  const handleConfirmAcknowledgement = async (comment: string) => {
    const ackUser = user || {
      id: 'u-1',
      name: 'Elena Rostova',
      role: 'lead_engineer',
      email: 'elena.r@acme.corp',
    };
    const updated = await incomingService.acknowledgeHandover(packageData.id, ackUser, comment);
    setPackageData(updated);
    success(
      'Handover Receipt Formally Acknowledged!',
      `Lead ${packageData.projectLead.name} has been notified in the activity feed.`
    );
  };

  // Task Status update
  const handleUpdateTaskStatus = async (
    taskId: string,
    status: 'pending' | 'in_progress' | 'completed'
  ) => {
    const updated = await incomingService.updateTaskStatus(packageData.id, taskId, status);
    setPackageData(updated);
  };

  // Task Progress Note add
  const handleAddTaskProgressNote = async (taskId: string, text: string, author: string) => {
    const updated = await incomingService.addTaskProgressNote(packageData.id, taskId, text, author);
    setPackageData(updated);
  };

  // Resolve question
  const handleResolveQuestion = async (qId: string) => {
    const answer = questionInput[qId]?.trim();
    if (!answer) return;

    const updated = await incomingService.resolveOpenQuestion(packageData.id, qId, answer);
    setPackageData(updated);
    setQuestionInput((prev) => ({ ...prev, [qId]: '' }));
    success('Question Updated', 'Clarification recorded on project handover.');
  };

  // Inspect source evidence
  const handleOpenEvidence = async (docName: string, snippet?: string, title?: string) => {
    const claims = await verificationService.getClaims();
    const matched = claims.find((c) => c.sourceDocName === docName || (title && c.claimText.includes(title.slice(0, 20))));
    if (matched) {
      setSelectedDrawerClaim(matched);
    } else {
      setSelectedDrawerClaim({
        id: `ev-${Date.now()}`,
        projectId: packageData.projectId,
        projectKey: packageData.projectKey,
        projectName: packageData.projectName,
        section: 'decisions',
        claimText: title || 'Approved Handover Statement',
        sourceDocId: 'doc-1',
        sourceDocName: docName,
        sourceDocType: 'pdf',
        pageOrSection: 'Primary Architecture Reference',
        evidenceSnippet: snippet || 'Verifiable architectural rationale.',
        evidenceStatus: 'supported',
        uncertaintyFlags: [],
        confidenceScore: 97,
        isSyntheticModelOutput: true,
        verificationStatus: 'verified',
        createdAt: new Date().toISOString(),
      });
    }
    setIsEvidenceDrawerOpen(true);
  };

  const isAck = packageData.acknowledgementStatus === 'acknowledged';

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/my-handovers')}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-mono transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back to My Handovers
            </button>
            <span className="text-slate-600">·</span>
            <span className="font-mono text-xs font-bold text-brand-400">
              {packageData.projectKey}
            </span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              {packageData.version}
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            {packageData.projectName}
          </h1>

          <p className="text-xs text-slate-400">
            Transferred by <strong className="text-slate-200">{packageData.outgoingMember.name}</strong> · Approved by{' '}
            <strong className="text-slate-200">{packageData.approvedBy.name}</strong> on{' '}
            {new Date(packageData.approvedDate).toLocaleDateString()}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsPrintViewOpen(true)}
            leftIcon={<Printer className="h-4 w-4" />}
            className="text-xs"
          >
            Export / Print PDF
          </Button>

          {!isAck ? (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsAckModalOpen(true)}
              leftIcon={<CheckCircle2 className="h-4 w-4" />}
              className="text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              Acknowledge Receipt
            </Button>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-xs text-emerald-400 font-semibold font-mono">
              <CheckCircle2 className="h-4 w-4" />
              <span>Receipt Acknowledged</span>
            </div>
          )}
        </div>
      </div>

      {/* Acknowledgement Status Callout Banner */}
      {isAck ? (
        <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-emerald-300">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="h-5 w-5 text-emerald-400 shrink-0" />
            <div>
              <strong>Receipt Acknowledged by You on {new Date(packageData.acknowledgedAt || '').toLocaleDateString()}</strong>
              {packageData.acknowledgementComment && (
                <p className="text-[11px] text-emerald-200/80 italic mt-0.5">
                  "{packageData.acknowledgementComment}"
                </p>
              )}
            </div>
          </div>
          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded">
            Project Lead Notified
          </span>
        </div>
      ) : (
        <div className="p-4 rounded-xl bg-gradient-to-r from-amber-950/40 via-slate-900 to-brand-950/30 border border-amber-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
          <div className="space-y-1">
            <div className="flex items-center gap-2 font-bold text-amber-300">
              <Clock className="h-4 w-4" />
              <span>Action Required: Acknowledge Handover Receipt</span>
            </div>
            <p className="text-slate-300 text-[11px] leading-relaxed max-w-2xl">
              Please inspect the project architecture, decisions, continuation tasks, and on-call escalation procedures below. Acknowledging confirms that you have reviewed the handoff package.
            </p>
          </div>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsAckModalOpen(true)}
            leftIcon={<CheckCircle2 className="h-4 w-4" />}
            className="text-xs shrink-0 bg-emerald-600 hover:bg-emerald-500 text-white"
          >
            Acknowledge Receipt
          </Button>
        </div>
      )}

      {/* Navigation Quick Anchors */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-slate-800 text-xs">
        <a href="#sec-intro" className="px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 whitespace-nowrap">
          A. Introduction
        </a>
        <a href="#sec-decisions" className="px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 whitespace-nowrap">
          B. Decisions (ADRs)
        </a>
        <a href="#sec-tasks" className="px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 whitespace-nowrap">
          C. Responsibilities ({packageData.responsibilities.length})
        </a>
        <a href="#sec-blockers" className="px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 whitespace-nowrap">
          D. Blockers ({packageData.blockers.length})
        </a>
        <a href="#sec-dependencies" className="px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 whitespace-nowrap">
          E. Dependencies
        </a>
        <a href="#sec-actions" className="px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 whitespace-nowrap">
          F. Starting Actions
        </a>
        <a href="#sec-questions" className="px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 whitespace-nowrap">
          G. Open Questions
        </a>
      </div>

      {/* SECTION A: PROJECT INTRODUCTION */}
      <Card id="sec-intro" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center font-mono font-bold text-xs">
              A
            </div>
            <h2 className="text-base font-bold text-white tracking-tight">
              Project Introduction & Scope
            </h2>
          </div>
          <Badge variant="success" size="sm">
            {packageData.introduction.healthScore}% Certified Health Score
          </Badge>
        </div>

        <div className="space-y-3 text-xs">
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
            <span className="text-[10px] uppercase font-mono font-bold text-slate-400">
              What The Project Does (Mission)
            </span>
            <p className="text-slate-200 text-sm leading-relaxed">
              {packageData.introduction.purpose}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
            <span className="text-[10px] uppercase font-mono font-bold text-slate-400">
              Core Deliverables & Objectives
            </span>
            <ul className="space-y-1.5 list-disc list-inside text-slate-300 text-xs">
              {packageData.introduction.objectives.map((obj, i) => (
                <li key={i}>{obj}</li>
              ))}
            </ul>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400 block text-[10px] font-mono">DEVELOPMENT STAGE</span>
              <strong className="text-white text-xs">{packageData.introduction.currentStage}</strong>
            </div>
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400 block text-[10px] font-mono">OVERALL STATUS</span>
              <strong className="text-emerald-400 text-xs">{packageData.introduction.overallStatus}</strong>
            </div>
          </div>
        </div>
      </Card>

      {/* SECTION B: IMPORTANT DECISIONS */}
      <Card id="sec-decisions" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center font-mono font-bold text-xs">
              B
            </div>
            <h2 className="text-base font-bold text-white tracking-tight">
              Important Architecture Decisions (ADRs)
            </h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {packageData.decisions.length} Decisions Documented
          </span>
        </div>

        <div className="space-y-3">
          {packageData.decisions.map((dec) => (
            <div
              key={dec.id}
              className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2 text-xs"
            >
              <div className="flex items-start justify-between gap-2">
                <h4 className="font-semibold text-white text-xs">{dec.decision}</h4>
                <span className="font-mono text-[10px] text-slate-500">{dec.date}</span>
              </div>

              <p className="text-slate-300 leading-relaxed text-[11px]">
                <strong className="text-slate-200">Rationale: </strong>
                {dec.rationale}
              </p>

              <div className="pt-1.5 flex items-center justify-between text-[11px]">
                <button
                  type="button"
                  onClick={() => handleOpenEvidence(dec.supportingSource, dec.sourceSnippet, dec.decision)}
                  className="font-mono text-brand-400 hover:text-brand-300 hover:underline flex items-center gap-1.5"
                >
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Source: {dec.supportingSource}</span>
                  <span className="text-[10px] text-slate-500 font-sans">(Click to verify evidence)</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* SECTION C: YOUR RESPONSIBILITIES (CONTINUATION TRACKER) */}
      <Card id="sec-tasks" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-mono font-bold text-xs">
              C
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">
                Your Responsibilities & Continuation Tracker
              </h2>
              <p className="text-[11px] text-slate-400">
                Tasks assigned to you. Update status, mark complete, and record audit notes as you execute.
              </p>
            </div>
          </div>
          <Badge variant="neutral" size="sm">
            {packageData.responsibilities.length} Tasks
          </Badge>
        </div>

        <ContinuationTracker
          tasks={packageData.responsibilities}
          onUpdateStatus={handleUpdateTaskStatus}
          onAddProgressNote={handleAddTaskProgressNote}
        />
      </Card>

      {/* SECTION D: CURRENT BLOCKERS */}
      {packageData.blockers.length > 0 && (
        <Card id="sec-blockers" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="h-7 w-7 rounded-lg bg-red-500/10 text-red-400 flex items-center justify-center font-mono font-bold text-xs">
                D
              </div>
              <h2 className="text-base font-bold text-white tracking-tight">
                Current Operational Blockers
              </h2>
            </div>
            <Badge variant="danger" size="sm">
              {packageData.blockers.length} Active
            </Badge>
          </div>

          <div className="space-y-3">
            {packageData.blockers.map((blk) => (
              <div
                key={blk.id}
                className="p-4 rounded-xl bg-red-950/20 border border-red-500/30 text-xs space-y-2"
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-red-200">{blk.description}</h4>
                  <Badge variant="danger" size="sm">
                    {blk.severity.toUpperCase()}
                  </Badge>
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  <strong className="text-red-300">Impact: </strong>
                  {blk.impact}
                </p>
                <div className="pt-1 p-2 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-brand-300">
                  <strong>Suggested Follow-up: </strong>
                  {blk.suggestedFollowUp}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* SECTION E: PROJECT DEPENDENCIES */}
      <Card id="sec-dependencies" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center font-mono font-bold text-xs">
              E
            </div>
            <h2 className="text-base font-bold text-white tracking-tight">
              Project Dependencies & Resources
            </h2>
          </div>
          <Badge variant="ai" size="sm">
            {packageData.dependencies.length} Prerequisites
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {packageData.dependencies.map((dep) => (
            <div
              key={dep.id}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2"
            >
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-white">{dep.dependency}</h4>
                <Badge variant="success" size="sm">
                  {dep.currentStatus}
                </Badge>
              </div>
              <div className="text-[11px] text-slate-400">
                Prerequisite for: <span className="text-slate-200 font-medium">{dep.prerequisiteTask}</span>
              </div>
              <div className="text-[11px] text-slate-400 font-mono">
                Required Resource: {dep.requiredPersonOrResource}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* SECTION F: RECOMMENDED STARTING ACTIONS */}
      <Card id="sec-actions" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-mono font-bold text-xs">
              F
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">
                Recommended Starting Actions
              </h2>
              <p className="text-[11px] text-slate-400">
                Prioritized Day 1 through Week 1 onboarding trajectory curated by outgoing lead
              </p>
            </div>
          </div>
          <Badge variant="success" size="sm">
            Action Plan
          </Badge>
        </div>

        <div className="space-y-2.5">
          {packageData.recommendedStartingActions.map((act) => (
            <div
              key={act.id}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start gap-3.5 text-xs"
            >
              <span className="font-mono text-[10px] font-bold text-brand-300 bg-brand-500/10 px-2.5 py-1 rounded border border-brand-500/20 shrink-0">
                {act.timeframe}
              </span>
              <div className="space-y-1">
                <h4 className="font-semibold text-white">{act.action}</h4>
                <p className="text-slate-400 text-[11px] leading-relaxed">{act.reason}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* SECTION G: OPEN QUESTIONS */}
      <Card id="sec-questions" className="bg-[#0F172A] border-slate-800 p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center font-mono font-bold text-xs">
              G
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">
                Open Questions & Clarifications
              </h2>
              <p className="text-[11px] text-slate-400">
                Unresolved questions flagged for project lead or previous member confirmation
              </p>
            </div>
          </div>
          <Badge variant="warning" size="sm">
            {packageData.openQuestions.length} Items
          </Badge>
        </div>

        <div className="space-y-3">
          {packageData.openQuestions.map((oq) => (
            <div
              key={oq.id}
              className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="font-semibold text-amber-200 flex items-start gap-2">
                  <HelpCircle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>{oq.question}</span>
                </div>
                {oq.status === 'clarified' && (
                  <Badge variant="success" size="sm">
                    Clarified
                  </Badge>
                )}
              </div>

              <p className="text-slate-300 text-[11px] leading-relaxed pl-6">
                <strong>Why It Matters: </strong>
                {oq.whyItMatters}
              </p>

              <div className="pl-6 text-[10px] text-amber-300 font-mono">
                Confirmation Required From: {oq.whoNeedsToConfirm}
              </div>

              {oq.clarificationResponse && (
                <div className="ml-6 p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/25 text-emerald-200 text-[11px]">
                  <strong>Clarification: </strong>
                  {oq.clarificationResponse}
                </div>
              )}

              {/* Clarification input */}
              <div className="pl-6 pt-1 flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Record clarification or note from lead..."
                  value={questionInput[oq.id] || ''}
                  onChange={(e) => setQuestionInput((prev) => ({ ...prev, [oq.id]: e.target.value }))}
                  className="flex-1 rounded-lg bg-slate-900 border border-slate-700/80 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleResolveQuestion(oq.id)}
                  disabled={!questionInput[oq.id]?.trim()}
                  className="h-8 text-xs"
                >
                  Save Answer
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* ACKNOWLEDGEMENT MODAL */}
      <AcknowledgementModal
        isOpen={isAckModalOpen}
        onClose={() => setIsAckModalOpen(false)}
        handoverPackage={packageData}
        onConfirm={handleConfirmAcknowledgement}
      />

      {/* EVIDENCE DRAWER */}
      <EvidenceDrawer
        isOpen={isEvidenceDrawerOpen}
        onClose={() => {
          setIsEvidenceDrawerOpen(false);
          setSelectedDrawerClaim(null);
        }}
        claim={selectedDrawerClaim}
      />
    </div>
  );
};

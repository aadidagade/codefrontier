import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ShieldCheck,
  Lock,
  GitBranch,
  Edit3,
  MessageSquare,
  FileText,
  RotateCcw,
  Sparkles,
  Share2,
  ExternalLink,
  Save,
  Check,
  HelpCircle,
  Users,
  Layers,
  ChevronRight,
  Flame,
} from 'lucide-react';
import { reviewService } from '../../services/reviewService';
import {
  HandoverReviewRecord,
  SectionKey,
  SectionReviewStatus,
} from '../../types/review';
import { VerificationClaim } from '../../types/verification';
import { verificationService } from '../../services/verificationService';
import { incomingService } from '../../services/incomingService';
import { notificationService } from '../../services/notificationService';
import { useRole } from '../../context/RoleContext';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { Textarea } from '../../components/common/Textarea';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../hooks/useAuth';
import { mockCurrentUser } from '../../data/mockData';
import { cn } from '../../utils/cn';

import { FinalApprovalChecklist } from '../../components/review/FinalApprovalChecklist';
import { ApprovalConfirmationModal } from '../../components/review/ApprovalConfirmationModal';
import { RequestChangesModal } from '../../components/review/RequestChangesModal';
import { SectionContentEditorModal } from '../../components/review/SectionContentEditorModal';
import { EvidenceDrawer } from '../../components/verification/EvidenceDrawer';

export const HandoverReviewWorkspacePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { setRole } = useRole();
  const { success, info, warning } = useToast();

  const [handover, setHandover] = useState<HandoverReviewRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<SectionKey>('overview');

  // Comment state
  const [commentText, setCommentText] = useState('');
  const [isPostingComment, setIsPostingComment] = useState(false);

  // Modals state
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [requestChangesMode, setRequestChangesMode] = useState<'changes' | 'reject' | null>(null);
  const [isEditorModalOpen, setIsEditorModalOpen] = useState(false);

  // Evidence Drawer state
  const [selectedDrawerClaim, setSelectedDrawerClaim] = useState<VerificationClaim | null>(null);
  const [isEvidenceDrawerOpen, setIsEvidenceDrawerOpen] = useState(false);

  // Show checklist toggle
  const [showChecklist, setShowChecklist] = useState(false);

  // Load handover
  const loadHandover = async () => {
    setLoading(true);
    try {
      const targetId = id || 'rev-auth-zero';
      const record = await reviewService.getHandoverById(targetId);
      if (record) {
        setHandover(record);
      } else {
        const all = await reviewService.getAllHandovers();
        if (all.length > 0) setHandover(all[0]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHandover();
  }, [id]);

  if (loading || !handover) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          <span className="text-xs text-slate-400">Loading Handover Review Workspace...</span>
        </div>
      </div>
    );
  }

  // Section list configuration
  const sectionList: { key: SectionKey; title: string; icon: React.ElementType }[] = [
    { key: 'overview', title: 'Project Overview', icon: FileText },
    { key: 'decisions', title: 'Decisions (ADRs)', icon: CheckCircle2 },
    { key: 'tasks', title: 'Tasks & Sprints', icon: Layers },
    { key: 'ownership', title: 'Service Ownership', icon: Users },
    { key: 'blockers', title: 'Blockers', icon: Flame },
    { key: 'risks', title: 'Operational Risks', icon: AlertTriangle },
    { key: 'dependencies', title: 'Dependencies', icon: GitBranch },
    { key: 'open_questions', title: 'Open Questions', icon: HelpCircle },
    { key: 'next_actions', title: 'Next Actions', icon: ArrowLeft },
  ];

  const sectionsArray = Object.values(handover.sections);
  const approvedSectionsCount = sectionsArray.filter((s) => s.status === 'approved').length;
  const currentSectionItem = handover.sections[activeSection];
  const activeComments = handover.comments.filter((c) => c.sectionKey === activeSection);

  // Section status actions
  const handleSetSectionStatus = async (status: SectionReviewStatus, note?: string) => {
    if (handover.isLocked) {
      warning('Handover Locked', 'This handover has been approved and certified. Ordinary edits are disabled.');
      return;
    }

    const reviewer = user || mockCurrentUser;

    const updated = await reviewService.updateSectionStatus(
      handover.id,
      activeSection,
      status,
      reviewer,
      note
    );
    setHandover(updated);
    success(
      `Section ${status === 'approved' ? 'Approved' : 'Updated'}`,
      `${handover.sections[activeSection].title} marked as ${status.replace('_', ' ')}.`
    );
  };

  // Add Comment
  const handleAddComment = async () => {
    if (!commentText.trim()) return;
    setIsPostingComment(true);
    try {
      const author = user || mockCurrentUser;
      const updated = await reviewService.addComment(
        handover.id,
        activeSection,
        author,
        commentText.trim()
      );
      setHandover(updated);
      setCommentText('');
      info('Comment Added', 'Your feedback was logged in the reviewer thread.');
    } finally {
      setIsPostingComment(false);
    }
  };

  // Final Approval
  const handleConfirmFinalApproval = async (notes: string) => {
    const approver = user || mockCurrentUser;
    const updated = await reviewService.approveHandover(handover.id, approver, notes);
    setHandover(updated);

    // Sync into Incoming Member Handover Portal
    await incomingService.publishApprovedHandover(updated, approver);
    notificationService.triggerSampleNotification('handover_approved');
    notificationService.triggerSampleNotification('new_handover_received');

    success(
      'Handover Formally Approved & Shared!',
      'All sections signed off. Handover package published to incoming successor portal.'
    );
  };

  // Request changes or reject
  const handleConfirmChangesOrReject = async (reason: string) => {
    const reviewer = user || mockCurrentUser;

    let updated: HandoverReviewRecord;
    if (requestChangesMode === 'reject') {
      updated = await reviewService.rejectHandover(handover.id, reviewer, reason);
      info('Handover Rejected', 'Outgoing lead has been notified to regenerate draft.');
    } else {
      updated = await reviewService.requestChanges(handover.id, reviewer, reason);
      info('Changes Requested', 'Feedback notes logged for outgoing lead.');
    }
    setHandover(updated);
  };

  // Fork new revision
  const handleForkNewRevision = async () => {
    const creator = user || mockCurrentUser;
    const newDraft = await reviewService.createRevision(handover.id, creator);
    success(
      'New Revision Created',
      `Forked Version ${newDraft.version} draft. You can now make updates.`
    );
    navigate(`/review/${newDraft.id}`);
  };

  // Open Evidence Drawer for a snippet
  const handleOpenEvidence = async (docName: string, snippet: string, claimTitle: string) => {
    const allClaims = await verificationService.getClaims();
    const matched = allClaims.find(
      (c) => c.sourceDocName === docName || c.claimText.includes(claimTitle.slice(0, 20))
    );
    if (matched) {
      setSelectedDrawerClaim(matched);
    } else {
      setSelectedDrawerClaim({
        id: `ev-${Date.now()}`,
        projectId: handover.projectId,
        projectKey: handover.projectKey,
        projectName: handover.projectName,
        section: 'decisions',
        claimText: claimTitle,
        sourceDocId: 'doc-1',
        sourceDocName: docName,
        sourceDocType: 'pdf',
        pageOrSection: 'Referenced Document Section',
        evidenceSnippet: snippet,
        evidenceStatus: 'supported',
        uncertaintyFlags: [],
        confidenceScore: 95,
        isSyntheticModelOutput: true,
        verificationStatus: 'unverified',
        createdAt: new Date().toISOString(),
      });
    }
    setIsEvidenceDrawerOpen(true);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Breadcrumb & Global Action Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/review')}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-mono transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back to Review Desk
            </button>
            <span className="text-slate-600">·</span>
            <span className="font-mono text-xs font-bold text-brand-400">
              {handover.projectKey}
            </span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              {handover.version}
            </span>
          </div>

          <h1 className="text-2xl font-bold text-white tracking-tight">
            {handover.projectName}
          </h1>

          <p className="text-xs text-slate-400">
            Outgoing Lead: <strong className="text-slate-200">{handover.outgoingMember.name}</strong> &rarr; Incoming Successor:{' '}
            <strong className="text-brand-300">{handover.incomingMember.name}</strong>
          </p>
        </div>

        {/* Global Review Actions Bar */}
        <div className="flex flex-wrap items-center gap-2.5">
          {handover.isLocked ? (
            <>
              <Badge variant="success" size="md" dot>
                Approved & Locked
              </Badge>
              <Button
                variant="outline"
                size="sm"
                onClick={handleForkNewRevision}
                leftIcon={<GitBranch className="h-4 w-4 text-brand-400" />}
                className="text-xs font-semibold"
              >
                Fork New Revision (v1.{handover.revisionNumber})
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  reviewService.saveDraft(handover.id, {});
                  success('Draft Saved', 'Your section approvals and notes are saved locally.');
                }}
                leftIcon={<Save className="h-4 w-4" />}
                className="text-xs text-slate-300"
              >
                Save Draft
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setRequestChangesMode('changes')}
                leftIcon={<RotateCcw className="h-4 w-4 text-amber-400" />}
                className="text-xs border-slate-700"
              >
                Request Changes
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => setRequestChangesMode('reject')}
                leftIcon={<XCircle className="h-4 w-4 text-rose-400" />}
                className="text-xs text-slate-400 hover:text-rose-400"
              >
                Reject
              </Button>

              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsApprovalModalOpen(true)}
                leftIcon={<ShieldCheck className="h-4 w-4" />}
                className="text-xs font-semibold"
              >
                Approve and Share
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Locked Handover Banner (if approved) */}
      {handover.isLocked && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-xs text-emerald-300">
          <div className="flex items-center gap-2.5">
            <Lock className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>
              <strong>Immutable Certified Version:</strong> Approved by{' '}
              <strong>{handover.approvedBy?.name || 'Sarah Jenkins'}</strong> on{' '}
              {new Date(handover.approvedAt || handover.lastUpdated).toLocaleDateString()}. Ordinary edits are disabled to protect audit compliance.
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setRole('incoming_member');
                navigate(`/my-handovers/inc-${handover.id}`);
              }}
              leftIcon={<Sparkles className="h-3.5 w-3.5 text-brand-400" />}
              className="text-xs h-7 text-white border-emerald-500/40 hover:bg-emerald-500/10"
            >
              View as Successor &rarr;
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleForkNewRevision}
              className="text-xs h-7 text-emerald-300 hover:text-white"
            >
              Create Next Revision &rarr;
            </Button>
          </div>
        </div>
      )}

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: Section Navigation (4 cols) */}
        <div className="lg:col-span-4 space-y-4 lg:sticky lg:top-24">
          <Card className="bg-[#0B101D] border-slate-800 p-4 space-y-4 shadow-xl">
            {/* Navigation Header & Progress */}
            <div className="pb-3 border-b border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono font-bold text-slate-300 uppercase tracking-wider text-[11px]">
                  Review Navigation
                </span>
                <span className="font-mono font-bold text-brand-300">
                  {approvedSectionsCount} of {sectionList.length} Approved
                </span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-500 to-emerald-400 transition-all duration-300"
                  style={{
                    width: `${Math.round((approvedSectionsCount / sectionList.length) * 100)}%`,
                  }}
                />
              </div>
            </div>

            {/* Section Links */}
            <div className="space-y-1">
              {sectionList.map((sec) => {
                const sectionData = handover.sections[sec.key];
                const isActive = activeSection === sec.key;
                const Icon = sec.icon;

                return (
                  <button
                    key={sec.key}
                    type="button"
                    onClick={() => setActiveSection(sec.key)}
                    className={cn(
                      'w-full flex items-center justify-between p-2.5 rounded-xl text-xs transition-all text-left select-none',
                      isActive
                        ? 'bg-brand-500/15 text-white border border-brand-500/40 font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                    )}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Icon className={cn('h-4 w-4 shrink-0', isActive ? 'text-brand-400' : 'text-slate-500')} />
                      <span className="truncate">{sec.title}</span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {sectionData?.commentCount > 0 && (
                        <span className="flex items-center gap-0.5 text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.2 rounded">
                          <MessageSquare className="h-2.5 w-2.5" />
                          {sectionData.commentCount}
                        </span>
                      )}

                      {sectionData?.status === 'approved' && (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      )}
                      {sectionData?.status === 'changes_requested' && (
                        <AlertTriangle className="h-4 w-4 text-amber-400" />
                      )}
                      {sectionData?.status === 'rejected' && (
                        <XCircle className="h-4 w-4 text-rose-400" />
                      )}
                      {sectionData?.status === 'pending' && (
                        <Clock className="h-3.5 w-3.5 text-slate-600" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Final Approval Checklist Summary Toggle */}
            <div className="pt-2 border-t border-slate-800">
              <Button
                variant={showChecklist ? 'primary' : 'outline'}
                size="sm"
                onClick={() => setShowChecklist(!showChecklist)}
                className="w-full text-xs justify-between"
                leftIcon={<ShieldCheck className="h-4 w-4" />}
                rightIcon={<ChevronRight className={cn('h-3.5 w-3.5 transition-transform', showChecklist && 'rotate-90')} />}
              >
                Approval Governance Checklist
              </Button>
            </div>
          </Card>
        </div>

        {/* RIGHT COLUMN: Selected Section Content & Review Controls (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Collapsible Final Approval Checklist */}
          {showChecklist && (
            <FinalApprovalChecklist
              handover={handover}
              onNavigateToSection={(target) => {
                setActiveSection(target);
                setShowChecklist(false);
              }}
            />
          )}

          {/* Section Review Header Card */}
          <Card className="bg-[#0F172A] border-slate-800 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs uppercase text-slate-400">Section Review</span>
                  {currentSectionItem?.status === 'approved' ? (
                    <Badge variant="success" size="sm" dot>
                      Section Approved
                    </Badge>
                  ) : currentSectionItem?.status === 'changes_requested' ? (
                    <Badge variant="accent" size="sm" dot>
                      Changes Requested
                    </Badge>
                  ) : currentSectionItem?.status === 'rejected' ? (
                    <Badge variant="danger" size="sm" dot>
                      Section Rejected
                    </Badge>
                  ) : (
                    <Badge variant="warning" size="sm" dot>
                      Pending Review
                    </Badge>
                  )}
                  {currentSectionItem?.isEdited && (
                    <span className="text-[10px] font-mono text-brand-300 bg-brand-500/10 px-1.5 py-0.5 rounded border border-brand-500/20">
                      Edited
                    </span>
                  )}
                </div>

                <h2 className="text-xl font-bold text-white tracking-tight mt-1">
                  {currentSectionItem?.title || 'Section Review'}
                </h2>
              </div>

              {/* Section-Level Review Actions */}
              {!handover.isLocked && (
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsEditorModalOpen(true)}
                    leftIcon={<Edit3 className="h-3.5 w-3.5" />}
                    className="text-xs h-8"
                  >
                    Edit
                  </Button>

                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleSetSectionStatus('approved')}
                    leftIcon={<Check className="h-3.5 w-3.5" />}
                    className="text-xs h-8 bg-emerald-600 hover:bg-emerald-500 text-white"
                  >
                    Approve
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSetSectionStatus('changes_requested', 'Reviewer requested changes')}
                    className="text-xs h-8 text-amber-400 hover:bg-amber-500/10"
                  >
                    Changes Req.
                  </Button>
                </div>
              )}
            </div>

            {/* Section Review Metadata if reviewed */}
            {currentSectionItem?.reviewedBy && (
              <div className="text-[11px] text-slate-400 flex items-center justify-between bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                <span>
                  Reviewed by: <strong className="text-white">{currentSectionItem.reviewedBy.name}</strong>
                </span>
                <span className="font-mono">
                  {new Date(currentSectionItem.reviewedAt || '').toLocaleString()}
                </span>
              </div>
            )}

            {/* DYNAMIC SECTION CONTENT RENDERER */}
            <div className="pt-2">
              {activeSection === 'overview' && (
                <div className="space-y-4 text-xs">
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5">
                    <span className="text-slate-400 font-mono text-[10px] uppercase font-bold">
                      Project Purpose & Mission
                    </span>
                    <p className="text-slate-200 text-sm leading-relaxed">
                      {handover.content.overview?.purpose}
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5">
                    <span className="text-slate-400 font-mono text-[10px] uppercase font-bold">
                      Current Operational Status
                    </span>
                    <p className="text-slate-200 leading-relaxed">
                      {handover.content.overview?.currentStatus}
                    </p>
                  </div>
                </div>
              )}

              {activeSection === 'decisions' && (
                <div className="space-y-3 text-xs">
                  {handover.content.decisions?.map((dec) => (
                    <div
                      key={dec.id}
                      className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-semibold text-white text-xs">{dec.decision}</h4>
                        <span className="font-mono text-[10px] text-slate-500">{dec.date}</span>
                      </div>
                      <p className="text-slate-300 leading-relaxed">
                        <strong className="text-slate-200">Rationale: </strong>
                        {dec.rationale}
                      </p>
                      <div className="pt-1.5 flex items-center justify-between text-[11px]">
                        <button
                          type="button"
                          onClick={() => handleOpenEvidence(dec.supportingSource, dec.rationale, dec.decision)}
                          className="font-mono text-brand-400 hover:text-brand-300 hover:underline flex items-center gap-1.5"
                        >
                          <ShieldCheck className="h-3.5 w-3.5" />
                          <span>Source: {dec.supportingSource}</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeSection === 'tasks' && (
                <div className="space-y-3 text-xs">
                  {handover.content.tasks?.map((tsk) => (
                    <div
                      key={tsk.id}
                      className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between gap-3"
                    >
                      <div className="space-y-0.5">
                        <div className="font-semibold text-white">{tsk.taskName}</div>
                        <div className="text-[11px] text-slate-400">
                          Assigned: <span className="text-slate-200">{tsk.assignedOwner.name}</span> · Status: {tsk.status}
                        </div>
                      </div>
                      <Badge variant={tsk.priority === 'critical' ? 'danger' : 'neutral'} size="sm">
                        {tsk.priority}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}

              {activeSection === 'ownership' && (
                <div className="space-y-3 text-xs">
                  {handover.content.ownership?.map((own) => (
                    <div
                      key={own.id}
                      className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <h4 className="font-semibold text-white text-xs">{own.serviceName}</h4>
                        <Badge variant="success" size="sm">
                          {own.status}
                        </Badge>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-300">
                        <div>Primary Lead: <strong>{own.primaryLead.name}</strong></div>
                        <div>Secondary On-Call: <strong>{own.secondaryOnCall.name}</strong></div>
                      </div>
                      <p className="text-[11px] text-slate-400 font-mono pt-1">
                        {own.escalationPolicy}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {activeSection === 'blockers' && (
                <div className="space-y-3 text-xs">
                  {handover.content.blockers?.map((blk) => (
                    <div
                      key={blk.id}
                      className="p-4 rounded-xl bg-red-950/20 border border-red-500/25 space-y-2"
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
                    </div>
                  ))}
                </div>
              )}

              {activeSection === 'risks' && (
                <div className="space-y-3 text-xs">
                  {handover.content.risks?.map((rsk) => (
                    <div
                      key={rsk.id}
                      className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/25 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <h4 className="font-semibold text-amber-200">{rsk.description}</h4>
                        <Badge variant="warning" size="sm">
                          {rsk.severity.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed">
                        <strong className="text-amber-300">Operational Risk: </strong>
                        {rsk.impact}
                      </p>
                      <div className="pt-1 text-[11px] text-brand-400 font-mono">
                        Evidence: {rsk.supportingEvidence}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeSection === 'dependencies' && (
                <div className="space-y-3 text-xs">
                  {handover.content.dependencies?.map((dep) => (
                    <div
                      key={dep.id}
                      className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1"
                    >
                      <div className="font-semibold text-white">{dep.dependency}</div>
                      <div className="text-[11px] text-slate-400">
                        Related: {dep.relatedTask} · Status: <span className="text-emerald-400">{dep.currentStatus}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeSection === 'open_questions' && (
                <div className="space-y-3 text-xs">
                  {handover.content.openQuestions?.map((oq) => (
                    <div
                      key={oq.id}
                      className="p-4 rounded-xl bg-purple-950/20 border border-purple-500/25 space-y-1.5"
                    >
                      <div className="font-semibold text-white">{oq.question}</div>
                      <p className="text-slate-300 text-[11px]">
                        <strong>Why It Matters: </strong>
                        {oq.whyItMatters}
                      </p>
                      <div className="text-[10px] text-purple-300 font-mono">
                        Confirmation Required From: {oq.whoNeedsToConfirm}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeSection === 'next_actions' && (
                <div className="space-y-3 text-xs">
                  {handover.content.nextActions?.map((act) => (
                    <div
                      key={act.id}
                      className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between gap-3"
                    >
                      <div className="space-y-0.5">
                        <div className="font-semibold text-white">{act.action}</div>
                        <p className="text-slate-400 text-[11px]">{act.reason}</p>
                      </div>
                      <Badge variant={act.priority === 'high' ? 'danger' : 'neutral'} size="sm">
                        {act.priority.toUpperCase()}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Card>

          {/* Section Reviewer Comments & Feedback Thread */}
          <Card className="bg-[#0F172A] border-slate-800 p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-brand-400" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                  Reviewer Comments & Feedback ({activeComments.length})
                </h3>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">
                {currentSectionItem?.title}
              </span>
            </div>

            {/* Comment Thread List */}
            <div className="space-y-3">
              {activeComments.length === 0 ? (
                <div className="p-4 text-center text-xs text-slate-500 italic">
                  No comments recorded on this section yet. Leave feedback or approve below.
                </div>
              ) : (
                activeComments.map((cmt) => (
                  <div
                    key={cmt.id}
                    className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1.5 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="h-6 w-6 rounded-full bg-brand-500/20 text-brand-300 flex items-center justify-center font-bold text-[10px]">
                          {cmt.author.name[0]}
                        </div>
                        <span className="font-semibold text-white">{cmt.author.name}</span>
                        <span className="text-[10px] text-slate-400">({cmt.author.role || 'Reviewer'})</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500">
                        {new Date(cmt.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    <p className="text-slate-300 pl-8 leading-relaxed">
                      "{cmt.text}"
                    </p>
                  </div>
                ))
              )}
            </div>

            {/* Add New Comment Box */}
            {!handover.isLocked && (
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <Textarea
                  placeholder={`Add review comment or question on ${currentSectionItem?.title}...`}
                  rows={2}
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                />
                <div className="flex justify-end">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleAddComment}
                    isLoading={isPostingComment}
                    disabled={!commentText.trim()}
                    className="text-xs"
                  >
                    Post Comment
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* MODALS */}
      <ApprovalConfirmationModal
        isOpen={isApprovalModalOpen}
        onClose={() => setIsApprovalModalOpen(false)}
        handover={handover}
        onConfirm={handleConfirmFinalApproval}
      />

      <RequestChangesModal
        isOpen={Boolean(requestChangesMode)}
        onClose={() => setRequestChangesMode(null)}
        handover={handover}
        mode={requestChangesMode || 'changes'}
        onSubmit={handleConfirmChangesOrReject}
      />

      <SectionContentEditorModal
        isOpen={isEditorModalOpen}
        onClose={() => setIsEditorModalOpen(false)}
        handover={handover}
        sectionKey={activeSection}
        onSave={async (key, newContent) => {
          const updated = await reviewService.updateSectionContent(handover.id, key, newContent);
          setHandover(updated);
        }}
      />

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

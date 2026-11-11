import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FolderGit2,
  ArrowRight,
  ArrowLeft,
  Check,
  Sparkles,
  Users,
  ShieldCheck,
  Calendar,
  Lock,
  Layers,
  FileText,
  AlertCircle,
  HelpCircle,
  Edit2,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Textarea } from '../common/Textarea';
import { Select } from '../common/Select';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import { mockUsers } from '../../data/mockData';
import { CreateProjectFormData, Project } from '../../types/project';
import { projectService } from '../../services/projectService';
import { useToast } from '../../hooks/useToast';

export interface CreateProjectWizardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (project: Project) => void;
}

const CATEGORIES = [
  'Infrastructure',
  'Security & Auth',
  'Core Payments',
  'Data & Analytics',
  'AI & Search',
  'Event Streaming',
  'Frontend & Mobile',
];

const INITIAL_FORM_DATA: CreateProjectFormData = {
  title: '',
  key: '',
  description: '',
  category: 'Infrastructure',
  startDate: new Date().toISOString().split('T')[0],
  expectedDeadline: new Date(Date.now() + 60 * 86400000).toISOString().split('T')[0],
  status: 'in_progress',

  outgoingMemberId: mockUsers[0].id,
  incomingMemberId: mockUsers[1].id,
  incomingRole: '',
  projectLeadId: mockUsers[0].id,
  handoverPurpose: 'Staff Engineer Transition to Core Architecture',
  handoverDeadline: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],

  authorizedMemberIds: [mockUsers[0].id, mockUsers[1].id, mockUsers[2].id],
  uploadDocs: 'all_members',
  reviewApprove: 'dual_approval',
  incomingAccess: 'full_access',
};

export const CreateProjectWizardModal: React.FC<CreateProjectWizardModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { success, error: toastError } = useToast();
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [formData, setFormData] = useState<CreateProjectFormData>(INITIAL_FORM_DATA);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Auto-generate project key from title
  const handleTitleChange = (val: string) => {
    setFormData((prev) => {
      const generatedKey = prev.key ||
        val
          .toUpperCase()
          .replace(/[^A-Z0-9\s]/g, '')
          .split(' ')
          .filter(Boolean)
          .slice(0, 2)
          .join('-');
      return { ...prev, title: val, key: prev.key ? prev.key : generatedKey };
    });
    if (errors.title) setErrors((prev) => ({ ...prev, title: '' }));
  };

  const validateStep = (currentStep: number): boolean => {
    const errs: Record<string, string> = {};

    if (currentStep === 1) {
      if (!formData.title.trim()) {
        errs.title = 'Project name is required';
      }
      if (!formData.key.trim()) {
        errs.key = 'Project key is required (e.g. PAY-V2)';
      }
      if (!formData.description.trim()) {
        errs.description = 'Please provide a brief description';
      }
    }

    if (currentStep === 2) {
      if (!formData.outgoingMemberId) {
        errs.outgoingMemberId = 'Please select the outgoing member';
      }
      if (!formData.incomingMemberId && !formData.incomingRole.trim()) {
        errs.incomingMemberId = 'Select an incoming successor or specify role title';
      }
      if (!formData.handoverPurpose.trim()) {
        errs.handoverPurpose = 'Handover purpose is required';
      }
    }

    if (currentStep === 3) {
      if (formData.authorizedMemberIds.length === 0) {
        errs.authorizedMembers = 'Select at least one authorized team member';
      }
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      setStep((prev) => (Math.min(prev + 1, 4) as 1 | 2 | 3 | 4));
    }
  };

  const handleBack = () => {
    setStep((prev) => (Math.max(prev - 1, 1) as 1 | 2 | 3 | 4));
  };

  const handleCreate = async () => {
    setIsSubmitting(true);
    try {
      const res = await projectService.create(formData);
      if (res.data) {
        success('Workspace Created', `Project "${res.data.title}" (${res.data.key}) initialized.`);
        onSuccess(res.data);
        onClose();
        // Reset
        setFormData(INITIAL_FORM_DATA);
        setStep(1);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create workspace';
      toastError('Creation Failed', msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const stepTitles = [
    { num: 1, label: 'Project Details' },
    { num: 2, label: 'Handover Config' },
    { num: 3, label: 'Permissions' },
    { num: 4, label: 'Review & Create' },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="2xl"
      title="Create New Project Workspace"
      description="Set up project context, successor mapping, and access governance"
      className="p-0 overflow-hidden"
    >
      {/* Wizard Progress Stepper */}
      <div className="px-6 py-3.5 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
        {stepTitles.map((s, idx) => (
          <React.Fragment key={s.num}>
            <div className="flex items-center gap-2">
              <div
                className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
                  step === s.num
                    ? 'bg-brand-500 text-white shadow-glow'
                    : step > s.num
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    : 'bg-slate-800 text-slate-400 border border-slate-700/60'
                }`}
              >
                {step > s.num ? <Check className="h-3.5 w-3.5" /> : s.num}
              </div>
              <span
                className={`text-xs hidden sm:inline font-medium ${
                  step === s.num ? 'text-white' : 'text-slate-400'
                }`}
              >
                {s.label}
              </span>
            </div>
            {idx < stepTitles.length - 1 && (
              <div
                className={`h-0.5 flex-1 mx-2 sm:mx-3 rounded transition-colors ${
                  step > idx + 1 ? 'bg-emerald-500/50' : 'bg-slate-800'
                }`}
              />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Step Content */}
      <div className="p-6 max-h-[60vh] overflow-y-auto space-y-4">
        {/* STEP 1: PROJECT DETAILS */}
        {step === 1 && (
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="space-y-4 text-xs"
          >
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <Input
                  label="Project Name *"
                  placeholder="e.g. Distributed Event Mesh & Schema Registry"
                  value={formData.title}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  error={errors.title}
                />
              </div>
              <div>
                <Input
                  label="Project Key *"
                  placeholder="e.g. STREAM-CORE"
                  value={formData.key}
                  onChange={(e) => {
                    setFormData({ ...formData, key: e.target.value.toUpperCase() });
                    if (errors.key) setErrors((prev) => ({ ...prev, key: '' }));
                  }}
                  error={errors.key}
                />
              </div>
            </div>

            <Textarea
              label="Description *"
              placeholder="High-level architecture purpose, mission-critical impact, and system dependencies..."
              rows={3}
              value={formData.description}
              onChange={(e) => {
                setFormData({ ...formData, description: e.target.value });
                if (errors.description) setErrors((prev) => ({ ...prev, description: '' }));
              }}
              error={errors.description}
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Category
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 px-3 h-10 text-xs text-slate-200 focus:border-brand-500 focus:outline-none"
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Input
                  label="Start Date"
                  type="date"
                  value={formData.startDate}
                  onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                />
              </div>

              <div>
                <Input
                  label="Expected Deadline"
                  type="date"
                  value={formData.expectedDeadline}
                  onChange={(e) => setFormData({ ...formData, expectedDeadline: e.target.value })}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Initial Status
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: 'in_progress', label: 'In Progress', variant: 'accent' as const },
                  { id: 'under_review', label: 'Under Review', variant: 'warning' as const },
                  { id: 'draft', label: 'Draft Mode', variant: 'neutral' as const },
                  { id: 'at_risk', label: 'At Risk', variant: 'danger' as const },
                ].map((st) => (
                  <button
                    key={st.id}
                    type="button"
                    onClick={() => setFormData({ ...formData, status: st.id as any })}
                    className={`p-2 rounded-lg border text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
                      formData.status === st.id
                        ? 'bg-slate-800 border-brand-500 text-white shadow-sm'
                        : 'bg-slate-900/50 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Badge variant={st.variant} size="sm">
                      {st.label}
                    </Badge>
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* STEP 2: HANDOVER CONFIGURATION */}
        {step === 2 && (
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="space-y-4 text-xs"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Outgoing Member */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Outgoing Member (Knowledge Holder) *
                </label>
                <select
                  value={formData.outgoingMemberId}
                  onChange={(e) => setFormData({ ...formData, outgoingMemberId: e.target.value })}
                  className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 px-3 h-10 text-xs text-slate-200 focus:border-brand-500 focus:outline-none"
                >
                  {mockUsers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name} ({u.role.replace('_', ' ')}) · {u.department}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-[11px] text-slate-500">
                  The person currently owning code, runbooks, and shadow crons.
                </p>
              </div>

              {/* Incoming Member */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Incoming Successor (Recipient) *
                </label>
                <select
                  value={formData.incomingMemberId}
                  onChange={(e) => setFormData({ ...formData, incomingMemberId: e.target.value })}
                  className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 px-3 h-10 text-xs text-slate-200 focus:border-brand-500 focus:outline-none"
                >
                  {mockUsers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name} ({u.role.replace('_', ' ')}) · {u.department}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-[11px] text-slate-500">
                  The engineer taking over operational pager duty & repository ownership.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Project Lead */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Project Lead / Lead Architect
                </label>
                <select
                  value={formData.projectLeadId}
                  onChange={(e) => setFormData({ ...formData, projectLeadId: e.target.value })}
                  className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 px-3 h-10 text-xs text-slate-200 focus:border-brand-500 focus:outline-none"
                >
                  {mockUsers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name} · {u.role.replace('_', ' ')}
                    </option>
                  ))}
                </select>
              </div>

              {/* Handover Deadline */}
              <div>
                <Input
                  label="Handover Target Completion Date"
                  type="date"
                  value={formData.handoverDeadline}
                  onChange={(e) => setFormData({ ...formData, handoverDeadline: e.target.value })}
                />
              </div>
            </div>

            {/* Handover Purpose */}
            <Input
              label="Handover Purpose *"
              placeholder="e.g. Staff engineer exit, team reorg, vendor offboarding, or knowledge preservation"
              value={formData.handoverPurpose}
              onChange={(e) => {
                setFormData({ ...formData, handoverPurpose: e.target.value });
                if (errors.handoverPurpose) setErrors((prev) => ({ ...prev, handoverPurpose: '' }));
              }}
              error={errors.handoverPurpose}
            />
          </motion.div>
        )}

        {/* STEP 3: PERMISSIONS */}
        {step === 3 && (
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="space-y-4 text-xs"
          >
            {/* Authorized Members Selection */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold text-slate-200">
                  Select Authorized Members *
                </label>
                <span className="text-[11px] text-slate-400">
                  {formData.authorizedMemberIds.length} members selected
                </span>
              </div>

              <div className="space-y-1.5 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                {mockUsers.map((user) => {
                  const isChecked = formData.authorizedMemberIds.includes(user.id);
                  return (
                    <label
                      key={user.id}
                      className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/50 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-2.5">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            const newIds = e.target.checked
                              ? [...formData.authorizedMemberIds, user.id]
                              : formData.authorizedMemberIds.filter((id) => id !== user.id);
                            setFormData({ ...formData, authorizedMemberIds: newIds });
                          }}
                          className="rounded border-slate-700 bg-slate-800 text-brand-600 focus:ring-brand-500 h-4 w-4"
                        />
                        <img
                          src={user.avatarUrl}
                          alt={user.name}
                          className="h-6 w-6 rounded-full object-cover"
                        />
                        <div>
                          <div className="font-medium text-slate-200">{user.name}</div>
                          <div className="text-[10px] text-slate-500">{user.email}</div>
                        </div>
                      </div>
                      <Badge variant="neutral" size="sm">
                        {user.role.replace('_', ' ')}
                      </Badge>
                    </label>
                  );
                })}
              </div>
              {errors.authorizedMembers && (
                <p className="mt-1 text-xs text-red-400">• {errors.authorizedMembers}</p>
              )}
            </div>

            {/* Document Upload Governance */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
              <label className="block text-xs font-semibold text-slate-200">
                Who can upload documents & runbooks?
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {[
                  { id: 'all_members', label: 'All Authorized Members' },
                  { id: 'lead_and_outgoing', label: 'Lead & Outgoing Only' },
                  { id: 'admins_only', label: 'Organization Admins' },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setFormData({ ...formData, uploadDocs: opt.id as any })}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      formData.uploadDocs === opt.id
                        ? 'bg-slate-800 border-brand-500 text-white'
                        : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <div className="font-semibold">{opt.label}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Review & Approve Governance */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
              <label className="block text-xs font-semibold text-slate-200">
                Who can review and approve handovers?
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {[
                  { id: 'dual_approval', label: 'Dual-Person Sign-off (Recommended)' },
                  { id: 'architecture_reviewers', label: 'Architecture Reviewers' },
                  { id: 'lead_only', label: 'Project Lead Only' },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setFormData({ ...formData, reviewApprove: opt.id as any })}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      formData.reviewApprove === opt.id
                        ? 'bg-slate-800 border-brand-500 text-white'
                        : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <div className="font-semibold">{opt.label}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Incoming Member Access */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
              <label className="block text-xs font-semibold text-slate-200">
                Incoming Successor Vault & Credential Access
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {[
                  { id: 'full_access', label: 'Full Read & Write' },
                  { id: 'read_only_until_approved', label: 'Read-Only Until Approved' },
                  { id: 'restricted_vault', label: 'Restricted Staging Secrets' },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setFormData({ ...formData, incomingAccess: opt.id as any })}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      formData.incomingAccess === opt.id
                        ? 'bg-slate-800 border-brand-500 text-white'
                        : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <div className="font-semibold">{opt.label}</div>
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* STEP 4: REVIEW AND CREATE */}
        {step === 4 && (
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="space-y-4 text-xs"
          >
            <div className="p-3 rounded-xl bg-brand-500/10 border border-brand-500/25 flex items-center justify-between text-brand-300">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-brand-400" />
                <span>Ready to initialize project continuity memory</span>
              </div>
              <Badge variant="ai" size="sm">
                AI Ready
              </Badge>
            </div>

            {/* Section 1 Review */}
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white flex items-center gap-1.5">
                  <FolderGit2 className="h-4 w-4 text-brand-400" />
                  <span>Project Details</span>
                </span>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="text-brand-400 hover:text-brand-300 flex items-center gap-1 text-[11px] font-semibold"
                >
                  <Edit2 className="h-3 w-3" /> Edit
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-slate-400 pt-1">
                <div>Name: <span className="text-white font-medium">{formData.title}</span></div>
                <div>Key: <span className="font-mono text-brand-400 font-bold">{formData.key}</span></div>
                <div>Category: <span className="text-white">{formData.category}</span></div>
                <div>Status: <span className="text-white capitalize">{formData.status.replace('_', ' ')}</span></div>
                <div className="col-span-2">Description: <span className="text-slate-300">{formData.description}</span></div>
              </div>
            </div>

            {/* Section 2 Review */}
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white flex items-center gap-1.5">
                  <Users className="h-4 w-4 text-indigo-400" />
                  <span>Handover Configuration</span>
                </span>
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="text-brand-400 hover:text-brand-300 flex items-center gap-1 text-[11px] font-semibold"
                >
                  <Edit2 className="h-3 w-3" /> Edit
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-slate-400 pt-1">
                <div>
                  Outgoing: <span className="text-white font-medium">
                    {mockUsers.find((u) => u.id === formData.outgoingMemberId)?.name}
                  </span>
                </div>
                <div>
                  Successor: <span className="text-white font-medium">
                    {mockUsers.find((u) => u.id === formData.incomingMemberId)?.name}
                  </span>
                </div>
                <div className="col-span-2">
                  Purpose: <span className="text-slate-300">{formData.handoverPurpose}</span>
                </div>
                <div>Handover Target: <span className="font-mono text-white">{formData.handoverDeadline}</span></div>
              </div>
            </div>

            {/* Section 3 Review */}
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span>Permissions & Governance</span>
                </span>
                <button
                  type="button"
                  onClick={() => setStep(3)}
                  className="text-brand-400 hover:text-brand-300 flex items-center gap-1 text-[11px] font-semibold"
                >
                  <Edit2 className="h-3 w-3" /> Edit
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-slate-400 pt-1">
                <div>Authorized Members: <span className="text-white font-medium">{formData.authorizedMemberIds.length} users</span></div>
                <div>Document Upload: <span className="text-white capitalize">{formData.uploadDocs.replace(/_/g, ' ')}</span></div>
                <div>Approval Requirement: <span className="text-white capitalize">{formData.reviewApprove.replace(/_/g, ' ')}</span></div>
                <div>Incoming Access: <span className="text-white capitalize">{formData.incomingAccess.replace(/_/g, ' ')}</span></div>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Footer Controls */}
      <div className="px-6 py-4 bg-slate-900/80 border-t border-slate-800 flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          onClick={step === 1 ? onClose : handleBack}
          leftIcon={step > 1 ? <ArrowLeft className="h-3.5 w-3.5" /> : undefined}
          disabled={isSubmitting}
        >
          {step === 1 ? 'Cancel' : 'Back'}
        </Button>

        {step < 4 ? (
          <Button
            variant="primary"
            size="sm"
            onClick={handleNext}
            rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
          >
            Continue to {stepTitles[step].label}
          </Button>
        ) : (
          <Button
            variant="ai"
            size="sm"
            isLoading={isSubmitting}
            onClick={handleCreate}
            leftIcon={<Sparkles className="h-3.5 w-3.5" />}
          >
            Create Workspace
          </Button>
        )}
      </div>
    </Modal>
  );
};

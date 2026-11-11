import React, { useState } from 'react';
import {
  Sparkles,
  ArrowRight,
  Search,
  CheckCircle,
  AlertTriangle,
  Info,
  SlidersHorizontal,
  FolderGit2,
  Lock,
  Plus,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Textarea } from '../../components/common/Textarea';
import { Select } from '../../components/common/Select';
import { Badge } from '../../components/common/Badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/common/Card';
import { Tooltip } from '../../components/common/Tooltip';
import { Tabs } from '../../components/common/Tabs';
import { Table, Column } from '../../components/common/Table';
import { Modal } from '../../components/common/Modal';
import { Dropdown } from '../../components/common/Dropdown';
import { useToast } from '../../hooks/useToast';
import { mockProjects } from '../../data/mockData';
import { Project } from '../../types/project';

export const ComponentShowcasePage: React.FC = () => {
  const { success, error, warning, info: toastInfo, ai } = useToast();

  const [activeTab, setActiveTab] = useState('buttons');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [inputText, setInputText] = useState('');
  const [selectedRole, setSelectedRole] = useState('engineer');

  const demoColumns: Column<Project>[] = [
    {
      key: 'key',
      header: 'Project Key',
      render: (p) => <span className="font-mono font-bold text-brand-400">{p.key}</span>,
    },
    {
      key: 'title',
      header: 'Project Title',
      render: (p) => (
        <div>
          <div className="font-semibold text-slate-200">{p.title}</div>
          <div className="text-[11px] text-slate-400 truncate max-w-xs">{p.description}</div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (p) => (
        <Badge
          variant={p.status === 'in_progress' ? 'accent' : p.status === 'at_risk' ? 'danger' : 'success'}
          size="sm"
          dot
        >
          {p.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'knowledgeHealthScore',
      header: 'Continuity Health',
      render: (p) => (
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs">{p.knowledgeHealthScore}%</span>
          <div className="w-16 bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                p.knowledgeHealthScore > 80 ? 'bg-emerald-400' : 'bg-amber-400'
              }`}
              style={{ width: `${p.knowledgeHealthScore}%` }}
            />
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="border-b border-slate-800 pb-5">
        <div className="flex items-center gap-2">
          <Badge variant="ai" size="sm">
            Design Tokens & UI Primitives
          </Badge>
        </div>
        <h1 className="text-2xl font-bold text-white tracking-tight mt-1">
          Component System Showcase
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Interactive gallery of all reusable UI foundation elements, dark-first styles, and states.
        </p>
      </div>

      {/* Tabs Switcher */}
      <Tabs
        tabs={[
          { id: 'buttons', label: 'Buttons & Badges', count: 6 },
          { id: 'forms', label: 'Inputs & Form Controls', count: 4 },
          { id: 'surfaces', label: 'Cards & Modals', count: 3 },
          { id: 'data', label: 'Tables & Tabs', count: 2 },
          { id: 'toasts', label: 'Toast Notifications', count: 5 },
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
        variant="pill"
      />

      {/* 1. BUTTONS & BADGES */}
      {activeTab === 'buttons' && (
        <div className="space-y-6">
          <Card className="p-6 bg-[#0F172A] border-slate-800">
            <h3 className="text-sm font-semibold text-white mb-4">Button Variants</h3>
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="primary">Primary Button</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="danger">Danger</Button>
              <Button variant="ai" leftIcon={<Sparkles className="h-4 w-4" />}>
                AI Accent Glow
              </Button>
              <Button variant="primary" isLoading>
                Loading
              </Button>
            </div>

            <h3 className="text-sm font-semibold text-white mt-8 mb-4">Button Sizes</h3>
            <div className="flex flex-wrap items-center gap-3">
              <Button size="sm" variant="secondary">Small (sm)</Button>
              <Button size="md" variant="secondary">Medium (md)</Button>
              <Button size="lg" variant="secondary">Large (lg)</Button>
            </div>
          </Card>

          <Card className="p-6 bg-[#0F172A] border-slate-800">
            <h3 className="text-sm font-semibold text-white mb-4">Status & AI Badges</h3>
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant="default">Default</Badge>
              <Badge variant="neutral">Neutral</Badge>
              <Badge variant="success" dot>Success (Live)</Badge>
              <Badge variant="warning" dot>Warning (Drift)</Badge>
              <Badge variant="danger" dot>Danger (At Risk)</Badge>
              <Badge variant="accent">Accent Indigo</Badge>
              <Badge variant="ai" dot>AI Verified (98%)</Badge>
            </div>
          </Card>
        </div>
      )}

      {/* 2. FORMS & INPUTS */}
      {activeTab === 'forms' && (
        <Card className="p-6 bg-[#0F172A] border-slate-800 space-y-5 max-w-2xl">
          <h3 className="text-sm font-semibold text-white mb-2">Form Components</h3>

          <Input
            label="Standard Input"
            placeholder="Type your repo name..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            helperText="Repository names must be kebab-cased"
          />

          <Input
            label="Search Input with Shortcut"
            placeholder="Search decisions, runbooks, gotchas..."
            leftIcon={<Search className="h-4 w-4" />}
            shortcut="⌘K"
          />

          <Input
            label="Input with Error State"
            placeholder="admin@techfrontier.io"
            value="invalid-email"
            error="Please provide a valid work email domain"
          />

          <Select
            label="Engineering Role"
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            options={[
              { value: 'lead_engineer', label: 'Lead Engineer' },
              { value: 'engineer', label: 'Staff Software Engineer' },
              { value: 'reviewer', label: 'Architecture Reviewer' },
              { value: 'admin', label: 'Engineering Director' },
            ]}
          />

          <Textarea
            label="Handover Notes / Architectural Rationale"
            placeholder="Document any subtle production gotchas or background scripts..."
            rows={3}
          />
        </Card>
      )}

      {/* 3. SURFACES & MODALS */}
      {activeTab === 'surfaces' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card hoverable className="p-5 bg-[#0F172A] border-slate-800">
              <CardTitle className="text-white">Hoverable Surface Card</CardTitle>
              <CardDescription className="mt-1">
                Subtle linear hover lift and fine slate border transition.
              </CardDescription>
              <CardContent className="px-0 pt-3 text-xs text-slate-300">
                Used throughout project lists, document indexes, and review queues.
              </CardContent>
            </Card>

            <Card glow className="p-5 bg-[#0F172A] border-brand-500/30">
              <CardTitle className="text-white flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-brand-400" />
                <span>Glow Active Surface Card</span>
              </CardTitle>
              <CardDescription className="mt-1">
                Electric indigo ambient shadow highlight for active focus items.
              </CardDescription>
              <CardContent className="px-0 pt-3 text-xs text-slate-300">
                Applied to current stage in handover pipeline or critical warnings.
              </CardContent>
            </Card>
          </div>

          <Card className="p-6 bg-[#0F172A] border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-white">Modal & Tooltip Demos</h3>
            <div className="flex items-center gap-4">
              <Button variant="primary" onClick={() => setIsModalOpen(true)}>
                Open Animated Modal
              </Button>

              <Tooltip content="Tooltip explains contextual actions instantly">
                <Button variant="secondary">Hover for Tooltip</Button>
              </Tooltip>

              <Dropdown
                trigger={<Button variant="outline">Open Dropdown Menu</Button>}
                items={[
                  { id: '1', label: 'Export Handover as PDF' },
                  { id: '2', label: 'Export as Markdown' },
                  { id: '3', label: '', divider: true },
                  { id: '4', label: 'Revoke Credentials', danger: true },
                ]}
              />
            </div>
          </Card>
        </div>
      )}

      {/* 4. TABLES & TABS */}
      {activeTab === 'data' && (
        <div className="space-y-6">
          <Card className="p-6 bg-[#0F172A] border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-white">Responsive Data Table</h3>
            <Table
              columns={demoColumns}
              data={mockProjects}
              keyExtractor={(p) => p.id}
              onRowClick={(p) => toastInfo('Selected Project', `${p.title} (${p.key})`)}
            />
          </Card>
        </div>
      )}

      {/* 5. TOAST NOTIFICATIONS */}
      {activeTab === 'toasts' && (
        <Card className="p-6 bg-[#0F172A] border-slate-800 space-y-4">
          <h3 className="text-sm font-semibold text-white">Trigger Toast Notifications</h3>
          <p className="text-xs text-slate-400">
            Click any button below to trigger stacked notifications with auto-dismiss timers.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => success('Success Notification', 'ADR-014 successfully verified against GitHub commit 9f8a12.')}
            >
              Trigger Success Toast
            </Button>
            <Button
              variant="secondary"
              onClick={() => toastInfo('Information', 'Background knowledge sync completed in 120ms.')}
            >
              Trigger Info Toast
            </Button>
            <Button
              variant="secondary"
              onClick={() => warning('Warning: Drift Detected', 'main.tf RDS failover config does not match runbook.')}
            >
              Trigger Warning Toast
            </Button>
            <Button
              variant="secondary"
              onClick={() => error('Error Encountered', 'Failed to fetch Slack message audit thread.')}
            >
              Trigger Error Toast
            </Button>
            <Button
              variant="ai"
              onClick={() => ai('AI Synthesis Complete', 'Generated executive handover summary and flagged 1 gotcha.')}
            >
              Trigger AI Toast
            </Button>
          </div>
        </Card>
      )}

      {/* Demo Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Interactive Dialog Example"
        description="Framer Motion scale + fade transitions with full keyboard accessibility."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setIsModalOpen(false);
                success('Modal Action Confirmed', 'Dialog completed successfully.');
              }}
            >
              Confirm Action
            </Button>
          </>
        }
      >
        <p className="text-xs text-slate-300 leading-relaxed">
          This modal demonstrates smooth backdrop blur, spring scaling, ESC key dismissal, and custom action footers.
        </p>
      </Modal>
    </div>
  );
};

import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  Sparkles,
  ShieldAlert,
  GitBranch,
  CheckCircle2,
  Lock,
  Layers,
  FileCheck,
  Search,
  Users,
  Terminal,
  Activity,
  Workflow,
  Clock,
  Compass,
  AlertTriangle,
  FolderGit2,
  ExternalLink,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const workflowSteps = [
    {
      step: '01',
      title: 'Upload',
      desc: 'Ingest repos, PRs, Jira tickets, Slack threads, and legacy Confluence docs.',
      icon: FolderGit2,
      badge: 'Multi-Source',
    },
    {
      step: '02',
      title: 'Analyze',
      desc: 'AI synthesizes architecture decisions, undocumented secrets, and operational runbooks.',
      icon: Sparkles,
      badge: 'Semantic Graph',
    },
    {
      step: '03',
      title: 'Verify',
      desc: 'Pin every assertion to verifiable evidence: git commits, config files, and tests.',
      icon: FileCheck,
      badge: 'Zero-Hallucination',
    },
    {
      step: '04',
      title: 'Approve',
      desc: 'Outgoing lead and incoming successor review, sign off, and resolve knowledge gaps.',
      icon: CheckCircle2,
      badge: 'Human Sign-off',
    },
    {
      step: '05',
      title: 'Handover',
      desc: 'Seamless transfer of ownership with interactive queryable project memory.',
      icon: ArrowRight,
      badge: 'Continuity Ensured',
    },
  ];

  const capabilities = [
    {
      title: 'Evidence-Linked AI',
      desc: 'No vague summaries. Every generated architectural decision or runbook step links directly to a GitHub commit, Slack thread, or config diff.',
      icon: FileCheck,
      gradient: 'from-blue-500/20 to-indigo-500/20',
      tag: 'Audit Trail',
    },
    {
      title: 'Conflict Detection',
      desc: 'Automatically flag contradictions between outdated documentation and current production infrastructure configurations.',
      icon: AlertTriangle,
      gradient: 'from-amber-500/20 to-rose-500/20',
      tag: 'Drift Prevention',
    },
    {
      title: 'Task & System Ownership',
      desc: 'Map every microservice, shadow cron job, and third-party credential explicitly to verified incoming successors.',
      icon: Users,
      gradient: 'from-emerald-500/20 to-teal-500/20',
      tag: 'Accountability',
    },
    {
      title: 'Dependency Tracking',
      desc: 'Visualize cross-repo architectural ties, webhook contracts, and third-party API dependencies before engineers transition.',
      icon: GitBranch,
      gradient: 'from-indigo-500/20 to-purple-500/20',
      tag: 'Full Topology',
    },
    {
      title: 'Human-in-the-Loop Sign-off',
      desc: 'Structured handover checklists requiring cryptographic verification and explicit sign-offs from both leads and reviewers.',
      icon: Lock,
      gradient: 'from-violet-500/20 to-brand-500/20',
      tag: 'Compliance Ready',
    },
  ];

  return (
    <div className="relative overflow-hidden">
      {/* Background radial glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[550px] bg-gradient-to-b from-brand-600/15 via-brand-accent/5 to-transparent blur-3xl pointer-events-none -z-10" />
      <div className="absolute top-[800px] right-0 w-[500px] h-[500px] bg-indigo-600/10 blur-3xl pointer-events-none -z-10" />

      {/* HERO SECTION */}
      <section className="relative pt-12 pb-20 md:pt-20 md:pb-32 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column: Copy & Actions */}
          <div className="lg:col-span-6 space-y-6 text-center lg:text-left">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/25 text-brand-300 text-xs font-medium"
            >
              <Sparkles className="h-3.5 w-3.5 text-brand-400" />
              <span>AI-Powered Project Knowledge Continuity</span>
              <span className="h-1 w-1 rounded-full bg-brand-400" />
              <span className="text-slate-400">v2.4 Released</span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.1]"
            >
              Your Projects Should <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 via-indigo-300 to-brand-accent">Never Forget.</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="text-base sm:text-lg text-slate-400 max-w-xl mx-auto lg:mx-0 leading-relaxed"
            >
              Turn scattered project knowledge into structured, evidence-backed handovers. Keep teams moving, even when people move on.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3.5 pt-2"
            >
              <Button
                variant="primary"
                size="lg"
                onClick={() => navigate('/register')}
                rightIcon={<ArrowRight className="h-4 w-4" />}
                className="w-full sm:w-auto text-sm px-6 font-semibold"
              >
                Get Started
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => navigate('/dashboard')}
                leftIcon={<Compass className="h-4 w-4 text-brand-400" />}
                className="w-full sm:w-auto text-sm px-6"
              >
                Explore Platform
              </Button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="pt-4 flex items-center justify-center lg:justify-start gap-6 text-xs text-slate-400"
            >
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>Zero Hallucination</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>SOC2 & Git Native</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>FastAPI Ready</span>
              </div>
            </motion.div>
          </div>

          {/* Right Column: Attractive Product Dashboard Preview */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="lg:col-span-6 relative"
          >
            {/* Ambient backlight glow */}
            <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-brand-600/30 via-indigo-600/20 to-purple-600/30 blur-xl opacity-75" />

            <div className="relative rounded-2xl bg-[#0B101D] border border-slate-800 shadow-2xl overflow-hidden">
              {/* Mock Window Title Bar */}
              <div className="flex items-center justify-between px-4 py-3 bg-[#080C14] border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <div className="h-2.5 w-2.5 rounded-full bg-rose-500/80" />
                  <div className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
                  <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
                  <span className="ml-2 text-[11px] font-mono text-slate-400">
                    knowledge-continuity · PAY-V2
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="ai" size="sm">
                    AI Verified: 94%
                  </Badge>
                </div>
              </div>

              {/* Mock Dashboard Body */}
              <div className="p-5 space-y-4">
                {/* Handover Hero Bar inside preview */}
                <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/90 border border-slate-800">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-brand-500/20 border border-brand-500/30 flex items-center justify-center text-brand-400">
                      <FolderGit2 className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-slate-200">
                        Global Payment Gateway v2
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Lead: Elena R. → Successor: David C.
                      </div>
                    </div>
                  </div>
                  <Badge variant="success" size="sm" dot>
                    On Track
                  </Badge>
                </div>

                {/* Metrics Row */}
                <div className="grid grid-cols-3 gap-2.5">
                  <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800/80 text-left">
                    <div className="text-[10px] text-slate-400 uppercase font-mono">Continuity</div>
                    <div className="text-lg font-bold text-slate-100 mt-0.5">89%</div>
                    <div className="text-[10px] text-emerald-400 flex items-center gap-1 mt-0.5">
                      <span>↑ 14% this week</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800/80 text-left">
                    <div className="text-[10px] text-slate-400 uppercase font-mono">Evidence</div>
                    <div className="text-lg font-bold text-slate-100 mt-0.5">34 PRs</div>
                    <div className="text-[10px] text-brand-400 flex items-center gap-1 mt-0.5">
                      <span>100% verified</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800/80 text-left">
                    <div className="text-[10px] text-slate-400 uppercase font-mono">Conflicts</div>
                    <div className="text-lg font-bold text-amber-300 mt-0.5">1 Flagged</div>
                    <div className="text-[10px] text-amber-400/90 flex items-center gap-1 mt-0.5">
                      <span>Terraform drift</span>
                    </div>
                  </div>
                </div>

                {/* Evidence Verification Checklist Preview */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                    <span>Evidence-Linked Checklist</span>
                    <span className="text-[10px] font-mono text-slate-400">3 of 4 Completed</span>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/40 border border-slate-800/70 text-xs">
                      <div className="flex items-center gap-2 text-slate-200">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                        <span className="truncate">ADR-014: Zero-downtime PSP Circuit Breaker</span>
                      </div>
                      <span className="text-[10px] font-mono text-brand-400 bg-brand-500/10 px-1.5 py-0.5 rounded shrink-0">
                        PR #418
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/40 border border-slate-800/70 text-xs">
                      <div className="flex items-center gap-2 text-slate-200">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                        <span className="truncate">Staging Credentials & KMS Keys Transferred</span>
                      </div>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded shrink-0">
                        Vault Sync
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-2 rounded-lg bg-amber-500/5 border border-amber-500/30 text-xs">
                      <div className="flex items-center gap-2 text-amber-300">
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                        <span className="truncate">Runbook: Failover Throttling Policy (Review Needed)</span>
                      </div>
                      <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded shrink-0">
                        Action Required
                      </span>
                    </div>
                  </div>
                </div>

                {/* AI Gotcha Notification box */}
                <div className="p-3 rounded-lg bg-gradient-to-r from-brand-950/60 to-purple-950/40 border border-brand-500/30 flex items-start gap-2.5">
                  <Sparkles className="h-4 w-4 text-brand-accent shrink-0 mt-0.5" />
                  <div className="text-[11px] leading-relaxed text-slate-300">
                    <span className="font-semibold text-white">AI Gotcha Alert:</span> PSP webhook keys rotate automatically every 90 days. Next rotation in 12 days.
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* THE PROBLEM SECTION */}
      <section id="problem" className="py-20 bg-slate-900/30 border-y border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <Badge variant="danger" size="sm">
              The Reality of Software Engineering
            </Badge>
            <h2 className="mt-4 text-3xl sm:text-4xl font-bold tracking-tight text-white">
              Knowledge Disappears When People Leave.
            </h2>
            <p className="mt-4 text-sm sm:text-base text-slate-400 leading-relaxed">
              When key engineers transition, critical architectural context, shadow cron jobs, and 3:00 AM production gotchas vanish with them.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="p-6 bg-slate-900/60 border-slate-800">
              <div className="h-10 w-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mb-4">
                <Clock className="h-5 w-5" />
              </div>
              <h3 className="text-base font-semibold text-white">3 to 6 Month Ramp-up</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                New engineers spend months reverse-engineering undocumented design decisions, decoding git history, and guessing why legacy compromises were made.
              </p>
            </Card>

            <Card className="p-6 bg-slate-900/60 border-slate-800">
              <div className="h-10 w-10 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-4">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <h3 className="text-base font-semibold text-white">Documentation Rot</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Wiki pages and Confluence trees lie. They describe how the system worked two years ago, leading directly to production outages during incidents.
              </p>
            </Card>

            <Card className="p-6 bg-slate-900/60 border-slate-800">
              <div className="h-10 w-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-brand-400 mb-4">
                <ShieldAlert className="h-5 w-5" />
              </div>
              <h3 className="text-base font-semibold text-white">Shadow Gotchas</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Unregistered cron jobs, secret rotation schedules, and manual database failovers live in engineers' heads, creating catastrophic single points of failure.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS SECTION */}
      <section id="how-it-works" className="py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <Badge variant="accent" size="sm">
            5-Stage Continuity Lifecycle
          </Badge>
          <h2 className="mt-4 text-3xl sm:text-4xl font-bold tracking-tight text-white">
            Upload → Analyze → Verify → Approve → Handover
          </h2>
          <p className="mt-4 text-sm sm:text-base text-slate-400">
            A battle-tested pipeline that guarantees zero knowledge loss without placing manual documentation burdens on departing engineers.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {workflowSteps.map((s, index) => {
            const Icon = s.icon;
            return (
              <div
                key={s.step}
                className="relative flex flex-col p-5 rounded-xl bg-[#0F172A] border border-slate-800 hover:border-brand-500/40 transition-all duration-200 group"
              >
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-mono font-bold text-brand-400">
                    {s.step}
                  </span>
                  <Badge variant="neutral" size="sm">
                    {s.badge}
                  </Badge>
                </div>
                <div className="h-8 w-8 rounded-lg bg-slate-800/80 group-hover:bg-brand-500/20 group-hover:text-brand-300 flex items-center justify-center text-slate-300 transition-colors mb-3">
                  <Icon className="h-4 w-4" />
                </div>
                <h4 className="text-sm font-semibold text-white mb-1.5">{s.title}</h4>
                <p className="text-xs text-slate-400 leading-relaxed flex-1">{s.desc}</p>
                {index < 4 && (
                  <div className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 z-10 text-slate-600">
                    →
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* CORE CAPABILITIES SECTION */}
      <section id="capabilities" className="py-20 bg-slate-900/30 border-y border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <Badge variant="ai" size="sm">
              Continuous Intelligence
            </Badge>
            <h2 className="mt-4 text-3xl sm:text-4xl font-bold tracking-tight text-white">
              Built for High-Stakes Engineering Handover
            </h2>
            <p className="mt-4 text-sm sm:text-base text-slate-400">
              Not another generic LLM summarizer. An immutable, evidence-backed knowledge graph designed specifically for engineering continuity.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {capabilities.map((cap) => {
              const Icon = cap.icon;
              return (
                <Card
                  key={cap.title}
                  hoverable
                  className="p-6 bg-[#0F172A] border-slate-800 hover:border-slate-700 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className={`h-10 w-10 rounded-lg bg-gradient-to-br ${cap.gradient} border border-white/10 flex items-center justify-center text-white`}>
                        <Icon className="h-5 w-5 text-brand-300" />
                      </div>
                      <Badge variant="accent" size="sm">
                        {cap.tag}
                      </Badge>
                    </div>
                    <h3 className="text-base font-semibold text-white">{cap.title}</h3>
                    <p className="mt-2 text-xs text-slate-400 leading-relaxed">{cap.desc}</p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center gap-1.5 text-xs text-brand-400 font-medium">
                    <span>Explore capability</span>
                    <ArrowRight className="h-3 w-3" />
                  </div>
                </Card>
              );
            })}

            {/* Metric Banner Card in Grid */}
            <div className="p-6 rounded-xl bg-gradient-to-br from-brand-900/50 via-slate-900 to-purple-950/40 border border-brand-500/30 flex flex-col justify-between">
              <div>
                <span className="text-[10px] font-mono text-brand-300 uppercase tracking-wider">
                  Real Enterprise Impact
                </span>
                <h4 className="text-3xl font-extrabold text-white mt-2">78% Faster</h4>
                <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                  Reduction in successor ramp-up time and zero missed production credentials across 1,200+ engineering transitions.
                </p>
              </div>
              <Button
                variant="ai"
                size="sm"
                onClick={() => navigate('/register')}
                className="mt-6 text-xs w-full"
              >
                Start Free Trial
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* VISUAL WORKFLOW SECTION */}
      <section id="workflow" className="py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-5 space-y-5 text-left">
            <Badge variant="accent" size="sm">
              Visual Product Workflow
            </Badge>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white leading-tight">
              Evidence Linked Directly To Your Source of Truth.
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              When an engineer marks an architecture decision as documented, Knowledge Handover validates it against git commits, PR descriptions, and Terraform configurations.
            </p>

            <div className="space-y-3 pt-2">
              <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                <GitBranch className="h-4 w-4 text-brand-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-slate-200">Git Native Ingestion</div>
                  <div className="text-slate-400 text-[11px] mt-0.5">Scans PRs, merge comments, and ADR markdown directly from your GitHub/GitLab org.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-slate-200">Automated Drift Flagging</div>
                  <div className="text-slate-400 text-[11px] mt-0.5">Detects if production infrastructure was manually modified outside documented procedures.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                <Lock className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-slate-200">Cryptographic Handover Sign-off</div>
                  <div className="text-slate-400 text-[11px] mt-0.5">Generates an immutable audit record signed by engineering directors and incoming successors.</div>
                </div>
              </div>
            </div>
          </div>

          {/* Workflow Interactive Preview Graphic */}
          <div className="lg:col-span-7">
            <div className="p-6 rounded-2xl bg-[#0B101D] border border-slate-800 shadow-2xl space-y-4">
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Workflow className="h-4 w-4 text-brand-400" />
                  <span className="text-xs font-semibold text-white">Live Verification Graph</span>
                </div>
                <Badge variant="ai" size="sm">
                  Active Audit
                </Badge>
              </div>

              {/* Node Graph Mockup */}
              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="text-brand-400">git:commit/7a2f91</span>
                    <span className="text-slate-500">→</span>
                    <span className="text-slate-200">Circuit Breaker Failover Logic</span>
                  </div>
                  <span className="text-emerald-400 text-[11px]">✓ Verified</span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="text-brand-400">slack:thread/p17892</span>
                    <span className="text-slate-500">→</span>
                    <span className="text-slate-200">3:00 AM Banking API Rate Limit Workaround</span>
                  </div>
                  <span className="text-emerald-400 text-[11px]">✓ Extracted</span>
                </div>

                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-amber-200">
                    <span className="text-amber-400">doc:confluence/rds</span>
                    <span className="text-amber-500">≠</span>
                    <span>Multi-AZ failover mismatch with main.tf</span>
                  </div>
                  <span className="text-amber-400 text-[11px] font-bold">! Conflict</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-slate-400">Ready for successor sign-off?</span>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => navigate('/dashboard')}
                  className="h-8 text-xs"
                >
                  Open in Workspace
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FINAL CALL TO ACTION */}
      <section className="py-20 relative px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="relative rounded-3xl bg-gradient-to-r from-brand-950 via-slate-900 to-indigo-950 border border-brand-500/30 p-8 sm:p-14 text-center overflow-hidden shadow-2xl">
          <div className="absolute top-0 right-0 w-96 h-96 bg-brand-500/10 blur-3xl pointer-events-none" />

          <Badge variant="ai" size="sm">
            Empower Your Engineering Org
          </Badge>
          <h2 className="mt-4 text-3xl sm:text-5xl font-extrabold tracking-tight text-white max-w-2xl mx-auto">
            Make Every Handover Effortless & Bulletproof.
          </h2>
          <p className="mt-4 text-slate-300 text-sm sm:text-base max-w-xl mx-auto leading-relaxed">
            Stop losing institutional engineering memory. Deploy Knowledge Handover in minutes and safeguard your mission-critical codebases.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              variant="primary"
              size="lg"
              onClick={() => navigate('/register')}
              rightIcon={<ArrowRight className="h-4 w-4" />}
              className="w-full sm:w-auto px-8"
            >
              Get Started Free
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => navigate('/login')}
              className="w-full sm:w-auto px-8 border-slate-700 hover:bg-slate-800"
            >
              Sign In to Account
            </Button>
          </div>
        </div>
      </section>

      {/* PROFESSIONAL FOOTER */}
      <footer className="border-t border-slate-800 bg-[#060910] text-slate-400 text-xs py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
          {/* Brand Col */}
          <div className="col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-lg bg-gradient-to-tr from-brand-600 to-purple-500 flex items-center justify-center text-white">
                <Layers className="h-4 w-4" />
              </div>
              <span className="font-bold text-white text-sm">Knowledge Handover</span>
            </div>
            <p className="text-slate-400 max-w-sm text-xs leading-relaxed">
              The AI-powered project continuity platform ensuring software engineering teams never lose critical institutional context.
            </p>
            <div className="pt-2 flex items-center gap-2 text-[11px] text-emerald-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>All AI verification engines operational</span>
            </div>
          </div>

          {/* Product */}
          <div className="space-y-2.5">
            <h4 className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">Product</h4>
            <ul className="space-y-2">
              <li><a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a></li>
              <li><a href="#capabilities" className="hover:text-white transition-colors">Evidence AI</a></li>
              <li><a href="#problem" className="hover:text-white transition-colors">Conflict Detection</a></li>
              <li><Link to="/design-system" className="hover:text-white transition-colors">Design System</Link></li>
            </ul>
          </div>

          {/* Solutions */}
          <div className="space-y-2.5">
            <h4 className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">Continuity</h4>
            <ul className="space-y-2">
              <li><a href="#" className="hover:text-white transition-colors">Staff Engineer Exits</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Agency Transfers</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Mergers & Acquisitions</a></li>
              <li><a href="#" className="hover:text-white transition-colors">SOC2 Audit Trails</a></li>
            </ul>
          </div>

          {/* Enterprise */}
          <div className="space-y-2.5">
            <h4 className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">Enterprise</h4>
            <ul className="space-y-2">
              <li><Link to="/login" className="hover:text-white transition-colors">Sign In</Link></li>
              <li><Link to="/register" className="hover:text-white transition-colors">Get Started</Link></li>
              <li><a href="#" className="hover:text-white transition-colors">Security & Privacy</a></li>
              <li><a href="#" className="hover:text-white transition-colors">FastAPI Specs</a></li>
            </ul>
          </div>
        </div>

        <div className="max-w-7xl mx-auto pt-8 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-4 text-slate-500 text-[11px]">
          <div>
            © {new Date().getFullYear()} Knowledge Handover Inc. Built with precision for engineering excellence.
          </div>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-slate-300">Privacy Policy</a>
            <a href="#" className="hover:text-slate-300">Terms of Service</a>
            <a href="#" className="hover:text-slate-300">Security Architecture</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

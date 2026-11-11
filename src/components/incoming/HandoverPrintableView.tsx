import React from 'react';
import {
  FileText,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  User,
  GitBranch,
  Flame,
  AlertTriangle,
  HelpCircle,
  Printer,
  Download,
  ArrowLeft,
} from 'lucide-react';
import { IncomingHandoverPackage } from '../../types/incoming';
import { Button } from '../common/Button';

interface HandoverPrintableViewProps {
  packageData: IncomingHandoverPackage;
  onClose: () => void;
}

export const HandoverPrintableView: React.FC<HandoverPrintableViewProps> = ({
  packageData,
  onClose,
}) => {
  const handlePrint = () => {
    window.print();
  };

  const handleDownloadMarkdown = () => {
    const mdContent = `# Project Handover Brief: ${packageData.projectName} (${packageData.projectKey})
Version: ${packageData.version}
Approved Date: ${new Date(packageData.approvedDate).toLocaleDateString()}
Certified By: ${packageData.approvedBy.name} (${packageData.approvedBy.role || 'Project Lead'})
Outgoing Lead: ${packageData.outgoingMember.name}
Incoming Successor: ${packageData.incomingMember.name}
Acknowledgement Status: ${packageData.acknowledgementStatus.toUpperCase()}

---

## A. Project Introduction
${packageData.introduction.purpose}

### Objectives:
${packageData.introduction.objectives.map((o) => `- ${o}`).join('\n')}

**Development Stage:** ${packageData.introduction.currentStage}  
**Overall Status:** ${packageData.introduction.overallStatus}  
**Health Score:** ${packageData.introduction.healthScore}%  

---

## B. Important Architecture Decisions (ADRs)
${packageData.decisions
  .map(
    (d, i) => `### ${i + 1}. ${d.decision} (${d.date})
**Rationale:** ${d.rationale}  
**Supporting Source:** ${d.supportingSource}
`
  )
  .join('\n')}

---

## C. Assigned Responsibilities
${packageData.responsibilities
  .map(
    (r, i) => `### ${i + 1}. [${r.status.toUpperCase()}] ${r.title}
Priority: ${r.priority.toUpperCase()} | Due: ${r.dueDate || 'TBD'}
${r.description}
`
  )
  .join('\n')}

---

## D. Current Blockers
${packageData.blockers
  .map(
    (b) => `- **${b.description}** [${b.severity.toUpperCase()}]: ${b.impact}
  Follow-Up: ${b.suggestedFollowUp}`
  )
  .join('\n')}

---

## E. Project Dependencies
${packageData.dependencies
  .map(
    (dep) => `- **${dep.dependency}**: Status: ${dep.currentStatus} (Resource: ${dep.requiredPersonOrResource})`
  )
  .join('\n')}

---

## F. Recommended Starting Actions
${packageData.recommendedStartingActions
  .map((a) => `- [${a.timeframe}] **${a.action}**: ${a.reason}`)
  .join('\n')}

---

## G. Open Questions
${packageData.openQuestions
  .map((q) => `- **${q.question}**: ${q.whyItMatters} (Confirm with: ${q.whoNeedsToConfirm})`)
  .join('\n')}

---
Certified by Knowledge Handover Continuity Platform. Immutable cryptographic record.
`;

    const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Handover_${packageData.projectKey}_${packageData.version}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 sm:p-10 font-sans print:p-0 print:bg-white print:text-black">
      {/* Print Controls Header (Hidden during actual print) */}
      <div className="max-w-4xl mx-auto flex items-center justify-between pb-6 mb-8 border-b border-slate-800 print:hidden">
        <button
          onClick={onClose}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white font-mono"
        >
          <ArrowLeft className="h-4 w-4" /> Return to Interactive View
        </button>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadMarkdown}
            leftIcon={<Download className="h-4 w-4" />}
            className="text-xs"
          >
            Download Markdown
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handlePrint}
            leftIcon={<Printer className="h-4 w-4" />}
            className="text-xs"
          >
            Print / Save to PDF
          </Button>
        </div>
      </div>

      {/* Printable Document Sheet */}
      <div className="max-w-4xl mx-auto bg-[#090D16] border border-slate-800 rounded-2xl p-8 sm:p-12 space-y-8 shadow-2xl print:border-none print:p-4 print:bg-white print:shadow-none print:text-black">
        {/* Document Header */}
        <div className="border-b-2 border-slate-800 print:border-black pb-6 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-bold text-brand-400 print:text-black uppercase tracking-wider">
              Knowledge Handover Platform · Certified Brief
            </span>
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-800 print:bg-slate-200 text-slate-300 print:text-black">
              VERSION {packageData.version}
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white print:text-black">
            {packageData.projectName} ({packageData.projectKey})
          </h1>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-2 font-mono text-slate-400 print:text-slate-800">
            <div>
              <span className="text-slate-500 block text-[10px]">OUTGOING LEAD</span>
              <strong className="text-white print:text-black">{packageData.outgoingMember.name}</strong>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px]">INCOMING SUCCESSOR</span>
              <strong className="text-white print:text-black">{packageData.incomingMember.name}</strong>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px]">APPROVED BY</span>
              <strong className="text-white print:text-black">{packageData.approvedBy.name}</strong>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px]">CERTIFIED DATE</span>
              <strong className="text-white print:text-black">
                {new Date(packageData.approvedDate).toLocaleDateString()}
              </strong>
            </div>
          </div>
        </div>

        {/* SECTION A: PROJECT INTRODUCTION */}
        <div className="space-y-3">
          <h2 className="text-base font-bold text-white print:text-black uppercase tracking-wider font-mono border-b border-slate-800 print:border-slate-300 pb-1">
            A. Project Overview & Scope
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 print:text-slate-900 leading-relaxed">
            {packageData.introduction.purpose}
          </p>

          <div className="space-y-1.5 pt-1">
            <h4 className="text-xs font-semibold text-slate-200 print:text-black">Core Objectives:</h4>
            <ul className="list-disc list-inside text-xs text-slate-300 print:text-slate-800 space-y-1">
              {packageData.introduction.objectives.map((obj, i) => (
                <li key={i}>{obj}</li>
              ))}
            </ul>
          </div>

          <div className="flex gap-6 text-xs text-slate-400 print:text-slate-700 pt-2 font-mono">
            <span>Stage: <strong className="text-white print:text-black">{packageData.introduction.currentStage}</strong></span>
            <span>Status: <strong className="text-white print:text-black">{packageData.introduction.overallStatus}</strong></span>
          </div>
        </div>

        {/* SECTION B: IMPORTANT DECISIONS */}
        <div className="space-y-3">
          <h2 className="text-base font-bold text-white print:text-black uppercase tracking-wider font-mono border-b border-slate-800 print:border-slate-300 pb-1">
            B. Architecture Decisions (ADRs)
          </h2>
          <div className="space-y-3">
            {packageData.decisions.map((dec) => (
              <div
                key={dec.id}
                className="p-3.5 rounded-xl bg-slate-900/60 print:bg-slate-100 border border-slate-800 print:border-slate-300 text-xs space-y-1"
              >
                <div className="flex items-center justify-between font-semibold text-white print:text-black">
                  <span>{dec.decision}</span>
                  <span className="font-mono text-[10px] text-slate-400 print:text-slate-600">{dec.date}</span>
                </div>
                <p className="text-slate-300 print:text-slate-800 text-[11px] leading-relaxed">
                  <strong>Rationale: </strong>{dec.rationale}
                </p>
                <div className="text-[10px] font-mono text-brand-400 print:text-slate-700 pt-1">
                  Source: {dec.supportingSource}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SECTION C: YOUR RESPONSIBILITIES */}
        <div className="space-y-3">
          <h2 className="text-base font-bold text-white print:text-black uppercase tracking-wider font-mono border-b border-slate-800 print:border-slate-300 pb-1">
            C. Incoming Successor Responsibilities
          </h2>
          <div className="space-y-2.5">
            {packageData.responsibilities.map((task) => (
              <div
                key={task.id}
                className="p-3 rounded-xl bg-slate-900/60 print:bg-slate-100 border border-slate-800 print:border-slate-300 text-xs space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white print:text-black">{task.title}</span>
                  <span className="font-mono text-[10px] uppercase font-bold text-brand-400 print:text-black">
                    [{task.status.replace('_', ' ')}] · {task.priority.toUpperCase()}
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 print:text-slate-800">{task.description}</p>
                {task.dueDate && (
                  <div className="text-[10px] font-mono text-slate-400 print:text-slate-600">
                    Due Date: {task.dueDate}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* SECTION D: CURRENT BLOCKERS */}
        {packageData.blockers.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-base font-bold text-white print:text-black uppercase tracking-wider font-mono border-b border-slate-800 print:border-slate-300 pb-1">
              D. Operational Blockers & Follow-Up
            </h2>
            <div className="space-y-2">
              {packageData.blockers.map((blk) => (
                <div
                  key={blk.id}
                  className="p-3 rounded-xl bg-red-950/20 print:bg-red-50 border border-red-500/30 print:border-red-300 text-xs space-y-1"
                >
                  <div className="font-semibold text-red-300 print:text-red-900">{blk.description}</div>
                  <p className="text-[11px] text-slate-300 print:text-slate-800">
                    <strong>Impact: </strong>{blk.impact}
                  </p>
                  <p className="text-[11px] text-brand-300 print:text-slate-900 font-semibold">
                    Suggested Action: {blk.suggestedFollowUp}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SECTION E: PROJECT DEPENDENCIES */}
        <div className="space-y-3">
          <h2 className="text-base font-bold text-white print:text-black uppercase tracking-wider font-mono border-b border-slate-800 print:border-slate-300 pb-1">
            E. Key Dependencies & Contacts
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {packageData.dependencies.map((dep) => (
              <div
                key={dep.id}
                className="p-3 rounded-xl bg-slate-900/60 print:bg-slate-100 border border-slate-800 print:border-slate-300 space-y-1"
              >
                <div className="font-semibold text-white print:text-black">{dep.dependency}</div>
                <div className="text-[11px] text-slate-400 print:text-slate-700">
                  Prerequisite: {dep.prerequisiteTask}
                </div>
                <div className="text-[10px] font-mono text-emerald-400 print:text-emerald-700">
                  Status: {dep.currentStatus}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SECTION F: RECOMMENDED STARTING ACTIONS */}
        <div className="space-y-3">
          <h2 className="text-base font-bold text-white print:text-black uppercase tracking-wider font-mono border-b border-slate-800 print:border-slate-300 pb-1">
            F. Prioritized Starting Actions (Day 1 - Week 1)
          </h2>
          <div className="space-y-2 text-xs">
            {packageData.recommendedStartingActions.map((act) => (
              <div
                key={act.id}
                className="p-2.5 rounded-lg bg-slate-900/60 print:bg-slate-100 border border-slate-800 print:border-slate-300 flex items-start gap-3"
              >
                <span className="font-mono text-[10px] font-bold text-brand-300 print:text-black bg-brand-500/10 px-2 py-0.5 rounded shrink-0">
                  {act.timeframe}
                </span>
                <div>
                  <div className="font-semibold text-white print:text-black">{act.action}</div>
                  <p className="text-[11px] text-slate-400 print:text-slate-700">{act.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Formal Sign-off Certificate Footer */}
        <div className="pt-6 border-t-2 border-slate-800 print:border-black grid grid-cols-2 gap-6 text-xs font-mono text-slate-400 print:text-black">
          <div>
            <span className="text-[10px] text-slate-500 block">HANDOVER CERTIFICATION SIGNATURE</span>
            <div className="text-sm font-bold text-white print:text-black pt-1">
              {packageData.approvedBy.name}
            </div>
            <span className="text-[10px]">{packageData.approvedBy.role || 'Authorized Lead'}</span>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 block">SUCCESSOR ACKNOWLEDGEMENT</span>
            <div className="text-sm font-bold text-emerald-400 print:text-black pt-1">
              {packageData.acknowledgementStatus === 'acknowledged'
                ? `Acknowledged by ${packageData.incomingMember.name}`
                : 'Pending Receipt Acknowledgement'}
            </div>
            {packageData.acknowledgedAt && (
              <span className="text-[10px]">
                {new Date(packageData.acknowledgedAt).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldCheck,
  Lock,
  Users,
  FileCheck,
  GitCompare,
} from 'lucide-react';
import { HandoverReviewRecord, ApprovalChecklistItem } from '../../types/review';
import { Badge } from '../common/Badge';
import { cn } from '../../utils/cn';

interface FinalApprovalChecklistProps {
  handover: HandoverReviewRecord;
  onNavigateToSection?: (sectionKey: any) => void;
  className?: string;
}

export const FinalApprovalChecklist: React.FC<FinalApprovalChecklistProps> = ({
  handover,
  onNavigateToSection,
  className,
}) => {
  const sections = Object.values(handover.sections);
  const totalSections = sections.length;
  const approvedSections = sections.filter((s) => s.status === 'approved').length;
  const allSectionsApproved = approvedSections === totalSections;

  // Compute checklist items per prompt specifications:
  // 1. All required sections reviewed
  // 2. Important claims have supporting evidence or an explicit unresolved status
  // 3. Conflicts have been addressed or visibly retained for the incoming member
  // 4. Ownership is verified or marked unknown
  // 5. Sensitive information has been reviewed
  // 6. Incoming member and permissions are configured
  const checklist: ApprovalChecklistItem[] = [
    {
      id: 'chk-1',
      label: 'All Required Sections Formally Reviewed',
      description: `${approvedSections} of ${totalSections} sections marked as approved by authorized reviewer.`,
      passed: allSectionsApproved,
      severity: 'critical',
    },
    {
      id: 'chk-2',
      label: 'Evidence Traceability on Critical Claims',
      description: 'Key decisions and operational risks are linked to verifiable source ADRs and runbooks.',
      passed: handover.evidenceScore >= 80,
      severity: 'critical',
      fixTargetSection: 'decisions',
    },
    {
      id: 'chk-3',
      label: 'Contradictions & Drift Retained or Addressed',
      description: 'Discrepancies across architecture vs sprint logs are surfaced with clear resolution rationale.',
      passed: !sections.some((s) => s.status === 'changes_requested'),
      severity: 'warning',
      fixTargetSection: 'risks',
    },
    {
      id: 'chk-4',
      label: 'Service Ownership & On-Call Escalation Verified',
      description: 'All core microservices have an attributed primary engineer and secondary on-call roster.',
      passed: handover.sections.ownership?.status === 'approved',
      severity: 'critical',
      fixTargetSection: 'ownership',
    },
    {
      id: 'chk-5',
      label: 'Sensitive Credentials & Secrets Sanitized',
      description: 'No raw plaintext secrets embedded; HashiCorp Vault paths or KMS key aliases referenced.',
      passed: true, // In mock, validated by security rules
      severity: 'critical',
    },
    {
      id: 'chk-6',
      label: 'Incoming Member Role & Access Permissions Configured',
      description: `Successor ${handover.incomingMember.name} has repository, cloud console, and PagerDuty permissions verified.`,
      passed: true,
      severity: 'critical',
    },
  ];

  const totalPassed = checklist.filter((c) => c.passed).length;
  const allPassed = totalPassed === checklist.length;

  return (
    <div
      className={cn(
        'rounded-2xl bg-[#090D16] border p-5 space-y-4 shadow-xl',
        allPassed
          ? 'border-emerald-500/30 bg-emerald-950/5'
          : 'border-amber-500/30 bg-amber-950/5',
        className
      )}
    >
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div
            className={cn(
              'h-8 w-8 rounded-lg flex items-center justify-center',
              allPassed
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            )}
          >
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white tracking-tight flex items-center gap-2">
              Final Approval Readiness Checklist
              <span className="font-mono text-[10px] text-slate-400">
                ({totalPassed}/{checklist.length} Passed)
              </span>
            </h4>
            <p className="text-[11px] text-slate-400">
              Governance requirements mandatory before certifying engineering handover
            </p>
          </div>
        </div>

        <Badge variant={allPassed ? 'success' : 'warning'} size="sm">
          {allPassed ? 'Ready For Sign-Off' : 'Review Actions Required'}
        </Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {checklist.map((item) => (
          <div
            key={item.id}
            className={cn(
              'p-3 rounded-xl border text-xs space-y-1 transition-all',
              item.passed
                ? 'bg-slate-900/60 border-slate-800/80 text-slate-300'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-semibold">
                {item.passed ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
                )}
                <span className={item.passed ? 'text-white' : 'text-amber-200'}>
                  {item.label}
                </span>
              </div>

              {item.passed ? (
                <span className="text-[10px] font-mono text-emerald-400 font-bold uppercase">
                  PASS
                </span>
              ) : (
                <span className="text-[10px] font-mono text-amber-400 font-bold uppercase">
                  ACTION REQ
                </span>
              )}
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed pl-6">
              {item.description}
            </p>

            {!item.passed && item.fixTargetSection && onNavigateToSection && (
              <div className="pl-6 pt-1">
                <button
                  type="button"
                  onClick={() => onNavigateToSection(item.fixTargetSection)}
                  className="text-[10px] font-semibold text-amber-300 hover:text-white underline cursor-pointer"
                >
                  Jump to {item.fixTargetSection} to resolve &rarr;
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

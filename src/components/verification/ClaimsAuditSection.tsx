import React, { useState } from 'react';
import {
  Search,
  Filter,
  ShieldCheck,
  AlertTriangle,
  FileText,
  ExternalLink,
  Sparkles,
  Info,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from 'lucide-react';
import { VerificationClaim, ClaimsFilter } from '../../types/verification';
import { EvidenceStatusBadge } from './EvidenceStatusBadge';
import { UncertaintyBadge } from './UncertaintyBadge';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { Input } from '../common/Input';
import { cn } from '../../utils/cn';

interface ClaimsAuditSectionProps {
  claims: VerificationClaim[];
  onSelectClaim: (claim: VerificationClaim) => void;
  onVerifyClaim: (claim: VerificationClaim) => void;
  onFlagClaim: (claim: VerificationClaim) => void;
}

export const ClaimsAuditSection: React.FC<ClaimsAuditSectionProps> = ({
  claims,
  onSelectClaim,
  onVerifyClaim,
  onFlagClaim,
}) => {
  const [filter, setFilter] = useState<ClaimsFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Filtering logic
  const filteredClaims = claims.filter((claim) => {
    // Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchSearch =
        claim.claimText.toLowerCase().includes(q) ||
        claim.sourceDocName.toLowerCase().includes(q) ||
        claim.evidenceSnippet.toLowerCase().includes(q) ||
        claim.projectKey.toLowerCase().includes(q);
      if (!matchSearch) return false;
    }

    // Filter type
    if (filter === 'supported') return claim.evidenceStatus === 'supported';
    if (filter === 'partially_supported') return claim.evidenceStatus === 'partially_supported';
    if (filter === 'unsupported') return claim.evidenceStatus === 'unsupported';
    if (filter === 'uncertain') return claim.uncertaintyFlags && claim.uncertaintyFlags.length > 0;
    if (filter === 'conflicts')
      return !!claim.conflictId || claim.uncertaintyFlags.includes('contradictory');
    if (filter === 'verified') return claim.verificationStatus === 'verified';
    if (filter === 'unverified') return claim.verificationStatus === 'unverified';

    return true;
  });

  const totalSupported = claims.filter((c) => c.evidenceStatus === 'supported').length;
  const totalUnsupported = claims.filter((c) => c.evidenceStatus === 'unsupported').length;
  const totalUncertain = claims.filter((c) => c.uncertaintyFlags && c.uncertaintyFlags.length > 0).length;
  const totalConflicts = claims.filter((c) => !!c.conflictId || c.uncertaintyFlags.includes('contradictory')).length;

  return (
    <div className="space-y-6">
      {/* Controls Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search Input */}
        <div className="w-full md:w-80">
          <Input
            placeholder="Search claims, documents, passages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            leftIcon={<Search className="h-4 w-4 text-slate-400" />}
          />
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          <Button
            variant={filter === 'all' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('all')}
            className="text-xs h-8"
          >
            All Claims ({claims.length})
          </Button>
          <Button
            variant={filter === 'supported' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('supported')}
            className="text-xs h-8 text-emerald-400"
          >
            Supported ({totalSupported})
          </Button>
          <Button
            variant={filter === 'unsupported' ? 'danger' : 'ghost'}
            size="sm"
            onClick={() => setFilter('unsupported')}
            className="text-xs h-8"
          >
            Unsupported ({totalUnsupported})
          </Button>
          <Button
            variant={filter === 'uncertain' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('uncertain')}
            className="text-xs h-8 text-amber-400"
          >
            Uncertain ({totalUncertain})
          </Button>
          <Button
            variant={filter === 'conflicts' ? 'danger' : 'ghost'}
            size="sm"
            onClick={() => setFilter('conflicts')}
            className="text-xs h-8"
          >
            Conflicts ({totalConflicts})
          </Button>
          <Button
            variant={filter === 'verified' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('verified')}
            className="text-xs h-8"
          >
            Verified
          </Button>
          <Button
            variant={filter === 'unverified' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setFilter('unverified')}
            className="text-xs h-8"
          >
            Unverified
          </Button>
        </div>
      </div>

      {/* Claims Grid / List */}
      <div className="space-y-3.5">
        {filteredClaims.length === 0 ? (
          <Card className="bg-[#0F172A] border-slate-800 p-12 text-center">
            <Info className="h-10 w-10 text-slate-500 mx-auto mb-3" />
            <h4 className="text-sm font-semibold text-white">No Claims Match Your Filter</h4>
            <p className="text-xs text-slate-400 mt-1">
              Try adjusting your search terms or filter selection.
            </p>
          </Card>
        ) : (
          filteredClaims.map((claim) => (
            <div
              key={claim.id}
              className={cn(
                'group p-4 sm:p-5 rounded-2xl bg-[#0F172A] border transition-all space-y-3 hover:border-brand-500/40 cursor-pointer',
                claim.verificationStatus === 'verified'
                  ? 'border-emerald-500/20'
                  : claim.verificationStatus === 'disputed'
                  ? 'border-rose-500/30'
                  : 'border-slate-800'
              )}
              onClick={() => onSelectClaim(claim)}
            >
              {/* Header Row */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold text-brand-400">
                    {claim.projectKey}
                  </span>
                  <span className="text-[10px] font-mono uppercase bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                    {claim.section}
                  </span>
                  <EvidenceStatusBadge status={claim.evidenceStatus} size="sm" />

                  {claim.confidenceScore !== undefined && (
                    <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      <Sparkles className="h-3 w-3 text-brand-400" />
                      {claim.confidenceScore}% alignment
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {claim.verificationStatus === 'verified' ? (
                    <Badge variant="success" size="sm" dot>
                      Verified by {claim.verifiedBy?.name?.split(' ')[0] || 'Lead'}
                    </Badge>
                  ) : claim.verificationStatus === 'disputed' ? (
                    <Badge variant="danger" size="sm" dot>
                      Disputed
                    </Badge>
                  ) : (
                    <Badge variant="warning" size="sm" dot>
                      Pending Review
                    </Badge>
                  )}
                </div>
              </div>

              {/* Claim Statement */}
              <div>
                <p className="text-sm font-semibold text-white group-hover:text-brand-300 transition-colors">
                  "{claim.claimText}"
                </p>
              </div>

              {/* Uncertainty Badges (if any) */}
              {claim.uncertaintyFlags && claim.uncertaintyFlags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {claim.uncertaintyFlags.map((flag) => (
                    <UncertaintyBadge key={flag} type={flag} />
                  ))}
                </div>
              )}

              {/* Source Passage Snippet & Footer */}
              <div className="pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2 text-slate-400 truncate max-w-xl">
                  <FileText className="h-3.5 w-3.5 text-brand-400 shrink-0" />
                  <span className="font-medium text-slate-300 truncate">
                    {claim.sourceDocName}
                  </span>
                  <span className="font-mono text-[11px] text-slate-500">
                    ({claim.pageOrSection})
                  </span>
                </div>

                <div className="flex items-center gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onSelectClaim(claim)}
                    className="text-xs h-7 text-brand-400 hover:text-brand-300"
                    rightIcon={<ExternalLink className="h-3 w-3" />}
                  >
                    Inspect Evidence
                  </Button>

                  {claim.verificationStatus !== 'verified' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onVerifyClaim(claim)}
                      leftIcon={<ShieldCheck className="h-3 w-3 text-emerald-400" />}
                      className="text-xs h-7 border-slate-700"
                    >
                      Verify
                    </Button>
                  )}

                  {claim.verificationStatus !== 'disputed' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onFlagClaim(claim)}
                      leftIcon={<AlertTriangle className="h-3 w-3 text-amber-400" />}
                      className="text-xs h-7 text-slate-400 hover:text-amber-300"
                    >
                      Flag
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

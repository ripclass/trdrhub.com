/**
 * Verdict Tab — answers "can I submit this?" in 3 seconds.
 *
 * Design principles:
 * - Answer first, details later
 * - No system diagnostics, no extraction noise
 * - Bank examiner language, not developer language
 * - One sentence verdict, numbered action items, LC summary
 */

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileText,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { IssueCard } from '@/types/lcopilot';
import type { ValidationDocument } from '@/types/lcopilot';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface VerdictTabProps {
  issueCards: IssueCard[];
  documents: ValidationDocument[];
  totalDocuments: number;
  complianceScore: number;
  lcNumber: string;
  lcData?: {
    applicant?: string;
    beneficiary?: string;
    amount?: string | number;
    currency?: string;
    expiryDate?: string;
  };
  /** 46A Documents Required — raw clause text array from LC */
  documentsRequired?: Array<string | { raw_text?: string; document_type?: string }>;
  /** 47A Additional Conditions — string array from LC */
  additionalConditions?: string[];
  /** Bank profile — issuing bank + tolerance policy */
  bankProfile?: { name?: string; policy_label?: string } | null;
  /** Amendments available from the validation result */
  amendmentsCount?: number;
  amendmentsFee?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type Severity = 'critical' | 'major' | 'minor';

function normSeverity(s: string | undefined): Severity {
  const low = (s ?? '').toLowerCase();
  if (['critical', 'high', 'error', 'fail'].includes(low)) return 'critical';
  if (['major', 'warning', 'warn', 'medium'].includes(low)) return 'major';
  return 'minor';
}

function deriveVerdict(critical: number, major: number, minor: number) {
  if (critical > 0)
    return {
      level: 'reject' as const,
      label: 'REJECT',
      headline: `${critical} blocking discrepanc${critical === 1 ? 'y' : 'ies'} found`,
      sublabel: 'Do not submit until blocking discrepancies are resolved.',
      color: 'bg-red-500/10 border-red-500/40 text-red-400',
      iconColor: 'text-red-500',
      Icon: XCircle,
    };
  if (major > 0)
    return {
      level: 'review' as const,
      label: 'REVIEW',
      headline: `${major} discrepanc${major === 1 ? 'y' : 'ies'} need attention`,
      sublabel: 'These may cause rejection. Review and decide before submitting.',
      color: 'bg-amber-500/10 border-amber-500/40 text-amber-400',
      iconColor: 'text-amber-500',
      Icon: AlertTriangle,
    };
  if (minor > 0)
    return {
      level: 'pass' as const,
      label: 'PASS',
      headline: 'Presentation is compliant with minor notes',
      sublabel: 'Minor advisory findings only. Safe to submit.',
      color: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400',
      iconColor: 'text-emerald-500',
      Icon: CheckCircle,
    };
  return {
    level: 'pass' as const,
    label: 'CLEAN',
    headline: 'No discrepancies found',
    sublabel: 'All documents checked. Presentation appears compliant.',
    color: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400',
    iconColor: 'text-emerald-500',
    Icon: CheckCircle,
  };
}

function deduplicateIssues(cards: IssueCard[]): IssueCard[] {
  const seen = new Set<string>();
  return cards.filter((c) => {
    // Deduplicate by title (normalized) — same finding from different layers
    const key = (c.title ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function formatAmount(amount: string | number | undefined, currency: string | undefined): string {
  if (amount == null) return '';
  const num = typeof amount === 'string' ? parseFloat(amount.replace(/,/g, '')) : amount;
  if (isNaN(num)) return String(amount);
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
  return currency ? `${currency} ${formatted}` : formatted;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function VerdictTab({
  issueCards,
  documents,
  totalDocuments,
  complianceScore,
  lcNumber,
  lcData,
  documentsRequired,
  additionalConditions,
  bankProfile,
  amendmentsCount,
  amendmentsFee,
}: VerdictTabProps) {
  const dedupedIssues = useMemo(() => deduplicateIssues(issueCards), [issueCards]);

  const counts = useMemo(() => {
    let critical = 0, major = 0, minor = 0;
    for (const card of dedupedIssues) {
      const s = normSeverity(card.severity);
      if (s === 'critical') critical++;
      else if (s === 'major') major++;
      else minor++;
    }
    return { critical, major, minor, total: critical + major + minor };
  }, [dedupedIssues]);

  const verdict = useMemo(
    () => deriveVerdict(counts.critical, counts.major, counts.minor),
    [counts],
  );

  const actionItems = useMemo(() => {
    // Only show real discrepancies (critical + major), not minor advisories
    return dedupedIssues
      .filter((c) => normSeverity(c.severity) !== 'minor')
      .map((c) => ({
        title: c.title ?? 'Review required',
        severity: normSeverity(c.severity),
        fix: (c as any).next_action ?? c.suggestion ?? (c as any).suggested_fix ?? '',
        document: ((c.documents ?? [])[0] ?? '').replace(/_/g, ' '),
      }));
  }, [dedupedIssues]);

  const docsWithIssues = useMemo(() => {
    const docSet = new Set<string>();
    for (const card of dedupedIssues) {
      for (const d of card.documents ?? []) {
        if (normSeverity(card.severity) !== 'minor') docSet.add(d);
      }
    }
    return docSet.size;
  }, [dedupedIssues]);

  const cleanDocs = totalDocuments - docsWithIssues;

  return (
    <div className="space-y-6">
      {/* Hero verdict card */}
      <Card className={cn('border-2 shadow-lg', verdict.color)}>
        <CardContent className="pt-6 pb-6">
          <div className="flex items-start gap-4">
            <verdict.Icon className={cn('w-10 h-10 flex-shrink-0 mt-1', verdict.iconColor)} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <span className={cn(
                  'text-sm font-bold tracking-widest px-3 py-1 rounded',
                  verdict.level === 'reject' ? 'bg-red-500 text-white' :
                  verdict.level === 'review' ? 'bg-amber-500 text-black' :
                  'bg-emerald-500 text-white'
                )}>
                  {verdict.label}
                </span>
                {counts.total > 0 && (
                  <span className="text-sm text-muted-foreground">
                    {counts.critical > 0 && <span className="text-red-400 font-semibold">{counts.critical} critical</span>}
                    {counts.critical > 0 && counts.major > 0 && ' · '}
                    {counts.major > 0 && <span className="text-amber-400 font-semibold">{counts.major} major</span>}
                    {(counts.critical > 0 || counts.major > 0) && counts.minor > 0 && ' · '}
                    {counts.minor > 0 && <span className="text-muted-foreground">{counts.minor} minor</span>}
                  </span>
                )}
              </div>
              <h2 className="text-xl font-semibold text-foreground mb-1">{verdict.headline}</h2>
              <p className="text-sm text-muted-foreground">{verdict.sublabel}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Presentation summary strip */}
      <div className="grid gap-3 sm:grid-cols-4">
        <div className="p-4 rounded-lg border bg-card">
          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Documents</p>
          <p className="text-2xl font-bold">{totalDocuments}</p>
          <p className="text-xs text-muted-foreground">
            {cleanDocs > 0 && `${cleanDocs} clean`}
            {cleanDocs > 0 && docsWithIssues > 0 && ' · '}
            {docsWithIssues > 0 && <span className="text-red-400">{docsWithIssues} with issues</span>}
            {cleanDocs === 0 && docsWithIssues === 0 && 'processed'}
          </p>
        </div>
        <div className="p-4 rounded-lg border bg-card">
          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Findings</p>
          <p className="text-2xl font-bold">{counts.total}</p>
          <p className="text-xs text-muted-foreground">
            {counts.total === 0 ? 'none' : 'see Findings tab'}
          </p>
        </div>
        <div className="p-4 rounded-lg border bg-card">
          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Compliance</p>
          <p className={cn(
            'text-2xl font-bold',
            complianceScore >= 80 ? 'text-emerald-500' :
            complianceScore >= 40 ? 'text-amber-500' :
            'text-red-500'
          )}>
            {complianceScore}%
          </p>
          <p className="text-xs text-muted-foreground">
            {complianceScore >= 80 ? 'submission ready' :
             complianceScore >= 40 ? 'needs attention' :
             'blocked'}
          </p>
        </div>
        <div className="p-4 rounded-lg border bg-card">
          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">LC</p>
          <p className="text-lg font-bold font-mono truncate">{lcNumber}</p>
          <p className="text-xs text-muted-foreground truncate">
            {formatAmount(lcData?.amount, lcData?.currency) || 'amount N/A'}
          </p>
        </div>
      </div>

      {/* Action items — the "what to fix" section */}
      {actionItems.length > 0 && (
        <Card className="border shadow-soft">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">What to Fix</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {actionItems.map((item, i) => (
              <div key={i} className="flex items-start gap-3 py-2">
                <span className={cn(
                  'flex-shrink-0 mt-0.5 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold',
                  item.severity === 'critical'
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-amber-500/20 text-amber-400',
                )}>
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">{item.title}</p>
                  {item.fix && (
                    <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                      <ArrowRight className="w-3 h-3 flex-shrink-0" />
                      {item.fix}
                    </p>
                  )}
                  {item.document && (
                    <Badge variant="outline" className="text-[10px] mt-1">
                      <FileText className="w-3 h-3 mr-1" />
                      {item.document}
                    </Badge>
                  )}
                </div>
                <Badge
                  variant="outline"
                  className={cn(
                    'text-[10px] flex-shrink-0',
                    item.severity === 'critical'
                      ? 'bg-red-500/10 text-red-400 border-red-500/30'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/30',
                  )}
                >
                  {item.severity}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Clean pass — positive reinforcement */}
      {actionItems.length === 0 && counts.total === 0 && (
        <Card className="border border-emerald-500/30 bg-emerald-500/5">
          <CardContent className="pt-6 pb-6 text-center">
            <CheckCircle className="w-12 h-12 mx-auto text-emerald-500 mb-3" />
            <p className="text-lg font-semibold text-foreground">All checks passed</p>
            <p className="text-sm text-muted-foreground mt-1">
              Your presentation set is compliant. Proceed to the Customs Pack tab to prepare submission documents.
            </p>
          </CardContent>
        </Card>
      )}

      {/* LC summary — compact */}
      {lcData && (
        <div className="grid gap-3 sm:grid-cols-2 text-sm">
          {lcData.applicant && (
            <div className="p-3 rounded-lg border bg-card">
              <p className="text-xs uppercase tracking-widest text-muted-foreground mb-0.5">Applicant</p>
              <p className="font-medium truncate">{lcData.applicant}</p>
            </div>
          )}
          {lcData.beneficiary && (
            <div className="p-3 rounded-lg border bg-card">
              <p className="text-xs uppercase tracking-widest text-muted-foreground mb-0.5">Beneficiary</p>
              <p className="font-medium truncate">{lcData.beneficiary}</p>
            </div>
          )}
        </div>
      )}

      {/* LC Requirements — what the LC demands */}
      {((documentsRequired && documentsRequired.length > 0) || (additionalConditions && additionalConditions.length > 0)) && (
        <Card className="border shadow-soft">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">LC Requirements</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {documentsRequired && documentsRequired.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">
                  Field 46A — Documents Required
                </p>
                <ol className="space-y-1.5 list-decimal list-inside">
                  {documentsRequired.map((doc, i) => {
                    const text = typeof doc === 'string' ? doc : (doc?.raw_text ?? '');
                    if (!text) return null;
                    return (
                      <li key={i} className="text-sm text-foreground leading-relaxed">
                        {text}
                      </li>
                    );
                  })}
                </ol>
              </div>
            )}
            {additionalConditions && additionalConditions.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">
                  Field 47A — Additional Conditions
                </p>
                <ol className="space-y-1.5 list-decimal list-inside">
                  {additionalConditions.map((cond, i) => (
                    <li key={i} className="text-sm text-foreground leading-relaxed">
                      {cond}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

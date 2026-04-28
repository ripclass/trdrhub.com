/**
 * Findings Tab — the examiner's report.
 *
 * Each finding is a self-contained discrepancy notice in bank language.
 * No badges overload, no workflow lanes, no extraction diagnostics.
 * Just: what's wrong, what the LC says, what the doc says, the rule, the fix.
 */

import { useMemo, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  XCircle,
  AlertTriangle,
  Info,
  Scale,
  Ban,
  Lightbulb,
  BookOpen,
  Filter,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { IssueCard } from '@/types/lcopilot';
import { BankProfileBadge } from '@/pages/exporter/results/BankProfileBadge';
import { isDiscrepancyWorkflowEnabled } from '@/lib/lcopilot/featureFlags';
import { DiscrepancyActions } from '@/components/discrepancy/DiscrepancyActions';
import { CommentThread } from '@/components/discrepancy/CommentThread';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Amendment {
  issue_id?: string;
  field?: { tag?: string; name?: string; current?: string; proposed?: string };
  current_value?: string;
  proposed_value?: string;
  narrative?: string;
  swift_mt707_text?: string;
  mt707_text?: string;
  iso20022_xml?: string;
  bank_processing_days?: number;
  estimated_fee_usd?: number;
  estimated_fee?: string;
}

interface FindingsTabProps {
  issueCards: IssueCard[];
  amendments?: Amendment[];
  totalAmendmentFee?: number;
  onDownloadMT707?: (amendment: Amendment) => void;
  onDownloadISO20022?: (amendment: Amendment) => void;
  /** The full bank profile object — passed straight to BankProfileBadge */
  bankProfile?: any;
}

type SeverityFilter = 'all' | 'critical' | 'major' | 'minor';
type Severity = 'critical' | 'major' | 'minor';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normSeverity(s: string | undefined): Severity {
  const low = (s ?? '').toLowerCase();
  if (['critical', 'high', 'error', 'fail', 'discrepancy'].includes(low)) return 'critical';
  if (['major', 'warning', 'warn', 'medium'].includes(low)) return 'major';
  return 'minor';
}

function deduplicateIssues(cards: IssueCard[]): IssueCard[] {
  const seen = new Set<string>();
  return cards.filter((c) => {
    const key = (c.title ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

const SEVERITY_CONFIG = {
  critical: {
    label: 'Critical Discrepancy',
    Icon: XCircle,
    border: 'border-l-red-500',
    headerBg: 'bg-red-500/5',
    badgeBg: 'bg-red-500 text-white',
    iconColor: 'text-red-500',
  },
  major: {
    label: 'Major Finding',
    Icon: AlertTriangle,
    border: 'border-l-amber-500',
    headerBg: 'bg-amber-500/5',
    badgeBg: 'bg-amber-500 text-black',
    iconColor: 'text-amber-500',
  },
  minor: {
    label: 'Advisory',
    Icon: Info,
    border: 'border-l-blue-400',
    headerBg: 'bg-blue-500/5',
    badgeBg: 'bg-blue-500 text-white',
    iconColor: 'text-blue-400',
  },
} as const;

// ---------------------------------------------------------------------------
// Finding Card
// ---------------------------------------------------------------------------

function FindingCard({ issue, index }: { issue: IssueCard; index: number }) {
  const severity = normSeverity(issue.severity);
  const config = SEVERITY_CONFIG[severity];
  const Icon = config.Icon;
  const workflowEnabled = isDiscrepancyWorkflowEnabled();
  const discrepancyId = typeof issue.id === 'string' ? issue.id : null;

  const lcClause = (issue as any).lc_clause;
  const impact = (issue as any).impact;
  const found = (issue as any).found ?? issue.actual;
  const expected = issue.expected;
  const ucpRef = issue.ucpReference || (issue as any).ucp_reference;
  const fix = (issue as any).next_action ?? issue.suggestion ?? (issue as any).suggested_fix;
  const description = (issue as any).examiner_note ?? issue.description;
  const docName = ((issue.documents ?? [])[0] ?? '').replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());

  return (
    <Card className={cn('border-l-4 shadow-sm', config.border)}>
      {/* Header */}
      <div className={cn('px-5 py-4', config.headerBg)}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <Icon className={cn('w-5 h-5 mt-0.5 flex-shrink-0', config.iconColor)} />
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className={cn('text-[10px] font-bold tracking-widest px-2 py-0.5 rounded', config.badgeBg)}>
                  {config.label.toUpperCase()}
                </span>
                <span className="text-xs text-muted-foreground">#{index + 1}</span>
              </div>
              <h3 className="text-base font-semibold text-foreground">
                {issue.title ?? 'Review Required'}
              </h3>
              {docName && (
                <p className="text-xs text-muted-foreground mt-0.5">{docName}</p>
              )}
            </div>
          </div>
          {ucpRef && (
            <Badge variant="secondary" className="text-[10px] flex-shrink-0 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              <BookOpen className="w-3 h-3 mr-1" />
              {ucpRef.replace('UCP600 Article ', 'UCP600 Art ').replace('UCP600 ', '')}
            </Badge>
          )}
        </div>
      </div>

      <CardContent className="px-5 py-4 space-y-4">
        {/* LC Clause quote */}
        {lcClause && (
          <div className="p-3 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-800">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-amber-600 dark:text-amber-400 flex items-center gap-1 mb-1">
              <Scale className="w-3 h-3" />
              LC Clause
            </p>
            <p className="text-sm text-amber-900 dark:text-amber-100 italic leading-relaxed">
              &ldquo;{lcClause}&rdquo;
            </p>
          </div>
        )}

        {/* Expected vs Found */}
        {(expected || found) && (
          <div className="grid gap-3 sm:grid-cols-2">
            {expected && (
              <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg border border-emerald-200 dark:border-emerald-800">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-600 dark:text-emerald-400 mb-1">Expected</p>
                <p className="text-sm font-mono text-emerald-900 dark:text-emerald-100">{expected}</p>
              </div>
            )}
            {found && (
              <div className="p-3 bg-red-50 dark:bg-red-950/30 rounded-lg border border-red-200 dark:border-red-800">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-red-600 dark:text-red-400 mb-1">Found</p>
                <p className="text-sm font-mono text-red-900 dark:text-red-100">{found}</p>
              </div>
            )}
          </div>
        )}

        {/* Description — the examiner's explanation */}
        {description && (
          <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
        )}

        {/* Impact */}
        {impact && (
          <div className="p-3 bg-rose-50 dark:bg-rose-950/30 rounded-lg border border-rose-200 dark:border-rose-800">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-rose-600 dark:text-rose-400 flex items-center gap-1 mb-1">
              <Ban className="w-3 h-3" />
              Bank Impact
            </p>
            <p className="text-sm text-rose-900 dark:text-rose-100">{impact}</p>
          </div>
        )}

        {/* How to fix */}
        {fix && (
          <div className="p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-400 flex items-center gap-1 mb-1">
              <Lightbulb className="w-3 h-3" />
              How to Fix
            </p>
            <p className="text-sm text-blue-900 dark:text-blue-100">{fix}</p>
          </div>
        )}

        {/* Phase A2 — workflow actions + comment thread.
         *
         * Gated by VITE_LCOPILOT_DISCREPANCY_WORKFLOW so legacy users
         * see read-only cards. The id must be a Discrepancy.id UUID
         * (option-B persistence in finding_persistence.py); otherwise
         * both child components self-suppress. */}
        {workflowEnabled && (
          <>
            <DiscrepancyActions discrepancyId={discrepancyId} />
            <CommentThread discrepancyId={discrepancyId} />
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function FindingsTab({ issueCards, amendments, totalAmendmentFee, onDownloadMT707, onDownloadISO20022, bankProfile }: FindingsTabProps) {
  const [amendmentsExpanded, setAmendmentsExpanded] = useState(false);
  const [previewContent, setPreviewContent] = useState<{ title: string; content: string } | null>(null);
  const [filter, setFilter] = useState<SeverityFilter>('all');
  const deduped = useMemo(() => deduplicateIssues(issueCards), [issueCards]);

  const counts = useMemo(() => {
    let critical = 0, major = 0, minor = 0;
    for (const c of deduped) {
      const s = normSeverity(c.severity);
      if (s === 'critical') critical++;
      else if (s === 'major') major++;
      else minor++;
    }
    return { critical, major, minor, total: critical + major + minor };
  }, [deduped]);

  const filtered = useMemo(() => {
    if (filter === 'all') return deduped;
    return deduped.filter((c) => normSeverity(c.severity) === filter);
  }, [deduped, filter]);

  // Sort: critical first, then major, then minor
  const sorted = useMemo(() => {
    const order: Record<Severity, number> = { critical: 0, major: 1, minor: 2 };
    return [...filtered].sort((a, b) => order[normSeverity(a.severity)] - order[normSeverity(b.severity)]);
  }, [filtered]);

  if (deduped.length === 0) {
    return (
      <Card className="border border-emerald-500/30 bg-emerald-500/5">
        <CardContent className="pt-8 pb-8 text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-emerald-500/20 flex items-center justify-center">
            <Scale className="w-6 h-6 text-emerald-500" />
          </div>
          <p className="text-lg font-semibold text-foreground">No findings</p>
          <p className="text-sm text-muted-foreground mt-1">
            All documents checked against LC requirements. No discrepancies detected.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="w-4 h-4 text-muted-foreground" />
        {(
          [
            { value: 'all', label: `All (${counts.total})` },
            { value: 'critical', label: `Critical (${counts.critical})`, color: 'text-red-400' },
            { value: 'major', label: `Major (${counts.major})`, color: 'text-amber-400' },
            { value: 'minor', label: `Advisory (${counts.minor})`, color: 'text-blue-400' },
          ] as const
        ).map((opt) => (
          <Button
            key={opt.value}
            size="sm"
            variant={filter === opt.value ? 'default' : 'outline'}
            className={cn('text-xs h-7', filter !== opt.value && (opt as any).color)}
            onClick={() => setFilter(opt.value)}
          >
            {opt.label}
          </Button>
        ))}
      </div>

      {/* Bank examination policy — sets context for how strict findings are judged */}
      {bankProfile && (
        <BankProfileBadge profile={bankProfile} />
      )}

      {/* Amendments — full featured with both formats, preview, fees */}
      {amendments && amendments.length > 0 && (
        <Card className="border border-blue-500/30 bg-blue-500/5">
          <CardContent className="py-4 px-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/20">
                  <Lightbulb className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-blue-400">
                    {amendments.length} Amendment{amendments.length > 1 ? 's' : ''} Available
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Fix via LC amendment instead of amending documents
                    {totalAmendmentFee != null && totalAmendmentFee > 0 && (
                      <> &middot; Est. total fee: <span className="font-medium">USD {totalAmendmentFee.toFixed(2)}</span></>
                    )}
                  </p>
                </div>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="text-blue-400 border-blue-500/30 hover:bg-blue-500/10"
                onClick={() => setAmendmentsExpanded(!amendmentsExpanded)}
              >
                {amendmentsExpanded ? 'Hide' : 'View'} Amendments
              </Button>
            </div>

            {amendmentsExpanded && (
              <div className="mt-4 pt-4 border-t border-blue-500/20 space-y-3">
                {amendments.map((a, i) => {
                  const current = a.field?.current ?? a.current_value ?? '';
                  const proposed = a.field?.proposed ?? a.proposed_value ?? '';
                  const fee = a.estimated_fee_usd ?? (a.estimated_fee ? parseFloat(a.estimated_fee) : null);
                  const mt707 = a.swift_mt707_text ?? a.mt707_text;

                  return (
                    <div key={i} className="p-3 rounded-lg bg-background/50 space-y-2">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium">
                            {a.field?.tag ? `Field ${a.field.tag}: ` : ''}{a.field?.name ?? `Amendment ${i + 1}`}
                          </p>
                          {(current || proposed) && (
                            <p className="text-xs mt-0.5">
                              <span className="text-red-400 line-through">{current}</span>
                              {current && proposed && ' → '}
                              <span className="text-emerald-400">{proposed}</span>
                            </p>
                          )}
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {a.narrative ?? 'Amendment to resolve discrepancy'}
                            {a.bank_processing_days != null && <> &middot; ~{a.bank_processing_days} days</>}
                            {fee != null && <> &middot; USD {fee.toFixed(2)}</>}
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          {mt707 && (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-xs h-7 text-muted-foreground hover:text-foreground"
                                title="Preview MT707 content"
                                onClick={() => setPreviewContent({
                                  title: `MT707 — ${a.field?.name ?? 'Amendment'}`,
                                  content: mt707,
                                })}
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </Button>
                              {onDownloadMT707 && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="text-xs h-7 text-blue-400 hover:text-blue-300"
                                  title="Download SWIFT MT707"
                                  onClick={() => onDownloadMT707(a)}
                                >
                                  <BookOpen className="w-3.5 h-3.5 mr-1" />
                                  MT707
                                </Button>
                              )}
                            </>
                          )}
                          {a.iso20022_xml && onDownloadISO20022 && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-xs h-7 text-emerald-400 hover:text-emerald-300"
                              title="Download ISO20022 XML (trad.002)"
                              onClick={() => onDownloadISO20022(a)}
                            >
                              <BookOpen className="w-3.5 h-3.5 mr-1" />
                              ISO20022
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
                <p className="text-[10px] text-muted-foreground pt-2 border-t border-blue-500/10">
                  <span className="font-medium">MT707:</span> Legacy SWIFT FIN format &middot;
                  <span className="font-medium ml-2">ISO20022:</span> Modern XML standard (trad.002)
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* MT707 Preview Dialog */}
      {previewContent && (
        <Card className="border border-blue-500/30">
          <CardContent className="py-3 px-5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-semibold">{previewContent.title}</p>
              <Button size="sm" variant="ghost" className="text-xs h-6" onClick={() => setPreviewContent(null)}>Close</Button>
            </div>
            <pre className="text-xs font-mono bg-background/80 rounded p-3 overflow-x-auto max-h-[300px] overflow-y-auto whitespace-pre-wrap">
              {previewContent.content}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Finding cards */}
      <div className="space-y-4">
        {sorted.map((issue, i) => (
          <FindingCard key={issue.id ?? i} issue={issue} index={i} />
        ))}
      </div>

      {filtered.length === 0 && deduped.length > 0 && (
        <p className="text-sm text-muted-foreground text-center py-6">
          No findings match the selected filter.
        </p>
      )}
    </div>
  );
}

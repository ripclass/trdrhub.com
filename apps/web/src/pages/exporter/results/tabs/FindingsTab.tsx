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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { IssueCard } from '@/types/lcopilot';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Amendment {
  field?: { tag?: string; name?: string };
  current_value?: string;
  proposed_value?: string;
  swift_mt707_text?: string;
  iso20022_xml?: string;
  estimated_fee?: string;
}

interface FindingsTabProps {
  issueCards: IssueCard[];
  amendments?: Amendment[];
  onDownloadMT707?: (amendment: Amendment) => void;
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
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function FindingsTab({ issueCards, amendments, onDownloadMT707 }: FindingsTabProps) {
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

      {/* Amendments banner — actionable */}
      {amendments && amendments.length > 0 && (
        <Card className="border border-blue-500/30 bg-blue-500/5">
          <CardContent className="py-4 px-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-blue-400">
                  {amendments.length} Amendment{amendments.length > 1 ? 's' : ''} Available
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Some discrepancies below can be resolved by amending the LC instead of amending the documents.
                </p>
              </div>
            </div>
            <div className="mt-3 space-y-2">
              {amendments.map((a, i) => (
                <div key={i} className="flex items-center justify-between gap-3 py-2 px-3 rounded-lg bg-blue-500/5 border border-blue-500/10">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">
                      {a.field?.name ?? a.field?.tag ?? `Amendment ${i + 1}`}
                    </p>
                    {a.current_value && a.proposed_value && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        <span className="text-red-400 line-through">{a.current_value}</span>
                        {' → '}
                        <span className="text-emerald-400">{a.proposed_value}</span>
                      </p>
                    )}
                    {a.estimated_fee && (
                      <p className="text-[10px] text-muted-foreground">Est. fee: {a.estimated_fee}</p>
                    )}
                  </div>
                  {a.swift_mt707_text && onDownloadMT707 && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-xs h-7 border-blue-500/30 text-blue-400 hover:bg-blue-500/10 shrink-0"
                      onClick={() => onDownloadMT707(a)}
                    >
                      Download MT707
                    </Button>
                  )}
                </div>
              ))}
            </div>
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

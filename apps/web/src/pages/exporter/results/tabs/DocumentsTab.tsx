/**
 * Documents Tab — per-document compliance view.
 *
 * This is how a bank examiner works: document by document.
 * Each doc shows status, field count, and issues on that doc.
 * Click to expand → see extracted fields with discrepant ones highlighted.
 */

import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { IssueCard } from '@/types/lcopilot';
import type { ValidationDocument } from '@/types/lcopilot';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DocumentsTabProps {
  documents: ValidationDocument[];
  issueCards: IssueCard[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DOCUMENT_LABELS: Record<string, string> = {
  letter_of_credit: 'Letter of Credit',
  commercial_invoice: 'Commercial Invoice',
  bill_of_lading: 'Bill of Lading',
  ocean_bill_of_lading: 'Ocean Bill of Lading',
  packing_list: 'Packing List',
  certificate_of_origin: 'Certificate of Origin',
  insurance_certificate: 'Insurance Certificate',
  insurance_policy: 'Insurance Policy',
  inspection_certificate: 'Inspection Certificate',
  beneficiary_certificate: 'Beneficiary Certificate',
  draft: 'Draft / Bill of Exchange',
  air_waybill: 'Air Waybill',
  weight_certificate: 'Weight Certificate',
  supporting_document: 'Supporting Document',
};

function humanizeDocType(typeKey: string): string {
  return DOCUMENT_LABELS[typeKey] ?? typeKey.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function humanizeFieldName(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bLc\b/, 'LC')
    .replace(/\bBl\b/, 'BL')
    .replace(/\bHs\b/, 'HS')
    .replace(/\bPo\b/, 'PO');
}

function formatFieldValue(val: unknown): string {
  if (val == null || val === '') return '—';
  if (typeof val === 'object') {
    try { return JSON.stringify(val); } catch { return String(val); }
  }
  return String(val);
}

function getDocIssues(doc: ValidationDocument, issueCards: IssueCard[]): IssueCard[] {
  const typeKey = doc.typeKey || doc.type || '';
  const name = doc.name || doc.filename || '';
  return issueCards.filter((ic) =>
    (ic.documents ?? []).some(
      (d) => d === typeKey || d === doc.type || d === name || d.toLowerCase() === typeKey.toLowerCase(),
    ),
  );
}

function normSeverity(s: string | undefined): 'critical' | 'major' | 'minor' {
  const low = (s ?? '').toLowerCase();
  if (['critical', 'high', 'error', 'fail'].includes(low)) return 'critical';
  if (['major', 'warning', 'warn', 'medium'].includes(low)) return 'major';
  return 'minor';
}

function worstSeverity(issues: IssueCard[]): 'clean' | 'critical' | 'major' | 'minor' {
  let worst: 'clean' | 'critical' | 'major' | 'minor' = 'clean';
  for (const ic of issues) {
    const s = normSeverity(ic.severity);
    if (s === 'critical') return 'critical';
    if (s === 'major') worst = 'major';
    else if (s === 'minor' && worst === 'clean') worst = 'minor';
  }
  return worst;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusIcon({ status }: { status: 'clean' | 'critical' | 'major' | 'minor' }) {
  if (status === 'critical') return <XCircle className="w-5 h-5 text-red-500" />;
  if (status === 'major') return <AlertTriangle className="w-5 h-5 text-amber-500" />;
  if (status === 'minor') return <AlertTriangle className="w-5 h-5 text-blue-400" />;
  return <CheckCircle className="w-5 h-5 text-emerald-500" />;
}

function FieldRow({ name, value, isDiscrepant }: { name: string; value: string; isDiscrepant: boolean }) {
  return (
    <div className={cn(
      'flex justify-between items-baseline py-1.5 px-2 rounded text-sm',
      isDiscrepant && 'bg-red-500/5 border-l-2 border-red-500',
    )}>
      <span className="text-muted-foreground min-w-[40%]">{humanizeFieldName(name)}</span>
      <span className={cn(
        'font-mono text-right max-w-[58%] truncate',
        isDiscrepant ? 'text-red-400 font-semibold' : 'text-foreground',
      )}>
        {value}
      </span>
    </div>
  );
}

function IssueInline({ issue }: { issue: IssueCard }) {
  const severity = normSeverity(issue.severity);
  return (
    <div className={cn(
      'flex items-start gap-2 py-2 px-3 rounded-lg text-sm',
      severity === 'critical' ? 'bg-red-500/10 border border-red-500/20' :
      severity === 'major' ? 'bg-amber-500/10 border border-amber-500/20' :
      'bg-blue-500/10 border border-blue-500/20',
    )}>
      <StatusIcon status={severity} />
      <div className="flex-1 min-w-0">
        <p className="font-medium">{issue.title}</p>
        {issue.expected && (
          <p className="text-xs text-muted-foreground mt-0.5">
            Expected: {issue.expected}
            {(issue as any).found && ` · Found: ${(issue as any).found}`}
          </p>
        )}
      </div>
      <Badge variant="outline" className={cn(
        'text-[10px] flex-shrink-0',
        severity === 'critical' ? 'text-red-400 border-red-500/30' :
        severity === 'major' ? 'text-amber-400 border-amber-500/30' :
        'text-blue-400 border-blue-500/30',
      )}>
        {severity}
      </Badge>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function DocumentsTab({ documents, issueCards }: DocumentsTabProps) {
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set());

  const toggleDoc = (id: string) => {
    setExpandedDocs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Sort: LC first, then docs with issues, then clean docs
  const sorted = useMemo(() => {
    return [...documents].sort((a, b) => {
      const aIsLc = (a.typeKey || a.type || '').includes('letter_of_credit') ? 0 : 1;
      const bIsLc = (b.typeKey || b.type || '').includes('letter_of_credit') ? 0 : 1;
      if (aIsLc !== bIsLc) return aIsLc - bIsLc;
      const aIssues = getDocIssues(a, issueCards).length;
      const bIssues = getDocIssues(b, issueCards).length;
      return bIssues - aIssues; // more issues first
    });
  }, [documents, issueCards]);

  if (documents.length === 0) {
    return (
      <Card className="border">
        <CardContent className="pt-6 pb-6 text-center text-muted-foreground">
          No documents in this validation session.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-muted-foreground">
          {documents.length} document{documents.length !== 1 ? 's' : ''} in presentation set
        </p>
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1"><CheckCircle className="w-3 h-3 text-emerald-500" /> Clean</span>
          <span className="flex items-center gap-1"><AlertTriangle className="w-3 h-3 text-amber-500" /> Issues</span>
          <span className="flex items-center gap-1"><XCircle className="w-3 h-3 text-red-500" /> Critical</span>
        </div>
      </div>

      {sorted.map((doc) => {
        const docId = doc.id || doc.documentId || doc.filename || '';
        const typeKey = doc.typeKey || doc.type || 'supporting_document';
        const issues = getDocIssues(doc, issueCards);
        const status = worstSeverity(issues);
        const fields = doc.extractedFields || {};
        const fieldEntries = Object.entries(fields).filter(
          ([k]) => !k.startsWith('_') && !k.startsWith('raw_text'),
        );
        const isExpanded = expandedDocs.has(docId);

        // Determine which field names are mentioned in issues
        const discrepantFields = new Set<string>();
        for (const ic of issues) {
          const fn = (ic as any).field_name ?? ic.field;
          if (fn) discrepantFields.add(fn);
          // Also match by issue title keywords against field names
          for (const [k] of fieldEntries) {
            if ((ic.title ?? '').toLowerCase().includes(k.replace(/_/g, ' '))) {
              discrepantFields.add(k);
            }
          }
        }

        return (
          <Card
            key={docId}
            className={cn(
              'border transition-all',
              status === 'critical' && 'border-red-500/30',
              status === 'major' && 'border-amber-500/30',
              status === 'clean' && 'border-border/60',
            )}
          >
            <button
              className="w-full text-left"
              onClick={() => toggleDoc(docId)}
            >
              <CardHeader className="py-4 px-5">
                <div className="flex items-center gap-3">
                  <StatusIcon status={status} />
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-semibold">
                      {humanizeDocType(typeKey)}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {doc.filename || doc.name || 'Uploaded document'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {fieldEntries.length} field{fieldEntries.length !== 1 ? 's' : ''}
                    </span>
                    {issues.length > 0 && (
                      <Badge
                        variant="outline"
                        className={cn(
                          'text-[10px]',
                          status === 'critical'
                            ? 'bg-red-500/10 text-red-400 border-red-500/30'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/30',
                        )}
                      >
                        {issues.length} issue{issues.length !== 1 ? 's' : ''}
                      </Badge>
                    )}
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    )}
                  </div>
                </div>
              </CardHeader>
            </button>

            {isExpanded && (
              <CardContent className="pt-0 pb-4 px-5 space-y-4">
                {/* Issues on this document */}
                {issues.length > 0 && (
                  <div className="space-y-2">
                    {issues.map((ic, i) => (
                      <IssueInline key={i} issue={ic} />
                    ))}
                  </div>
                )}

                {/* Extracted fields */}
                {fieldEntries.length > 0 && (
                  <div className="space-y-0.5">
                    <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">
                      Extracted Fields
                    </p>
                    {fieldEntries.map(([key, val]) => (
                      <FieldRow
                        key={key}
                        name={key}
                        value={formatFieldValue(val)}
                        isDiscrepant={discrepantFields.has(key)}
                      />
                    ))}
                  </div>
                )}

                {fieldEntries.length === 0 && issues.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No fields extracted for this document.
                  </p>
                )}
              </CardContent>
            )}
          </Card>
        );
      })}
    </div>
  );
}

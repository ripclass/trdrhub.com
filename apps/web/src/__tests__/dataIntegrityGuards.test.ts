/**
 * DATA INTEGRITY GUARD TESTS
 *
 * P1 incident fix: LCopilot dashboard data integrity mismatch.
 * These tests assert that document-status counts, issue totals, and
 * compliance metrics are consistent across all dashboard widgets.
 *
 * Invariant: All three sources of document-status counts must agree:
 *   1. resultsMapper output (summary.canonical_document_status)
 *   2. analytics.document_status_distribution
 *   3. documents array filtered by status
 *
 * And compliance score must NOT be confused with extraction success rate.
 */

import { buildValidationResponse } from '@/lib/exporter/resultsMapper';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a minimal structured_result_v1 payload that mimics what the backend
 * sends over the wire for jobId 3fa78054-40c1-4109-b3eb-20de02ebc2c5-style jobs.
 */
function makeStructuredResult(overrides: {
  docs?: Array<{ extraction_status?: string; issues_count?: number; discrepancyCount?: number }>;
  issues?: Array<{ id: string; title: string; severity: string }>;
  analyticsComplianceScore?: number;
  backendStatusCounts?: Record<string, number>;
}) {
  const docs = overrides.docs ?? [
    { extraction_status: 'success', issues_count: 0 },
    { extraction_status: 'success', issues_count: 0 },
    { extraction_status: 'success', issues_count: 0 },
    { extraction_status: 'success', issues_count: 0 },
    { extraction_status: 'success', issues_count: 0 },
    { extraction_status: 'success', issues_count: 0 },
  ];

  const issues = overrides.issues ?? [
    { id: 'iss-1', title: 'Critical issue', severity: 'critical' },
    { id: 'iss-2', title: 'Major issue', severity: 'major' },
    { id: 'iss-3', title: 'Another major', severity: 'major' },
  ];

  const documents_structured = docs.map((doc, i) => ({
    document_id: `doc-${i}`,
    document_type: 'commercial_invoice',
    filename: `doc-${i}.pdf`,
    extraction_status: doc.extraction_status ?? 'success',
    extracted_fields: {},
    issues_count: doc.issues_count ?? 0,
    discrepancyCount: doc.discrepancyCount,
  }));

  return {
    structured_result: {
      version: 'structured_result_v1',
      documents_structured,
      issues,
      processing_summary: {
        total_documents: docs.length,
        successful_extractions: docs.filter(d => (d.extraction_status ?? 'success') === 'success').length,
        failed_extractions: docs.filter(d => d.extraction_status === 'error').length,
        total_issues: issues.length,
        severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
        // Simulate potentially stale/wrong backend status counts:
        status_counts: overrides.backendStatusCounts ?? {},
        document_status: overrides.backendStatusCounts ?? {},
      },
      analytics: {
        compliance_score: overrides.analyticsComplianceScore ?? 0,
        issue_counts: { critical: 0, major: 0, medium: 0, minor: 0 },
        document_risk: [],
        // Simulate potentially wrong backend distribution:
        document_status_distribution: overrides.backendStatusCounts ?? {},
      },
      lc_structured: null,
    },
  };
}

// ---------------------------------------------------------------------------
// Core invariant: single source of truth for document status counts
// ---------------------------------------------------------------------------

describe('resultsMapper — document status canonical source-of-truth', () => {
  it('summary.canonical_document_status always equals documents filtered by status', () => {
    const payload = makeStructuredResult({});
    const result = buildValidationResponse(payload);

    // Count directly from mapped documents (what Documents tab shows)
    const directSuccess = result.documents.filter(d => d.status === 'success').length;
    const directWarning = result.documents.filter(d => d.status === 'warning').length;
    const directError   = result.documents.filter(d => d.status === 'error').length;

    // Must match canonical_document_status stored in summary
    expect(result.summary.canonical_document_status).toBeDefined();
    expect(result.summary.canonical_document_status!.success).toBe(directSuccess);
    expect(result.summary.canonical_document_status!.warning).toBe(directWarning);
    expect(result.summary.canonical_document_status!.error).toBe(directError);
  });

  it('summary.document_status equals canonical_document_status (not backend status_counts)', () => {
    // Backend sends wrong status counts (stale)
    const payload = makeStructuredResult({
      backendStatusCounts: { success: 2, warning: 2, error: 2 }, // wrong!
    });
    const result = buildValidationResponse(payload);

    // With 6 docs all extraction_status=success and issues_count=0, all should be 'success'
    const directSuccess = result.documents.filter(d => d.status === 'success').length;
    expect(directSuccess).toBe(6);

    // Mapper should NOT use the stale backend counts; must use canonical
    expect(result.summary.document_status!.success).toBe(directSuccess);
    expect(result.summary.document_status!.success).toBe(6);
    expect(result.summary.document_status!.warning).toBe(0);
    expect(result.summary.document_status!.error).toBe(0);
  });

  it('analytics.document_status_distribution matches summary.canonical_document_status', () => {
    const payload = makeStructuredResult({
      backendStatusCounts: { success: 99, warning: 99, error: 99 }, // wrong backend values
    });
    const result = buildValidationResponse(payload);

    const canon = result.summary.canonical_document_status!;
    expect(result.analytics.document_status_distribution).toEqual(canon);
  });

  it('summary.verified equals canonical_document_status.success', () => {
    const payload = makeStructuredResult({});
    const result = buildValidationResponse(payload);

    expect(result.summary.verified).toBe(result.summary.canonical_document_status!.success);
  });

  it('summary.warnings equals canonical_document_status.warning', () => {
    const payload = makeStructuredResult({
      docs: [
        { extraction_status: 'success', issues_count: 2 }, // -> warning
        { extraction_status: 'success', issues_count: 0 }, // -> success
        { extraction_status: 'error',   issues_count: 0 }, // -> error
      ],
    });
    const result = buildValidationResponse(payload);

    expect(result.summary.warnings).toBe(result.summary.canonical_document_status!.warning);
    expect(result.summary.errors).toBe(result.summary.canonical_document_status!.error);
  });
});

// ---------------------------------------------------------------------------
// Compliance score vs extraction success rate — must NOT be conflated
// ---------------------------------------------------------------------------

describe('resultsMapper — compliance score is separate from extraction success rate', () => {
  it('compliance_score=0 does not force document_status to all-warning', () => {
    // Scenario: 6 docs extracted OK, but v2 scorer gives compliance=0 (REJECT)
    // because there are critical issues
    const payload = makeStructuredResult({
      docs: Array(6).fill({ extraction_status: 'success', issues_count: 0 }),
      issues: [{ id: 'iss-1', title: 'Critical', severity: 'critical' }],
      analyticsComplianceScore: 0,
    });
    const result = buildValidationResponse(payload);

    // All 6 docs should be 'success' (extraction OK)
    expect(result.summary.canonical_document_status!.success).toBe(6);
    expect(result.summary.canonical_document_status!.warning).toBe(0);
    expect(result.summary.canonical_document_status!.error).toBe(0);

    // Compliance score should still be 0 (from analytics, issue-based)
    expect(result.analytics.compliance_score).toBe(0);

    // These two values represent DIFFERENT things and both can be valid simultaneously:
    // - extraction success: 6 docs extracted OK
    // - compliance: 0% because critical LC issues exist
    // This is NOT a contradiction — guard test confirms the mapper preserves both.
  });

  it('high compliance score does not suppress doc-level error counts', () => {
    const payload = makeStructuredResult({
      docs: [
        { extraction_status: 'error', issues_count: 0 }, // extraction failed
        { extraction_status: 'success', issues_count: 0 },
      ],
      issues: [],
      analyticsComplianceScore: 100,
    });
    const result = buildValidationResponse(payload);

    expect(result.summary.canonical_document_status!.error).toBe(1);
    expect(result.summary.canonical_document_status!.success).toBe(1);
    // Compliance score is issue-based and can be high even with extraction errors
    expect(result.analytics.compliance_score).toBe(100);
  });
});

// ---------------------------------------------------------------------------
// Issue totals vs document warning counts — must NOT be conflated
// ---------------------------------------------------------------------------

describe('resultsMapper — issue count vs document warning count are distinct', () => {
  it('totalIssues (issue cards) is independent of warningCount (doc status)', () => {
    // 6 docs all extracted OK, but 9 issues found (from LC cross-doc checks)
    const nineIssues = Array(9).fill(null).map((_, i) => ({
      id: `iss-${i}`,
      title: `Issue ${i}`,
      severity: i < 2 ? 'critical' : 'major',
    }));

    const payload = makeStructuredResult({
      docs: Array(6).fill({ extraction_status: 'success', issues_count: 0 }),
      issues: nineIssues,
    });
    const result = buildValidationResponse(payload);

    // All docs extracted OK → doc warning count = 0
    expect(result.summary.canonical_document_status!.warning).toBe(0);
    expect(result.summary.canonical_document_status!.success).toBe(6);

    // But issues list = 9
    expect(result.issues).toHaveLength(9);

    // These must not be conflated in any widget.
    // summary.warnings = doc-status warnings (0), not issue count (9)
    expect(result.summary.warnings).toBe(0);
    expect(result.summary.total_issues).toBe(9);
  });

  it('docs with issues_count > 0 (but < 3) become "warning" in doc status', () => {
    // Mapper: issuesCount >= 3 → error, issuesCount > 0 → warning, else success
    const payload = makeStructuredResult({
      docs: [
        { extraction_status: 'success', issues_count: 2 }, // -> warning (0 < count < 3)
        { extraction_status: 'success', issues_count: 0 }, // -> success
        { extraction_status: 'success', issues_count: 3 }, // -> error (count >= 3)
      ],
      issues: [],
    });
    const result = buildValidationResponse(payload);

    expect(result.summary.canonical_document_status!.warning).toBe(1);
    expect(result.summary.canonical_document_status!.success).toBe(1);
    expect(result.summary.canonical_document_status!.error).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// Cross-widget consistency for jobId 3fa78054 scenario
// ---------------------------------------------------------------------------

describe('jobId 3fa78054 consistency scenario', () => {
  /**
   * Reproduces the original P1 incident:
   * - 6 docs all extracted OK (extraction_status=success, no doc-level issues)
   * - 9 LC cross-doc issues found (severity: critical/major)
   * - v2 compliance scorer → 0% (REJECT) because critical issues
   *
   * Expected consistent output:
   * - SummaryStrip "Extraction Status": 6 extracted OK, 0 with warnings, 0 failed
   * - Overview "Docs Verified": 6, "Docs Need Review": 0
   * - Document Status card: Extracted OK = 6 (100%), LC Compliance = 0%
   * - Issues tab: 9 total issues
   */
  it('all widgets use consistent numbers from canonical source', () => {
    const nineIssues = Array(9).fill(null).map((_, i) => ({
      id: `iss-${i}`,
      title: `Issue ${i}`,
      severity: i < 2 ? 'critical' : 'major',
    }));

    const payload = makeStructuredResult({
      docs: Array(6).fill({ extraction_status: 'success', issues_count: 0 }),
      issues: nineIssues,
      analyticsComplianceScore: 0,
      // Simulate stale backend sending wrong numbers (as observed in the incident)
      backendStatusCounts: { success: 2, warning: 2, error: 2 },
    });
    const result = buildValidationResponse(payload);

    // 1. Canonical document status (drives SummaryStrip and Overview card)
    const canon = result.summary.canonical_document_status!;
    expect(canon.success).toBe(6);
    expect(canon.warning).toBe(0);
    expect(canon.error).toBe(0);

    // 2. analytics.document_status_distribution (drives Document Status pie chart)
    expect(result.analytics.document_status_distribution).toEqual(canon);

    // 3. summary.verified / warnings / errors (drives SummaryStrip directly)
    expect(result.summary.verified).toBe(6);
    expect(result.summary.warnings).toBe(0);
    expect(result.summary.errors).toBe(0);

    // 4. Issues count (drives Issues tab counter)
    expect(result.issues).toHaveLength(9);

    // 5. Compliance score (drives compliance badge — separate from extraction)
    expect(result.analytics.compliance_score).toBe(0);

    // 6. All three "doc status" sources agree
    const fromDocuments = {
      success: result.documents.filter(d => d.status === 'success').length,
      warning: result.documents.filter(d => d.status === 'warning').length,
      error:   result.documents.filter(d => d.status === 'error').length,
    };
    expect(fromDocuments).toEqual(canon);
    expect(result.summary.document_status).toEqual(canon);
  });

  it('sample job with mixed doc statuses also passes consistency check', () => {
    // Second sample job: 4 success, 1 warning (partial extraction), 1 error
    const payload = makeStructuredResult({
      docs: [
        { extraction_status: 'success', issues_count: 0 },
        { extraction_status: 'success', issues_count: 1 }, // -> warning (has issues)
        { extraction_status: 'success', issues_count: 0 },
        { extraction_status: 'partial', issues_count: 0 }, // -> warning (partial)
        { extraction_status: 'success', issues_count: 0 },
        { extraction_status: 'error',   issues_count: 0 }, // -> error
      ],
      issues: [{ id: 'iss-1', title: 'Mismatch', severity: 'major' }],
      analyticsComplianceScore: 80,
    });
    const result = buildValidationResponse(payload);

    const canon = result.summary.canonical_document_status!;
    const fromDocs = {
      success: result.documents.filter(d => d.status === 'success').length,
      warning: result.documents.filter(d => d.status === 'warning').length,
      error:   result.documents.filter(d => d.status === 'error').length,
    };

    // All three sources agree
    expect(canon).toEqual(fromDocs);
    expect(result.analytics.document_status_distribution).toEqual(canon);
    expect(result.summary.document_status).toEqual(canon);
    expect(result.summary.verified).toBe(canon.success);
    expect(result.summary.warnings).toBe(canon.warning);
    expect(result.summary.errors).toBe(canon.error);
  });
});

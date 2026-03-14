import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import ExporterResults from '@/pages/ExporterResults';
import { buildValidationResponse } from '@/lib/exporter/resultsMapper';
import { renderWithProviders } from './testUtils';
import { buildValidationResults, mockValidationResults } from './fixtures/lcopilot';

let activeResults = buildValidationResults();
const totalDocuments = mockValidationResults.documents.length;
const totalDiscrepancies = mockValidationResults.issues.length;
const successCount = mockValidationResults.documents.filter((doc) => doc.status === 'success').length;
const expectedSeverityCounts = mockValidationResults.issues.reduce(
  (acc, issue) => {
    const severity = (issue.severity ?? '').toLowerCase();
    if (['critical', 'fail', 'error', 'high'].includes(severity)) {
      acc.critical += 1;
    } else if (['warning', 'warn', 'major', 'medium'].includes(severity)) {
      acc.major += 1;
    } else {
      acc.minor += 1;
    }
    return acc;
  },
  { critical: 0, major: 0, minor: 0 },
);

const findCardByTitle = (title: RegExp | string): HTMLElement => {
  const heading = screen.getByText(title);
  let current: HTMLElement | null = heading as HTMLElement;
  while (current && !current.className.toString().includes('shadow-soft')) {
    current = current.parentElement as HTMLElement | null;
  }
  return current ?? (heading as HTMLElement);
};

vi.mock('@/hooks/use-lcopilot', () => {
  return {
    useJob: () => ({
      jobStatus: { status: 'completed' },
      isPolling: false,
      error: null,
      startPolling: vi.fn(),
      clearError: vi.fn(),
    }),
    useResults: () => ({
      getResults: vi.fn().mockResolvedValue(activeResults),
      results: activeResults,
      isLoading: false,
      error: null,
      clearError: vi.fn(),
    }),
  };
});

vi.mock('@/api/exporter', () => ({
  exporterApi: {
    checkGuardrails: vi.fn().mockResolvedValue({
      can_submit: true,
      blocking_issues: [],
      warnings: [],
      required_docs_present: true,
      high_severity_discrepancies: 0,
      policy_checks_passed: true,
    }),
    listBankSubmissions: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    generateCustomsPack: vi.fn().mockResolvedValue({
      download_url: '',
      file_name: 'CustomsPack.zip',
      sha256: '',
      generated_at: new Date().toISOString(),
      manifest: {
        lc_number: 'LC123',
        validation_session_id: 'session',
        generated_at: new Date().toISOString(),
        documents: [],
        generator_version: 'test',
      },
    }),
    downloadCustomsPack: vi.fn().mockResolvedValue(new Blob()),
    createBankSubmission: vi.fn().mockResolvedValue({
      id: 'submission',
      company_id: 'company',
      user_id: 'user',
      validation_session_id: 'session',
      lc_number: 'LC123',
      status: 'pending',
      created_at: new Date().toISOString(),
    }),
    getSubmissionEvents: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}));

describe('ExporterResults', () => {
  beforeEach(() => {
    activeResults = buildValidationResults();
  });

  it('renders overview metrics from processing summary', async () => {
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Processing Performance/i)).toBeInTheDocument();
    expect(screen.getByText(/Required Document Checklist/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Processing Summary/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument();
    expect(
      screen.getByText(new RegExp(`Documents \\(${totalDocuments}\\)`, 'i')),
    ).toBeInTheDocument();
    expect(
      screen.getByText(new RegExp(`Issues \\(${totalDiscrepancies}\\)`, 'i')),
    ).toBeInTheDocument();
    expect(screen.getByText(/LC Compliance/i)).toBeInTheDocument();

    const statsCard = findCardByTitle(/Export Document Statistics/i);
    const verifiedLabel = within(statsCard).getByText(/^Verified$/i);
    const verifiedValue = verifiedLabel.previousElementSibling;
    expect(verifiedValue?.textContent).toBe(String(successCount));

    const warningsLabel = within(statsCard).getByText(/^Warnings$/i);
    const warningsValue = warningsLabel.previousElementSibling;
    expect(warningsValue?.textContent).toBe(String(totalDiscrepancies));

    const complianceRow = screen.getByText(/LC Compliance:/i).parentElement as HTMLElement;
    const expectedCompliance = `${Math.round((successCount / totalDocuments) * 100)}%`;
    expect(within(complianceRow).getByText(expectedCompliance)).toBeInTheDocument();
  });

  it('renders documents tab with all trade documents', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Documents \(6\)/i }));
    for (const doc of mockValidationResults.documents) {
      expect(screen.getByText(doc.name)).toBeInTheDocument();
    }
  });

  it('renders issues tab with expected/found values', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Issues \(3\)/i }));
    const primaryIssue = screen.getByTestId('issue-card-issue-1');
    expect(within(primaryIssue).getByRole('heading', { name: /Amount mismatch/i })).toBeInTheDocument();
    expect(
      within(primaryIssue)
        .getAllByText(/^Expected$/i)[0],
    ).toBeInTheDocument();
    const expectedValueNodes = within(primaryIssue).getAllByText((_, node) =>
      (node?.textContent ?? '').includes('50000 USD'),
    );
    const actualValueNodes = within(primaryIssue).getAllByText((_, node) =>
      (node?.textContent ?? '').includes('49000 USD'),
    );
    expect(expectedValueNodes[0]).toBeInTheDocument();
    expect(actualValueNodes[0]).toBeInTheDocument();

    const criticalCard = screen.getAllByText(/^Critical$/i)[0]?.closest('div') as HTMLElement;
    const majorCard = screen.getAllByText(/^Major$/i)[0]?.closest('div') as HTMLElement;
    const minorCard = screen.getAllByText(/^Minor$/i)[0]?.closest('div') as HTMLElement;

    const getCountText = (element?: HTMLElement | null) =>
      element?.querySelector('.text-2xl')?.textContent ?? '';
    expect(getCountText(criticalCard)).toBe(expectedSeverityCounts.critical.toString());
    expect(getCountText(majorCard)).toBe(expectedSeverityCounts.major.toString());
    expect(getCountText(minorCard)).toBe(expectedSeverityCounts.minor.toString());

    const severityBadge = screen.getByTestId('severity-issue-1');
    expect(severityBadge.dataset.icon).toBe('critical');
    expect(severityBadge.className).toContain('bg-[#E24A4A]/10');
  });

  it('renders merged analytics content in overview', async () => {
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Processing Performance/i)).toBeInTheDocument();
    expect(screen.getByText(`${mockValidationResults.analytics.compliance_score}%`)).toBeInTheDocument();
  });

  it('keeps document status counts aligned between overview and documents tab', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );

    const statusCard = findCardByTitle(/Document Status/i);
    expect(within(statusCard).getByText('4 (67%)')).toBeInTheDocument();
    expect(within(statusCard).getByText('2 (33%)')).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Documents \(6\)/i }));
    const documentsPanel = screen.getByRole('tabpanel', { name: /documents/i });
    expect(within(documentsPanel).getAllByText('Verified')).toHaveLength(4);
    expect(within(documentsPanel).getAllByText('With Warnings')).toHaveLength(2);
  });

  it('keeps issue counts aligned when summary totals are stale', async () => {
    const staleSummary = buildValidationResults();
    staleSummary.structured_result!.processing_summary = {
      ...staleSummary.structured_result!.processing_summary,
      total_issues: 1,
    };
    activeResults = staleSummary;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument(),
    );
    expect(screen.getByRole('tab', { name: /Issues \(3\)/i })).toBeInTheDocument();

    const statsCard = findCardByTitle(/Export Document Statistics/i);
    const warningsLabel = within(statsCard).getByText(/^Warnings$/i);
    const warningsValue = warningsLabel.previousElementSibling;
    expect(warningsValue?.textContent).toBe('3');

    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: /Issues \(3\)/i }));
    expect(screen.getAllByTestId(/issue-card-/)).toHaveLength(3);
  });

  it('keeps customs readiness aligned between overview and customs tab', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument(),
    );

    const statsCard = findCardByTitle(/Export Document Statistics/i);
    const readinessRow = within(statsCard).getByText(/Compliance Readiness/i).parentElement as HTMLElement;
    const readinessValue = readinessRow.querySelector('span.font-medium')?.textContent;
    expect(readinessValue).toBeTruthy();

    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    expect(within(customsPanel).getByText(readinessValue as string)).toBeInTheDocument();
  });

  it('separates requirement coverage from review readiness in checklist rows', async () => {
    const checklistResults = buildValidationResults();
    checklistResults.documents = checklistResults.documents.map((doc) => {
      if (doc.typeKey === 'commercial_invoice') {
        return {
          ...doc,
          requirementStatus: 'matched',
          reviewState: 'needs_review',
          reviewReasons: ['Invoice totals need manual review'],
        };
      }
      return doc;
    });
    checklistResults.structured_result = {
      ...checklistResults.structured_result,
      lc_structured: {
        ...(checklistResults.structured_result?.lc_structured ?? {}),
        documents_required: ['Signed Commercial Invoice', 'Beneficiary Certificate'],
      },
    } as typeof checklistResults.structured_result;
    activeResults = checklistResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Document Checklist/i)).toBeInTheDocument(),
    );

    const checklistCard = findCardByTitle(/Required Document Checklist/i);
    expect(within(checklistCard).getByText(/Requirement: Matched/i)).toBeInTheDocument();
    expect(within(checklistCard).getByText(/Review: Review required/i)).toBeInTheDocument();
    expect(within(checklistCard).getByText(/Requirement: Missing/i)).toBeInTheDocument();
    expect(within(checklistCard).getByText(/Review: Awaiting document/i)).toBeInTheDocument();
  });

  it('uses internal compliance review wording in the action engine', async () => {
    const complianceResults = buildValidationResults({
      issues: [
        {
          ...mockValidationResults.issues[0],
          id: 'issue-compliance',
          title: 'Potential sanctions match',
          severity: 'critical',
          bucket: 'Compliance / Risk Review',
          workflow_lane: 'compliance_review',
          fix_owner: 'Internal Compliance Review',
          remediation_owner: 'Internal Compliance Review',
          next_action: 'Route to internal compliance review, capture the disposition, and keep submission on hold until cleared.',
        },
      ],
    });
    activeResults = complianceResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Action Engine/i)).toBeInTheDocument(),
    );

    const actionCard = findCardByTitle(/Action Engine/i);
    expect(within(actionCard).getByText(/Route Potential sanctions match to internal compliance review/i)).toBeInTheDocument();
    expect(within(actionCard).getByText(/keep submission on hold until cleared/i)).toBeInTheDocument();
  });

  it('gates submit eligibility when validation blocks submission', async () => {
    const gatedResults = buildValidationResults();
    gatedResults.structured_result = {
      ...gatedResults.structured_result,
      submission_eligibility: { can_submit: false, reasons: ['issues'] },
    } as typeof gatedResults.structured_result;
    activeResults = gatedResults;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    expect(within(customsPanel).queryByRole('button', { name: /Submit to Bank/i })).toBeNull();
  });

  it('shows submit to bank when eligibility and guardrails allow', async () => {
    const eligibleResults = buildValidationResults();
    eligibleResults.structured_result = {
      ...eligibleResults.structured_result,
      bank_verdict: {
        verdict: 'SUBMIT',
        verdict_color: 'green',
        verdict_message: 'Safe to submit',
        recommendation: 'Ready for bank submission',
        can_submit: true,
        will_be_rejected: false,
        estimated_discrepancy_fee: 0,
        issue_summary: { critical: 0, major: 0, minor: 0, total: 0 },
        action_items: [],
        action_items_count: 0,
      },
    } as typeof eligibleResults.structured_result;
    activeResults = eligibleResults;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    expect(within(customsPanel).getByRole('button', { name: /Submit to Bank/i })).toBeInTheDocument();
  });

  it('renders UI when only structured_result payload is provided', async () => {
    const user = userEvent.setup();
    const structuredOnly = buildValidationResponse({
      structured_result: mockValidationResults.structured_result,
    });
    activeResults = structuredOnly;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Documents/i }));
    expect(
      screen.getByText(structuredOnly.documents[0]?.name ?? 'Letter of Credit'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Issues/i }));
    expect(screen.getByText(structuredOnly.issues[0]?.title ?? 'Review Required')).toBeInTheDocument();
  });

  it('shows success state when there are no issues', async () => {
    const withoutIssues = buildValidationResults();
    withoutIssues.issues = [];
    withoutIssues.structured_result!.issues = [];
    withoutIssues.summary = {
      ...withoutIssues.summary,
      total_issues: 0,
      severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
    };
    withoutIssues.structured_result!.processing_summary = {
      ...withoutIssues.structured_result!.processing_summary,
      total_issues: 0,
      severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
    };
    activeResults = withoutIssues;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await user.click(screen.getByRole('tab', { name: /Issues/i }));
    expect(screen.getByText(/All documents comply with LC terms/i)).toBeInTheDocument();
  });

  it('still renders overview when structured_result analytics are missing', async () => {
    const withoutAnalytics = buildValidationResults();
    (withoutAnalytics.structured_result as any).analytics = undefined;
    activeResults = withoutAnalytics;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Processing Performance/i)).toBeInTheDocument();
  });

  it('hides the timeline when no events are provided', async () => {
    const noTimeline = buildValidationResults();
    noTimeline.timeline = [];
    if (noTimeline.structured_result) {
      noTimeline.structured_result.timeline = [];
    }
    activeResults = noTimeline;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() => expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument());
    expect(screen.queryByText(/Export Processing Timeline/i)).not.toBeInTheDocument();
  });

  it('shows document parsing warning when extracted fields are empty', async () => {
    const docWithNoFields = buildValidationResults();
    docWithNoFields.documents[0].extractedFields = {};
    docWithNoFields.documents[0].extractionStatus = 'partial';
    if (docWithNoFields.structured_result?.documents_structured?.[0]) {
      docWithNoFields.structured_result.documents_structured[0].extracted_fields = {};
      docWithNoFields.structured_result.documents_structured[0].extraction_status = 'partial';
    }
    if (docWithNoFields.structured_result?.lc_structured?.documents_structured?.[0]) {
      docWithNoFields.structured_result.lc_structured.documents_structured[0].extracted_fields = {};
      docWithNoFields.structured_result.lc_structured.documents_structured[0].extraction_status = 'partial';
    }
    activeResults = docWithNoFields;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await user.click(screen.getByRole('tab', { name: /Documents/i }));
    expect(
      screen.getByText(/This document could not be fully parsed/i),
    ).toBeInTheDocument();
  });

  it('does not show parse-failed messaging for verified documents with no extracted fields', async () => {
    const docNoFieldsButVerified = buildValidationResults();
    docNoFieldsButVerified.documents[0].status = 'success';
    docNoFieldsButVerified.documents[0].extractionStatus = 'success';
    docNoFieldsButVerified.documents[0].extractedFields = {};
    if (docNoFieldsButVerified.structured_result?.documents_structured?.[0]) {
      docNoFieldsButVerified.structured_result.documents_structured[0].extracted_fields = {};
      docNoFieldsButVerified.structured_result.documents_structured[0].extraction_status = 'success';
    }
    if (docNoFieldsButVerified.structured_result?.lc_structured?.documents_structured?.[0]) {
      docNoFieldsButVerified.structured_result.lc_structured.documents_structured[0].extracted_fields = {};
      docNoFieldsButVerified.structured_result.lc_structured.documents_structured[0].extraction_status = 'success';
    }
    activeResults = docNoFieldsButVerified;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await user.click(screen.getByRole('tab', { name: /Documents/i }));
    expect(
      screen.getByText(/No structured fields were extracted for this document/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/could not be fully parsed/i)).not.toBeInTheDocument();
  });
});

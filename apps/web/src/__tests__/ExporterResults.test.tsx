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
const warningDocumentCount = mockValidationResults.documents.filter((doc) => doc.status === 'warning').length;
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

const findCardByTitle = (title: RegExp | string, index = 0): HTMLElement => {
  const heading =
    screen.queryAllByRole('heading', { name: title }).at(index) ??
    screen.getAllByText(title)[index];
  let current: HTMLElement | null = heading as HTMLElement;
  while (current && !current.className.toString().includes('shadow-soft')) {
    current = current.parentElement as HTMLElement | null;
  }
  return current ?? (heading as HTMLElement);
};

const getMetricValueFromCard = (card: HTMLElement, label: RegExp | string): string | undefined => {
  const labelNode = within(card).getByText(label);
  const metricCard = labelNode.parentElement as HTMLElement | null;
  const metricLines = metricCard?.querySelectorAll('p') ?? [];
  return metricLines.length > 1 ? metricLines[1]?.textContent ?? undefined : undefined;
};

const mockUseCanonicalJobResult = vi.fn();
const mockToast = vi.fn();

vi.mock('@/hooks/use-lcopilot', () => {
  return {
    useCanonicalJobResult: () => mockUseCanonicalJobResult(),
  };
});

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: mockToast,
  }),
}));

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
    saveFieldOverride: vi.fn().mockResolvedValue({
      job_id: 'job-123',
      jobId: 'job-123',
      document_id: 'doc-invoice',
      field_name: 'invoice_date',
      override_value: '2026-04-20',
      verification: 'operator_confirmed',
      applied_at: new Date().toISOString(),
    }),
  },
}));

vi.mock('@/config/exporterFeatureFlags', () => ({
  isExporterFeatureEnabled: vi.fn(() => true),
}));

describe('ExporterResults', () => {
  beforeEach(() => {
    activeResults = buildValidationResults();
    mockToast.mockReset();
    mockUseCanonicalJobResult.mockImplementation(() => ({
      jobStatus: { status: 'completed' },
      results: activeResults,
      isLoading: false,
      resultsError: null,
      jobError: null,
      refreshResults: vi.fn().mockResolvedValue(activeResults),
    }));
  });

  it('renders overview metrics from processing summary', async () => {
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument();
    expect(
      screen.getByText(new RegExp(`Documents \\(${totalDocuments}\\)`, 'i')),
    ).toBeInTheDocument();
    expect(
      screen.getByText(new RegExp(`Issues \\(${totalDiscrepancies}\\)`, 'i')),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Validation Score/i).length).toBeGreaterThan(0);
  });

  it('renders documents tab with all trade documents', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
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
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
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

    const noteCard = findCardByTitle(/Overall Validation Note/i);
    expect(within(noteCard).getByText(/^Discrepancy findings$/i)).toBeInTheDocument();
    expect(within(noteCard).getByText(/^Total findings$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: new RegExp(`High-likelihood \\(${expectedSeverityCounts.critical}\\)`, 'i') })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: new RegExp(`Likely \\(${expectedSeverityCounts.major}\\)`, 'i') })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: new RegExp(`Review required \\(${expectedSeverityCounts.minor}\\)`, 'i') })).toBeInTheDocument();

    const severityBadge = screen.getByTestId('severity-issue-1');
    expect(severityBadge.dataset.icon).toBe('critical');
    expect(severityBadge.className).toContain('bg-[#E24A4A]/10');
  });

  it('renders provisional findings as a separate lane from final discrepancy findings', async () => {
    const user = userEvent.setup();
    activeResults = buildValidationResults({
      issues: [
        {
          id: 'issue-final-1',
          title: 'Invoice extraction is unreliable',
          description: 'AI L3 marked this invoice as low-confidence.',
          severity: 'major',
          documents: ['Invoice.pdf'],
          expected: 'Reliable invoice extraction',
          actual: 'Low-confidence invoice extraction',
          suggestion: 'Review the invoice source and rerun validation.',
          rule: 'AI-L3-LOW-CONFIDENCE-INVOICE',
        } as any,
      ],
      provisional_issues: [
        {
          id: 'issue-prov-1',
          title: 'Invoice amount could not be trusted',
          description: 'This deterministic finding remains provisional until extraction is confirmed.',
          severity: 'major',
          documents: ['Invoice.pdf'],
          expected: 'Trusted invoice amount extraction',
          actual: 'Invoice amount remains provisional',
          suggestion: 'Confirm the source invoice before treating this as final.',
          rule: 'CROSSDOC-INV-005',
        } as any,
      ],
    });

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Issues/i }));

    expect(screen.getByRole('heading', { name: /^Provisional Findings$/i })).toBeInTheDocument();
    expect(
      screen.getByText(/These findings were generated from a document the AI layer marked as extraction-unreliable/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId('issue-card-issue-final-1')).toBeInTheDocument();
    expect(screen.getByTestId('issue-card-issue-prov-1')).toBeInTheDocument();

    const noteCard = findCardByTitle(/Overall Validation Note/i);
    expect(within(noteCard).getByText(/^Provisional findings$/i)).toBeInTheDocument();
  });

  it('renders merged analytics content in overview', async () => {
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
    );
    expect(screen.getAllByText(`${mockValidationResults.analytics.compliance_score}%`).length).toBeGreaterThan(0);
  });

  it('keeps document status counts aligned between overview and documents tab', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Documents \(6\)/i }));
    const structuredReadCards = mockValidationResults.documents.filter((doc) => doc.status === 'success');
    const warningCards = mockValidationResults.documents.filter((doc) => doc.status === 'warning');
    expect(
      structuredReadCards.filter((doc) =>
        within(findCardByTitle(new RegExp(`^${doc.name.replace('.', '\\.')}$`, 'i'))).queryAllByText('Structured read complete').length > 0,
      ),
    ).toHaveLength(4);
    expect(
      warningCards.filter((doc) =>
        within(findCardByTitle(new RegExp(`^${doc.name.replace('.', '\\.')}$`, 'i'))).queryAllByText('Extraction needs review').length > 0,
      ),
    ).toHaveLength(2);
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
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );
    expect(screen.getByRole('tab', { name: /Issues \(3\)/i })).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: /Issues \(3\)/i }));
    expect(screen.getAllByTestId(/issue-card-/)).toHaveLength(3);
    const noteCard = findCardByTitle(/Overall Validation Note/i);
    const totalFindingsLabel = within(noteCard).getByText(/Total findings/i);
    expect(totalFindingsLabel.nextElementSibling?.textContent).toBe('3');
  });

  it('keeps customs readiness aligned between overview and customs tab', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    expect(within(customsPanel).getByText(/Submission Readiness/i)).toBeInTheDocument();
    expect(
      within(customsPanel).getByText((_, node) => (node?.textContent ?? '').trim() === 'Hard Blockers'),
    ).toBeInTheDocument();
    expect(within(customsPanel).getByText(/Presentation Reviews/i)).toBeInTheDocument();
  });

  it('shows a finalizing bridge instead of a dead-end mismatch when terminal results are still hydrating', async () => {
    const refreshResults = vi.fn().mockResolvedValue(null);
    mockUseCanonicalJobResult.mockReturnValue({
      jobStatus: { status: 'completed' },
      results: null,
      isLoading: false,
      resultsError: null,
      jobError: null,
      refreshResults,
      isFinalizingResults: true,
      terminalResultsTimedOut: false,
    });

    render(renderWithProviders(<ExporterResults />));

    expect(screen.getByText(/Validation finished\. Preparing your results/i)).toBeInTheDocument();
    expect(screen.getByText(/Finalizing the review workspace/i)).toBeInTheDocument();
    expect(screen.queryByText(/Validation in progress/i)).toBeNull();
  });

  it('uses backend submission eligibility as the source of truth for customs readiness status', async () => {
    const backendReadyResults = buildValidationResults();
    backendReadyResults.structured_result = {
      ...backendReadyResults.structured_result,
      lc_structured: {
        ...(backendReadyResults.structured_result?.lc_structured ?? {}),
        lc_classification: {
          workflow_orientation: 'export',
          instrument_type: 'documentary_credit',
          required_documents: [
            { code: 'commercial_invoice', display_name: 'Commercial Invoice' },
            { code: 'beneficiary_certificate', display_name: 'Beneficiary Certificate' },
          ],
        },
      },
      submission_eligibility: { can_submit: true, reasons: [] },
      effective_submission_eligibility: { can_submit: true, reasons: [] },
      customs_pack: {
        ready: true,
        manifest: [],
        format: 'zip-manifest-v1',
      },
      bank_verdict: {
        verdict: 'CAUTION',
        verdict_color: 'yellow',
        verdict_message: 'Minor corrections recommended',
        recommendation: 'Review warnings before submission',
        can_submit: true,
        will_be_rejected: false,
        estimated_discrepancy_fee: 0,
        issue_summary: { critical: 0, major: 1, minor: 0, total: 1 },
        action_items: [],
        action_items_count: 0,
      },
    } as typeof backendReadyResults.structured_result;
    activeResults = backendReadyResults;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    expect(within(customsPanel).getByText(/Submission Readiness/i)).toBeInTheDocument();
    expect(within(customsPanel).getByText(/Shared presentation truth/i)).toBeInTheDocument();
  });

  it('renders structured review-finding cards in the issues tab when checklist review stays open without discrepancy cards', async () => {
    const user = userEvent.setup();
    const reviewOnlyResults = buildValidationResults({
      issues: [],
      documents: [
        {
          id: 'doc-pack',
          documentId: 'doc-pack',
          name: 'Packing_List.pdf',
          filename: 'Packing_List.pdf',
          type: 'Packing List',
          typeKey: 'packing_list',
          extractionStatus: 'partial',
          status: 'warning',
          issuesCount: 0,
          extractedFields: { gross_weight: '20,400 kg' },
          missingRequiredFields: ['issue_date'],
          requirementStatus: 'partial',
          reviewRequired: true,
          reviewState: 'needs_review',
          reviewReasons: ['FIELD_NOT_FOUND'],
          criticalFieldStates: { issue_date: 'missing' },
          rawText: 'Packing list showing gross weight 20,400 kg and net weight 18,950 kg.',
        },
      ] as any,
      structured_result: {
        ...mockValidationResults.structured_result,
        issues: [],
        documents_structured: [
          {
            document_id: 'doc-pack',
            document_type: 'packing_list',
            filename: 'Packing_List.pdf',
            extraction_status: 'partial',
            extracted_fields: { gross_weight: '20,400 kg' },
            missing_required_fields: ['issue_date'],
            review_required: true,
            review_reasons: ['FIELD_NOT_FOUND'],
            critical_field_states: { issue_date: 'missing' },
            extraction_artifacts_v1: {
              raw_text: 'Packing list showing gross weight 20,400 kg and net weight 18,950 kg.',
              field_diagnostics: { issue_date: { state: 'missing' } },
            },
          } as any,
        ],
        lc_structured: {
          ...(mockValidationResults.structured_result?.lc_structured ?? {}),
          required_documents_detailed: [
            {
              code: 'packing_list',
              label: 'Packing List',
              requirement_text: 'Detailed packing list showing carton-wise breakdown.',
            },
          ],
        } as any,
      } as any,
      summary: {
        ...mockValidationResults.summary,
        total_issues: 0,
      },
    });
    activeResults = reviewOnlyResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Issues \(1\)/i }));
    expect(screen.getByText(/No formal discrepancy cards were generated, but unresolved review findings still need operator attention/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Review Findings$/i })).toBeInTheDocument();
    expect(screen.getByText(/Current state/i)).toBeInTheDocument();
    expect(screen.getByText(/Expected state/i)).toBeInTheDocument();
    expect(screen.getByText(/Why it matters/i)).toBeInTheDocument();
    expect(screen.getByText(/Evidence \/ basis/i)).toBeInTheDocument();
    expect(screen.getByText(/How to fix/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Source packing list does not clearly show a document date\./i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Source basis: Source document content review/i)).toBeInTheDocument();
  });

  it('reuses structured review-finding content in overview and customs action surfaces', async () => {
    const user = userEvent.setup();
    const reviewOnlyResults = buildValidationResults({
      issues: [],
      documents: [
        {
          id: 'doc-pack',
          documentId: 'doc-pack',
          name: 'Packing_List.pdf',
          filename: 'Packing_List.pdf',
          type: 'Packing List',
          typeKey: 'packing_list',
          extractionStatus: 'partial',
          status: 'warning',
          issuesCount: 0,
          extractedFields: { gross_weight: '20,400 kg' },
          missingRequiredFields: ['issue_date'],
          requirementStatus: 'partial',
          reviewRequired: true,
          reviewState: 'needs_review',
          reviewReasons: ['FIELD_NOT_FOUND'],
          criticalFieldStates: { issue_date: 'missing' },
          rawText: 'Packing list showing gross weight 20,400 kg and net weight 18,950 kg.',
        },
      ] as any,
      structured_result: {
        ...mockValidationResults.structured_result,
        issues: [],
        documents_structured: [
          {
            document_id: 'doc-pack',
            document_type: 'packing_list',
            filename: 'Packing_List.pdf',
            extraction_status: 'partial',
            extracted_fields: { gross_weight: '20,400 kg' },
            missing_required_fields: ['issue_date'],
            review_required: true,
            review_reasons: ['FIELD_NOT_FOUND'],
            critical_field_states: { issue_date: 'missing' },
            extraction_artifacts_v1: {
              raw_text: 'Packing list showing gross weight 20,400 kg and net weight 18,950 kg.',
              field_diagnostics: { issue_date: { state: 'missing' } },
            },
          } as any,
        ],
        lc_structured: {
          ...(mockValidationResults.structured_result?.lc_structured ?? {}),
          required_documents_detailed: [
            {
              code: 'packing_list',
              label: 'Packing List',
              requirement_text: 'Detailed packing list showing carton-wise breakdown.',
            },
          ],
        } as any,
      } as any,
      summary: {
        ...mockValidationResults.summary,
        total_issues: 0,
      },
    });
    activeResults = reviewOnlyResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );
    expect(screen.queryByRole('heading', { name: /What To Do Next/i })).toBeNull();

    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    expect(within(customsPanel).getByText(/Presentation Reviews/i)).toBeInTheDocument();
    expect(within(customsPanel).getByText(/Open review items that still need operator attention before clean presentation/i)).toBeInTheDocument();
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
      if (doc.typeKey === 'packing_list') {
        return {
          ...doc,
          requirementStatus: 'partial',
          reviewState: 'needs_review',
          reviewReasons: ['Packing list date requires manual confirmation'],
        };
      }
      return doc;
    });
    checklistResults.structured_result = {
      ...checklistResults.structured_result,
      lc_structured: {
        ...(checklistResults.structured_result?.lc_structured ?? {}),
        required_documents_detailed: [
          {
            code: 'commercial_invoice',
            label: 'Commercial Invoice',
            requirement_text: 'Signed commercial invoice in 3 originals.',
          },
          {
            code: 'packing_list',
            label: 'Packing List',
            requirement_text: 'Detailed packing list with carton-wise breakdown.',
          },
          {
            code: 'beneficiary_certificate',
            label: 'Beneficiary Certificate',
            requirement_text: 'Beneficiary certificate confirming goods are brand new.',
          },
        ],
      },
    } as typeof checklistResults.structured_result;
    activeResults = checklistResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );

    const checklistCard = findCardByTitle(/Required Documents Checklist/i);
    expect(within(checklistCard).getAllByText(/Covers requirement/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).getAllByText(/Partially covers requirement/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).getAllByText(/Missing upload/i).length).toBeGreaterThan(0);
  });

  it('builds checklist rows from canonical MT required document types and keeps export lc label', async () => {
    const mtResults = buildValidationResults();
    mtResults.structured_result = {
      ...mtResults.structured_result,
      lc_type: 'export',
      lc_type_reason: 'Detected exporter lane from beneficiary/applicant plus port flow.',
      lc_structured: {
        ...(mtResults.structured_result?.lc_structured ?? {}),
        lc_type: 'export',
        documents_required: "['INVOICE', 'BL', 'PL', 'COO', 'INSURANCE']",
        required_document_types: [
          'commercial_invoice',
          'bill_of_lading',
          'packing_list',
          'certificate_of_origin',
          'insurance_certificate',
        ],
        lc_classification: {
          workflow_orientation: 'export',
          instrument_type: 'documentary_credit',
          required_documents: [
            { code: 'commercial_invoice', display_name: 'Commercial Invoice' },
            { code: 'ocean_bill_of_lading', display_name: 'Ocean Bill of Lading' },
            { code: 'packing_list', display_name: 'Packing List' },
            { code: 'certificate_of_origin', display_name: 'Certificate of Origin' },
            { code: 'insurance_certificate', display_name: 'Insurance Certificate' },
          ],
        },
      },
    } as typeof mtResults.structured_result;
    activeResults = mtResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );

    expect(screen.getAllByText(/Export LC/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Workflow: Export LC/i)).toBeInTheDocument();
    expect(screen.getByText(/Instrument: Documentary Credit/i)).toBeInTheDocument();
    const checklistCard = findCardByTitle(/Required Documents Checklist/i);
    expect(within(checklistCard).getAllByText(/Commercial Invoice/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).getAllByText(/Ocean Bill of Lading/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).getAllByText(/Packing List/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).getAllByText(/Certificate of Origin/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).getAllByText(/Insurance Certificate/i).length).toBeGreaterThan(0);
  });

  it('labels summary confidence as workflow confidence instead of generic confidence', async () => {
    const confidenceResults = buildValidationResults();
    confidenceResults.structured_result = {
      ...confidenceResults.structured_result,
      lc_type_confidence: 0.85,
      lc_structured: {
        ...(confidenceResults.structured_result?.lc_structured ?? {}),
        lc_classification: {
          workflow_orientation: 'export',
          instrument_type: 'documentary_credit',
        },
      },
    } as typeof confidenceResults.structured_result;
    activeResults = confidenceResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
    );

    expect(screen.getByText(/85% workflow confidence/i)).toBeInTheDocument();
    expect(screen.queryByText(/^85% confidence$/i)).toBeNull();
  });

  it('keeps non-document requirement conditions out of checklist rows and surfaces them separately', async () => {
    const requirementResults = buildValidationResults();
    requirementResults.documents = requirementResults.documents.map((doc) => {
      if (doc.typeKey === 'beneficiary_certificate') {
        return {
          ...doc,
          requirementStatus: 'matched',
          reviewState: 'ready',
        };
      }
      return doc;
    });
    requirementResults.structured_result = {
      ...requirementResults.structured_result,
      lc_structured: {
        ...(requirementResults.structured_result?.lc_structured ?? {}),
        lc_classification: {
          workflow_orientation: 'export',
          instrument_type: 'documentary_credit',
          required_documents: [
            {
              code: 'beneficiary_certificate',
              display_name: 'Beneficiary Certificate',
              raw_text: 'BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026.',
            },
          ],
          requirement_conditions: [
            'ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001 AND BUYER PURCHASE ORDER NO. GBE-44592.',
          ],
          unmapped_requirements: [
            'UNKNOWN CERTIFICATE WORDING REQUIRING MANUAL MAPPING.',
          ],
        },
      },
    } as typeof requirementResults.structured_result;
    activeResults = requirementResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );

    const checklistCard = findCardByTitle(/Required Documents Checklist/i);
    expect(within(checklistCard).getAllByText(/Beneficiary Certificate/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).queryByText(/Required Document 1/i)).toBeNull();
    expect(within(checklistCard).queryByText(/Other Specified Document/i)).toBeNull();
    expect(within(checklistCard).getByText(/Document Presentation Conditions/i)).toBeInTheDocument();
    expect(within(checklistCard).getByText(/ALL DOCUMENTS MUST SHOW LC NO/i)).toBeInTheDocument();
    expect(within(checklistCard).getByText(/Requirement Text Needing Mapping/i)).toBeInTheDocument();
    expect(within(checklistCard).getByText(/UNKNOWN CERTIFICATE WORDING REQUIRING MANUAL MAPPING/i)).toBeInTheDocument();
  });

  it('uses canonical LC results in the drawer instead of raw per-document LC fields', async () => {
    const drawerResults = buildValidationResults();
    drawerResults.documents = drawerResults.documents.map((doc) =>
      doc.typeKey === 'letter_of_credit'
        ? {
            ...doc,
            extractedFields: {
              bl_number: 'MADE',
              issue_date: '260415',
              issuer: 'MARKING: NAME, BUYER NAME, LC NUMBER, STYLE, SIZE BREAKDOWN.',
            },
          }
        : doc,
    );
    drawerResults.structured_result = {
      ...drawerResults.structured_result,
      lc_structured: {
        ...(drawerResults.structured_result?.lc_structured ?? {}),
        number: 'EXP2026BD001',
        issue_date: '2026-04-15',
        expiry_date: '2026-10-15',
        latest_shipment_date: '2026-09-30',
        beneficiary: 'Dhaka Knitwear & Exports Ltd.',
        port_of_loading: 'CHITTAGONG SEA PORT, BANGLADESH',
        required_documents_detailed: [
          {
            code: 'beneficiary_certificate',
            display_name: 'Beneficiary Certificate',
            raw_text: 'BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026.',
          },
        ],
      },
    } as typeof drawerResults.structured_result;
    activeResults = drawerResults;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Documents/i }));
    const lcCard = findCardByTitle(/^LC\.pdf$/i);
    await user.click(within(lcCard).getByRole('button', { name: /View Details/i }));

    expect(screen.getByText(/Issue Date/i)).toBeInTheDocument();
    expect(screen.getByText('2026-04-15')).toBeInTheDocument();
    expect(screen.getAllByText(/Required Documents/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026\./i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/B\/L Number/i)).toBeNull();
    expect(screen.queryByText(/^MADE$/i)).toBeNull();
  });

  it('shows canonical LC dates on the results card from the structured LC payload', async () => {
    const lcDateResults = buildValidationResults();
    lcDateResults.structured_result = {
      ...lcDateResults.structured_result,
      lc_structured: {
        ...(lcDateResults.structured_result?.lc_structured ?? {}),
        issue_date: '2026-04-15',
        expiry_date: '2026-10-15',
        latest_shipment_date: '2026-09-30',
        dates: {
          issue: '2026-04-15',
          expiry: '2026-10-15',
          latest_shipment: '2026-09-30',
          place_of_expiry: 'USA',
        },
      },
    } as typeof lcDateResults.structured_result;
    activeResults = lcDateResults;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Documents/i }));
    const lcCard = findCardByTitle(/^LC\.pdf$/i);
    expect(within(lcCard).getByText(/Key Dates/i)).toBeInTheDocument();
    expect(within(lcCard).getByText('2026-10-15')).toBeInTheDocument();
    expect(within(lcCard).getByText('2026-09-30')).toBeInTheDocument();
    expect(within(lcCard).getByText('USA')).toBeInTheDocument();
  });

  it('does not present generic 47A placeholders as extracted condition detail', async () => {
    const placeholderResults = buildValidationResults();
    placeholderResults.structured_result = {
      ...placeholderResults.structured_result,
      lc_structured: {
        ...(placeholderResults.structured_result?.lc_structured ?? {}),
        number: '100924060096',
        amount: '100000',
        applicant: 'Applicant Co.',
        beneficiary: 'Beneficiary Co.',
        additional_conditions: ['ADDITIONAL CONDITIONS APPLY'],
      },
    } as typeof placeholderResults.structured_result;
    activeResults = placeholderResults;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Documents/i }));
    expect(
      screen.getByText(/Field 47A references additional conditions, but no detailed clause text was extracted/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/^ADDITIONAL CONDITIONS APPLY$/i)).toBeNull();
  });

  it('prioritizes canonical workflow and structured required documents over legacy lc_type fields', async () => {
    const canonicalResults = buildValidationResults();
    canonicalResults.structured_result = {
      ...canonicalResults.structured_result,
      lc_type: 'import',
      lc_structured: {
        ...(canonicalResults.structured_result?.lc_structured ?? {}),
        lc_type: 'import',
        required_document_types: ['commercial_invoice'],
        lc_classification: {
          workflow_orientation: 'export',
          instrument_type: 'standby_letter_of_credit',
          required_documents: [
            { code: 'commercial_invoice', display_name: 'Signed Commercial Invoice' },
            { code: 'beneficiary_certificate', display_name: 'Beneficiary Statement' },
            { code: 'insurance_certificate', raw_text: 'Insurance Certificate covering ICC (A) risks' },
            { code: 'analysis_certificate', display_name: 'Analysis Certificate' },
            {
              code: 'courier_or_post_receipt_or_certificate_of_posting',
              display_name: 'Courier Receipt',
              raw_text: 'Courier receipt evidencing dispatch within three days after shipment',
            },
          ],
        },
      },
    } as typeof canonicalResults.structured_result;
    activeResults = canonicalResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );

    expect(screen.getByText(/Workflow: Export LC/i)).toBeInTheDocument();
    expect(screen.getByText(/Instrument: Standby Letter of Credit/i)).toBeInTheDocument();
    const checklistCard = findCardByTitle(/Required Documents Checklist/i);
    expect(within(checklistCard).getAllByText(/Commercial Invoice/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).getAllByText(/Beneficiary (Certificate|Statement)/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).getAllByText(/Insurance Certificate/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).getAllByText(/Analysis Certificate/i).length).toBeGreaterThan(0);
    expect(within(checklistCard).getAllByText(/Courier Receipt/i).length).toBeGreaterThan(0);
  });

  it('does not derive workflow from legacy lc_type when lc_classification is missing', async () => {
    const legacyOnlyResults = buildValidationResults();
    legacyOnlyResults.structured_result = {
      ...legacyOnlyResults.structured_result,
      lc_type: 'export',
      lc_structured: {
        ...(legacyOnlyResults.structured_result?.lc_structured ?? {}),
        lc_type: 'export',
        lc_classification: null,
      },
    } as typeof legacyOnlyResults.structured_result;
    activeResults = legacyOnlyResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );

    expect(screen.queryByText(/Workflow: Export LC/i)).not.toBeInTheDocument();
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
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );
    expect(screen.getAllByText(/Route Potential sanctions match to internal compliance review/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/keep submission on hold until cleared/i).length).toBeGreaterThan(0);
  });

  it('keeps the summary strip documentary-first when only advisory findings are present', async () => {
    const advisoryResults = buildValidationResults({
      issues: [
        {
          ...mockValidationResults.issues[0],
          id: 'issue-advisory-only',
          title: 'Potential sanctions match',
          severity: 'critical',
          bucket: 'Compliance / Risk Review',
          workflow_lane: 'compliance_review',
          fix_owner: 'Internal Compliance Review',
          remediation_owner: 'Internal Compliance Review',
        },
      ],
    });
    advisoryResults.summary = {
      ...advisoryResults.summary,
      total_issues: 1,
    };
    advisoryResults.structured_result = {
      ...advisoryResults.structured_result,
      validation_contract_v1: {
        final_verdict: 'pass',
        rules_evidence: {
          issue_lanes: {
            documentary: { count: 0 },
            advisory: { count: 1 },
          },
          advisory_review_needed: true,
          primary_decision_lane: 'advisory',
        },
        evidence_summary: {
          primary_decision_lane: 'advisory',
          advisory_review_needed: true,
        },
      },
      effective_submission_eligibility: {
        can_submit: true,
        reasons: [],
      },
    } as typeof advisoryResults.structured_result;
    activeResults = advisoryResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );

    expect(screen.getByText('Documentary Issues')).toBeInTheDocument();
    expect(
      screen.getByText(/No blocking documentary issues\. 1 advisory alert remains visible separately\./i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Issues \(1\)/i)).toBeInTheDocument();
  });

  it('uses LC-required statement wording in the overview action engine and bank verdict card', async () => {
    const wordingResults = buildValidationResults({
      issues: [
        {
          ...mockValidationResults.issues[0],
          id: 'issue-wording',
          title: 'LC-required wording missing from Beneficiary Certificate',
          severity: 'critical',
          bucket: 'LC Required Statements',
          workflow_lane: 'documentary_review',
          fix_owner: 'Beneficiary',
          remediation_owner: 'Beneficiary',
          next_action:
            "Update the document to include the exact LC-required statement 'WE HEREBY CERTIFY GOODS ARE BRAND NEW' or seek an LC amendment before presentation.",
          requirement_source: 'requirements_graph_v1',
          requirement_kind: 'document_exact_wording',
          requirement_text: 'WE HEREBY CERTIFY GOODS ARE BRAND NEW',
          documentName: 'Beneficiary_Certificate.pdf',
          documentType: 'Beneficiary Certificate',
          documents: ['Beneficiary_Certificate.pdf'],
        },
      ],
    });
    wordingResults.structured_result = {
      ...wordingResults.structured_result,
      bank_verdict: {
        verdict: 'SUBMIT',
        verdict_color: 'green',
        verdict_message: 'Documents appear compliant',
        recommendation: 'Documents are ready for bank submission.',
        can_submit: true,
        will_be_rejected: false,
        estimated_discrepancy_fee: 0,
        issue_summary: { critical: 0, major: 0, minor: 0, total: 0 },
        action_items: [],
        action_items_count: 0,
      },
    } as typeof wordingResults.structured_result;
    activeResults = wordingResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );
    expect(screen.getAllByText(/Add LC-required statement to Beneficiary Certificate/i).length).toBeGreaterThan(0);
    expect(
      screen.getAllByText(/WE HEREBY CERTIFY GOODS ARE BRAND NEW/i).length,
    ).toBeGreaterThan(0);
  });

  it('reads readiness evidence from validation_contract_v1 even when no issue cards are present', async () => {
    const contractDrivenResults = buildValidationResults({
      issues: [],
    });
    contractDrivenResults.summary = {
      ...contractDrivenResults.summary,
      total_issues: 0,
      severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
    };
    contractDrivenResults.structured_result = {
      ...contractDrivenResults.structured_result,
      issues: [],
      processing_summary: {
        ...contractDrivenResults.structured_result?.processing_summary,
        total_issues: 0,
        severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
      },
      submission_eligibility: {
        can_submit: false,
        reasons: ['lc_required_statement_missing'],
      },
      effective_submission_eligibility: {
        can_submit: false,
        reasons: ['lc_required_statement_missing'],
      },
      validation_contract_v1: {
        final_verdict: 'review',
        rules_evidence: {
          requirement_readiness_items: [
            {
              title: 'LC-required wording missing from Beneficiary Certificate',
              document_name: 'Beneficiary Certificate',
              severity: 'critical',
              requirement_kind: 'document_exact_wording',
              requirement_text: 'WE HEREBY CERTIFY GOODS ARE BRAND NEW',
              action:
                "Update Beneficiary Certificate to include the exact LC-required statement 'WE HEREBY CERTIFY GOODS ARE BRAND NEW' or seek an LC amendment before presentation.",
            },
          ],
          requirement_reason_codes: ['lc_required_statement_missing'],
          requirements_review_needed: true,
        },
        evidence_summary: {
          requirements_review_needed: true,
          requirement_reason_codes: ['lc_required_statement_missing'],
          primary_requirement_actions: ['LC-required wording missing from Beneficiary Certificate'],
        },
      },
      bank_verdict: {
        verdict: 'SUBMIT',
        verdict_color: 'green',
        verdict_message: 'Documents appear compliant',
        recommendation: 'Documents are ready for bank submission.',
        can_submit: true,
        will_be_rejected: false,
        estimated_discrepancy_fee: 0,
        issue_summary: { critical: 0, major: 0, minor: 0, total: 0 },
        action_items: [],
        action_items_count: 0,
      },
    } as typeof contractDrivenResults.structured_result;
    activeResults = contractDrivenResults;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(
        screen.getByText(/Clean presentation still needs review because one or more LC-required statements or documentary requirements are unresolved/i),
      ).toBeInTheDocument(),
    );
    expect(screen.getAllByText(/Add LC-required statement to Beneficiary Certificate/i).length).toBeGreaterThan(0);
  });

  it('uses contract readiness evidence in the customs tab and keeps submit gated', async () => {
    const contractDrivenResults = buildValidationResults({
      issues: [],
    });
    contractDrivenResults.summary = {
      ...contractDrivenResults.summary,
      total_issues: 0,
      severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
    };
    contractDrivenResults.structured_result = {
      ...contractDrivenResults.structured_result,
      issues: [],
      processing_summary: {
        ...contractDrivenResults.structured_result?.processing_summary,
        total_issues: 0,
        severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
      },
      submission_eligibility: {
        can_submit: false,
        reasons: ['lc_required_statement_missing'],
      },
      effective_submission_eligibility: {
        can_submit: false,
        reasons: ['lc_required_statement_missing'],
      },
      validation_contract_v1: {
        final_verdict: 'review',
        rules_evidence: {
          requirement_readiness_items: [
            {
              title: 'LC-required wording missing from Beneficiary Certificate',
              document_name: 'Beneficiary Certificate',
              severity: 'critical',
              requirement_kind: 'document_exact_wording',
              requirement_text: 'WE HEREBY CERTIFY GOODS ARE BRAND NEW',
              action:
                "Update Beneficiary Certificate to include the exact LC-required statement 'WE HEREBY CERTIFY GOODS ARE BRAND NEW' or seek an LC amendment before presentation.",
            },
          ],
          requirement_reason_codes: ['lc_required_statement_missing'],
          requirements_review_needed: true,
        },
        evidence_summary: {
          requirements_review_needed: true,
          requirement_reason_codes: ['lc_required_statement_missing'],
          primary_requirement_actions: ['LC-required wording missing from Beneficiary Certificate'],
        },
      },
      bank_verdict: {
        verdict: 'SUBMIT',
        verdict_color: 'green',
        verdict_message: 'Documents appear compliant',
        recommendation: 'Documents are ready for bank submission.',
        can_submit: true,
        will_be_rejected: false,
        estimated_discrepancy_fee: 0,
        issue_summary: { critical: 0, major: 0, minor: 0, total: 0 },
        action_items: [],
        action_items_count: 0,
      },
    } as typeof contractDrivenResults.structured_result;
    activeResults = contractDrivenResults;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(
        screen.getByText(/Clean presentation still needs review because one or more LC-required statements or documentary requirements are unresolved/i),
      ).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    expect(within(customsPanel).getByText(/Contract readiness evidence/i)).toBeInTheDocument();
    expect(within(customsPanel).getByText(/Clean presentation remains blocked by compiled LC requirements/i)).toBeInTheDocument();
    expect(within(customsPanel).getAllByText(/LC-required wording missing from Beneficiary Certificate/i).length).toBeGreaterThan(0);
    expect(within(customsPanel).queryByRole('button', { name: /Submit to Bank/i })).toBeNull();
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
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    expect(within(customsPanel).queryByRole('button', { name: /Submit to Bank/i })).toBeNull();
  });

  it('shows submit to bank when eligibility and guardrails allow', async () => {
    const eligibleResults = buildValidationResults();
    eligibleResults.issues = [];
    eligibleResults.summary = {
      ...eligibleResults.summary,
      total_issues: 0,
      severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
    };
    eligibleResults.structured_result = {
      ...eligibleResults.structured_result,
      issues: [],
      processing_summary: {
        ...eligibleResults.structured_result?.processing_summary,
        total_issues: 0,
        severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
      },
      submission_eligibility: { can_submit: true, reasons: [] },
      effective_submission_eligibility: { can_submit: true, reasons: [] },
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
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    await waitFor(() =>
      expect(within(customsPanel).getByRole('button', { name: /Submit to Bank/i })).toBeInTheDocument(),
    );
  });

  it('downgrades ready-to-submit surfaces when checklist review is still unresolved', async () => {
    const reviewResults = buildValidationResults();
    reviewResults.issues = [];
    reviewResults.summary = {
      ...reviewResults.summary,
      total_issues: 0,
      severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
    };
    reviewResults.documents = reviewResults.documents.map((doc) => {
      if (doc.typeKey === 'commercial_invoice') {
        return {
          ...doc,
          issuesCount: 0,
          requirementStatus: 'matched',
          reviewState: 'needs_review',
          reviewReasons: ['Invoice totals need manual review'],
        };
      }
      return {
        ...doc,
        issuesCount: 0,
        requirementStatus: 'matched',
        reviewState: 'ready',
        reviewReasons: [],
      };
    });
    reviewResults.structured_result = {
      ...reviewResults.structured_result,
      issues: [],
      processing_summary: {
        ...reviewResults.structured_result?.processing_summary,
        total_issues: 0,
        severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
      },
      submission_eligibility: { can_submit: true, reasons: [] },
      effective_submission_eligibility: { can_submit: true, reasons: [] },
      bank_verdict: {
        verdict: 'SUBMIT',
        verdict_color: 'green',
        verdict_message: 'Documents appear compliant',
        recommendation: 'Documents are ready for bank submission.',
        can_submit: true,
        will_be_rejected: false,
        estimated_discrepancy_fee: 0,
        issue_summary: { critical: 0, major: 0, minor: 0, total: 0 },
        action_items: [],
        action_items_count: 0,
      },
      lc_structured: {
        ...(reviewResults.structured_result?.lc_structured ?? {}),
        lc_classification: {
          workflow_orientation: 'export',
          instrument_type: 'documentary_credit',
          required_documents: [{ code: 'commercial_invoice', display_name: 'Commercial Invoice' }],
        },
      },
    } as typeof reviewResults.structured_result;
    activeResults = reviewResults;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Review needed/i)).toBeInTheDocument(),
    );

    expect(screen.queryByText(/READY TO SUBMIT/i)).not.toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Issues \(1\)/i })).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Issues \(1\)/i }));
    expect(screen.getByText(/No formal discrepancy cards were generated, but unresolved review findings still need operator attention/i)).toBeInTheDocument();
    expect(screen.queryByText(/No documentary discrepancies, review findings, or compliance alerts are open for this run/i)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Complete review for Commercial Invoice/i).length).toBeGreaterThan(0);
  });

  it('renders UI when only structured_result payload is provided', async () => {
    const user = userEvent.setup();
    const structuredOnly = buildValidationResponse({
      structured_result: mockValidationResults.structured_result,
    });
    activeResults = structuredOnly;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Documents/i }));
    expect(
      screen.getByText(structuredOnly.documents[0]?.name ?? 'Letter of Credit'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Issues/i }));
    expect(screen.getAllByText(structuredOnly.issues[0]?.title ?? 'Review Required').length).toBeGreaterThan(0);
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
    expect(screen.getByText(/No documentary discrepancies, review findings, or compliance alerts are open for this run/i)).toBeInTheDocument();
  });

  it('renders non-required insurance uploads as informational instead of failed requirement coverage', async () => {
    const insuranceResults = buildValidationResults();
    insuranceResults.documents = insuranceResults.documents.map((doc) => {
      if (doc.typeKey === 'insurance_certificate') {
        return {
          ...doc,
          issuesCount: 0,
          requirementStatus: 'partial',
          reviewState: 'needs_review',
          warningReasons: ['Insurance coverage details need manual confirmation before presentation.'],
          reviewReasons: ['Insurance coverage details need manual confirmation before presentation.'],
        };
      }
      return doc;
    });
    insuranceResults.structured_result = {
      ...insuranceResults.structured_result,
      lc_structured: {
        ...(insuranceResults.structured_result?.lc_structured ?? {}),
        lc_classification: {
          workflow_orientation: 'export',
          instrument_type: 'documentary_credit',
          required_documents: [
            { code: 'commercial_invoice', display_name: 'Commercial Invoice' },
            { code: 'bill_of_lading', display_name: 'Bill of Lading' },
          ],
        },
      },
    } as typeof insuranceResults.structured_result;
    activeResults = insuranceResults;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await user.click(screen.getByRole('tab', { name: /Documents/i }));

    const insuranceCard = findCardByTitle(/Insurance\.pdf/i);
    expect(within(insuranceCard).getByText(/Extra upload/i)).toBeInTheDocument();
    expect(within(insuranceCard).getByText(/Informational only/i)).toBeInTheDocument();
    expect(within(insuranceCard).queryByText(/Partially covers requirement/i)).toBeNull();
  });

  it('replaces generic invoice and packing review text with source-aware reasons from structured payloads', async () => {
    const structured = JSON.parse(JSON.stringify(mockValidationResults.structured_result));
    structured.issues = [];
    structured.processing_summary = {
      ...structured.processing_summary,
      total_issues: 0,
      severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
    };
    structured.lc_structured = {
      ...(structured.lc_structured ?? {}),
      lc_classification: {
        workflow_orientation: 'export',
        instrument_type: 'documentary_credit',
        required_documents: [
          { code: 'commercial_invoice', display_name: 'Commercial Invoice' },
          { code: 'packing_list', display_name: 'Packing List' },
        ],
      },
    };

    const documentsStructured = [
      {
        document_id: 'doc-invoice',
        document_type: 'commercial_invoice',
        filename: 'Invoice.pdf',
        extraction_status: 'success',
        review_required: true,
        review_reasons: ['FIELD_NOT_FOUND', 'critical_issue_date_missing'],
        critical_field_states: { issue_date: 'missing' },
        extracted_fields: { invoice_number: 'DKEL/EXP/2026/114' },
        extraction_artifacts_v1: {
          raw_text: 'Commercial Invoice\nLC No: EXP2026BD001\nTotal Amount: USD 458,750.00\n',
          field_diagnostics: {
            issue_date: { state: 'missing', reason_codes: ['FIELD_NOT_FOUND'] },
          },
        },
      },
      {
        document_id: 'doc-pack',
        document_type: 'packing_list',
        filename: 'Packing_List.pdf',
        extraction_status: 'partial',
        review_required: true,
        review_reasons: ['FIELD_NOT_FOUND', 'critical_issue_date_missing'],
        critical_field_states: { issue_date: 'missing' },
        extracted_fields: { gross_weight: '20400 KG', net_weight: '18950 KG' },
        extraction_artifacts_v1: {
          raw_text: 'Packing List\nLC No: EXP2026BD001\nNet Weight: 18,950 kg\nGross Weight: 20,400 kg\n',
          field_diagnostics: {
            issue_date: { state: 'missing', reason_codes: ['FIELD_NOT_FOUND'] },
          },
        },
      },
    ];

    structured.documents_structured = documentsStructured;
    structured.documents = documentsStructured as any;
    structured.lc_structured.documents_structured = documentsStructured;
    activeResults = buildValidationResponse({ structured_result: structured });

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /Documents/i })).toHaveAttribute('aria-selected', 'true'),
    );

    expect(screen.getAllByText(/Source invoice does not show an invoice date/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Source packing list does not clearly show a document date/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/^Field not found$/i)).toBeNull();
  });

  it('marks unresolved extraction as provisional and uses source-aware review notes in the invoice and packing detail drawers', async () => {
    const structured = buildValidationResults().structured_result!;
    const documentsStructured = [
      {
        document_id: 'doc-invoice',
        document_type: 'commercial_invoice',
        filename: 'Invoice.pdf',
        extraction_status: 'success',
        review_required: true,
        review_reasons: ['FIELD_NOT_FOUND', 'critical_issue_date_missing', 'critical_gross_weight_missing', 'critical_net_weight_missing'],
        critical_field_states: {
          issue_date: 'missing',
          gross_weight: 'missing',
          net_weight: 'missing',
          issuer: 'found',
        },
        field_details: {
          invoice_number: {
            value: 'DKEL/EXP/2026/114',
            confidence: 0.93,
            verification: 'confirmed',
            evidence: {
              source: 'native_text',
              snippet: 'Commercial Invoice Invoice Number: DKEL/EXP/2026/114',
            },
          },
          issuer: {
            value: 'Dhaka Knitwear & Exports Ltd.',
            confidence: 0.88,
            verification: 'model_suggested',
          },
        },
        extracted_fields: { invoice_number: 'DKEL/EXP/2026/114', issuer: 'Dhaka Knitwear & Exports Ltd.' },
        extraction_artifacts_v1: {
          raw_text: 'Commercial Invoice\nLC No: EXP2026BD001\nTotal Amount: USD 458,750.00\n',
          field_diagnostics: {
            issue_date: { state: 'missing', reason_codes: ['FIELD_NOT_FOUND'] },
            gross_weight: { state: 'missing', reason_codes: ['FIELD_NOT_FOUND'] },
            net_weight: { state: 'missing', reason_codes: ['FIELD_NOT_FOUND'] },
          },
        },
      },
      {
        document_id: 'doc-pack',
        document_type: 'packing_list',
        filename: 'Packing_List.pdf',
        extraction_status: 'partial',
        review_required: true,
        review_reasons: ['FIELD_NOT_FOUND', 'critical_issue_date_missing'],
        critical_field_states: { issue_date: 'missing', gross_weight: 'found', net_weight: 'found' },
        field_details: {
          gross_weight: {
            value: '20,400 kg',
            confidence: 0.9,
            verification: 'confirmed',
            evidence: {
              source: 'native_text',
              snippet: 'Gross Weight: 20,400 kg',
            },
          },
        },
        extracted_fields: { gross_weight: '20,400 kg', net_weight: '18,950 kg' },
        extraction_artifacts_v1: {
          raw_text: 'Packing List\nLC No: EXP2026BD001\nNet Weight: 18,950 kg\nGross Weight: 20,400 kg\n',
          field_diagnostics: {
            issue_date: { state: 'missing', reason_codes: ['FIELD_NOT_FOUND'] },
          },
        },
      },
    ];

    structured.documents_structured = documentsStructured;
    structured.documents = documentsStructured as any;
    structured.lc_structured.documents_structured = documentsStructured;
    structured.workflow_stage = {
      stage: 'extraction_resolution',
      provisional_validation: true,
      ready_for_final_validation: false,
      unresolved_documents: 2,
      unresolved_fields: 4,
      summary: '2 documents still need 4 fields confirmed before validation should be treated as final.',
    } as any;
    activeResults = buildValidationResponse({ structured_result: structured });

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /Documents/i })).toHaveAttribute('aria-selected', 'true'),
    );

    expect(screen.getByRole('heading', { name: /Export LC Extraction Resolution/i })).toBeInTheDocument();
    expect(
      screen.getByText(/Confirm unresolved extracted fields from source evidence before treating validation as final\./i),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Extraction Resolution Required/i })).toBeInTheDocument();
    expect(
      screen.getAllByText(/2 documents still need 4 fields confirmed before validation should be treated as final\./i).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByRole('heading', { name: /Validation Results Unlock After Extraction Resolution/i }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /Issues/i })).toBeNull();
    expect(screen.queryByRole('tab', { name: /Customs Pack/i })).toBeNull();
    expect(screen.getByText(/Opens later: Issues/i)).toBeInTheDocument();
    expect(screen.getByText(/Opens later: Customs Pack/i)).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Overview/i }));
    expect(screen.getByRole('heading', { name: /Current Stage: Extraction Resolution/i })).toBeInTheDocument();
    expect(screen.getByText(/LC-required documents, uploaded files, and provisional requirement coverage/i)).toBeInTheDocument();
    expect(screen.getByText(/Checklist coverage is still provisional/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Use the Documents tab to review source evidence and confirm only the unresolved fields\./i),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Documents/i }));

    const invoiceCard = findCardByTitle(/^Invoice\.pdf$/i);
    expect(within(invoiceCard).getAllByText(/Needs field confirmation/i).length).toBeGreaterThan(0);
    await user.click(within(invoiceCard).getByRole('button', { name: /View Details/i }));
    const invoiceDrawer = screen.getByRole('dialog');
    expect(within(invoiceDrawer).getByText(/Source invoice does not show an invoice date\./i)).toBeInTheDocument();
    expect(within(invoiceDrawer).getByText(/This workflow confirms gross\/net weight from the packing list or bill of lading, not from the invoice\./i)).toBeInTheDocument();
    expect(within(invoiceDrawer).getByText(/Confirmed from native_text: Commercial Invoice Invoice Number: DKEL\/EXP\/2026\/114/i)).toBeInTheDocument();
    expect(within(invoiceDrawer).getByText(/Model suggested this value, but the source text did not confirm it directly\./i)).toBeInTheDocument();
    expect(within(invoiceDrawer).queryByText(/^Field not found$/i)).toBeNull();
    expect(within(invoiceDrawer).queryByText(/Field Diagnostics/i)).toBeNull();

    await user.keyboard('{Escape}');

    const packingCard = findCardByTitle(/^Packing_List\.pdf$/i);
    await user.click(within(packingCard).getByRole('button', { name: /View Details/i }));
    const packingDrawer = screen.getByRole('dialog');
    expect(within(packingDrawer).getByText(/Source packing list does not clearly show a document date\./i)).toBeInTheDocument();
    expect(within(packingDrawer).getByText(/Confirmed from native_text: Gross Weight: 20,400 kg/i)).toBeInTheDocument();
    expect(within(packingDrawer).queryByText(/^Field not found$/i)).toBeNull();

    await user.keyboard('{Escape}');
  });

  it('keeps an explicitly requested tab during extraction resolution instead of auto-switching to documents', async () => {
    const structured = buildValidationResults().structured_result!;
    structured.workflow_stage = {
      stage: 'extraction_resolution',
      provisional_validation: true,
      ready_for_final_validation: false,
      unresolved_documents: 1,
      unresolved_fields: 1,
      summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
    } as any;
    activeResults = buildValidationResponse({ structured_result: structured });

    render(renderWithProviders(<ExporterResults initialTab="overview" />));

    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /Overview/i })).toHaveAttribute('aria-selected', 'true'),
    );
    expect(screen.getByText(/Validation Timeline/i)).toBeInTheDocument();
  });

  it('redirects blocked final-validation tabs back to documents during extraction resolution', async () => {
    const structured = buildValidationResults().structured_result!;
    structured.workflow_stage = {
      stage: 'extraction_resolution',
      provisional_validation: true,
      ready_for_final_validation: false,
      unresolved_documents: 1,
      unresolved_fields: 1,
      summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
    } as any;
    activeResults = buildValidationResponse({ structured_result: structured });

    render(renderWithProviders(<ExporterResults initialTab="discrepancies" />));

    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /Documents/i })).toHaveAttribute('aria-selected', 'true'),
    );
    expect(screen.queryByRole('tab', { name: /Issues/i })).toBeNull();
    expect(screen.getByRole('heading', { name: /Validation Results Unlock After Extraction Resolution/i })).toBeInTheDocument();
  });

  it('lets the operator directly confirm a suggested unresolved value when evidence already exists', async () => {
    const structured = buildValidationResults().structured_result!;
    const refreshResults = vi.fn().mockResolvedValue(activeResults);
    const { exporterApi } = await import('@/api/exporter');
    const saveFieldOverride = vi.mocked(exporterApi.saveFieldOverride);

    const documentsStructured = [
      {
        document_id: 'doc-invoice',
        document_type: 'commercial_invoice',
        filename: 'Invoice.pdf',
        extraction_status: 'success',
        review_required: true,
        review_reasons: ['critical_issue_date_missing'],
        critical_field_states: { issue_date: 'missing' },
        field_details: {
          invoice_date: {
            verification: 'model_suggested',
            status: 'missing',
            value: '2026-04-20',
            evidence: {
              source: 'native_text',
              snippet: 'Invoice Date: 20 Apr 2026',
            },
          },
        },
        extraction_resolution: {
          required: true,
          unresolved_count: 1,
          summary: 'Invoice date still needs confirmation from source evidence.',
          fields: [{ field_name: 'invoice_date', label: 'Invoice Date', verification: 'model_suggested' }],
        },
        extracted_fields: { invoice_number: 'DKEL/EXP/2026/114' },
        extraction_artifacts_v1: {
          raw_text: 'Commercial Invoice\nInvoice Date: 20 Apr 2026\nLC No: EXP2026BD001\n',
          field_diagnostics: {
            issue_date: { state: 'missing', reason_codes: ['FIELD_NOT_FOUND'] },
          },
        },
      },
    ];

    structured.documents_structured = documentsStructured;
    structured.documents = documentsStructured as any;
    structured.lc_structured.documents_structured = documentsStructured;
    structured.workflow_stage = {
      stage: 'extraction_resolution',
      provisional_validation: true,
      ready_for_final_validation: false,
      unresolved_documents: 1,
      unresolved_fields: 1,
      summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
    } as any;
    activeResults = buildValidationResponse({ structured_result: structured });
    refreshResults.mockResolvedValue(activeResults);
    mockUseCanonicalJobResult.mockReturnValue({
      jobStatus: { status: 'completed' },
      results: activeResults,
      isLoading: false,
      resultsError: null,
      jobError: null,
      refreshResults,
    });

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults jobId="job-123" />));
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /Documents/i })).toHaveAttribute('aria-selected', 'true'),
    );

    const invoiceCard = findCardByTitle(/^Invoice\.pdf$/i);
    await user.click(within(invoiceCard).getByRole('button', { name: /View Details/i }));

    const drawer = screen.getByRole('dialog');
    expect(within(drawer).getAllByText(/Suggested value/i).length).toBeGreaterThan(0);
    expect(within(drawer).getByText('2026-04-20')).toBeInTheDocument();
    expect(within(drawer).getByText(/Model-suggested candidate/i)).toBeInTheDocument();
    expect(within(drawer).queryByLabelText(/^Confirmed value$/i)).toBeNull();
    await user.click(within(drawer).getByRole('button', { name: /Confirm suggested value/i }));

    await waitFor(() =>
      expect(saveFieldOverride).toHaveBeenCalledWith('job-123', {
        document_id: 'doc-invoice',
        field_name: 'invoice_date',
        override_value: '2026-04-20',
        verification: 'operator_confirmed',
        note: undefined,
      }),
    );
    await waitFor(() => expect(refreshResults).toHaveBeenCalledWith('manual'));
  });

  it('uses backend resolution queue items for invoice confirmation instead of deriving invoice misses from raw field metadata', async () => {
    const structured = buildValidationResults().structured_result!;
    const documentsStructured = [
      {
        document_id: 'doc-invoice',
        document_type: 'commercial_invoice',
        filename: 'Invoice.pdf',
        extraction_status: 'success',
        review_required: true,
        review_reasons: ['FIELD_NOT_FOUND'],
        critical_field_states: { seller: 'missing' },
        field_details: {
          seller: {
            verification: 'not_found',
          },
        },
        missing_required_fields: ['seller'],
        required_fields_found: 0,
        required_fields_total: 1,
        parse_complete: false,
        extracted_fields: { invoice_number: 'DKEL/EXP/2026/114' },
        extraction_artifacts_v1: {
          raw_text: 'Commercial Invoice\nInvoice Date: 20 Apr 2026\nLC No: EXP2026BD001\n',
          field_diagnostics: {
            seller: { state: 'missing', reason_codes: ['FIELD_NOT_FOUND'] },
          },
        },
      },
    ];

    structured.document_extraction_v1 = { documents: documentsStructured } as any;
    structured.documents_structured = documentsStructured as any;
    structured.documents = documentsStructured as any;
    structured.lc_structured.documents_structured = documentsStructured as any;
    structured.resolution_queue_v1 = {
      version: 'resolution_queue_v1',
      items: [
        {
          document_id: 'doc-invoice',
          document_type: 'commercial_invoice',
          filename: 'Invoice.pdf',
          field_name: 'invoice_date',
          label: 'Invoice Date',
          priority: 'high',
          candidate_value: '2026-04-20',
          normalized_value: '2026-04-20',
          evidence_snippet: 'Invoice Date: 20 Apr 2026',
          evidence_source: 'native_text',
          page: 1,
          reason: 'system_could_not_confirm',
          verification_state: 'model_suggested',
          resolvable_by_user: true,
          origin: 'document_ai',
        },
      ],
      summary: {
        total_items: 1,
        user_resolvable_items: 1,
        unresolved_documents: 1,
        document_counts: { commercial_invoice: 1 },
      },
    } as any;
    structured.workflow_stage = {
      stage: 'extraction_resolution',
      provisional_validation: true,
      ready_for_final_validation: false,
      unresolved_documents: 1,
      unresolved_fields: 1,
      summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
    } as any;

    activeResults = buildValidationResponse({ structured_result: structured });

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults jobId="job-123" />));
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /Documents/i })).toHaveAttribute('aria-selected', 'true'),
    );

    const invoiceCard = findCardByTitle(/^Invoice\.pdf$/i);
    expect(within(invoiceCard).queryByText(/extraction-required fields found/i)).toBeNull();
    await user.click(within(invoiceCard).getByRole('button', { name: /View Details/i }));

    const drawer = screen.getByRole('dialog');
    expect(within(drawer).getByRole('button', { name: /^Invoice Date$/i })).toBeInTheDocument();
    expect(within(drawer).queryByRole('button', { name: /^Seller$/i })).toBeNull();
    expect(within(drawer).getByText('2026-04-20')).toBeInTheDocument();
    expect(within(drawer).getByText(/Invoice Date: 20 Apr 2026/i)).toBeInTheDocument();
  });

  it('lets the operator reject a suggested unresolved value and keep the session provisional', async () => {
    const structured = buildValidationResults().structured_result!;
    const refreshResults = vi.fn().mockResolvedValue(activeResults);
    const { exporterApi } = await import('@/api/exporter');
    const saveFieldOverride = vi.mocked(exporterApi.saveFieldOverride);

    const documentsStructured = [
      {
        document_id: 'doc-invoice',
        document_type: 'commercial_invoice',
        filename: 'Invoice.pdf',
        extraction_status: 'success',
        review_required: true,
        review_reasons: ['critical_issue_date_missing'],
        critical_field_states: { issue_date: 'missing' },
        field_details: {
          invoice_date: {
            verification: 'model_suggested',
            status: 'missing',
            value: '2026-04-20',
            evidence: {
              source: 'native_text',
              snippet: 'Invoice Date: 20 Apr 2026',
            },
          },
        },
        extraction_resolution: {
          required: true,
          unresolved_count: 1,
          summary: 'Invoice date still needs confirmation from source evidence.',
          fields: [{ field_name: 'invoice_date', label: 'Invoice Date', verification: 'model_suggested' }],
        },
        extracted_fields: { invoice_number: 'DKEL/EXP/2026/114' },
        extraction_artifacts_v1: {
          raw_text: 'Commercial Invoice\nInvoice Date: 20 Apr 2026\nLC No: EXP2026BD001\n',
          field_diagnostics: {
            issue_date: { state: 'missing', reason_codes: ['FIELD_NOT_FOUND'] },
          },
        },
      },
    ];

    structured.documents_structured = documentsStructured;
    structured.documents = documentsStructured as any;
    structured.lc_structured.documents_structured = documentsStructured;
    structured.workflow_stage = {
      stage: 'extraction_resolution',
      provisional_validation: true,
      ready_for_final_validation: false,
      unresolved_documents: 1,
      unresolved_fields: 1,
      summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
    } as any;
    activeResults = buildValidationResponse({ structured_result: structured });
    refreshResults.mockResolvedValue(activeResults);
    mockUseCanonicalJobResult.mockReturnValue({
      jobStatus: { status: 'completed' },
      results: activeResults,
      isLoading: false,
      resultsError: null,
      jobError: null,
      refreshResults,
    });

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults jobId="job-123" />));
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /Documents/i })).toHaveAttribute('aria-selected', 'true'),
    );

    const invoiceCard = findCardByTitle(/^Invoice\.pdf$/i);
    await user.click(within(invoiceCard).getByRole('button', { name: /View Details/i }));

    const drawer = screen.getByRole('dialog');
    await user.click(within(drawer).getByRole('button', { name: /Reject suggested value/i }));

    await waitFor(() =>
      expect(saveFieldOverride).toHaveBeenCalledWith('job-123', {
        document_id: 'doc-invoice',
        field_name: 'invoice_date',
        override_value: '2026-04-20',
        verification: 'operator_rejected',
        note: undefined,
      }),
    );
    await waitFor(() => expect(refreshResults).toHaveBeenCalledWith('manual'));
    expect(mockToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Suggestion rejected for this session',
      }),
    );
  });

  it('saves an operator-confirmed field override from the document detail drawer and refreshes the same session results', async () => {
    const structured = buildValidationResults().structured_result!;
    const refreshResults = vi.fn().mockResolvedValue(activeResults);
    const { exporterApi } = await import('@/api/exporter');
    const saveFieldOverride = vi.mocked(exporterApi.saveFieldOverride);

    const documentsStructured = [
      {
        document_id: 'doc-invoice',
        document_type: 'commercial_invoice',
        filename: 'Invoice.pdf',
        extraction_status: 'success',
        review_required: true,
        review_reasons: ['FIELD_NOT_FOUND', 'critical_issue_date_missing'],
        critical_field_states: { issue_date: 'missing' },
        field_details: {
          invoice_date: {
            verification: 'not_found',
            status: 'missing',
          },
        },
        extracted_fields: { invoice_number: 'DKEL/EXP/2026/114' },
        extraction_artifacts_v1: {
          raw_text: 'Commercial Invoice\nLC No: EXP2026BD001\nTotal Amount: USD 458,750.00\n',
          field_diagnostics: {
            issue_date: { state: 'missing', reason_codes: ['FIELD_NOT_FOUND'] },
          },
        },
      },
    ];

    structured.documents_structured = documentsStructured;
    structured.documents = documentsStructured as any;
    structured.lc_structured.documents_structured = documentsStructured;
    activeResults = buildValidationResponse({ structured_result: structured });
    refreshResults.mockResolvedValue(activeResults);
    mockUseCanonicalJobResult.mockReturnValue({
      jobStatus: { status: 'completed' },
      results: activeResults,
      isLoading: false,
      resultsError: null,
      jobError: null,
      refreshResults,
    });

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults jobId="job-123" />));
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /Documents/i })).toHaveAttribute('aria-selected', 'true'),
    );

    const invoiceCard = findCardByTitle(/^Invoice\.pdf$/i);
    await user.click(within(invoiceCard).getByRole('button', { name: /View Details/i }));

    const drawer = screen.getByRole('dialog');
    expect(within(drawer).getByText(/Confirm Unresolved Fields/i)).toBeInTheDocument();
    expect(within(drawer).getByText(/No suggested value yet/i)).toBeInTheDocument();
    expect(
      within(drawer).getByText(/The system could not propose a reliable value for this field from the uploaded document\./i),
    ).toBeInTheDocument();
    expect(within(drawer).queryByLabelText(/Confirmed value/i)).toBeNull();
    await user.click(within(drawer).getByRole('button', { name: /Enter value manually/i }));
    await user.type(within(drawer).getByLabelText(/Confirmed value/i), '2026-04-20');
    await user.type(within(drawer).getByLabelText(/Operator note/i), 'Confirmed from invoice header');
    await user.click(within(drawer).getByRole('button', { name: /Confirm field value/i }));

    await waitFor(() =>
      expect(saveFieldOverride).toHaveBeenCalledWith('job-123', {
        document_id: 'doc-invoice',
        field_name: 'invoice_date',
        override_value: '2026-04-20',
        verification: 'operator_confirmed',
        note: 'Confirmed from invoice header',
      }),
    );
    await waitFor(() => expect(refreshResults).toHaveBeenCalledWith('manual'));
    expect(mockToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Field saved for this session',
      }),
    );
  });

  it('still renders overview when structured_result analytics are missing', async () => {
    const withoutAnalytics = buildValidationResults();
    (withoutAnalytics.structured_result as any).analytics = undefined;
    activeResults = withoutAnalytics;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument();
  });

  it('hides the timeline when no events are provided', async () => {
    const noTimeline = buildValidationResults();
    noTimeline.timeline = [];
    if (noTimeline.structured_result) {
      noTimeline.structured_result.timeline = [];
    }
    activeResults = noTimeline;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() => expect(screen.getByText(/Required Documents Checklist/i)).toBeInTheDocument());
    expect(screen.queryByText(/Validation Timeline/i)).not.toBeInTheDocument();
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
    expect(screen.getAllByText(/Extraction needs review/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/LC requirement match/i).length).toBeGreaterThan(0);
  });

  it('separates extraction, requirement, and review truth on document cards', async () => {
    const docTruth = buildValidationResults();
    docTruth.documents[0].status = 'success';
    docTruth.documents[0].requirementStatus = 'matched';
    docTruth.documents[0].reviewState = 'needs_review';
    docTruth.documents[0].reviewReasons = ['Invoice totals need manual review'];
    activeResults = docTruth;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await user.click(screen.getByRole('tab', { name: /Documents/i }));

    expect(screen.getAllByText(/What we read from this file/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/LC requirement match/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Current review status/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Covers LC requirement/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Current review status/i).length).toBeGreaterThan(0);
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
    expect(screen.getAllByText(/Structured read complete/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Covers LC requirement/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/could not be fully parsed/i)).not.toBeInTheDocument();
  });
});

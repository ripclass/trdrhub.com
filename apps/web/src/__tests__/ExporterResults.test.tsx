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
  const heading = screen.getAllByText(title)[index];
  let current: HTMLElement | null = heading as HTMLElement;
  while (current && !current.className.toString().includes('shadow-soft')) {
    current = current.parentElement as HTMLElement | null;
  }
  return current ?? (heading as HTMLElement);
};

const mockUseCanonicalJobResult = vi.fn();

vi.mock('@/hooks/use-lcopilot', () => {
  return {
    useCanonicalJobResult: () => mockUseCanonicalJobResult(),
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

vi.mock('@/config/exporterFeatureFlags', () => ({
  isExporterFeatureEnabled: vi.fn(() => true),
}));

describe('ExporterResults', () => {
  beforeEach(() => {
    activeResults = buildValidationResults();
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
    expect(screen.getByText(/LC Compliance:/i)).toBeInTheDocument();

    const statsCard = findCardByTitle(/Export Document Statistics/i);
    const verifiedLabel = within(statsCard).getByText(/^Verified$/i);
    const verifiedValue = verifiedLabel.previousElementSibling;
    expect(verifiedValue?.textContent).toBe(String(successCount));

    const warningsLabel = within(statsCard).getByText(/^Warnings$/i);
    const warningsValue = warningsLabel.previousElementSibling;
    expect(warningsValue?.textContent).toBe(String(warningDocumentCount));

    const complianceRow = screen.getByText(/LC Compliance:/i).parentElement as HTMLElement;
    const expectedCompliance = `${mockValidationResults.analytics.compliance_score}%`;
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

    const summaryCard = findCardByTitle(/Issue Review Summary/i);
    const criticalLabel = within(summaryCard).getByText(/High-likelihood discrepancy/i);
    const majorLabel = within(summaryCard).getByText(/Likely discrepancy/i);
    const minorLabel = within(summaryCard).getByText(/^Review required$/i);
    expect(criticalLabel.nextElementSibling?.textContent).toBe(expectedSeverityCounts.critical.toString());
    expect(majorLabel.nextElementSibling?.textContent).toBe(expectedSeverityCounts.major.toString());
    expect(minorLabel.nextElementSibling?.textContent).toBe(expectedSeverityCounts.minor.toString());

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
    expect(screen.getAllByText(`${mockValidationResults.analytics.compliance_score}%`).length).toBeGreaterThan(0);
  });

  it('keeps document status counts aligned between overview and documents tab', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );

    const statusCard = findCardByTitle(/Document Status/i, 1);
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

    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: /Issues \(3\)/i }));
    expect(screen.getAllByTestId(/issue-card-/)).toHaveLength(3);
    const summaryCard = findCardByTitle(/Issue Review Summary/i);
    const totalIssuesLabel = within(summaryCard).getByText(/Total Issues/i);
    expect(totalIssuesLabel.nextElementSibling?.textContent).toBe('3');
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

  it('shows a terminal no-results state instead of pretending validation is still running', async () => {
    const refreshResults = vi.fn().mockResolvedValue(null);
    mockUseCanonicalJobResult.mockReturnValue({
      jobStatus: { status: 'completed' },
      results: null,
      isLoading: false,
      resultsError: null,
      jobError: null,
      refreshResults,
    });

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));

    expect(screen.getByText(/Validation finished, but results are not available yet/i)).toBeInTheDocument();
    expect(screen.queryByText(/Validation in progress/i)).toBeNull();

    await user.click(screen.getByRole('button', { name: /Retry loading results/i }));
    expect(refreshResults).toHaveBeenCalledWith('manual');
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
      expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    expect(within(customsPanel).getAllByText(/Ready for presentation/i).length).toBeGreaterThan(0);
    expect(within(customsPanel).queryByText(/Not ready for presentation/i)).toBeNull();
    expect(
      within(customsPanel).getByText(/Submission readiness follows backend validation eligibility/i),
    ).toBeInTheDocument();
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
      expect(screen.getByText(/Required Document Checklist/i)).toBeInTheDocument(),
    );

    expect(screen.getAllByText(/Export LC/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Workflow: Export LC/i)).toBeInTheDocument();
    expect(screen.getByText(/Instrument: Documentary Credit/i)).toBeInTheDocument();
    const checklistCard = findCardByTitle(/Required Document Checklist/i);
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
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
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
      expect(screen.getByText(/Required Document Checklist/i)).toBeInTheDocument(),
    );

    const checklistCard = findCardByTitle(/Required Document Checklist/i);
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
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Documents/i }));
    const lcCard = findCardByTitle(/^LC\.pdf$/i);
    await user.click(within(lcCard).getByRole('button', { name: /View Details/i }));

    expect(screen.getByText(/Issue Date/i)).toBeInTheDocument();
    expect(screen.getByText('2026-04-15')).toBeInTheDocument();
    expect(screen.getAllByText(/Required Documents/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026\./i)).toBeInTheDocument();
    expect(screen.queryByText(/B\/L Number/i)).toBeNull();
    expect(screen.queryByText(/^MADE$/i)).toBeNull();
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
      expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument(),
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
      expect(screen.getByText(/Required Document Checklist/i)).toBeInTheDocument(),
    );

    expect(screen.getByText(/Workflow: Export LC/i)).toBeInTheDocument();
    expect(screen.getByText(/Instrument: Standby Letter of Credit/i)).toBeInTheDocument();
    const checklistCard = findCardByTitle(/Required Document Checklist/i);
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
      expect(screen.getByText(/Required Document Checklist/i)).toBeInTheDocument(),
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
      expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));
    const customsPanel = screen.getByRole('tabpanel', { name: /customs/i });
    await waitFor(() =>
      expect(within(customsPanel).getByRole('button', { name: /Submit to Bank/i })).toBeInTheDocument(),
    );
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
    expect(screen.getAllByText(/Extraction warning/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Requirement coverage/i).length).toBeGreaterThan(0);
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

    expect(screen.getAllByText(/Extraction truth/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Requirement coverage/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Review consequence/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Requirement matched/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Review consequence/i).length).toBeGreaterThan(0);
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
    expect(screen.getAllByText(/Extracted/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Requirement matched/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/could not be fully parsed/i)).not.toBeInTheDocument();
  });
});

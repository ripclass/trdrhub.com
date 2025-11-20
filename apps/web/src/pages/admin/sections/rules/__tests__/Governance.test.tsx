import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import { RulesGovernance } from '../Governance';
import { renderWithProviders } from '@/__tests__/testUtils';
import type { RuleRecord } from '@/lib/admin/types';

const listRules = vi.fn();
const updateRule = vi.fn();
const bulkSyncRules = vi.fn();

vi.mock('@/lib/admin/services', () => ({
  getAdminService: () => ({
    listRules,
    updateRule,
    bulkSyncRules,
  }),
}));

const baseRule: RuleRecord = {
  ruleId: 'RULE-1',
  ruleVersion: '1.0.0',
  article: '14(a)',
  version: 'ucp600',
  domain: 'icc',
  jurisdiction: 'global',
  documentType: 'lc',
  ruleType: 'deterministic',
  severity: 'warning',
  deterministic: true,
  requiresLlm: false,
  title: 'Consistency check',
  reference: 'UCP600',
  description: 'Example rule',
  conditions: [],
  expectedOutcome: { valid: [], invalid: [] },
  tags: [],
  metadata: null,
  checksum: 'abc',
  rulesetId: 'ruleset-1',
  rulesetVersion: '1.0.0',
  isActive: true,
  archivedAt: null,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

const renderComponent = () => render(renderWithProviders(<RulesGovernance />, '/admin/rules'));

describe('RulesGovernance', () => {
  beforeEach(() => {
    listRules.mockResolvedValue({
      items: [baseRule],
      total: 1,
      page: 1,
      pageSize: 25,
    });
    updateRule.mockResolvedValue(baseRule);
    bulkSyncRules.mockResolvedValue({ items: [] });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders fetched rules', async () => {
    renderComponent();
    expect(await screen.findByText(/consistency check/i)).toBeInTheDocument();
    expect(listRules).toHaveBeenCalledTimes(1);
  });

  it('toggles rule active state via dialog', async () => {
    const user = userEvent.setup();
    updateRule.mockResolvedValue({ ...baseRule, isActive: false });

    renderComponent();
    await user.click(await screen.findByText(/consistency check/i));
    const toggle = await screen.findByRole('switch');
    await user.click(toggle);

    await waitFor(() => {
      expect(updateRule).toHaveBeenCalledWith('RULE-1', { isActive: false });
    });
  });

  it('runs bulk sync for active rulesets', async () => {
    const user = userEvent.setup();
    renderComponent();
    const button = await screen.findByRole('button', { name: /bulk sync active rules/i });
    await user.click(button);

    await waitFor(() => {
      expect(bulkSyncRules).toHaveBeenCalled();
      expect(listRules).toHaveBeenCalledTimes(2);
    });
  });
});


import { test, expect } from '@playwright/test';
import { AuthService } from '../../utils/auth-service';
import { TestDataService } from '../../utils/test-data-service';

test.describe('Billing Dashboard - Core Flows', () => {
  let authService: AuthService;
  let testDataService: TestDataService;

  test.beforeEach(async () => {
    authService = new AuthService();
    testDataService = new TestDataService();
  });

  test.describe('Quota Monitoring', () => {
    test('should display quota meter for company admin', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');

      await page.goto('/dashboard/billing');

      // Verify quota meter is visible
      await expect(page.locator('[data-testid="quota-meter"]')).toBeVisible();

      // Check quota values are displayed
      await expect(page.locator('[data-testid="quota-used"]')).toBeVisible();
      await expect(page.locator('[data-testid="quota-limit"]')).toBeVisible();

      // Verify percentage calculation
      const usedText = await page.locator('[data-testid="quota-used"]').textContent();
      const limitText = await page.locator('[data-testid="quota-limit"]').textContent();

      expect(usedText).toMatch(/\d+/);
      expect(limitText).toMatch(/\d+/);
    });

    test('should show quota breach warning when approaching limit', async ({ page }) => {
      // Create company with high quota usage
      const testCompany = await testDataService.createTestCompany({
        quota_limit: 100,
        quota_used: 95
      });

      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Should show warning state
      await expect(page.locator('[data-testid="quota-warning"]')).toBeVisible();
      await expect(page.locator('[data-testid="quota-warning"]')).toContainText('approaching limit');
    });

    test('should trigger quota breach alert when limit exceeded', async ({ page }) => {
      const testCompanyId = 'test-company-001';

      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Trigger quota breach
      await testDataService.triggerQuotaBreach(testCompanyId);

      // Refresh to see updated state
      await page.reload();

      // Should show breach state
      await expect(page.locator('[data-testid="quota-breach"]')).toBeVisible();
      await expect(page.locator('[data-testid="quota-breach"]')).toContainText('exceeded');
    });

    test('should display unlimited quota for enterprise plan', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Switch to enterprise company context
      await page.goto('/dashboard/billing?company=test-company-003');

      await expect(page.locator('[data-testid="quota-unlimited"]')).toBeVisible();
      await expect(page.locator('[data-testid="quota-unlimited"]')).toContainText('Unlimited');
    });
  });

  test.describe('Plan Management', () => {
    test('should display current plan details', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Verify plan card is visible
      await expect(page.locator('[data-testid="current-plan-card"]')).toBeVisible();

      // Check plan name and features
      await expect(page.locator('[data-testid="plan-name"]')).toBeVisible();
      await expect(page.locator('[data-testid="plan-features"]')).toBeVisible();
      await expect(page.locator('[data-testid="plan-price"]')).toBeVisible();
    });

    test('should show upgrade options for starter plan', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Switch to starter plan company
      await page.goto('/dashboard/billing?company=test-company-002');

      // Should show upgrade button
      await expect(page.locator('[data-testid="upgrade-plan-button"]')).toBeVisible();

      // Click upgrade button
      await page.click('[data-testid="upgrade-plan-button"]');

      // Should open upgrade modal
      await expect(page.locator('[data-testid="upgrade-modal"]')).toBeVisible();

      // Should show available plans
      await expect(page.locator('[data-testid="plan-professional"]')).toBeVisible();
      await expect(page.locator('[data-testid="plan-enterprise"]')).toBeVisible();
    });

    test('should process plan upgrade flow', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Switch to starter plan company
      await page.goto('/dashboard/billing?company=test-company-002');

      // Initiate upgrade
      await page.click('[data-testid="upgrade-plan-button"]');
      await page.click('[data-testid="select-professional-plan"]');

      // Should show payment form
      await expect(page.locator('[data-testid="payment-form"]')).toBeVisible();

      // Fill payment details (test mode)
      await page.fill('[data-testid="card-number"]', '4242424242424242');
      await page.fill('[data-testid="card-expiry"]', '12/25');
      await page.fill('[data-testid="card-cvc"]', '123');
      await page.fill('[data-testid="cardholder-name"]', 'Test User');

      // Submit payment
      await page.click('[data-testid="submit-payment"]');

      // Should show success confirmation
      await expect(page.locator('[data-testid="upgrade-success"]')).toBeVisible();

      // Should redirect to updated billing page
      await page.waitForURL('**/dashboard/billing');
      await expect(page.locator('[data-testid="plan-name"]')).toContainText('Professional');
    });

    test('should handle payment failures gracefully', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      await page.click('[data-testid="upgrade-plan-button"]');
      await page.click('[data-testid="select-professional-plan"]');

      // Use declined card number
      await page.fill('[data-testid="card-number"]', '4000000000000002');
      await page.fill('[data-testid="card-expiry"]', '12/25');
      await page.fill('[data-testid="card-cvc"]', '123');
      await page.fill('[data-testid="cardholder-name"]', 'Test User');

      await page.click('[data-testid="submit-payment"]');

      // Should show error message
      await expect(page.locator('[data-testid="payment-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="payment-error"]')).toContainText('declined');
    });
  });

  test.describe('Invoice Management', () => {
    test('should display invoice list for company admin', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing/invoices');

      // Verify invoice table is visible
      await expect(page.locator('[data-testid="invoices-table"]')).toBeVisible();

      // Check table headers
      await expect(page.locator('[data-testid="invoice-header-id"]')).toBeVisible();
      await expect(page.locator('[data-testid="invoice-header-amount"]')).toBeVisible();
      await expect(page.locator('[data-testid="invoice-header-status"]')).toBeVisible();
      await expect(page.locator('[data-testid="invoice-header-due-date"]')).toBeVisible();

      // Should show at least one invoice
      await expect(page.locator('[data-testid^="invoice-row-"]')).toHaveCount({ gte: 1 });
    });

    test('should filter invoices by status', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing/invoices');

      // Apply PAID filter
      await page.selectOption('[data-testid="status-filter"]', 'PAID');
      await page.click('[data-testid="apply-filters"]');

      // Should only show paid invoices
      const invoiceRows = page.locator('[data-testid^="invoice-row-"]');
      const count = await invoiceRows.count();

      for (let i = 0; i < count; i++) {
        const statusCell = invoiceRows.nth(i).locator('[data-testid$="-status"]');
        await expect(statusCell).toContainText('PAID');
      }
    });

    test('should download invoice PDF', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing/invoices');

      // Wait for download
      const downloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="download-invoice-test-invoice-001"]');
      const download = await downloadPromise;

      // Verify download
      expect(download.suggestedFilename()).toMatch(/invoice.*\.pdf$/);
    });

    test('should handle overdue invoice notifications', async ({ page }) => {
      // Create overdue invoice
      await testDataService.createOverdueInvoice('test-company-001');

      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Should show overdue warning
      await expect(page.locator('[data-testid="overdue-invoice-alert"]')).toBeVisible();
      await expect(page.locator('[data-testid="overdue-invoice-alert"]')).toContainText('overdue');

      // Click to view overdue invoices
      await page.click('[data-testid="view-overdue-invoices"]');

      // Should navigate to invoices page with overdue filter
      await expect(page).toHaveURL(/.*\/invoices.*status=OVERDUE/);
    });

    test('should process invoice payment', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing/invoices');

      // Find pending invoice and pay
      await page.click('[data-testid="pay-invoice-test-invoice-002"]');

      // Should open payment modal
      await expect(page.locator('[data-testid="payment-modal"]')).toBeVisible();

      // Fill payment details
      await page.fill('[data-testid="card-number"]', '4242424242424242');
      await page.fill('[data-testid="card-expiry"]', '12/25');
      await page.fill('[data-testid="card-cvc"]', '123');

      await page.click('[data-testid="submit-payment"]');

      // Should show success and update status
      await expect(page.locator('[data-testid="payment-success"]')).toBeVisible();
      await expect(page.locator('[data-testid="invoice-status-test-invoice-002"]')).toContainText('PAID');
    });
  });

  test.describe('Usage Analytics', () => {
    test('should display usage summary cards', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Verify usage summary cards
      await expect(page.locator('[data-testid="usage-summary"]')).toBeVisible();
      await expect(page.locator('[data-testid="current-month-usage"]')).toBeVisible();
      await expect(page.locator('[data-testid="previous-month-usage"]')).toBeVisible();
      await expect(page.locator('[data-testid="average-daily-usage"]')).toBeVisible();
    });

    test('should show usage trends chart', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing/usage');

      // Verify charts are rendered
      await expect(page.locator('[data-testid="usage-trends-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="cost-breakdown-chart"]')).toBeVisible();

      // Test date range filter
      await page.selectOption('[data-testid="date-range-filter"]', '7d');

      // Should update chart data
      await expect(page.locator('[data-testid="chart-loading"]')).toBeVisible();
      await expect(page.locator('[data-testid="chart-loading"]')).not.toBeVisible();
    });

    test('should export usage data', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing/usage');

      // Test CSV export
      const downloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="export-usage-csv"]');
      const download = await downloadPromise;

      expect(download.suggestedFilename()).toMatch(/usage.*\.csv$/);
    });
  });

  test.describe('Role-Based Access Control', () => {
    test('should restrict billing access for regular users', async ({ page }) => {
      await authService.authenticateAs(page, 'exporter');

      // Should not be able to access billing dashboard
      const response = await page.goto('/dashboard/billing');
      expect(response?.status()).toBe(403);
    });

    test('should allow company admin full billing access', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Should see all billing sections
      await expect(page.locator('[data-testid="quota-meter"]')).toBeVisible();
      await expect(page.locator('[data-testid="current-plan-card"]')).toBeVisible();
      await expect(page.locator('[data-testid="usage-summary"]')).toBeVisible();
      await expect(page.locator('[data-testid="recent-invoices"]')).toBeVisible();
    });

    test('should verify user permissions for billing actions', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Verify permissions are set correctly
      await authService.verifyPermissions(page, ['view_billing', 'upgrade_plan']);
    });
  });

  test.describe('Error Handling & Edge Cases', () => {
    test('should handle API errors gracefully', async ({ page }) => {
      // Mock API failure
      await page.route('**/api/billing/usage', route => route.abort());

      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Should show error state
      await expect(page.locator('[data-testid="billing-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
    });

    test('should handle slow loading states', async ({ page }) => {
      // Simulate slow API
      await page.route('**/api/billing/usage', route =>
        setTimeout(() => route.continue(), 2000)
      );

      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      // Should show loading state
      await expect(page.locator('[data-testid="billing-loading"]')).toBeVisible();

      // Should eventually load content
      await expect(page.locator('[data-testid="billing-loading"]')).not.toBeVisible({ timeout: 5000 });
      await expect(page.locator('[data-testid="quota-meter"]')).toBeVisible();
    });

    test('should validate form inputs', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/billing');

      await page.click('[data-testid="upgrade-plan-button"]');
      await page.click('[data-testid="select-professional-plan"]');

      // Submit without filling required fields
      await page.click('[data-testid="submit-payment"]');

      // Should show validation errors
      await expect(page.locator('[data-testid="card-number-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="card-expiry-error"]')).toBeVisible();
    });
  });
});
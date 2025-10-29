import { test, expect } from '@playwright/test';
import { AuthService } from '../../utils/auth-service';
import { TestDataService } from '../../utils/test-data-service';

test.describe('Bank Compliance View', () => {
  let authService: AuthService;
  let testDataService: TestDataService;

  test.beforeEach(async () => {
    authService = new AuthService();
    testDataService = new TestDataService();
  });

  test.describe('Access Control', () => {
    test('should allow bank users to access compliance view', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      await expect(page.locator('[data-testid="compliance-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="sme-metrics-overview"]')).toBeVisible();
    });

    test('should allow admin users to access compliance view', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/compliance');

      await expect(page.locator('[data-testid="compliance-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="sme-metrics-overview"]')).toBeVisible();
    });

    test('should restrict access for company users', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');

      const response = await page.goto('/dashboard/compliance');
      expect(response?.status()).toBe(403);
    });

    test('should restrict access for regular users', async ({ page }) => {
      await authService.authenticateAs(page, 'exporter');

      const response = await page.goto('/dashboard/compliance');
      expect(response?.status()).toBe(403);
    });
  });

  test.describe('SME Metrics Overview', () => {
    test('should display key SME metrics', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      // Verify key metrics are displayed
      await expect(page.locator('[data-testid="total-sme-companies"]')).toBeVisible();
      await expect(page.locator('[data-testid="active-sme-companies"]')).toBeVisible();
      await expect(page.locator('[data-testid="total-monthly-volume"]')).toBeVisible();
      await expect(page.locator('[data-testid="compliance-score"]')).toBeVisible();

      // Check that metrics show numeric values
      const totalCompanies = await page.locator('[data-testid="total-sme-companies"] .metric-value').textContent();
      const activeCompanies = await page.locator('[data-testid="active-sme-companies"] .metric-value').textContent();

      expect(totalCompanies).toMatch(/\d+/);
      expect(activeCompanies).toMatch(/\d+/);
    });

    test('should show regional breakdown', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      // Switch to regional view
      await page.click('[data-testid="view-regional"]');

      // Verify regional metrics
      await expect(page.locator('[data-testid="regional-breakdown"]')).toBeVisible();
      await expect(page.locator('[data-testid="region-apac"]')).toBeVisible();
      await expect(page.locator('[data-testid="region-emea"]')).toBeVisible();
      await expect(page.locator('[data-testid="region-americas"]')).toBeVisible();
    });

    test('should display compliance trends chart', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      // Verify compliance trends chart
      await expect(page.locator('[data-testid="compliance-trends-chart"]')).toBeVisible();

      // Test date range filters
      await page.selectOption('[data-testid="compliance-date-range"]', '30d');
      await expect(page.locator('[data-testid="chart-loading"]')).toBeVisible();
      await expect(page.locator('[data-testid="chart-loading"]')).not.toBeVisible();

      // Verify chart updated
      await expect(page.locator('[data-testid="compliance-trends-chart"]')).toBeVisible();
    });
  });

  test.describe('Revenue Analytics', () => {
    test('should display revenue metrics for bank users', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      // Switch to revenue view
      await page.click('[data-testid="view-revenue"]');

      // Verify revenue metrics
      await expect(page.locator('[data-testid="total-revenue"]')).toBeVisible();
      await expect(page.locator('[data-testid="monthly-growth"]')).toBeVisible();
      await expect(page.locator('[data-testid="revenue-per-sme"]')).toBeVisible();
      await expect(page.locator('[data-testid="top-performing-smes"]')).toBeVisible();

      // Check revenue chart
      await expect(page.locator('[data-testid="revenue-trends-chart"]')).toBeVisible();
    });

    test('should show revenue breakdown by service type', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      await page.click('[data-testid="view-revenue"]');

      // Verify service breakdown
      await expect(page.locator('[data-testid="service-breakdown-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="lc-validation-revenue"]')).toBeVisible();
      await expect(page.locator('[data-testid="compliance-checks-revenue"]')).toBeVisible();
      await expect(page.locator('[data-testid="document-verification-revenue"]')).toBeVisible();
    });

    test('should filter revenue by time period', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      await page.click('[data-testid="view-revenue"]');

      // Test quarterly filter
      await page.selectOption('[data-testid="revenue-period-filter"]', 'quarterly');

      // Should update charts and metrics
      await expect(page.locator('[data-testid="chart-loading"]')).toBeVisible();
      await expect(page.locator('[data-testid="chart-loading"]')).not.toBeVisible();

      // Verify updated data
      await expect(page.locator('[data-testid="revenue-trends-chart"]')).toBeVisible();
    });
  });

  test.describe('Company Directory', () => {
    test('should list SME companies with filtering', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      // Switch to companies view
      await page.click('[data-testid="view-companies"]');

      // Verify companies table
      await expect(page.locator('[data-testid="companies-table"]')).toBeVisible();
      await expect(page.locator('[data-testid="company-header-name"]')).toBeVisible();
      await expect(page.locator('[data-testid="company-header-plan"]')).toBeVisible();
      await expect(page.locator('[data-testid="company-header-status"]')).toBeVisible();
      await expect(page.locator('[data-testid="company-header-revenue"]')).toBeVisible();

      // Should show test companies
      await expect(page.locator('[data-testid^="company-row-"]')).toHaveCount({ gte: 1 });
    });

    test('should filter companies by plan type', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      await page.click('[data-testid="view-companies"]');

      // Apply plan filter
      await page.selectOption('[data-testid="plan-filter"]', 'PROFESSIONAL');
      await page.click('[data-testid="apply-company-filters"]');

      // Should only show professional plan companies
      const companyRows = page.locator('[data-testid^="company-row-"]');
      const count = await companyRows.count();

      for (let i = 0; i < count; i++) {
        const planCell = companyRows.nth(i).locator('[data-testid$="-plan"]');
        await expect(planCell).toContainText('PROFESSIONAL');
      }
    });

    test('should search companies by name', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      await page.click('[data-testid="view-companies"]');

      // Search for specific company
      await page.fill('[data-testid="company-search"]', 'Test Export');
      await page.click('[data-testid="search-companies"]');

      // Should filter results
      await expect(page.locator('[data-testid="company-row-test-company-001"]')).toBeVisible();
      await expect(page.locator('[data-testid="company-row-test-company-002"]')).not.toBeVisible();
    });

    test('should view individual company details', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      await page.click('[data-testid="view-companies"]');

      // Click on company to view details
      await page.click('[data-testid="view-company-test-company-001"]');

      // Should open company modal or navigate to details page
      await expect(page.locator('[data-testid="company-details-modal"]')).toBeVisible();

      // Verify company information
      await expect(page.locator('[data-testid="company-name"]')).toContainText('Test Export Company');
      await expect(page.locator('[data-testid="company-plan"]')).toContainText('PROFESSIONAL');
      await expect(page.locator('[data-testid="company-usage-chart"]')).toBeVisible();
    });
  });

  test.describe('Compliance Reports', () => {
    test('should generate compliance report', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance/reports');

      // Generate new report
      await page.click('[data-testid="generate-report"]');

      // Configure report parameters
      await page.selectOption('[data-testid="report-type"]', 'quarterly');
      await page.selectOption('[data-testid="report-region"]', 'all');
      await page.fill('[data-testid="report-period-start"]', '2024-01-01');
      await page.fill('[data-testid="report-period-end"]', '2024-03-31');

      // Submit report generation
      await page.click('[data-testid="submit-report-generation"]');

      // Should show generation in progress
      await expect(page.locator('[data-testid="report-generating"]')).toBeVisible();

      // Should eventually complete
      await expect(page.locator('[data-testid="report-complete"]')).toBeVisible({ timeout: 30000 });
    });

    test('should download existing reports', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance/reports');

      // Verify reports list
      await expect(page.locator('[data-testid="reports-list"]')).toBeVisible();

      // Download latest report
      const downloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="download-latest-report"]');
      const download = await downloadPromise;

      expect(download.suggestedFilename()).toMatch(/compliance.*\.pdf$/);
    });

    test('should schedule automated reports', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance/reports');

      // Open scheduling modal
      await page.click('[data-testid="schedule-reports"]');

      // Configure schedule
      await page.selectOption('[data-testid="schedule-frequency"]', 'monthly');
      await page.selectOption('[data-testid="schedule-day"]', '1');
      await page.fill('[data-testid="schedule-recipients"]', 'compliance@bank.com');

      // Save schedule
      await page.click('[data-testid="save-schedule"]');

      // Should show confirmation
      await expect(page.locator('[data-testid="schedule-saved"]')).toBeVisible();
    });
  });

  test.describe('Data Export', () => {
    test('should export SME metrics to CSV', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      // Export metrics
      const downloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="export-metrics-csv"]');
      const download = await downloadPromise;

      expect(download.suggestedFilename()).toMatch(/sme-metrics.*\.csv$/);
    });

    test('should export company data with filters', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      await page.click('[data-testid="view-companies"]');

      // Apply filters before export
      await page.selectOption('[data-testid="plan-filter"]', 'PROFESSIONAL');
      await page.selectOption('[data-testid="status-filter"]', 'active');

      // Export filtered data
      const downloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="export-companies-csv"]');
      const download = await downloadPromise;

      expect(download.suggestedFilename()).toMatch(/companies.*\.csv$/);
    });
  });

  test.describe('Real-time Updates', () => {
    test('should update metrics in real-time', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      // Get initial metric value
      const initialValue = await page.locator('[data-testid="total-monthly-volume"] .metric-value').textContent();

      // Generate new usage data
      await testDataService.createTestUsageRecord('test-company-001');

      // Wait for real-time update (assuming WebSocket or polling)
      await page.waitForTimeout(2000);

      // Verify metric updated
      const updatedValue = await page.locator('[data-testid="total-monthly-volume"] .metric-value').textContent();
      expect(updatedValue).not.toBe(initialValue);
    });

    test('should show live status indicators', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      // Verify live indicator is active
      await expect(page.locator('[data-testid="live-indicator"]')).toBeVisible();
      await expect(page.locator('[data-testid="live-indicator"]')).toHaveClass(/live-active/);

      // Should show last updated timestamp
      await expect(page.locator('[data-testid="last-updated"]')).toBeVisible();
    });
  });

  test.describe('Performance & Error Handling', () => {
    test('should handle large datasets efficiently', async ({ page }) => {
      // Generate performance test data
      await testDataService.generatePerformanceTestData(1000);

      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      // Should load within acceptable time
      await expect(page.locator('[data-testid="compliance-dashboard"]')).toBeVisible({ timeout: 10000 });

      // Verify pagination works with large datasets
      await page.click('[data-testid="view-companies"]');
      await expect(page.locator('[data-testid="pagination"]')).toBeVisible();
    });

    test('should gracefully handle API failures', async ({ page }) => {
      // Mock API failure
      await page.route('**/api/compliance/metrics', route => route.abort());

      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/compliance');

      // Should show error state
      await expect(page.locator('[data-testid="compliance-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();

      // Retry should work
      await page.unroute('**/api/compliance/metrics');
      await page.click('[data-testid="retry-button"]');

      await expect(page.locator('[data-testid="compliance-dashboard"]')).toBeVisible();
    });
  });
});
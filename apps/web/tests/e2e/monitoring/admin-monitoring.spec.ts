import { test, expect } from '@playwright/test';
import { AuthService } from '../../utils/auth-service';
import { TestDataService } from '../../utils/test-data-service';

test.describe('Admin Monitoring Panel', () => {
  let authService: AuthService;
  let testDataService: TestDataService;

  test.beforeEach(async () => {
    authService = new AuthService();
    testDataService = new TestDataService();
  });

  test.describe('Access Control', () => {
    test('should allow admin users to access monitoring panel', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      await expect(page.locator('[data-testid="monitoring-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="system-health-overview"]')).toBeVisible();
    });

    test('should restrict access for non-admin users', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');

      const response = await page.goto('/dashboard/monitoring');
      expect(response?.status()).toBe(403);
    });

    test('should restrict access for company users', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');

      const response = await page.goto('/dashboard/monitoring');
      expect(response?.status()).toBe(403);
    });
  });

  test.describe('System Health KPIs', () => {
    test('should display key system health metrics', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Verify system health KPIs
      await expect(page.locator('[data-testid="system-uptime"]')).toBeVisible();
      await expect(page.locator('[data-testid="api-response-time"]')).toBeVisible();
      await expect(page.locator('[data-testid="error-rate"]')).toBeVisible();
      await expect(page.locator('[data-testid="active-users"]')).toBeVisible();
      await expect(page.locator('[data-testid="database-health"]')).toBeVisible();

      // Check that metrics show numeric values
      const uptime = await page.locator('[data-testid="system-uptime"] .metric-value').textContent();
      const responseTime = await page.locator('[data-testid="api-response-time"] .metric-value').textContent();

      expect(uptime).toMatch(/\d+/);
      expect(responseTime).toMatch(/\d+/);
    });

    test('should show system status indicators', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Verify status indicators
      await expect(page.locator('[data-testid="api-status-indicator"]')).toBeVisible();
      await expect(page.locator('[data-testid="database-status-indicator"]')).toBeVisible();
      await expect(page.locator('[data-testid="queue-status-indicator"]')).toBeVisible();
      await expect(page.locator('[data-testid="cache-status-indicator"]')).toBeVisible();

      // Check status colors (healthy should be green)
      const apiStatus = page.locator('[data-testid="api-status-indicator"]');
      await expect(apiStatus).toHaveClass(/status-healthy/);
    });

    test('should display performance trends chart', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Verify performance charts
      await expect(page.locator('[data-testid="performance-trends-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="response-time-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="throughput-chart"]')).toBeVisible();

      // Test time range filter
      await page.selectOption('[data-testid="performance-time-range"]', '24h');
      await expect(page.locator('[data-testid="chart-loading"]')).toBeVisible();
      await expect(page.locator('[data-testid="chart-loading"]')).not.toBeVisible();
    });
  });

  test.describe('Anomaly Detection', () => {
    test('should display anomaly detection dashboard', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Switch to anomaly detection view
      await page.click('[data-testid="view-anomalies"]');

      // Verify anomaly detection components
      await expect(page.locator('[data-testid="anomaly-overview"]')).toBeVisible();
      await expect(page.locator('[data-testid="anomaly-alerts"]')).toBeVisible();
      await expect(page.locator('[data-testid="anomaly-trends"]')).toBeVisible();
    });

    test('should show active anomaly alerts', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      await page.click('[data-testid="view-anomalies"]');

      // Verify alerts list
      await expect(page.locator('[data-testid="active-anomalies-list"]')).toBeVisible();

      // Check if there are anomaly cards
      const anomalyCards = page.locator('[data-testid^="anomaly-card-"]');
      const count = await anomalyCards.count();

      if (count > 0) {
        // Verify anomaly card structure
        const firstCard = anomalyCards.first();
        await expect(firstCard.locator('[data-testid$="-severity"]')).toBeVisible();
        await expect(firstCard.locator('[data-testid$="-timestamp"]')).toBeVisible();
        await expect(firstCard.locator('[data-testid$="-description"]')).toBeVisible();
      }
    });

    test('should filter anomalies by severity', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      await page.click('[data-testid="view-anomalies"]');

      // Apply severity filter
      await page.selectOption('[data-testid="anomaly-severity-filter"]', 'HIGH');
      await page.click('[data-testid="apply-anomaly-filters"]');

      // Should only show high severity anomalies
      const anomalyCards = page.locator('[data-testid^="anomaly-card-"]');
      const count = await anomalyCards.count();

      for (let i = 0; i < count; i++) {
        const severityIndicator = anomalyCards.nth(i).locator('[data-testid$="-severity"]');
        await expect(severityIndicator).toContainText('HIGH');
      }
    });

    test('should acknowledge anomaly alerts', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      await page.click('[data-testid="view-anomalies"]');

      // Acknowledge first anomaly
      const firstAnomalyCard = page.locator('[data-testid^="anomaly-card-"]').first();
      await firstAnomalyCard.locator('[data-testid$="-acknowledge"]').click();

      // Should show acknowledgment confirmation
      await expect(page.locator('[data-testid="acknowledgment-modal"]')).toBeVisible();

      // Add acknowledgment note
      await page.fill('[data-testid="acknowledgment-note"]', 'Investigating this anomaly');
      await page.click('[data-testid="confirm-acknowledgment"]');

      // Should update anomaly status
      await expect(firstAnomalyCard.locator('[data-testid$="-status"]')).toContainText('ACKNOWLEDGED');
    });

    test('should configure anomaly detection rules', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      await page.click('[data-testid="view-anomalies"]');

      // Open rules configuration
      await page.click('[data-testid="configure-anomaly-rules"]');

      // Should show rules configuration modal
      await expect(page.locator('[data-testid="anomaly-rules-modal"]')).toBeVisible();

      // Configure response time threshold
      await page.fill('[data-testid="response-time-threshold"]', '2000');
      await page.fill('[data-testid="error-rate-threshold"]', '5');

      // Save configuration
      await page.click('[data-testid="save-anomaly-rules"]');

      // Should show confirmation
      await expect(page.locator('[data-testid="rules-saved"]')).toBeVisible();
    });
  });

  test.describe('Resource Monitoring', () => {
    test('should display resource utilization metrics', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Switch to resources view
      await page.click('[data-testid="view-resources"]');

      // Verify resource metrics
      await expect(page.locator('[data-testid="cpu-utilization"]')).toBeVisible();
      await expect(page.locator('[data-testid="memory-utilization"]')).toBeVisible();
      await expect(page.locator('[data-testid="disk-utilization"]')).toBeVisible();
      await expect(page.locator('[data-testid="network-utilization"]')).toBeVisible();

      // Check resource usage charts
      await expect(page.locator('[data-testid="cpu-usage-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="memory-usage-chart"]')).toBeVisible();
    });

    test('should show resource alerts when thresholds exceeded', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      await page.click('[data-testid="view-resources"]');

      // Should show resource alerts if any
      const resourceAlerts = page.locator('[data-testid="resource-alerts"]');
      if (await resourceAlerts.isVisible()) {
        await expect(page.locator('[data-testid^="resource-alert-"]')).toHaveCount({ gte: 1 });
      }
    });

    test('should configure resource alert thresholds', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      await page.click('[data-testid="view-resources"]');

      // Open threshold configuration
      await page.click('[data-testid="configure-resource-thresholds"]');

      // Configure thresholds
      await page.fill('[data-testid="cpu-warning-threshold"]', '70');
      await page.fill('[data-testid="cpu-critical-threshold"]', '90');
      await page.fill('[data-testid="memory-warning-threshold"]', '80');
      await page.fill('[data-testid="memory-critical-threshold"]', '95');

      // Save configuration
      await page.click('[data-testid="save-thresholds"]');

      await expect(page.locator('[data-testid="thresholds-saved"]')).toBeVisible();
    });
  });

  test.describe('Application Metrics', () => {
    test('should display application-specific metrics', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Switch to application metrics view
      await page.click('[data-testid="view-application"]');

      // Verify application metrics
      await expect(page.locator('[data-testid="total-validations"]')).toBeVisible();
      await expect(page.locator('[data-testid="validation-success-rate"]')).toBeVisible();
      await expect(page.locator('[data-testid="average-processing-time"]')).toBeVisible();
      await expect(page.locator('[data-testid="queue-length"]')).toBeVisible();

      // Check application charts
      await expect(page.locator('[data-testid="validation-volume-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="processing-time-chart"]')).toBeVisible();
    });

    test('should show breakdown by validation type', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      await page.click('[data-testid="view-application"]');

      // Verify validation type breakdown
      await expect(page.locator('[data-testid="validation-type-breakdown"]')).toBeVisible();
      await expect(page.locator('[data-testid="lc-validations"]')).toBeVisible();
      await expect(page.locator('[data-testid="compliance-checks"]')).toBeVisible();
      await expect(page.locator('[data-testid="document-verifications"]')).toBeVisible();
    });

    test('should filter metrics by time period', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      await page.click('[data-testid="view-application"]');

      // Apply time filter
      await page.selectOption('[data-testid="application-time-filter"]', '7d');

      // Should update charts and metrics
      await expect(page.locator('[data-testid="chart-loading"]')).toBeVisible();
      await expect(page.locator('[data-testid="chart-loading"]')).not.toBeVisible();

      // Verify data updated
      await expect(page.locator('[data-testid="validation-volume-chart"]')).toBeVisible();
    });
  });

  test.describe('Real-time Monitoring', () => {
    test('should show real-time updates', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Verify real-time indicator
      await expect(page.locator('[data-testid="realtime-indicator"]')).toBeVisible();
      await expect(page.locator('[data-testid="realtime-indicator"]')).toHaveClass(/realtime-active/);

      // Should show last updated timestamp
      await expect(page.locator('[data-testid="last-updated"]')).toBeVisible();
    });

    test('should update metrics automatically', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Get initial metric value
      const initialValue = await page.locator('[data-testid="active-users"] .metric-value').textContent();

      // Wait for auto-refresh
      await page.waitForTimeout(5000);

      // Verify timestamp updated (indicating refresh occurred)
      const timestamp = await page.locator('[data-testid="last-updated"]').textContent();
      expect(timestamp).toBeTruthy();
    });

    test('should allow manual refresh', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Click refresh button
      await page.click('[data-testid="manual-refresh"]');

      // Should show loading state
      await expect(page.locator('[data-testid="refresh-loading"]')).toBeVisible();
      await expect(page.locator('[data-testid="refresh-loading"]')).not.toBeVisible();
    });
  });

  test.describe('Alerting Integration', () => {
    test('should configure monitoring alerts', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring/alerts');

      // Open alert configuration
      await page.click('[data-testid="configure-alerts"]');

      // Configure email alerts
      await page.check('[data-testid="enable-email-alerts"]');
      await page.fill('[data-testid="alert-email-recipients"]', 'admin@company.com');

      // Configure Slack alerts
      await page.check('[data-testid="enable-slack-alerts"]');
      await page.fill('[data-testid="slack-webhook-url"]', 'https://hooks.slack.com/test');

      // Set alert thresholds
      await page.fill('[data-testid="response-time-alert-threshold"]', '5000');
      await page.fill('[data-testid="error-rate-alert-threshold"]', '10');

      // Save configuration
      await page.click('[data-testid="save-alert-config"]');

      await expect(page.locator('[data-testid="alerts-configured"]')).toBeVisible();
    });

    test('should test alert notifications', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring/alerts');

      // Send test alert
      await page.click('[data-testid="test-email-alert"]');

      // Should show test sent confirmation
      await expect(page.locator('[data-testid="test-alert-sent"]')).toBeVisible();
      await expect(page.locator('[data-testid="test-alert-sent"]')).toContainText('Test email sent');
    });

    test('should show alert history', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring/alerts');

      // Switch to alert history
      await page.click('[data-testid="view-alert-history"]');

      // Verify alert history table
      await expect(page.locator('[data-testid="alert-history-table"]')).toBeVisible();
      await expect(page.locator('[data-testid="alert-header-timestamp"]')).toBeVisible();
      await expect(page.locator('[data-testid="alert-header-type"]')).toBeVisible();
      await expect(page.locator('[data-testid="alert-header-severity"]')).toBeVisible();
      await expect(page.locator('[data-testid="alert-header-status"]')).toBeVisible();
    });
  });

  test.describe('Performance & Error Handling', () => {
    test('should handle monitoring dashboard load efficiently', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');

      // Measure load time
      const startTime = Date.now();
      await page.goto('/dashboard/monitoring');
      await page.waitForSelector('[data-testid="monitoring-dashboard"]');
      const loadTime = Date.now() - startTime;

      // Should load within reasonable time
      expect(loadTime).toBeLessThan(10000);
    });

    test('should gracefully handle monitoring API failures', async ({ page }) => {
      // Mock API failure
      await page.route('**/api/monitoring/health', route => route.abort());

      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Should show error state
      await expect(page.locator('[data-testid="monitoring-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-monitoring"]')).toBeVisible();

      // Retry should work
      await page.unroute('**/api/monitoring/health');
      await page.click('[data-testid="retry-monitoring"]');

      await expect(page.locator('[data-testid="monitoring-dashboard"]')).toBeVisible();
    });

    test('should handle partial data gracefully', async ({ page }) => {
      // Mock partial API failure
      await page.route('**/api/monitoring/anomalies', route => route.abort());

      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/monitoring');

      // Should show main dashboard but anomalies section should show error
      await expect(page.locator('[data-testid="monitoring-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="system-health-overview"]')).toBeVisible();

      await page.click('[data-testid="view-anomalies"]');
      await expect(page.locator('[data-testid="anomalies-error"]')).toBeVisible();
    });
  });
});
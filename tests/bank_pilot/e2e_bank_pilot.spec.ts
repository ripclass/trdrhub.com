/**
 * End-to-End Tests for Bank Pilot Dashboard
 * Tests bank officer and auditor workflows
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const BANK_PILOT_URL = 'http://localhost:3000/bank';
const DEMO_TENANT = 'demo';

// Mock user roles
const BANK_OFFICER = {
  email: 'officer@demo.bank.com',
  roles: ['bank_officer'],
  tenants: ['demo']
};

const BANK_AUDITOR = {
  email: 'auditor@demo.bank.com',
  roles: ['bank_auditor'],
  tenants: ['demo']
};

// Helper function to mock authentication
async function mockAuth(page: Page, user: any) {
  await page.addInitScript((userData) => {
    window.localStorage.setItem('auth_user', JSON.stringify(userData));
    window.localStorage.setItem('auth_token', 'mock_token_' + userData.email);
  }, user);
}

// Helper function to mock API responses
async function mockApiResponses(page: Page) {
  // Mock tenant info
  await page.route('**/api/tenant/demo', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        alias: 'demo',
        name: 'Bank Demo Tenant',
        environment: 'sandbox',
        sla_tier: 'demo',
        domain: 'demo.enterprise.trdrhub.com',
        billing_enabled: false,
        data_region: 'us-east-1'
      })
    });
  });

  // Mock SLA metrics
  await page.route('**/api/metrics/sla', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        uptime: 99.2,
        responseTime: 245,
        errorRate: 0.8,
        throughput: 156
      })
    });
  });

  // Mock onboarding status
  await page.route('**/api/bankpilot/onboarding/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          environment: 'sandbox',
          status: 'completed',
          checklist_complete: true,
          last_updated: '2024-01-15T10:30:00Z'
        },
        {
          environment: 'uat',
          status: 'pending',
          checklist_complete: false,
          last_updated: '2024-01-15T10:30:00Z'
        },
        {
          environment: 'production',
          status: 'pending',
          checklist_complete: false,
          last_updated: '2024-01-15T10:30:00Z'
        }
      ])
    });
  });

  // Mock report download endpoints
  await page.route('**/api/bankpilot/reports/**', async (route) => {
    const url = route.request().url();
    const reportType = url.split('/').pop()?.split('.')[0];

    await route.fulfill({
      status: 200,
      contentType: 'application/pdf',
      body: Buffer.from(`Mock ${reportType} report content`),
      headers: {
        'Content-Disposition': `attachment; filename="${reportType}_demo_${new Date().toISOString().split('T')[0]}.pdf"`
      }
    });
  });
}

test.describe('Bank Pilot Dashboard - Bank Officer Role', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuth(page, BANK_OFFICER);
    await mockApiResponses(page);
  });

  test('should display dashboard overview correctly', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Check page title and header
    await expect(page.locator('h1')).toContainText('Bank Pilot Dashboard');
    await expect(page.locator('text=Bank Demo Tenant')).toBeVisible();
    await expect(page.locator('text=demo.enterprise.trdrhub.com')).toBeVisible();

    // Check SLA badges
    await expect(page.locator('text=DEMO SLA')).toBeVisible();
    await expect(page.locator('text=SANDBOX')).toBeVisible();

    // Check quick stats cards
    await expect(page.locator('text=99.2%')).toBeVisible(); // Uptime
    await expect(page.locator('text=245ms')).toBeVisible(); // Response time
    await expect(page.locator('text=0.8%')).toBeVisible(); // Error rate
    await expect(page.locator('text=us-east-1')).toBeVisible(); // Data region
  });

  test('should navigate between tabs correctly', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Test tab navigation
    const tabs = ['Overview', 'Onboarding', 'Reports', 'SLA Monitor', 'Security'];

    for (const tab of tabs) {
      await page.click(`text=${tab}`);
      await expect(page.locator(`[aria-selected="true"]`)).toContainText(tab);
    }
  });

  test('should display tenant configuration in overview tab', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Should be on overview tab by default
    await expect(page.locator('text=Tenant Configuration')).toBeVisible();
    await expect(page.locator('text=demo')).toBeVisible(); // Tenant alias
    await expect(page.locator('text=DISABLED')).toBeVisible(); // Billing status
  });

  test('should show onboarding progress', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Navigate to onboarding tab
    await page.click('text=Onboarding');

    // Check environment status
    await expect(page.locator('text=Sandbox')).toBeVisible();
    await expect(page.locator('text=Uat')).toBeVisible();
    await expect(page.locator('text=Production')).toBeVisible();

    // Check status indicators
    await expect(page.locator('text=COMPLETED')).toBeVisible(); // Sandbox status
    await expect(page.locator('text=PENDING').first()).toBeVisible(); // UAT status
  });

  test('should allow report downloads', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Navigate to reports tab
    await page.click('text=Reports');

    // Test downloading discrepancies report
    const downloadPromise = page.waitForEvent('download');
    await page.click('text=Discrepancies Report');
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toContain('discrepancies');
    expect(download.suggestedFilename()).toContain('.pdf');
  });

  test('should display SLA metrics and targets', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Navigate to SLA tab
    await page.click('text=SLA Monitor');

    // Check SLA metrics
    await expect(page.locator('text=SLA Metrics')).toBeVisible();
    await expect(page.locator('text=SLA Targets')).toBeVisible();

    // Check progress bars are visible
    await expect(page.locator('[role="progressbar"]').first()).toBeVisible();

    // Check target values
    await expect(page.locator('text=99.0%')).toBeVisible(); // Uptime target
    await expect(page.locator('text=< 1000ms')).toBeVisible(); // Response time target
  });

  test('should show security and compliance status', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Navigate to security tab
    await page.click('text=Security');

    // Check security status
    await expect(page.locator('text=Security Status')).toBeVisible();
    await expect(page.locator('text=Data Residency')).toBeVisible();

    // Check security indicators
    await expect(page.locator('text=mTLS Authentication:')).toBeVisible();
    await expect(page.locator('text=IP Whitelisting:')).toBeVisible();
    await expect(page.locator('text=Data Encryption:')).toBeVisible();
  });
});

test.describe('Bank Pilot Dashboard - Bank Auditor Role', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuth(page, BANK_AUDITOR);
    await mockApiResponses(page);
  });

  test('should access all regulatory reports', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Navigate to reports tab
    await page.click('text=Reports');

    // Test all regulatory reports
    const reports = [
      'Discrepancies Report',
      'Audit Trail Report',
      'Data Residency & DR Report',
      'SLA Performance Report'
    ];

    for (const report of reports) {
      const downloadPromise = page.waitForEvent('download');
      await page.click(`text=${report}`);
      const download = await downloadPromise;
      expect(download).toBeTruthy();
    }
  });

  test('should access live dashboards', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Navigate to reports tab
    await page.click('text=Reports');

    // Test Grafana dashboard link
    await page.click('text=Live Dashboards');

    // Should open in new tab (mocked)
    // In real test, this would verify navigation to Grafana
  });

  test('should view comprehensive audit trail information', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Auditors should see all security information
    await page.click('text=Security');

    // Verify all security controls are visible
    await expect(page.locator('text=Network Isolation')).toBeVisible();
    await expect(page.locator('text=Last Backup:')).toBeVisible();
    await expect(page.locator('text=DR Test Status:')).toBeVisible();
  });
});

test.describe('Bank Pilot Dashboard - Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuth(page, BANK_OFFICER);
  });

  test('should handle API failures gracefully', async ({ page }) => {
    // Mock API failure
    await page.route('**/api/tenant/demo', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
      });
    });

    await page.goto(BANK_PILOT_URL);

    // Should show loading state or error message
    // This depends on implementation - adjust based on actual error handling
    await expect(page.locator('text=Loading')).toBeVisible();
  });

  test('should handle network timeouts', async ({ page }) => {
    // Mock slow API response
    await page.route('**/api/tenant/demo', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 5000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({})
      });
    });

    await page.goto(BANK_PILOT_URL);

    // Should show loading indicator
    await expect(page.locator('text=Loading bank pilot dashboard')).toBeVisible();
  });

  test('should handle missing tenant data', async ({ page }) => {
    // Mock empty tenant response
    await page.route('**/api/tenant/demo', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Tenant not found' })
      });
    });

    await page.goto(BANK_PILOT_URL);

    // Should handle missing tenant gracefully
    // Implementation specific - might redirect or show error
  });
});

test.describe('Bank Pilot Dashboard - Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuth(page, BANK_OFFICER);
    await mockApiResponses(page);
  });

  test('should work on mobile devices', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
    await page.goto(BANK_PILOT_URL);

    // Should display mobile-friendly layout
    await expect(page.locator('h1')).toBeVisible();

    // Stats cards should stack vertically
    const statsCards = page.locator('[role="group"]').first();
    await expect(statsCards).toBeVisible();
  });

  test('should work on tablet devices', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 }); // iPad
    await page.goto(BANK_PILOT_URL);

    // Should display tablet-friendly layout
    await expect(page.locator('text=Bank Pilot Dashboard')).toBeVisible();

    // Tabs should be accessible
    await page.click('text=Reports');
    await expect(page.locator('text=Regulatory Reports')).toBeVisible();
  });
});

test.describe('Bank Pilot Dashboard - Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuth(page, BANK_OFFICER);
    await mockApiResponses(page);
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Test tab navigation with keyboard
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Should be able to navigate to tabs
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Enter');

    // Focus should move between interactive elements
    const focusedElement = await page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });

  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Check for proper ARIA attributes
    await expect(page.locator('[role="tablist"]')).toBeVisible();
    await expect(page.locator('[role="tabpanel"]')).toBeVisible();
    await expect(page.locator('[aria-selected="true"]')).toBeVisible();
  });

  test('should support screen readers', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);

    // Check for descriptive text and labels
    await expect(page.locator('[aria-label]').first()).toBeVisible();

    // Progress bars should have accessible labels
    await page.click('text=SLA Monitor');
    await expect(page.locator('[role="progressbar"][aria-label]').first()).toBeVisible();
  });
});

test.describe('Bank Pilot Dashboard - Performance', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuth(page, BANK_OFFICER);
    await mockApiResponses(page);
  });

  test('should load within performance budget', async ({ page }) => {
    const startTime = Date.now();

    await page.goto(BANK_PILOT_URL);

    // Wait for main content to load
    await expect(page.locator('text=Bank Pilot Dashboard')).toBeVisible();

    const loadTime = Date.now() - startTime;

    // Should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('should handle concurrent report downloads', async ({ page }) => {
    await page.goto(BANK_PILOT_URL);
    await page.click('text=Reports');

    // Start multiple downloads simultaneously
    const downloadPromises = [
      page.waitForEvent('download'),
      page.waitForEvent('download'),
      page.waitForEvent('download')
    ];

    // Trigger downloads
    await page.click('text=Discrepancies Report');
    await page.click('text=Audit Trail Report');
    await page.click('text=SLA Performance Report');

    // Wait for all downloads to complete
    const downloads = await Promise.all(downloadPromises);

    expect(downloads).toHaveLength(3);
    downloads.forEach(download => {
      expect(download).toBeTruthy();
    });
  });
});
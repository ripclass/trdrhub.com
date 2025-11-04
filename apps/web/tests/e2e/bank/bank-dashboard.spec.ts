import { test, expect, Page } from '@playwright/test';

const stubHealth = (page: Page, enabled: boolean) =>
  page.route('**/health/info', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        configuration: {
          use_stubs: enabled,
        },
      }),
    });
  });

test.describe('Bank dashboard hardening', () => {
  test('restricts access for non-bank users when stub mode is disabled', async ({ page }) => {
    await stubHealth(page, false);

    await page.route('**/auth/me', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-user',
          email: 'exporter@example.com',
          full_name: 'Test User',
          role: 'exporter',
          is_active: true,
        }),
      });
    });

    await page.goto('/lcopilot/bank-dashboard');

    await expect(page.getByText('Access Restricted')).toBeVisible();
    await expect(
      page.getByText('This dashboard is only available for bank users.'),
    ).toBeVisible();
  });

  test('sanitizes queue data to prevent script execution', async ({ page }) => {
    await stubHealth(page, true);

    const now = new Date().toISOString();

    await page.route('**/auth/me', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'bank-user',
          email: 'bank@example.com',
          full_name: 'Bank User',
          role: 'bank_officer',
          is_active: true,
        }),
      });
    });

    await page.route('**/bank/jobs', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total: 1,
          count: 1,
          jobs: [
            {
              id: 'job-1',
              job_id: 'job-1',
              client_name: "<img src=x onerror=alert('xss')>",
              lc_number: '<b>LC-401</b>',
              status: 'processing',
              progress: 42,
              submitted_at: now,
            },
          ],
        }),
      });
    });

    await page.route('**/bank/results', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total: 1,
          count: 1,
          results: [
            {
              id: 'result-1',
              job_id: 'job-1',
              jobId: 'job-1',
              client_name: '<script>alert(1)</script>',
              lc_number: '<i>LC-401</i>',
              submitted_at: now,
              completed_at: now,
              status: 'compliant',
              compliance_score: 100,
              discrepancy_count: 0,
              document_count: 3,
            },
          ],
        }),
      });
    });

    let dialogTriggered = false;
    page.on('dialog', async (dialog) => {
      dialogTriggered = true;
      await dialog.dismiss().catch(() => undefined);
    });

    await page.goto('/lcopilot/bank-dashboard');

    await expect(page.getByText('Processing Queue')).toBeVisible();
    await expect(page.getByText('Unknown Client')).toBeVisible();
    await expect(page.locator('text=N/A')).toBeVisible();

    // Ensure potentially dangerous markup is rendered inert
    await expect(page.locator('img[onerror]')).toHaveCount(0);
    await expect(page.locator('script')).toHaveCount(0);

    expect(dialogTriggered).toBeFalsy();
  });
});


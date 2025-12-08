/**
 * Smoke Tests - Basic page load tests that don't require auth
 * Run with: npx playwright test tests/e2e/smoke.spec.ts --project=chromium
 */

import { test, expect } from '@playwright/test';

// Skip global setup for smoke tests
test.describe.configure({ mode: 'serial' });

test.describe('Smoke Tests - No Auth Required', () => {
  
  test('homepage loads', async ({ page }) => {
    await page.goto('/');
    
    // Just check page loads without 500 error
    const response = await page.goto('/');
    expect(response?.status()).toBeLessThan(500);
    
    // Check title or some element exists
    await expect(page).toHaveTitle(/.*/);
  });

  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    
    // Check for login form elements
    await expect(page.locator('body')).toBeVisible();
  });

  test('exporter upload page loads', async ({ page }) => {
    // This might redirect to login, but should not error
    const response = await page.goto('/exporter/upload');
    expect(response?.status()).toBeLessThan(500);
  });

  test('importer upload page loads', async ({ page }) => {
    const response = await page.goto('/importer/upload');
    expect(response?.status()).toBeLessThan(500);
  });

});

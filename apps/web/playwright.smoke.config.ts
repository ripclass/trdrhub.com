/**
 * Simplified Playwright config for smoke tests
 * Skips global setup/teardown for quick testing
 * 
 * Run with: npx playwright test --config=playwright.smoke.config.ts
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/smoke.spec.ts',
  
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  
  reporter: 'list',
  
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
    navigationTimeout: 30000,
    actionTimeout: 10000,
  },

  // NO global setup - just run tests directly

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Auto-start dev server
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 120000,
  },

  timeout: 30000,
});

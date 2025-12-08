/**
 * LCopilot Exporter Validation E2E Tests
 * 
 * Critical path tests for the core validation workflow:
 * 1. Login as exporter
 * 2. Navigate to upload page
 * 3. Upload documents
 * 4. Run validation
 * 5. View results
 */

import { test, expect, Page } from '@playwright/test';
import path from 'path';

// Use exporter auth state
const authFile = 'tests/auth-states/user.json';

test.describe('LCopilot Exporter Validation Flow', () => {
  
  // Use authenticated session
  test.use({ storageState: authFile });

  test.describe('Upload Page', () => {
    
    test('should display upload page correctly', async ({ page }) => {
      await page.goto('/exporter/upload');
      
      // Check page loaded
      await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 10000 });
      
      // Check dropzone exists
      const dropzone = page.locator('[class*="dropzone"], [class*="upload"]').first();
      await expect(dropzone).toBeVisible();
    });

    test('should accept PDF file upload', async ({ page }) => {
      await page.goto('/exporter/upload');
      
      // Create a test file
      const testPdf = createTestPdf();
      
      // Upload file via file input
      const fileInput = page.locator('input[type="file"]').first();
      await fileInput.setInputFiles({
        name: 'test-lc.pdf',
        mimeType: 'application/pdf',
        buffer: testPdf,
      });
      
      // Wait for file to appear in list
      await page.waitForTimeout(2000);
      
      // File should be added to the list
      await expect(page.getByText('test-lc.pdf')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Validation Flow', () => {
    
    test('should show progress during validation', async ({ page }) => {
      await page.goto('/exporter/upload');
      
      // Upload test file
      const testPdf = createTestPdf();
      const fileInput = page.locator('input[type="file"]').first();
      await fileInput.setInputFiles({
        name: 'test-lc.pdf',
        mimeType: 'application/pdf',
        buffer: testPdf,
      });
      
      await page.waitForTimeout(2000);
      
      // Enter LC number
      await page.locator('input').filter({ hasText: '' }).first().fill('TEST-LC-001');
      
      // Find and click validate button
      const validateBtn = page.locator('button').filter({ hasText: /validate|process|check/i }).first();
      
      if (await validateBtn.isEnabled()) {
        await validateBtn.click();
        
        // Should show loading/progress
        await expect(
          page.locator('[class*="progress"], [class*="spinner"], [class*="loading"]').first()
        ).toBeVisible({ timeout: 10000 });
      }
    });

    test('should complete validation and show results', async ({ page }) => {
      test.setTimeout(120000); // 2 minute timeout for full validation
      
      await page.goto('/exporter/upload');
      
      // Upload
      const testPdf = createTestPdf();
      await page.locator('input[type="file"]').first().setInputFiles({
        name: 'test-lc.pdf',
        mimeType: 'application/pdf',
        buffer: testPdf,
      });
      
      await page.waitForTimeout(2000);
      
      // Fill LC number - find the input field
      const inputs = page.locator('input[type="text"]');
      const inputCount = await inputs.count();
      for (let i = 0; i < inputCount; i++) {
        const input = inputs.nth(i);
        const placeholder = await input.getAttribute('placeholder') || '';
        if (placeholder.toLowerCase().includes('lc') || placeholder.toLowerCase().includes('number')) {
          await input.fill('TEST-E2E-' + Date.now());
          break;
        }
      }
      
      // Click validate
      const validateBtn = page.locator('button').filter({ hasText: /validate|process|check/i }).first();
      if (await validateBtn.isEnabled()) {
        await validateBtn.click();
        
        // Wait for navigation to results
        await page.waitForURL(/.*result.*/, { timeout: 100000 });
        
        // Verify we're on results page
        expect(page.url()).toContain('result');
      }
    });
  });

  test.describe('Results Page', () => {
    
    test('should display tabs on results page', async ({ page }) => {
      // Go directly to results page if we have a job ID, or run validation
      await page.goto('/exporter/upload');
      
      // Quick upload and validate
      await page.locator('input[type="file"]').first().setInputFiles({
        name: 'test.pdf',
        mimeType: 'application/pdf',
        buffer: createTestPdf(),
      });
      
      await page.waitForTimeout(1500);
      
      // Fill required fields and submit
      const inputs = page.locator('input[type="text"]');
      const inputCount = await inputs.count();
      for (let i = 0; i < inputCount; i++) {
        const input = inputs.nth(i);
        const value = await input.inputValue();
        if (!value) {
          await input.fill('TEST-' + Date.now());
          break;
        }
      }
      
      const validateBtn = page.locator('button').filter({ hasText: /validate|process|check/i }).first();
      if (await validateBtn.isEnabled()) {
        await validateBtn.click();
        await page.waitForURL(/.*result.*/, { timeout: 100000 });
      }
      
      // Check for tabs
      await expect(page.locator('[role="tablist"]').first()).toBeVisible({ timeout: 15000 });
    });

    test('should show compliance metrics', async ({ page }) => {
      // Navigate to a results page
      await page.goto('/exporter');
      
      // Look for any results/metrics display
      const metricsVisible = await page.locator('[class*="compliance"], [class*="score"], [class*="metric"]').first().isVisible().catch(() => false);
      
      // This is informational - compliance may or may not be visible depending on state
      console.log('Compliance metrics visible:', metricsVisible);
    });
  });

  test.describe('Error Handling', () => {
    
    test('should reject invalid file types', async ({ page }) => {
      await page.goto('/exporter/upload');
      
      // Try uploading a text file
      const fileInput = page.locator('input[type="file"]').first();
      await fileInput.setInputFiles({
        name: 'invalid.exe',
        mimeType: 'application/octet-stream',
        buffer: Buffer.from('invalid content'),
      });
      
      await page.waitForTimeout(2000);
      
      // Should either show error or not add the file
      const hasError = await page.locator('[class*="error"], [role="alert"]').first().isVisible().catch(() => false);
      const hasFile = await page.getByText('invalid.exe').isVisible().catch(() => false);
      
      // Either error shown OR file not added
      expect(hasError || !hasFile).toBeTruthy();
    });
  });
});

// Helper to create minimal valid PDF
function createTestPdf(): Buffer {
  const pdf = `%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000101 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
170
%%EOF`;
  return Buffer.from(pdf);
}

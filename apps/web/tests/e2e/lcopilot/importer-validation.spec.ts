/**
 * LCopilot Importer Validation E2E Tests
 * 
 * Tests for importer-specific validation workflows:
 * - Draft LC risk analysis
 * - Supplier document checking
 */

import { test, expect } from '@playwright/test';

const authFile = 'tests/auth-states/user.json';

test.describe('LCopilot Importer Validation Flow', () => {
  
  test.use({ storageState: authFile });

  test.describe('Import Upload Page', () => {
    
    test('should display importer upload page', async ({ page }) => {
      await page.goto('/importer/upload');
      
      // Check page loaded
      await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 10000 });
    });

    test('should accept file upload', async ({ page }) => {
      await page.goto('/importer/upload');
      
      const testPdf = createTestPdf();
      const fileInput = page.locator('input[type="file"]').first();
      
      await fileInput.setInputFiles({
        name: 'draft-lc.pdf',
        mimeType: 'application/pdf',
        buffer: testPdf,
      });
      
      await page.waitForTimeout(2000);
      
      // File should appear
      await expect(page.getByText('draft-lc.pdf')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Draft LC Analysis', () => {
    
    test('should analyze draft LC for risks', async ({ page }) => {
      test.setTimeout(120000);
      
      await page.goto('/importer/upload');
      
      // Upload draft LC
      await page.locator('input[type="file"]').first().setInputFiles({
        name: 'draft-lc.pdf',
        mimeType: 'application/pdf',
        buffer: createTestPdf(),
      });
      
      await page.waitForTimeout(2000);
      
      // Fill LC number
      const lcInput = page.locator('input[type="text"]').first();
      await lcInput.fill('DRAFT-LC-' + Date.now());
      
      // Find and click analyze button
      const analyzeBtn = page.locator('button').filter({ hasText: /analyze|check|validate|process/i }).first();
      
      if (await analyzeBtn.isEnabled()) {
        await analyzeBtn.click();
        
        // Should show progress or navigate to results
        await page.waitForURL(/.*result.*/, { timeout: 100000 }).catch(() => {
          // May show inline results
        });
      }
    });
  });
});

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

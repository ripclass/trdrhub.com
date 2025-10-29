import { chromium, FullConfig } from '@playwright/test';
import { AuthService } from './utils/auth-service';
import { TestDataService } from './utils/test-data-service';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global test setup...');

  const browser = await chromium.launch();

  try {
    // Initialize test services
    const authService = new AuthService();
    const testDataService = new TestDataService();

    // Setup test users for different roles
    await authService.setupTestUsers();

    // Setup test data
    await testDataService.setupTestData();

    // Warm up the application
    const context = await browser.newContext();
    const page = await context.newPage();

    console.log('🌐 Warming up application...');
    await page.goto(config.projects[0].use?.baseURL || 'http://localhost:5173');

    // Wait for application to be ready
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

    await context.close();

    console.log('✅ Global setup completed successfully');
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

export default globalSetup;
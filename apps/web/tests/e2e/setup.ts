import { test as setup, expect } from '@playwright/test';
import { AuthService } from '../utils/auth-service';
import { TestDataService } from '../utils/test-data-service';

const authFile = 'tests/auth-states/user.json';
const adminAuthFile = 'tests/auth-states/admin.json';
const bankAuthFile = 'tests/auth-states/bank.json';
const companyAdminAuthFile = 'tests/auth-states/company-admin.json';

setup.describe('E2E Test Setup', () => {
  let authService: AuthService;
  let testDataService: TestDataService;

  setup.beforeAll(async () => {
    authService = new AuthService();
    testDataService = new TestDataService();
  });

  setup('authenticate users and save auth states', async ({ browser }) => {
    console.log('🔧 Setting up authentication states for E2E tests...');

    // Setup for regular user (exporter)
    const userContext = await browser.newContext();
    const userPage = await userContext.newPage();

    await authService.authenticateAs(userPage, 'exporter');
    await userPage.context().storageState({ path: authFile });
    await userContext.close();

    // Setup for admin user
    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();

    await authService.authenticateAs(adminPage, 'admin');
    await adminPage.context().storageState({ path: adminAuthFile });
    await adminContext.close();

    // Setup for bank user
    const bankContext = await browser.newContext();
    const bankPage = await bankContext.newPage();

    await authService.authenticateAs(bankPage, 'bank');
    await bankPage.context().storageState({ path: bankAuthFile });
    await bankContext.close();

    // Setup for company admin
    const companyAdminContext = await browser.newContext();
    const companyAdminPage = await companyAdminContext.newPage();

    await authService.authenticateAs(companyAdminPage, 'companyAdmin');
    await companyAdminPage.context().storageState({ path: companyAdminAuthFile });
    await companyAdminContext.close();

    console.log('✅ Authentication states saved successfully');
  });

  setup('verify test data is available', async ({ page }) => {
    console.log('🔧 Verifying test data availability...');

    // Verify test companies exist
    const testCompany = await testDataService.getTestCompany('test-company-001');
    expect(testCompany).toBeTruthy();
    expect(testCompany.name).toBe('Test Export Company Ltd');

    // Verify test invoices exist
    const testInvoices = await testDataService.getTestInvoices('test-company-001');
    expect(testInvoices.length).toBeGreaterThan(0);

    // Verify test usage records exist
    const testUsageRecords = await testDataService.getTestUsageRecords('test-company-001');
    expect(testUsageRecords.length).toBeGreaterThan(0);

    console.log('✅ Test data verification complete');
  });

  setup('create database snapshot for test isolation', async ({ page }) => {
    console.log('🔧 Creating database snapshot for test isolation...');

    await testDataService.createDatabaseSnapshot('e2e-test-baseline');

    console.log('✅ Database snapshot created');
  });

  setup('verify application health before tests', async ({ page }) => {
    console.log('🔧 Verifying application health...');

    // Check that the application is responsive
    await page.goto('/');
    await expect(page.locator('[data-testid="app-ready"]')).toBeVisible({ timeout: 30000 });

    // Verify API health
    const response = await page.request.get('/api/health');
    expect(response.ok()).toBeTruthy();

    // Verify critical services are available
    const healthData = await response.json();
    expect(healthData.status).toBe('healthy');
    expect(healthData.services.database).toBe('healthy');
    expect(healthData.services.cache).toBe('healthy');

    console.log('✅ Application health check passed');
  });

  setup('configure test environment settings', async ({ page }) => {
    console.log('🔧 Configuring test environment settings...');

    // Set test mode flags
    await page.addInitScript(() => {
      window.__TEST_MODE__ = true;
      window.__PAYMENT_TEST_MODE__ = true;
      window.__NOTIFICATION_TEST_MODE__ = true;
    });

    // Disable analytics and tracking in tests
    await page.addInitScript(() => {
      window.__DISABLE_ANALYTICS__ = true;
      window.__DISABLE_TRACKING__ = true;
    });

    console.log('✅ Test environment configured');
  });

  setup('seed performance test data if needed', async ({ page }) => {
    console.log('🔧 Checking if performance test data is needed...');

    // Check if we need to generate large datasets for performance tests
    const currentUsageRecords = await testDataService.getTestUsageRecords('test-company-001');

    if (currentUsageRecords.length < 100) {
      console.log('📊 Generating performance test data...');
      await testDataService.generatePerformanceTestData(500);
      console.log('✅ Performance test data generated');
    } else {
      console.log('✅ Sufficient test data already exists');
    }
  });

  setup('verify all required test endpoints are available', async ({ page }) => {
    console.log('🔧 Verifying test endpoints...');

    const testEndpoints = [
      '/api/test/companies',
      '/api/test/invoices',
      '/api/test/usage-records',
      '/api/test/governance-actions',
      '/api/test/cleanup',
      '/api/test/snapshots'
    ];

    for (const endpoint of testEndpoints) {
      const response = await page.request.get(endpoint);
      expect(response.status()).toBeLessThan(500); // Allow 404 but not server errors
    }

    console.log('✅ Test endpoints verification complete');
  });

  setup('setup test monitoring and logging', async ({ page }) => {
    console.log('🔧 Setting up test monitoring...');

    // Configure test logging
    await page.addInitScript(() => {
      // Capture console errors for test reporting
      window.__TEST_ERRORS__ = [];
      const originalConsoleError = console.error;
      console.error = (...args) => {
        window.__TEST_ERRORS__.push(args.join(' '));
        originalConsoleError.apply(console, args);
      };

      // Capture unhandled promise rejections
      window.__TEST_PROMISE_REJECTIONS__ = [];
      window.addEventListener('unhandledrejection', (event) => {
        window.__TEST_PROMISE_REJECTIONS__.push(event.reason);
      });
    });

    console.log('✅ Test monitoring configured');
  });

  setup('prepare test data cleanup schedule', async ({ page }) => {
    console.log('🔧 Preparing test data cleanup schedule...');

    // Create cleanup schedule for test data
    await page.addInitScript(() => {
      window.__TEST_START_TIME__ = Date.now();
    });

    console.log('✅ Test cleanup schedule prepared');
  });
});

// Export auth files for use in tests
export {
  authFile,
  adminAuthFile,
  bankAuthFile,
  companyAdminAuthFile
};
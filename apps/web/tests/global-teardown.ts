import { FullConfig } from '@playwright/test';
import { TestDataService } from './utils/test-data-service';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting global test teardown...');

  try {
    const testDataService = new TestDataService();

    // Clean up test data
    await testDataService.cleanupTestData();

    console.log('✅ Global teardown completed successfully');
  } catch (error) {
    console.error('❌ Global teardown failed:', error);
    // Don't throw error to avoid masking test failures
  }
}

export default globalTeardown;
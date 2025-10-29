/**
 * Test data service for E2E tests
 * Manages test data setup, cleanup, and factories
 */

export interface TestCompany {
  id: string;
  name: string;
  plan: string;
  quota_limit: number;
  quota_used: number;
  billing_email: string;
}

export interface TestInvoice {
  id: string;
  company_id: string;
  amount: number;
  status: string;
  due_date: string;
}

export interface TestUsageRecord {
  id: string;
  company_id: string;
  action: string;
  cost: number;
  created_at: string;
}

export class TestDataService {
  private apiUrl: string;

  constructor() {
    this.apiUrl = process.env.API_URL || 'http://localhost:8000';
  }

  async setupTestData(): Promise<void> {
    console.log('🔧 Setting up test data...');

    try {
      // Setup test companies
      await this.setupTestCompanies();

      // Setup test invoices
      await this.setupTestInvoices();

      // Setup test usage records
      await this.setupTestUsageRecords();

      // Setup test governance actions
      await this.setupTestGovernanceActions();

      console.log('✅ Test data setup complete');
    } catch (error) {
      console.error('❌ Test data setup failed:', error);
      throw error;
    }
  }

  async cleanupTestData(): Promise<void> {
    console.log('🧹 Cleaning up test data...');

    try {
      await this.makeTestRequest('/test/cleanup', 'DELETE');
      console.log('✅ Test data cleanup complete');
    } catch (error) {
      console.error('❌ Test data cleanup failed:', error);
    }
  }

  private async setupTestCompanies(): Promise<void> {
    const companies: TestCompany[] = [
      {
        id: 'test-company-001',
        name: 'Test Export Company Ltd',
        plan: 'PROFESSIONAL',
        quota_limit: 500,
        quota_used: 245,
        billing_email: 'billing@test-company.com'
      },
      {
        id: 'test-company-002',
        name: 'Sample Import Corp',
        plan: 'STARTER',
        quota_limit: 100,
        quota_used: 89,
        billing_email: 'accounts@sample-import.com'
      },
      {
        id: 'test-company-003',
        name: 'Enterprise Trading LLC',
        plan: 'ENTERPRISE',
        quota_limit: null, // unlimited
        quota_used: 1250,
        billing_email: 'finance@enterprise-trading.com'
      }
    ];

    for (const company of companies) {
      await this.makeTestRequest('/test/companies', 'POST', company);
    }
  }

  private async setupTestInvoices(): Promise<void> {
    const invoices: TestInvoice[] = [
      {
        id: 'test-invoice-001',
        company_id: 'test-company-001',
        amount: 45000,
        status: 'PAID',
        due_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
      },
      {
        id: 'test-invoice-002',
        company_id: 'test-company-001',
        amount: 45000,
        status: 'PENDING',
        due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
      },
      {
        id: 'test-invoice-003',
        company_id: 'test-company-002',
        amount: 15000,
        status: 'OVERDUE',
        due_date: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString()
      }
    ];

    for (const invoice of invoices) {
      await this.makeTestRequest('/test/invoices', 'POST', invoice);
    }
  }

  private async setupTestUsageRecords(): Promise<void> {
    const usageRecords: TestUsageRecord[] = [];

    // Generate usage records for the last 30 days
    for (let i = 0; i < 30; i++) {
      const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000);
      const recordsPerDay = Math.floor(Math.random() * 10) + 1;

      for (let j = 0; j < recordsPerDay; j++) {
        usageRecords.push({
          id: `test-usage-${i}-${j}`,
          company_id: 'test-company-001',
          action: 'LC_VALIDATION',
          cost: 1200,
          created_at: new Date(date.getTime() + j * 60 * 60 * 1000).toISOString()
        });
      }
    }

    // Batch create usage records
    await this.makeTestRequest('/test/usage-records/batch', 'POST', { records: usageRecords });
  }

  private async setupTestGovernanceActions(): Promise<void> {
    const governanceActions = [
      {
        id: 'test-governance-001',
        type: 'QUOTA_OVERRIDE',
        title: 'Emergency Quota Increase for Test Company',
        description: 'Increase quota from 500 to 1000 for critical project',
        requester_id: 'test-company-admin-001',
        status: 'PENDING',
        risk_level: 'HIGH',
        requires_approval: true,
        approval_count_required: 2,
        current_approval_count: 0
      },
      {
        id: 'test-governance-002',
        type: 'COMPLIANCE_REPORT_EXPORT',
        title: 'Q4 Compliance Report Export',
        description: 'Export quarterly compliance report for regulatory filing',
        requester_id: 'test-bank-user-001',
        status: 'APPROVED',
        risk_level: 'MEDIUM',
        requires_approval: true,
        approval_count_required: 2,
        current_approval_count: 2
      }
    ];

    for (const action of governanceActions) {
      await this.makeTestRequest('/test/governance-actions', 'POST', action);
    }
  }

  // Data factories for creating test data on-demand
  async createTestCompany(overrides: Partial<TestCompany> = {}): Promise<TestCompany> {
    const company: TestCompany = {
      id: `test-company-${Date.now()}`,
      name: `Test Company ${Date.now()}`,
      plan: 'STARTER',
      quota_limit: 100,
      quota_used: 0,
      billing_email: `test${Date.now()}@company.com`,
      ...overrides
    };

    await this.makeTestRequest('/test/companies', 'POST', company);
    return company;
  }

  async createTestInvoice(companyId: string, overrides: Partial<TestInvoice> = {}): Promise<TestInvoice> {
    const invoice: TestInvoice = {
      id: `test-invoice-${Date.now()}`,
      company_id: companyId,
      amount: 15000,
      status: 'PENDING',
      due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      ...overrides
    };

    await this.makeTestRequest('/test/invoices', 'POST', invoice);
    return invoice;
  }

  async createTestUsageRecord(companyId: string, overrides: Partial<TestUsageRecord> = {}): Promise<TestUsageRecord> {
    const usageRecord: TestUsageRecord = {
      id: `test-usage-${Date.now()}`,
      company_id: companyId,
      action: 'LC_VALIDATION',
      cost: 1200,
      created_at: new Date().toISOString(),
      ...overrides
    };

    await this.makeTestRequest('/test/usage-records', 'POST', usageRecord);
    return usageRecord;
  }

  async createTestGovernanceAction(overrides: any = {}): Promise<any> {
    const action = {
      id: `test-governance-${Date.now()}`,
      type: 'QUOTA_OVERRIDE',
      title: `Test Governance Action ${Date.now()}`,
      description: 'Test governance action for E2E testing',
      requester_id: 'test-admin-001',
      status: 'PENDING',
      risk_level: 'MEDIUM',
      requires_approval: true,
      approval_count_required: 1,
      current_approval_count: 0,
      ...overrides
    };

    await this.makeTestRequest('/test/governance-actions', 'POST', action);
    return action;
  }

  // Test data queries
  async getTestCompany(companyId: string): Promise<TestCompany> {
    return await this.makeTestRequest(`/test/companies/${companyId}`, 'GET');
  }

  async getTestInvoices(companyId: string): Promise<TestInvoice[]> {
    return await this.makeTestRequest(`/test/companies/${companyId}/invoices`, 'GET');
  }

  async getTestUsageRecords(companyId: string): Promise<TestUsageRecord[]> {
    return await this.makeTestRequest(`/test/companies/${companyId}/usage-records`, 'GET');
  }

  // Test data manipulation
  async updateCompanyQuota(companyId: string, newQuota: number): Promise<void> {
    await this.makeTestRequest(`/test/companies/${companyId}/quota`, 'PUT', { quota_used: newQuota });
  }

  async triggerQuotaBreach(companyId: string): Promise<void> {
    const company = await this.getTestCompany(companyId);
    if (company.quota_limit) {
      await this.updateCompanyQuota(companyId, company.quota_limit + 1);
    }
  }

  async createOverdueInvoice(companyId: string): Promise<TestInvoice> {
    return await this.createTestInvoice(companyId, {
      status: 'OVERDUE',
      due_date: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString()
    });
  }

  // Performance test data
  async generatePerformanceTestData(recordCount: number = 1000): Promise<void> {
    console.log(`🔧 Generating ${recordCount} performance test records...`);

    const batchSize = 100;
    const batches = Math.ceil(recordCount / batchSize);

    for (let batch = 0; batch < batches; batch++) {
      const records = [];
      const currentBatchSize = Math.min(batchSize, recordCount - batch * batchSize);

      for (let i = 0; i < currentBatchSize; i++) {
        records.push({
          id: `perf-test-${batch}-${i}`,
          company_id: 'test-company-001',
          action: 'LC_VALIDATION',
          cost: 1200,
          created_at: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString()
        });
      }

      await this.makeTestRequest('/test/usage-records/batch', 'POST', { records });
      console.log(`✅ Generated batch ${batch + 1}/${batches}`);
    }
  }

  private async makeTestRequest(endpoint: string, method: string, data?: any): Promise<any> {
    const response = await fetch(`${this.apiUrl}${endpoint}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.TEST_ADMIN_TOKEN}`
      },
      body: data ? JSON.stringify(data) : undefined
    });

    if (!response.ok) {
      throw new Error(`Test API request failed: ${response.status} ${response.statusText}`);
    }

    return method !== 'DELETE' ? response.json() : null;
  }

  // Database state management for test isolation
  async createDatabaseSnapshot(name: string): Promise<void> {
    await this.makeTestRequest('/test/snapshots', 'POST', { name });
  }

  async restoreDatabaseSnapshot(name: string): Promise<void> {
    await this.makeTestRequest(`/test/snapshots/${name}/restore`, 'POST');
  }

  async cleanupDatabaseSnapshot(name: string): Promise<void> {
    await this.makeTestRequest(`/test/snapshots/${name}`, 'DELETE');
  }
}
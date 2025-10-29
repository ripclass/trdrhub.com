/**
 * Authentication service for E2E tests
 * Handles user authentication and role-based testing
 */

import { Page, BrowserContext } from '@playwright/test';

export interface TestUser {
  id: string;
  email: string;
  password: string;
  role: 'EXPORTER' | 'IMPORTER' | 'BANK' | 'ADMIN' | 'COMPANY_ADMIN';
  companyId?: string;
  permissions: string[];
}

export const TEST_USERS: Record<string, TestUser> = {
  exporter: {
    id: 'test-exporter-001',
    email: 'exporter@test.lcopilot.com',
    password: 'TestPass123!',
    role: 'EXPORTER',
    companyId: 'test-company-001',
    permissions: ['create_validation', 'view_own_validations']
  },
  importer: {
    id: 'test-importer-001',
    email: 'importer@test.lcopilot.com',
    password: 'TestPass123!',
    role: 'IMPORTER',
    companyId: 'test-company-001',
    permissions: ['create_validation', 'view_own_validations', 'view_company_validations']
  },
  companyAdmin: {
    id: 'test-company-admin-001',
    email: 'admin@test-company.com',
    password: 'TestPass123!',
    role: 'COMPANY_ADMIN',
    companyId: 'test-company-001',
    permissions: ['manage_company_users', 'view_billing', 'upgrade_plan', 'view_usage']
  },
  bank: {
    id: 'test-bank-user-001',
    email: 'bank@test-bank.com',
    password: 'TestPass123!',
    role: 'BANK',
    permissions: ['view_sme_metrics', 'export_compliance_reports', 'approve_governance_actions']
  },
  admin: {
    id: 'test-admin-001',
    email: 'admin@lcopilot.com',
    password: 'TestPass123!',
    role: 'ADMIN',
    permissions: ['*'] // All permissions
  }
};

export class AuthService {
  private apiUrl: string;

  constructor() {
    this.apiUrl = process.env.API_URL || 'http://localhost:8000';
  }

  async setupTestUsers(): Promise<void> {
    console.log('🔧 Setting up test users...');

    for (const [key, user] of Object.entries(TEST_USERS)) {
      try {
        // Create or update test user via API
        const response = await fetch(`${this.apiUrl}/test/users`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.TEST_ADMIN_TOKEN}`
          },
          body: JSON.stringify(user)
        });

        if (!response.ok) {
          console.warn(`⚠️  Failed to setup user ${key}:`, await response.text());
        } else {
          console.log(`✅ Test user ${key} setup complete`);
        }
      } catch (error) {
        console.warn(`⚠️  Error setting up user ${key}:`, error);
      }
    }
  }

  async authenticateAs(page: Page, userType: keyof typeof TEST_USERS): Promise<void> {
    const user = TEST_USERS[userType];
    if (!user) {
      throw new Error(`Unknown user type: ${userType}`);
    }

    await page.goto('/login');

    // Fill login form
    await page.fill('[data-testid="email-input"]', user.email);
    await page.fill('[data-testid="password-input"]', user.password);

    // Submit login
    await page.click('[data-testid="login-button"]');

    // Wait for authentication to complete
    await page.waitForURL('/dashboard', { timeout: 10000 });

    // Verify user is authenticated
    await page.waitForSelector(`[data-testid="user-role"][data-role="${user.role}"]`, { timeout: 5000 });
  }

  async authenticateWithToken(page: Page, userType: keyof typeof TEST_USERS): Promise<void> {
    const user = TEST_USERS[userType];
    if (!user) {
      throw new Error(`Unknown user type: ${userType}`);
    }

    // Get authentication token
    const token = await this.getAuthToken(user);

    // Set authentication token in browser context
    await page.context().addInitScript((token) => {
      localStorage.setItem('auth_token', token);
    }, token);

    // Navigate to dashboard
    await page.goto('/dashboard');

    // Verify authentication
    await page.waitForSelector(`[data-testid="user-role"][data-role="${user.role}"]`, { timeout: 5000 });
  }

  private async getAuthToken(user: TestUser): Promise<string> {
    const response = await fetch(`${this.apiUrl}/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email: user.email,
        password: user.password
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to get auth token for ${user.email}`);
    }

    const data = await response.json();
    return data.access_token;
  }

  async logout(page: Page): Promise<void> {
    // Click user menu
    await page.click('[data-testid="user-menu-button"]');

    // Click logout
    await page.click('[data-testid="logout-button"]');

    // Verify logout
    await page.waitForURL('/login', { timeout: 5000 });
  }

  async verifyRole(page: Page, expectedRole: string): Promise<void> {
    const roleElement = await page.waitForSelector('[data-testid="user-role"]', { timeout: 5000 });
    const actualRole = await roleElement.getAttribute('data-role');

    if (actualRole !== expectedRole) {
      throw new Error(`Expected role ${expectedRole}, but got ${actualRole}`);
    }
  }

  async verifyPermissions(page: Page, requiredPermissions: string[]): Promise<void> {
    for (const permission of requiredPermissions) {
      const hasPermission = await page.evaluate((perm) => {
        return window.userPermissions?.includes(perm) || window.userPermissions?.includes('*');
      }, permission);

      if (!hasPermission) {
        throw new Error(`User does not have required permission: ${permission}`);
      }
    }
  }

  // Context-based authentication for parallel tests
  async createAuthenticatedContext(browser: any, userType: keyof typeof TEST_USERS): Promise<BrowserContext> {
    const user = TEST_USERS[userType];
    const token = await this.getAuthToken(user);

    const context = await browser.newContext({
      storageState: {
        cookies: [],
        origins: [
          {
            origin: process.env.BASE_URL || 'http://localhost:5173',
            localStorage: [
              {
                name: 'auth_token',
                value: token
              },
              {
                name: 'user_role',
                value: user.role
              },
              {
                name: 'user_id',
                value: user.id
              }
            ]
          }
        ]
      }
    });

    return context;
  }

  // Session management for test isolation
  async saveAuthState(page: Page, filename: string): Promise<void> {
    await page.context().storageState({ path: `tests/auth-states/${filename}` });
  }

  async loadAuthState(context: BrowserContext, filename: string): Promise<void> {
    // This would be used with pre-saved auth states
    // Implementation depends on specific test requirements
  }

  // Multi-factor authentication simulation
  async handleMFA(page: Page, code: string = '123456'): Promise<void> {
    // Wait for MFA prompt
    await page.waitForSelector('[data-testid="mfa-code-input"]', { timeout: 5000 });

    // Enter MFA code
    await page.fill('[data-testid="mfa-code-input"]', code);

    // Submit MFA
    await page.click('[data-testid="mfa-submit-button"]');

    // Wait for MFA completion
    await page.waitForURL('/dashboard', { timeout: 10000 });
  }

  // Session timeout testing
  async simulateSessionTimeout(page: Page): Promise<void> {
    // Clear auth token to simulate timeout
    await page.evaluate(() => {
      localStorage.removeItem('auth_token');
    });

    // Navigate to protected route
    await page.goto('/dashboard/billing');

    // Should redirect to login
    await page.waitForURL('/login', { timeout: 5000 });
  }

  // Role switching for testing
  async switchRole(page: Page, newRole: string): Promise<void> {
    // This would be used for testing role delegation
    await page.evaluate((role) => {
      localStorage.setItem('delegated_role', role);
    }, newRole);

    // Refresh page to apply new role
    await page.reload();

    // Verify role change
    await this.verifyRole(page, newRole);
  }
}
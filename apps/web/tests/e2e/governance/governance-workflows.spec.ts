import { test, expect } from '@playwright/test';
import { AuthService } from '../../utils/auth-service';
import { TestDataService } from '../../utils/test-data-service';

test.describe('Governance Workflows - 4-Eyes Principle', () => {
  let authService: AuthService;
  let testDataService: TestDataService;

  test.beforeEach(async () => {
    authService = new AuthService();
    testDataService = new TestDataService();
  });

  test.describe('Access Control & Permissions', () => {
    test('should allow admins to access governance panel', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      await expect(page.locator('[data-testid="governance-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="governance-actions-list"]')).toBeVisible();
    });

    test('should allow bank users to view governance actions', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/governance');

      await expect(page.locator('[data-testid="governance-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="governance-actions-list"]')).toBeVisible();
    });

    test('should restrict governance access for company users', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');

      const response = await page.goto('/dashboard/governance');
      expect(response?.status()).toBe(403);
    });
  });

  test.describe('Governance Action Creation', () => {
    test('should create quota override request', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      // Create new governance action
      await page.click('[data-testid="create-governance-action"]');

      // Select action type
      await page.selectOption('[data-testid="action-type"]', 'QUOTA_OVERRIDE');

      // Fill action details
      await page.fill('[data-testid="action-title"]', 'Emergency Quota Increase for Critical Project');
      await page.fill('[data-testid="action-description"]', 'Customer needs immediate quota increase for urgent compliance validation');
      await page.selectOption('[data-testid="target-company"]', 'test-company-001');
      await page.fill('[data-testid="new-quota-limit"]', '1000');

      // Set risk level
      await page.selectOption('[data-testid="risk-level"]', 'HIGH');

      // Submit action
      await page.click('[data-testid="submit-governance-action"]');

      // Should show success confirmation
      await expect(page.locator('[data-testid="action-created"]')).toBeVisible();

      // Should appear in actions list
      await expect(page.locator('[data-testid^="action-card-"][data-status="PENDING"]')).toHaveCount({ gte: 1 });
    });

    test('should create compliance report export request', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/governance');

      await page.click('[data-testid="create-governance-action"]');

      // Select compliance report export
      await page.selectOption('[data-testid="action-type"]', 'COMPLIANCE_REPORT_EXPORT');

      // Fill details
      await page.fill('[data-testid="action-title"]', 'Q1 Regulatory Compliance Report');
      await page.fill('[data-testid="action-description"]', 'Quarterly compliance report for regulatory filing');
      await page.selectOption('[data-testid="report-type"]', 'QUARTERLY');
      await page.fill('[data-testid="report-period-start"]', '2024-01-01');
      await page.fill('[data-testid="report-period-end"]', '2024-03-31');

      await page.selectOption('[data-testid="risk-level"]', 'MEDIUM');

      await page.click('[data-testid="submit-governance-action"]');

      await expect(page.locator('[data-testid="action-created"]')).toBeVisible();
    });

    test('should validate required approvals based on risk level', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      await page.click('[data-testid="create-governance-action"]');

      // High risk should require multiple approvals
      await page.selectOption('[data-testid="action-type"]', 'SYSTEM_CONFIG_CHANGE');
      await page.selectOption('[data-testid="risk-level"]', 'HIGH');

      // Should show approval requirements
      await expect(page.locator('[data-testid="approval-requirements"]')).toContainText('2 approvals required');

      // Medium risk should require fewer approvals
      await page.selectOption('[data-testid="risk-level"]', 'MEDIUM');
      await expect(page.locator('[data-testid="approval-requirements"]')).toContainText('1 approval required');
    });
  });

  test.describe('Approval Workflows', () => {
    test('should approve governance action', async ({ page }) => {
      // Create test action first
      const testAction = await testDataService.createTestGovernanceAction({
        status: 'PENDING',
        requires_approval: true,
        approval_count_required: 2,
        current_approval_count: 0
      });

      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      // Find and approve the action
      const actionCard = page.locator(`[data-testid="action-card-${testAction.id}"]`);
      await actionCard.locator('[data-testid="approve-action"]').click();

      // Should open approval modal
      await expect(page.locator('[data-testid="approval-modal"]')).toBeVisible();

      // Add approval comment
      await page.fill('[data-testid="approval-comment"]', 'Approved after reviewing the business justification');

      // Submit approval
      await page.click('[data-testid="submit-approval"]');

      // Should show approval confirmation
      await expect(page.locator('[data-testid="approval-submitted"]')).toBeVisible();

      // Should update approval count
      await expect(actionCard.locator('[data-testid="approval-count"]')).toContainText('1 / 2');
    });

    test('should reject governance action with justification', async ({ page }) => {
      const testAction = await testDataService.createTestGovernanceAction({
        status: 'PENDING'
      });

      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      const actionCard = page.locator(`[data-testid="action-card-${testAction.id}"]`);
      await actionCard.locator('[data-testid="reject-action"]').click();

      // Should open rejection modal
      await expect(page.locator('[data-testid="rejection-modal"]')).toBeVisible();

      // Rejection reason is required
      await page.click('[data-testid="submit-rejection"]');
      await expect(page.locator('[data-testid="rejection-reason-error"]')).toBeVisible();

      // Add rejection reason
      await page.fill('[data-testid="rejection-reason"]', 'Insufficient business justification provided');
      await page.click('[data-testid="submit-rejection"]');

      // Should update action status
      await expect(actionCard.locator('[data-testid="action-status"]')).toContainText('REJECTED');
    });

    test('should complete action after sufficient approvals', async ({ page }) => {
      const testAction = await testDataService.createTestGovernanceAction({
        status: 'PENDING',
        approval_count_required: 1,
        current_approval_count: 0
      });

      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      const actionCard = page.locator(`[data-testid="action-card-${testAction.id}"]`);
      await actionCard.locator('[data-testid="approve-action"]').click();

      await page.fill('[data-testid="approval-comment"]', 'Final approval granted');
      await page.click('[data-testid="submit-approval"]');

      // Should automatically execute after sufficient approvals
      await expect(actionCard.locator('[data-testid="action-status"]')).toContainText('APPROVED');

      // Should show execution button for applicable actions
      if (await actionCard.locator('[data-testid="execute-action"]').isVisible()) {
        await actionCard.locator('[data-testid="execute-action"]').click();
        await expect(actionCard.locator('[data-testid="action-status"]')).toContainText('EXECUTED');
      }
    });

    test('should prevent self-approval', async ({ page }) => {
      // Create action by admin user
      await authService.authenticateAs(page, 'admin');
      const testAction = await testDataService.createTestGovernanceAction({
        requester_id: 'test-admin-001', // Same as current user
        status: 'PENDING'
      });

      await page.goto('/dashboard/governance');

      const actionCard = page.locator(`[data-testid="action-card-${testAction.id}"]`);

      // Approve button should be disabled for own actions
      await expect(actionCard.locator('[data-testid="approve-action"]')).toBeDisabled();

      // Should show self-approval prevention message
      await expect(actionCard.locator('[data-testid="self-approval-disabled"]')).toBeVisible();
    });
  });

  test.describe('Role Delegation', () => {
    test('should delegate role temporarily', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance/delegation');

      // Create role delegation
      await page.click('[data-testid="create-delegation"]');

      // Configure delegation
      await page.selectOption('[data-testid="delegatee"]', 'test-bank-user-001');
      await page.selectOption('[data-testid="delegated-role"]', 'COMPLIANCE_APPROVER');
      await page.fill('[data-testid="delegation-start"]', '2024-01-01T09:00');
      await page.fill('[data-testid="delegation-end"]', '2024-01-07T17:00');
      await page.fill('[data-testid="delegation-reason"]', 'Covering approval duties during vacation');

      // Submit delegation
      await page.click('[data-testid="submit-delegation"]');

      // Should show in active delegations
      await expect(page.locator('[data-testid="active-delegations"]')).toContainText('COMPLIANCE_APPROVER');
    });

    test('should revoke role delegation', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance/delegation');

      // Find active delegation and revoke
      const delegationCard = page.locator('[data-testid^="delegation-card-"]').first();
      await delegationCard.locator('[data-testid="revoke-delegation"]').click();

      // Confirm revocation
      await page.fill('[data-testid="revocation-reason"]', 'User returned early from vacation');
      await page.click('[data-testid="confirm-revocation"]');

      // Should update delegation status
      await expect(delegationCard.locator('[data-testid="delegation-status"]')).toContainText('REVOKED');
    });

    test('should switch to delegated role', async ({ page }) => {
      await authService.authenticateAs(page, 'bank');
      await page.goto('/dashboard/governance');

      // Should show role delegation option if available
      const delegationNotice = page.locator('[data-testid="delegation-available"]');
      if (await delegationNotice.isVisible()) {
        await page.click('[data-testid="activate-delegation"]');

        // Should switch role context
        await expect(page.locator('[data-testid="active-role"]')).toContainText('COMPLIANCE_APPROVER');

        // Should have additional permissions
        await authService.verifyPermissions(page, ['approve_governance_actions']);
      }
    });
  });

  test.describe('Audit Trail', () => {
    test('should display comprehensive audit trail', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance/audit');

      // Verify audit trail components
      await expect(page.locator('[data-testid="audit-trail"]')).toBeVisible();
      await expect(page.locator('[data-testid="audit-filters"]')).toBeVisible();
      await expect(page.locator('[data-testid="audit-entries"]')).toBeVisible();

      // Check audit entry structure
      const auditEntries = page.locator('[data-testid^="audit-entry-"]');
      if (await auditEntries.count() > 0) {
        const firstEntry = auditEntries.first();
        await expect(firstEntry.locator('[data-testid$="-timestamp"]')).toBeVisible();
        await expect(firstEntry.locator('[data-testid$="-user"]')).toBeVisible();
        await expect(firstEntry.locator('[data-testid$="-action"]')).toBeVisible();
        await expect(firstEntry.locator('[data-testid$="-details"]')).toBeVisible();
      }
    });

    test('should filter audit trail by action type', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance/audit');

      // Apply action type filter
      await page.selectOption('[data-testid="audit-action-filter"]', 'APPROVAL');
      await page.click('[data-testid="apply-audit-filters"]');

      // Should only show approval actions
      const auditEntries = page.locator('[data-testid^="audit-entry-"]');
      const count = await auditEntries.count();

      for (let i = 0; i < count; i++) {
        const actionType = auditEntries.nth(i).locator('[data-testid$="-action"]');
        await expect(actionType).toContainText('APPROVAL');
      }
    });

    test('should filter audit trail by date range', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance/audit');

      // Set date range filter
      await page.fill('[data-testid="audit-date-start"]', '2024-01-01');
      await page.fill('[data-testid="audit-date-end"]', '2024-01-31');
      await page.click('[data-testid="apply-audit-filters"]');

      // Should update audit entries
      await expect(page.locator('[data-testid="audit-entries"]')).toBeVisible();
    });

    test('should export audit trail', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance/audit');

      // Export audit data
      const downloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="export-audit-trail"]');
      const download = await downloadPromise;

      expect(download.suggestedFilename()).toMatch(/audit-trail.*\.csv$/);
    });
  });

  test.describe('Emergency Procedures', () => {
    test('should handle emergency override with additional approvals', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      await page.click('[data-testid="create-governance-action"]');

      // Mark as emergency
      await page.check('[data-testid="emergency-override"]');

      // Should require additional justification
      await expect(page.locator('[data-testid="emergency-justification"]')).toBeVisible();
      await page.fill('[data-testid="emergency-justification"]', 'Critical system outage requires immediate configuration change');

      // Should increase approval requirements
      await expect(page.locator('[data-testid="emergency-approval-notice"]')).toContainText('Emergency actions require enhanced approval');

      await page.selectOption('[data-testid="action-type"]', 'SYSTEM_CONFIG_CHANGE');
      await page.fill('[data-testid="action-title"]', 'Emergency Database Connection Increase');
      await page.fill('[data-testid="action-description"]', 'Increase database connection pool to handle traffic spike');

      await page.click('[data-testid="submit-governance-action"]');

      // Emergency actions should be flagged
      const actionCard = page.locator('[data-testid^="action-card-"][data-emergency="true"]').first();
      await expect(actionCard.locator('[data-testid="emergency-indicator"]')).toBeVisible();
    });

    test('should bypass normal approval for break-glass scenarios', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      await page.click('[data-testid="emergency-break-glass"]');

      // Should show break-glass modal
      await expect(page.locator('[data-testid="break-glass-modal"]')).toBeVisible();

      // Require strong justification
      await page.fill('[data-testid="break-glass-justification"]', 'Critical security incident requires immediate response');

      // Require additional authentication
      await page.fill('[data-testid="admin-password-confirm"]', 'TestPass123!');

      await page.click('[data-testid="confirm-break-glass"]');

      // Should enable temporary bypass mode
      await expect(page.locator('[data-testid="break-glass-active"]')).toBeVisible();
      await expect(page.locator('[data-testid="bypass-mode-warning"]')).toBeVisible();
    });

    test('should audit emergency overrides thoroughly', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance/audit');

      // Filter for emergency actions
      await page.selectOption('[data-testid="audit-action-filter"]', 'EMERGENCY_OVERRIDE');
      await page.click('[data-testid="apply-audit-filters"]');

      // Emergency entries should have enhanced detail
      const emergencyEntries = page.locator('[data-testid^="audit-entry-"][data-emergency="true"]');
      if (await emergencyEntries.count() > 0) {
        const firstEntry = emergencyEntries.first();
        await expect(firstEntry.locator('[data-testid$="-emergency-flag"]')).toBeVisible();
        await expect(firstEntry.locator('[data-testid$="-justification"]')).toBeVisible();
      }
    });
  });

  test.describe('Notifications & Alerts', () => {
    test('should send notifications for pending approvals', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      // Create action requiring approval
      const testAction = await testDataService.createTestGovernanceAction({
        status: 'PENDING',
        requires_approval: true
      });

      // Should show pending approval notification
      await expect(page.locator('[data-testid="pending-approvals-alert"]')).toBeVisible();
      await expect(page.locator('[data-testid="pending-count"]')).toContainText('1');

      // Click notification should navigate to governance dashboard
      await page.click('[data-testid="pending-approvals-alert"]');
      await expect(page).toHaveURL(/.*\/governance/);
    });

    test('should alert on governance action timeouts', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      // Find overdue actions
      const overdueActions = page.locator('[data-testid^="action-card-"][data-overdue="true"]');
      if (await overdueActions.count() > 0) {
        await expect(overdueActions.first().locator('[data-testid="overdue-indicator"]')).toBeVisible();
      }
    });

    test('should configure governance notification preferences', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance/settings');

      // Configure notification preferences
      await page.check('[data-testid="notify-pending-approvals"]');
      await page.check('[data-testid="notify-emergency-actions"]');
      await page.selectOption('[data-testid="notification-frequency"]', 'immediately');

      // Configure channels
      await page.check('[data-testid="email-notifications"]');
      await page.check('[data-testid="slack-notifications"]');

      await page.click('[data-testid="save-notification-preferences"]');

      await expect(page.locator('[data-testid="preferences-saved"]')).toBeVisible();
    });
  });

  test.describe('Performance & Error Handling', () => {
    test('should handle governance dashboard load efficiently', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');

      const startTime = Date.now();
      await page.goto('/dashboard/governance');
      await page.waitForSelector('[data-testid="governance-dashboard"]');
      const loadTime = Date.now() - startTime;

      expect(loadTime).toBeLessThan(8000);
    });

    test('should gracefully handle approval failures', async ({ page }) => {
      // Mock API failure
      await page.route('**/api/governance/actions/*/approve', route => route.abort());

      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      const actionCard = page.locator('[data-testid^="action-card-"]').first();
      await actionCard.locator('[data-testid="approve-action"]').click();

      await page.fill('[data-testid="approval-comment"]', 'Test approval');
      await page.click('[data-testid="submit-approval"]');

      // Should show error message
      await expect(page.locator('[data-testid="approval-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-approval"]')).toBeVisible();
    });

    test('should validate governance action forms', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/governance');

      await page.click('[data-testid="create-governance-action"]');

      // Submit without required fields
      await page.click('[data-testid="submit-governance-action"]');

      // Should show validation errors
      await expect(page.locator('[data-testid="action-type-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="action-title-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="action-description-error"]')).toBeVisible();
    });
  });
});
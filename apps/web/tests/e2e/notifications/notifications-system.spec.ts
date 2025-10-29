import { test, expect } from '@playwright/test';
import { AuthService } from '../../utils/auth-service';
import { TestDataService } from '../../utils/test-data-service';

test.describe('Notifications System', () => {
  let authService: AuthService;
  let testDataService: TestDataService;

  test.beforeEach(async () => {
    authService = new AuthService();
    testDataService = new TestDataService();
  });

  test.describe('Access Control', () => {
    test('should allow admin users to access notifications panel', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await expect(page.locator('[data-testid="notifications-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="notification-settings"]')).toBeVisible();
    });

    test('should allow company admins to configure their notifications', async ({ page }) => {
      await authService.authenticateAs(page, 'companyAdmin');
      await page.goto('/dashboard/notifications');

      await expect(page.locator('[data-testid="notifications-dashboard"]')).toBeVisible();
      // Should see company-specific notifications only
      await expect(page.locator('[data-testid="company-notifications-only"]')).toBeVisible();
    });

    test('should restrict advanced notification features for regular users', async ({ page }) => {
      await authService.authenticateAs(page, 'exporter');
      await page.goto('/dashboard/notifications');

      // Should see basic notification preferences only
      await expect(page.locator('[data-testid="basic-notification-preferences"]')).toBeVisible();
      await expect(page.locator('[data-testid="advanced-notification-settings"]')).not.toBeVisible();
    });
  });

  test.describe('Email Notifications', () => {
    test('should configure email notification settings', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      // Configure email settings
      await page.click('[data-testid="configure-email"]');

      // SMTP Configuration
      await page.fill('[data-testid="smtp-host"]', 'smtp.gmail.com');
      await page.fill('[data-testid="smtp-port"]', '587');
      await page.fill('[data-testid="smtp-username"]', 'notifications@lcopilot.com');
      await page.fill('[data-testid="smtp-password"]', 'app-password-123');
      await page.check('[data-testid="smtp-tls"]');

      // Email templates
      await page.selectOption('[data-testid="email-template"]', 'quota_warning');
      await page.fill('[data-testid="email-subject"]', 'Quota Warning: {{company_name}} - {{quota_percentage}}% Used');

      // Save configuration
      await page.click('[data-testid="save-email-config"]');

      await expect(page.locator('[data-testid="email-config-saved"]')).toBeVisible();
    });

    test('should test email delivery', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-email"]');

      // Send test email
      await page.fill('[data-testid="test-email-recipient"]', 'admin@test.com');
      await page.click('[data-testid="send-test-email"]');

      // Should show delivery status
      await expect(page.locator('[data-testid="test-email-sending"]')).toBeVisible();
      await expect(page.locator('[data-testid="test-email-sent"]')).toBeVisible({ timeout: 10000 });
    });

    test('should configure email notification triggers', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-email"]');
      await page.click('[data-testid="notification-triggers"]');

      // Configure quota warning trigger
      await page.check('[data-testid="trigger-quota-warning"]');
      await page.fill('[data-testid="quota-warning-threshold"]', '80');

      // Configure invoice overdue trigger
      await page.check('[data-testid="trigger-invoice-overdue"]');
      await page.fill('[data-testid="overdue-days-threshold"]', '7');

      // Configure compliance alert trigger
      await page.check('[data-testid="trigger-compliance-alert"]');

      await page.click('[data-testid="save-triggers"]');

      await expect(page.locator('[data-testid="triggers-saved"]')).toBeVisible();
    });

    test('should manage email recipient lists', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-email"]');
      await page.click('[data-testid="manage-recipients"]');

      // Add recipient group
      await page.click('[data-testid="add-recipient-group"]');
      await page.fill('[data-testid="group-name"]', 'Finance Team');
      await page.fill('[data-testid="group-emails"]', 'finance@company.com, billing@company.com');

      // Assign to notification types
      await page.check('[data-testid="assign-quota-alerts"]');
      await page.check('[data-testid="assign-invoice-alerts"]');

      await page.click('[data-testid="save-recipient-group"]');

      await expect(page.locator('[data-testid="recipient-group-saved"]')).toBeVisible();
    });
  });

  test.describe('Slack Integration', () => {
    test('should configure Slack webhook integration', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-slack"]');

      // Slack configuration
      await page.fill('[data-testid="slack-webhook-url"]', 'https://hooks.slack.com/services/T1234/B5678/abcdef123456');
      await page.fill('[data-testid="slack-channel"]', '#lcopilot-alerts');
      await page.fill('[data-testid="slack-username"]', 'LCopilot Bot');

      // Message formatting
      await page.selectOption('[data-testid="slack-message-format"]', 'detailed');
      await page.check('[data-testid="slack-include-attachments"]');

      await page.click('[data-testid="save-slack-config"]');

      await expect(page.locator('[data-testid="slack-config-saved"]')).toBeVisible();
    });

    test('should test Slack message delivery', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-slack"]');

      // Send test message
      await page.fill('[data-testid="test-slack-message"]', 'Test message from LCopilot notifications system');
      await page.click('[data-testid="send-test-slack"]');

      // Should show delivery status
      await expect(page.locator('[data-testid="slack-test-sending"]')).toBeVisible();
      await expect(page.locator('[data-testid="slack-test-sent"]')).toBeVisible({ timeout: 10000 });
    });

    test('should configure Slack notification channels', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-slack"]');
      await page.click('[data-testid="slack-channels"]');

      // Configure different channels for different alert types
      await page.fill('[data-testid="critical-alerts-channel"]', '#critical-alerts');
      await page.fill('[data-testid="billing-alerts-channel"]', '#billing-notifications');
      await page.fill('[data-testid="compliance-alerts-channel"]', '#compliance-team');

      await page.click('[data-testid="save-slack-channels"]');

      await expect(page.locator('[data-testid="slack-channels-saved"]')).toBeVisible();
    });

    test('should handle Slack webhook failures gracefully', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-slack"]');

      // Use invalid webhook URL
      await page.fill('[data-testid="slack-webhook-url"]', 'https://invalid-webhook-url.com');
      await page.click('[data-testid="send-test-slack"]');

      // Should show error handling
      await expect(page.locator('[data-testid="slack-delivery-failed"]')).toBeVisible();
      await expect(page.locator('[data-testid="slack-error-details"]')).toBeVisible();
    });
  });

  test.describe('SMS Notifications', () => {
    test('should configure SMS provider settings', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-sms"]');

      // SMS provider configuration (Twilio)
      await page.selectOption('[data-testid="sms-provider"]', 'twilio');
      await page.fill('[data-testid="twilio-account-sid"]', 'YOUR_TWILIO_ACCOUNT_SID');
      await page.fill('[data-testid="twilio-auth-token"]', 'test-auth-token-123');
      await page.fill('[data-testid="twilio-from-number"]', '+1234567890');

      // SMS limits and throttling
      await page.fill('[data-testid="sms-rate-limit"]', '10');
      await page.selectOption('[data-testid="sms-rate-period"]', 'hour');

      await page.click('[data-testid="save-sms-config"]');

      await expect(page.locator('[data-testid="sms-config-saved"]')).toBeVisible();
    });

    test('should manage SMS recipient lists', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-sms"]');
      await page.click('[data-testid="manage-sms-recipients"]');

      // Add emergency contact group
      await page.click('[data-testid="add-sms-group"]');
      await page.fill('[data-testid="sms-group-name"]', 'Emergency Contacts');
      await page.fill('[data-testid="sms-group-numbers"]', '+1234567890, +1987654321');

      // Configure for critical alerts only
      await page.check('[data-testid="critical-alerts-only"]');

      await page.click('[data-testid="save-sms-group"]');

      await expect(page.locator('[data-testid="sms-group-saved"]')).toBeVisible();
    });

    test('should test SMS delivery', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-sms"]');

      // Send test SMS
      await page.fill('[data-testid="test-sms-number"]', '+1234567890');
      await page.fill('[data-testid="test-sms-message"]', 'Test SMS from LCopilot');
      await page.click('[data-testid="send-test-sms"]');

      // Should show delivery status
      await expect(page.locator('[data-testid="sms-test-sending"]')).toBeVisible();
      await expect(page.locator('[data-testid="sms-test-sent"]')).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Webhook Notifications', () => {
    test('should configure webhook endpoints', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-webhooks"]');

      // Add webhook endpoint
      await page.click('[data-testid="add-webhook"]');
      await page.fill('[data-testid="webhook-name"]', 'Company Integration');
      await page.fill('[data-testid="webhook-url"]', 'https://api.company.com/lcopilot/webhooks');
      await page.selectOption('[data-testid="webhook-method"]', 'POST');

      // Authentication
      await page.selectOption('[data-testid="webhook-auth-type"]', 'bearer');
      await page.fill('[data-testid="webhook-auth-token"]', 'bearer-token-123');

      // Custom headers
      await page.click('[data-testid="add-custom-header"]');
      await page.fill('[data-testid="header-name-0"]', 'X-Source');
      await page.fill('[data-testid="header-value-0"]', 'LCopilot');

      await page.click('[data-testid="save-webhook"]');

      await expect(page.locator('[data-testid="webhook-saved"]')).toBeVisible();
    });

    test('should configure webhook payload templates', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-webhooks"]');

      const webhookCard = page.locator('[data-testid^="webhook-card-"]').first();
      await webhookCard.locator('[data-testid="configure-payload"]').click();

      // Configure payload template
      await page.selectOption('[data-testid="payload-format"]', 'json');
      await page.fill('[data-testid="payload-template"]', JSON.stringify({
        event: '{{event_type}}',
        timestamp: '{{timestamp}}',
        data: {
          company_id: '{{company_id}}',
          message: '{{message}}',
          severity: '{{severity}}'
        }
      }, null, 2));

      await page.click('[data-testid="save-payload-template"]');

      await expect(page.locator('[data-testid="payload-template-saved"]')).toBeVisible();
    });

    test('should test webhook delivery', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-webhooks"]');

      const webhookCard = page.locator('[data-testid^="webhook-card-"]').first();
      await webhookCard.locator('[data-testid="test-webhook"]').click();

      // Configure test payload
      await page.fill('[data-testid="test-payload"]', JSON.stringify({
        event: 'test',
        message: 'Test webhook from LCopilot'
      }));

      await page.click('[data-testid="send-test-webhook"]');

      // Should show delivery status
      await expect(page.locator('[data-testid="webhook-test-sending"]')).toBeVisible();
      await expect(page.locator('[data-testid="webhook-test-sent"]')).toBeVisible({ timeout: 10000 });
    });

    test('should handle webhook delivery failures with retry logic', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-webhooks"]');

      // Configure webhook with retry settings
      const webhookCard = page.locator('[data-testid^="webhook-card-"]').first();
      await webhookCard.locator('[data-testid="configure-retry"]').click();

      await page.fill('[data-testid="max-retries"]', '3');
      await page.fill('[data-testid="retry-delay"]', '5');
      await page.selectOption('[data-testid="retry-strategy"]', 'exponential');

      await page.click('[data-testid="save-retry-config"]');

      await expect(page.locator('[data-testid="retry-config-saved"]')).toBeVisible();
    });
  });

  test.describe('Notification Templates', () => {
    test('should create custom notification templates', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications/templates');

      // Create new template
      await page.click('[data-testid="create-template"]');

      await page.fill('[data-testid="template-name"]', 'Custom Quota Alert');
      await page.selectOption('[data-testid="template-type"]', 'quota_warning');
      await page.selectOption('[data-testid="template-channel"]', 'email');

      // Template content
      await page.fill('[data-testid="template-subject"]', 'Quota Alert: {{company_name}} - {{quota_percentage}}% Used');
      await page.fill('[data-testid="template-body"]', `
Dear {{contact_name}},

Your company {{company_name}} has used {{quota_percentage}}% of its allocated quota.

Current Usage: {{quota_used}} / {{quota_limit}}
Remaining: {{quota_remaining}}

Please consider upgrading your plan to avoid service interruptions.

Best regards,
LCopilot Team
      `);

      await page.click('[data-testid="save-template"]');

      await expect(page.locator('[data-testid="template-saved"]')).toBeVisible();
    });

    test('should preview notification templates', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications/templates');

      const templateCard = page.locator('[data-testid^="template-card-"]').first();
      await templateCard.locator('[data-testid="preview-template"]').click();

      // Should show preview modal
      await expect(page.locator('[data-testid="template-preview-modal"]')).toBeVisible();

      // Fill sample data for preview
      await page.fill('[data-testid="preview-company-name"]', 'Test Company');
      await page.fill('[data-testid="preview-quota-percentage"]', '85');
      await page.fill('[data-testid="preview-contact-name"]', 'John Doe');

      await page.click('[data-testid="generate-preview"]');

      // Should show rendered template
      await expect(page.locator('[data-testid="rendered-template"]')).toBeVisible();
      await expect(page.locator('[data-testid="rendered-template"]')).toContainText('Test Company');
      await expect(page.locator('[data-testid="rendered-template"]')).toContainText('85%');
    });

    test('should manage template versions', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications/templates');

      const templateCard = page.locator('[data-testid^="template-card-"]').first();
      await templateCard.locator('[data-testid="edit-template"]').click();

      // Make changes to create new version
      await page.fill('[data-testid="template-body"]', 'Updated template content with new messaging');

      // Save as new version
      await page.check('[data-testid="create-new-version"]');
      await page.fill('[data-testid="version-notes"]', 'Updated messaging for better clarity');
      await page.click('[data-testid="save-template"]');

      // Should show version history
      await page.click('[data-testid="view-versions"]');
      await expect(page.locator('[data-testid="version-history"]')).toBeVisible();
      await expect(page.locator('[data-testid^="version-"]')).toHaveCount({ gte: 2 });
    });
  });

  test.describe('Delivery Tracking & Analytics', () => {
    test('should display notification delivery statistics', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications/analytics');

      // Verify delivery stats
      await expect(page.locator('[data-testid="delivery-stats"]')).toBeVisible();
      await expect(page.locator('[data-testid="total-sent"]')).toBeVisible();
      await expect(page.locator('[data-testid="delivery-rate"]')).toBeVisible();
      await expect(page.locator('[data-testid="bounce-rate"]')).toBeVisible();
      await expect(page.locator('[data-testid="failure-rate"]')).toBeVisible();

      // Delivery trends chart
      await expect(page.locator('[data-testid="delivery-trends-chart"]')).toBeVisible();
    });

    test('should show delivery status breakdown by channel', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications/analytics');

      // Channel breakdown
      await expect(page.locator('[data-testid="channel-breakdown"]')).toBeVisible();
      await expect(page.locator('[data-testid="email-delivery-stats"]')).toBeVisible();
      await expect(page.locator('[data-testid="slack-delivery-stats"]')).toBeVisible();
      await expect(page.locator('[data-testid="sms-delivery-stats"]')).toBeVisible();
      await expect(page.locator('[data-testid="webhook-delivery-stats"]')).toBeVisible();
    });

    test('should filter analytics by date range', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications/analytics');

      // Apply date filter
      await page.selectOption('[data-testid="analytics-date-range"]', '30d');

      // Should update charts and stats
      await expect(page.locator('[data-testid="analytics-loading"]')).toBeVisible();
      await expect(page.locator('[data-testid="analytics-loading"]')).not.toBeVisible();

      // Verify updated data
      await expect(page.locator('[data-testid="delivery-trends-chart"]')).toBeVisible();
    });

    test('should export delivery reports', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications/analytics');

      // Export delivery report
      const downloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="export-delivery-report"]');
      const download = await downloadPromise;

      expect(download.suggestedFilename()).toMatch(/notification-delivery.*\.csv$/);
    });
  });

  test.describe('Real-time Notifications', () => {
    test('should display real-time notification queue', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications/queue');

      // Verify queue display
      await expect(page.locator('[data-testid="notification-queue"]')).toBeVisible();
      await expect(page.locator('[data-testid="queue-stats"]')).toBeVisible();
      await expect(page.locator('[data-testid="pending-notifications"]')).toBeVisible();

      // Real-time updates
      await expect(page.locator('[data-testid="realtime-indicator"]')).toBeVisible();
    });

    test('should handle notification queue management', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications/queue');

      // Pause queue processing
      await page.click('[data-testid="pause-queue"]');
      await expect(page.locator('[data-testid="queue-paused"]')).toBeVisible();

      // Resume queue processing
      await page.click('[data-testid="resume-queue"]');
      await expect(page.locator('[data-testid="queue-active"]')).toBeVisible();

      // Clear failed notifications
      await page.click('[data-testid="clear-failed"]');
      await expect(page.locator('[data-testid="failed-cleared"]')).toBeVisible();
    });

    test('should retry failed notifications', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications/queue');

      // Find failed notifications
      const failedNotifications = page.locator('[data-testid^="failed-notification-"]');
      if (await failedNotifications.count() > 0) {
        // Retry individual notification
        await failedNotifications.first().locator('[data-testid="retry-notification"]').click();
        await expect(page.locator('[data-testid="notification-retrying"]')).toBeVisible();
      }

      // Retry all failed
      await page.click('[data-testid="retry-all-failed"]');
      await expect(page.locator('[data-testid="bulk-retry-started"]')).toBeVisible();
    });
  });

  test.describe('Performance & Error Handling', () => {
    test('should handle high notification volume efficiently', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      // Should load efficiently even with many notifications
      const startTime = Date.now();
      await page.waitForSelector('[data-testid="notifications-dashboard"]');
      const loadTime = Date.now() - startTime;

      expect(loadTime).toBeLessThan(8000);
    });

    test('should gracefully handle provider failures', async ({ page }) => {
      // Mock email service failure
      await page.route('**/api/notifications/email/test', route => route.abort());

      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-email"]');
      await page.click('[data-testid="send-test-email"]');

      // Should show provider error
      await expect(page.locator('[data-testid="email-provider-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="check-configuration"]')).toBeVisible();
    });

    test('should validate notification configurations', async ({ page }) => {
      await authService.authenticateAs(page, 'admin');
      await page.goto('/dashboard/notifications');

      await page.click('[data-testid="configure-email"]');

      // Submit invalid SMTP configuration
      await page.fill('[data-testid="smtp-host"]', '');
      await page.fill('[data-testid="smtp-port"]', 'invalid');
      await page.click('[data-testid="save-email-config"]');

      // Should show validation errors
      await expect(page.locator('[data-testid="smtp-host-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="smtp-port-error"]')).toBeVisible();
    });
  });
});
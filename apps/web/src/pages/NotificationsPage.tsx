/**
 * Notifications Page - Notification management and configuration
 * Restricted to Admin users only
 */

import React from 'react';
import { BillingNav, BillingBreadcrumb } from '@/components/billing/BillingNav';
import { NotificationsPanel } from '@/components/billing/notifications/NotificationsPanel';

export function NotificationsPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Breadcrumb */}
      <BillingBreadcrumb />

      {/* Navigation */}
      <BillingNav />

      {/* Notifications Panel */}
      <NotificationsPanel />
    </div>
  );
}

export default NotificationsPage;
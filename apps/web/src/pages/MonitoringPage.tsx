/**
 * Monitoring Page - System health and performance monitoring
 * Restricted to Admin users only
 */

import React from 'react';
import { BillingNav, BillingBreadcrumb } from '@/components/billing/BillingNav';
import { MonitoringPanel } from '@/components/billing/monitoring/MonitoringPanel';

export function MonitoringPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Breadcrumb */}
      <BillingBreadcrumb />

      {/* Navigation */}
      <BillingNav />

      {/* Monitoring Panel */}
      <MonitoringPanel refreshInterval={30} />
    </div>
  );
}

export default MonitoringPage;
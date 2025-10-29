/**
 * Bank Compliance Page - SME-wide billing metrics and compliance tracking
 * Restricted to Bank + Admin roles only
 */

import React from 'react';
import { BillingNav, BillingBreadcrumb } from '@/components/billing/BillingNav';
import { BankComplianceView } from '@/components/billing/bank/BankComplianceView';

export function BankCompliancePage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Breadcrumb */}
      <BillingBreadcrumb />

      {/* Navigation */}
      <BillingNav />

      {/* Bank Compliance View */}
      <BankComplianceView />
    </div>
  );
}

export default BankCompliancePage;
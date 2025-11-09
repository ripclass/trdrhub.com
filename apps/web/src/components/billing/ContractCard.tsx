/**
 * ContractCard component - displays bank contract information
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Building, Calendar, FileText, Mail, Phone, DollarSign } from 'lucide-react';
// Inline cn function to avoid import/bundling issues
function cn(...classes: (string | undefined | null | boolean | Record<string, boolean>)[]): string {
  return classes
    .filter(Boolean)
    .map((cls) => {
      if (typeof cls === 'string') return cls;
      if (typeof cls === 'object' && cls !== null) {
        return Object.entries(cls)
          .filter(([_, val]) => val)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join(' ');
}
;
import {
  PlanType,
  PLAN_DEFINITIONS,
  formatCurrency,
  getPlanDisplayName,
  isUnlimitedPlan
} from '@/types/billing';
import type { BankContract } from '@/types/billing';
import { format } from 'date-fns';

interface ContractCardProps {
  contract: BankContract;
  className?: string;
}

export function ContractCard({
  contract,
  className
}: ContractCardProps) {
  const { plan, contract_number, contract_term_months, start_date, end_date, quota_limit, overage_rate, billing_contact_name, billing_contact_email, billing_contact_phone, po_reference, next_settlement_date, payment_terms, currency, status } = contract;
  const planDef = PLAN_DEFINITIONS[plan];
  const isUnlimited = isUnlimitedPlan(plan);

  const getStatusBadge = () => {
    switch (status) {
      case 'active':
        return (
          <Badge variant="default" className="bg-green-100 text-green-600">
            Active
          </Badge>
        );
      case 'expired':
        return (
          <Badge variant="secondary" className="bg-gray-100 text-gray-600">
            Expired
          </Badge>
        );
      case 'terminated':
        return (
          <Badge variant="destructive">
            Terminated
          </Badge>
        );
      default:
        return null;
    }
  };

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'MMM dd, yyyy');
  };

  return (
    <Card className={cn('', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Building className="h-5 w-5 text-blue-500" />
            <CardTitle className="text-lg">
              Contract Details
            </CardTitle>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Contract Number */}
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <FileText className="h-4 w-4" />
            <span>Contract Number</span>
          </div>
          <p className="text-base font-medium">{contract_number}</p>
          {po_reference && (
            <p className="text-sm text-muted-foreground">PO: {po_reference}</p>
          )}
        </div>

        <Separator />

        {/* Plan & Quota */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Plan</span>
            <span className="text-sm font-medium">{getPlanDisplayName(plan)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Quota</span>
            <span className="text-sm font-medium">
              {isUnlimited ? 'Unlimited' : `${quota_limit?.toLocaleString() || 'N/A'} validations`}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Overage Rate</span>
            <span className="text-sm font-medium">
              {formatCurrency(overage_rate, currency)} per validation
            </span>
          </div>
        </div>

        <Separator />

        {/* Contract Term */}
        <div className="space-y-2">
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <Calendar className="h-4 w-4" />
            <span>Contract Term</span>
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Start Date</span>
              <span className="font-medium">{formatDate(start_date)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">End Date</span>
              <span className="font-medium">{formatDate(end_date)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Term</span>
              <span className="font-medium">{contract_term_months} months</span>
            </div>
          </div>
        </div>

        <Separator />

        {/* Billing Contact */}
        <div className="space-y-2">
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <Mail className="h-4 w-4" />
            <span>Billing Contact</span>
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium">{billing_contact_name}</p>
            <p className="text-sm text-muted-foreground">{billing_contact_email}</p>
            {billing_contact_phone && (
              <div className="flex items-center space-x-1 text-sm text-muted-foreground">
                <Phone className="h-3 w-3" />
                <span>{billing_contact_phone}</span>
              </div>
            )}
          </div>
        </div>

        <Separator />

        {/* Payment Terms & Next Settlement */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Payment Terms</span>
            <span className="font-medium">{payment_terms}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Next Settlement</span>
            <span className="font-medium">{formatDate(next_settlement_date)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}


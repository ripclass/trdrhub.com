/**
 * AlertBanner component - displays billing-related alerts and notifications
 */

import React from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertTriangle,
  XCircle,
  Clock,
  CreditCard,
  TrendingUp,
  X,
  ArrowUpRight
} from 'lucide-react';
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
  getQuotaThreshold,
  formatCurrency,
  getPlanDisplayName
} from '@/types/billing';
import type { UsageStats, PlanType, InvoiceStatus } from '@/types/billing';

interface AlertBannerProps {
  usage: UsageStats;
  plan: PlanType;
  lastInvoiceStatus?: InvoiceStatus;
  onUpgrade?: () => void;
  onRetryPayment?: () => void;
  onDismiss?: (alertType: string) => void;
  dismissedAlerts?: string[];
  className?: string;
}

interface Alert {
  id: string;
  type: 'error' | 'warning' | 'info';
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  action?: {
    label: string;
    onClick: () => void;
  };
  dismissible?: boolean;
  priority: number; // Higher numbers = higher priority
}

export function AlertBanner({
  usage,
  plan,
  lastInvoiceStatus,
  onUpgrade,
  onRetryPayment,
  onDismiss,
  dismissedAlerts = [],
  className
}: AlertBannerProps) {
  const alerts: Alert[] = [];

  // Quota exceeded alert
  if (usage.quota_limit && usage.quota_used >= usage.quota_limit) {
    alerts.push({
      id: 'quota-exceeded',
      type: 'error',
      title: 'Quota Exceeded',
      description: `You've used all ${usage.quota_limit} validations in your ${getPlanDisplayName(plan)} plan. Upgrade to continue validation services.`,
      icon: XCircle,
      action: onUpgrade ? {
        label: 'Upgrade Plan',
        onClick: onUpgrade
      } : undefined,
      dismissible: false,
      priority: 10
    });
  }
  // Quota critical alert (95%+)
  else if (usage.quota_limit && getQuotaThreshold(usage.quota_used, usage.quota_limit) === 'critical') {
    const remaining = usage.quota_remaining || 0;
    alerts.push({
      id: 'quota-critical',
      type: 'warning',
      title: 'Quota Almost Exceeded',
      description: `Only ${remaining} validations remaining in your ${getPlanDisplayName(plan)} plan. Consider upgrading to avoid service interruption.`,
      icon: AlertTriangle,
      action: onUpgrade ? {
        label: 'Upgrade Plan',
        onClick: onUpgrade
      } : undefined,
      dismissible: true,
      priority: 8
    });
  }
  // Quota warning alert (80%+)
  else if (usage.quota_limit && getQuotaThreshold(usage.quota_used, usage.quota_limit) === 'warning') {
    const remaining = usage.quota_remaining || 0;
    alerts.push({
      id: 'quota-warning',
      type: 'info',
      title: 'Quota Usage High',
      description: `${remaining} validations remaining in your ${getPlanDisplayName(plan)} plan. You're at ${Math.round((usage.quota_used / usage.quota_limit) * 100)}% of your monthly limit.`,
      icon: Clock,
      action: onUpgrade ? {
        label: 'View Plans',
        onClick: onUpgrade
      } : undefined,
      dismissible: true,
      priority: 5
    });
  }

  // Payment failed alert
  if (lastInvoiceStatus === 'FAILED') {
    alerts.push({
      id: 'payment-failed',
      type: 'error',
      title: 'Payment Failed',
      description: 'Your last payment could not be processed. Please retry payment or update your payment method to avoid service interruption.',
      icon: CreditCard,
      action: onRetryPayment ? {
        label: 'Retry Payment',
        onClick: onRetryPayment
      } : undefined,
      dismissible: false,
      priority: 9
    });
  }

  // Overdue invoice alert
  if (lastInvoiceStatus === 'OVERDUE') {
    alerts.push({
      id: 'invoice-overdue',
      type: 'error',
      title: 'Invoice Overdue',
      description: 'Your invoice is past due. Please make payment immediately to avoid service suspension.',
      icon: AlertTriangle,
      action: onRetryPayment ? {
        label: 'Pay Now',
        onClick: onRetryPayment
      } : undefined,
      dismissible: false,
      priority: 9
    });
  }

  // Pending payment alert
  if (lastInvoiceStatus === 'PENDING') {
    alerts.push({
      id: 'payment-pending',
      type: 'info',
      title: 'Payment Processing',
      description: 'Your payment is being processed. This may take a few minutes to complete.',
      icon: Clock,
      dismissible: true,
      priority: 3
    });
  }

  // Usage forecast alert (if trending to exceed quota)
  if (usage.quota_limit && usage.quota_used < usage.quota_limit) {
    const usageRate = usage.quota_used / new Date().getDate(); // Daily average
    const daysInMonth = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).getDate();
    const projectedUsage = usageRate * daysInMonth;

    if (projectedUsage > usage.quota_limit * 1.1) { // 110% of quota
      const daysToExceed = Math.ceil((usage.quota_limit - usage.quota_used) / usageRate);

      alerts.push({
        id: 'usage-forecast',
        type: 'warning',
        title: 'Usage Forecast Warning',
        description: `At your current rate, you'll exceed your quota in approximately ${daysToExceed} days. Consider upgrading to avoid interruption.`,
        icon: TrendingUp,
        action: onUpgrade ? {
          label: 'Upgrade Plan',
          onClick: onUpgrade
        } : undefined,
        dismissible: true,
        priority: 6
      });
    }
  }

  // Filter out dismissed alerts and sort by priority
  const visibleAlerts = alerts
    .filter(alert => !dismissedAlerts.includes(alert.id))
    .sort((a, b) => b.priority - a.priority);

  if (visibleAlerts.length === 0) {
    return null;
  }

  // Show only the highest priority alert
  const primaryAlert = visibleAlerts[0];

  const getAlertVariant = (type: Alert['type']) => {
    switch (type) {
      case 'error':
        return 'destructive';
      case 'warning':
        return 'default';
      case 'info':
        return 'default';
      default:
        return 'default';
    }
  };

  const getAlertClassName = (type: Alert['type']) => {
    switch (type) {
      case 'error':
        return 'border-red-200 bg-red-50';
      case 'warning':
        return 'border-yellow-200 bg-yellow-50';
      case 'info':
        return 'border-blue-200 bg-blue-50';
      default:
        return '';
    }
  };

  return (
    <div className={cn('space-y-2', className)}>
      <Alert
        variant={getAlertVariant(primaryAlert.type)}
        className={cn(getAlertClassName(primaryAlert.type))}
      >
        <primaryAlert.icon className="h-4 w-4" />
        <div className="flex-1 space-y-2">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <AlertTitle className="flex items-center space-x-2">
                <span>{primaryAlert.title}</span>
                <Badge variant="outline" className="text-xs">
                  {primaryAlert.type.toUpperCase()}
                </Badge>
              </AlertTitle>
              <AlertDescription className="mt-1">
                {primaryAlert.description}
              </AlertDescription>
            </div>

            {/* Actions */}
            <div className="flex items-center space-x-2 ml-4">
              {primaryAlert.action && (
                <Button
                  size="sm"
                  onClick={primaryAlert.action.onClick}
                  className="h-8"
                >
                  <ArrowUpRight className="h-3 w-3 mr-1" />
                  {primaryAlert.action.label}
                </Button>
              )}

              {primaryAlert.dismissible && onDismiss && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onDismiss(primaryAlert.id)}
                  className="h-8 w-8 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </Alert>

      {/* Show additional alerts count if there are more */}
      {visibleAlerts.length > 1 && (
        <div className="text-xs text-muted-foreground text-center">
          +{visibleAlerts.length - 1} more {visibleAlerts.length === 2 ? 'alert' : 'alerts'}
        </div>
      )}
    </div>
  );
}

// Compact version for mobile or smaller spaces
export function AlertBannerCompact({
  usage,
  plan,
  lastInvoiceStatus,
  onUpgrade,
  className
}: AlertBannerProps) {
  const hasQuotaIssue = usage.quota_limit &&
    getQuotaThreshold(usage.quota_used, usage.quota_limit) !== 'normal';
  const hasPaymentIssue = lastInvoiceStatus === 'FAILED' || lastInvoiceStatus === 'OVERDUE';

  if (!hasQuotaIssue && !hasPaymentIssue) {
    return null;
  }

  return (
    <div className={cn('space-y-1', className)}>
      {hasPaymentIssue && (
        <div className="flex items-center space-x-2 p-2 bg-red-50 border border-red-200 rounded-md">
          <CreditCard className="h-4 w-4 text-red-600" />
          <span className="text-sm text-red-800">Payment issue - action required</span>
        </div>
      )}

      {hasQuotaIssue && (
        <div className="flex items-center justify-between p-2 bg-yellow-50 border border-yellow-200 rounded-md">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
            <span className="text-sm text-yellow-800">
              {usage.quota_remaining} validations remaining
            </span>
          </div>
          {onUpgrade && (
            <Button size="sm" variant="outline" onClick={onUpgrade}>
              Upgrade
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
/**
 * UsageSummaryCard component - displays usage summary metrics
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle2,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Calendar,
  FileText,
  Activity
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/types/billing';
import type { UsageStats, InvoiceStatus } from '@/types/billing';

interface UsageSummaryCardProps {
  type: 'validations' | 'rechecks' | 'cost' | 'invoice';
  usage?: UsageStats;
  lastInvoiceStatus?: InvoiceStatus;
  className?: string;
  trend?: {
    value: number;
    isPositive: boolean;
    period: string;
  };
}

export function UsageSummaryCard({
  type,
  usage,
  lastInvoiceStatus,
  className,
  trend
}: UsageSummaryCardProps) {
  const getCardContent = () => {
    switch (type) {
      case 'validations':
        return {
          title: 'Validations This Month',
          value: usage?.current_month || 0,
          icon: CheckCircle2,
          iconColor: 'text-green-600',
          bgColor: 'bg-green-50',
          description: `${usage?.today || 0} today, ${usage?.current_week || 0} this week`,
          suffix: 'validations'
        };

      case 'rechecks':
        return {
          title: 'Re-checks Used',
          value: Math.floor((usage?.current_month || 0) * 0.15), // Approximate 15% re-check rate
          icon: RefreshCw,
          iconColor: 'text-blue-600',
          bgColor: 'bg-blue-50',
          description: 'Quality assurance validations',
          suffix: 're-checks'
        };

      case 'cost':
        return {
          title: 'Total Cost',
          value: usage?.total_cost || 0,
          icon: DollarSign,
          iconColor: 'text-purple-600',
          bgColor: 'bg-purple-50',
          description: 'Current month spending',
          isCurrency: true,
          suffix: 'BDT'
        };

      case 'invoice':
        return {
          title: 'Last Invoice',
          value: getInvoiceStatusDisplay(),
          icon: FileText,
          iconColor: getInvoiceStatusColor(),
          bgColor: getInvoiceStatusBg(),
          description: 'Most recent billing status',
          isStatus: true
        };

      default:
        return {
          title: 'Unknown',
          value: 0,
          icon: Activity,
          iconColor: 'text-gray-600',
          bgColor: 'bg-gray-50',
          description: 'No data available'
        };
    }
  };

  const getInvoiceStatusDisplay = () => {
    switch (lastInvoiceStatus) {
      case 'PAID':
        return 'Paid';
      case 'PENDING':
        return 'Pending';
      case 'OVERDUE':
        return 'Overdue';
      case 'FAILED':
        return 'Failed';
      case 'CANCELLED':
        return 'Cancelled';
      default:
        return 'No Invoice';
    }
  };

  const getInvoiceStatusColor = () => {
    switch (lastInvoiceStatus) {
      case 'PAID':
        return 'text-green-600';
      case 'PENDING':
        return 'text-yellow-600';
      case 'OVERDUE':
      case 'FAILED':
        return 'text-red-600';
      case 'CANCELLED':
        return 'text-gray-600';
      default:
        return 'text-gray-600';
    }
  };

  const getInvoiceStatusBg = () => {
    switch (lastInvoiceStatus) {
      case 'PAID':
        return 'bg-green-50';
      case 'PENDING':
        return 'bg-yellow-50';
      case 'OVERDUE':
      case 'FAILED':
        return 'bg-red-50';
      case 'CANCELLED':
        return 'bg-gray-50';
      default:
        return 'bg-gray-50';
    }
  };

  const content = getCardContent();
  const Icon = content.icon;

  const formatValue = () => {
    if (content.isStatus) {
      return content.value;
    }

    if (content.isCurrency) {
      return formatCurrency(content.value as number);
    }

    if (typeof content.value === 'number') {
      return content.value.toLocaleString();
    }

    return content.value;
  };

  return (
    <Card className={cn('transition-all hover:shadow-md', className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {content.title}
        </CardTitle>
        <div className={cn('p-2 rounded-full', content.bgColor)}>
          <Icon className={cn('h-4 w-4', content.iconColor)} />
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-2">
          {/* Main value */}
          <div className="flex items-center space-x-2">
            <div className="text-2xl font-bold">
              {formatValue()}
            </div>
            {content.isStatus && (
              <Badge
                variant={lastInvoiceStatus === 'PAID' ? 'default' :
                        lastInvoiceStatus === 'PENDING' ? 'secondary' : 'destructive'}
                className="text-xs"
              >
                {content.value}
              </Badge>
            )}
          </div>

          {/* Description */}
          <p className="text-xs text-muted-foreground">
            {content.description}
          </p>

          {/* Trend indicator */}
          {trend && (
            <div className="flex items-center space-x-1 pt-1">
              {trend.isPositive ? (
                <TrendingUp className="h-3 w-3 text-green-600" />
              ) : (
                <TrendingDown className="h-3 w-3 text-red-600" />
              )}
              <span className={cn(
                'text-xs font-medium',
                trend.isPositive ? 'text-green-600' : 'text-red-600'
              )}>
                {trend.isPositive ? '+' : ''}{trend.value}%
              </span>
              <span className="text-xs text-muted-foreground">
                vs {trend.period}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// Grid layout for multiple summary cards
interface UsageSummaryGridProps {
  usage: UsageStats;
  lastInvoiceStatus?: InvoiceStatus;
  className?: string;
  trends?: {
    validations?: { value: number; isPositive: boolean; period: string };
    cost?: { value: number; isPositive: boolean; period: string };
  };
}

export function UsageSummaryGrid({
  usage,
  lastInvoiceStatus,
  className,
  trends
}: UsageSummaryGridProps) {
  return (
    <div className={cn('grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4', className)}>
      <UsageSummaryCard
        type="validations"
        usage={usage}
        trend={trends?.validations}
      />
      <UsageSummaryCard
        type="rechecks"
        usage={usage}
      />
      <UsageSummaryCard
        type="cost"
        usage={usage}
        trend={trends?.cost}
      />
      <UsageSummaryCard
        type="invoice"
        lastInvoiceStatus={lastInvoiceStatus}
      />
    </div>
  );
}

// Compact version for mobile or sidebar
export function UsageSummaryCompact({
  usage,
  lastInvoiceStatus,
  className
}: UsageSummaryGridProps) {
  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-green-100 rounded-full">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </div>
          <div>
            <div className="text-sm font-medium">{usage.current_month} validations</div>
            <div className="text-xs text-muted-foreground">this month</div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-purple-100 rounded-full">
            <DollarSign className="h-4 w-4 text-purple-600" />
          </div>
          <div>
            <div className="text-sm font-medium">{formatCurrency(usage.total_cost)}</div>
            <div className="text-xs text-muted-foreground">total cost</div>
          </div>
        </div>
      </div>

      {lastInvoiceStatus && (
        <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
          <div className="flex items-center space-x-3">
            <div className={cn('p-2 rounded-full', getInvoiceStatusBg())}>
              <FileText className={cn('h-4 w-4', getInvoiceStatusColor())} />
            </div>
            <div>
              <div className="text-sm font-medium">Last Invoice</div>
              <Badge
                variant={lastInvoiceStatus === 'PAID' ? 'default' :
                        lastInvoiceStatus === 'PENDING' ? 'secondary' : 'destructive'}
                className="text-xs mt-1"
              >
                {getInvoiceStatusDisplay()}
              </Badge>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  function getInvoiceStatusDisplay() {
    switch (lastInvoiceStatus) {
      case 'PAID': return 'Paid';
      case 'PENDING': return 'Pending';
      case 'OVERDUE': return 'Overdue';
      case 'FAILED': return 'Failed';
      case 'CANCELLED': return 'Cancelled';
      default: return 'No Invoice';
    }
  }

  function getInvoiceStatusColor() {
    switch (lastInvoiceStatus) {
      case 'PAID': return 'text-green-600';
      case 'PENDING': return 'text-yellow-600';
      case 'OVERDUE':
      case 'FAILED': return 'text-red-600';
      case 'CANCELLED': return 'text-gray-600';
      default: return 'text-gray-600';
    }
  }

  function getInvoiceStatusBg() {
    switch (lastInvoiceStatus) {
      case 'PAID': return 'bg-green-100';
      case 'PENDING': return 'bg-yellow-100';
      case 'OVERDUE':
      case 'FAILED': return 'bg-red-100';
      case 'CANCELLED': return 'bg-gray-100';
      default: return 'bg-gray-100';
    }
  }
}
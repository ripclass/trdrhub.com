/**
 * QuotaMeter component - displays quota usage with visual indicator
 */

import React from 'react';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle, XCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getQuotaThreshold, isUnlimitedPlan, formatCurrency } from '@/types/billing';
import type { UsageStats, PlanType } from '@/types/billing';

interface QuotaMeterProps {
  usage: UsageStats;
  plan: PlanType;
  className?: string;
  showCost?: boolean;
}

export function QuotaMeter({ usage, plan, className, showCost = true }: QuotaMeterProps) {
  const { quota_used, quota_limit, quota_remaining, total_cost } = usage;

  const isUnlimited = isUnlimitedPlan(plan);
  const threshold = getQuotaThreshold(quota_used, quota_limit);
  const percentage = quota_limit ? Math.min((quota_used / quota_limit) * 100, 100) : 0;

  const getThresholdConfig = () => {
    switch (threshold) {
      case 'exceeded':
        return {
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          progressColor: 'bg-red-500',
          icon: XCircle,
          label: 'Quota Exceeded',
          badgeVariant: 'destructive' as const
        };
      case 'critical':
        return {
          color: 'text-orange-600',
          bgColor: 'bg-orange-50',
          borderColor: 'border-orange-200',
          progressColor: 'bg-orange-500',
          icon: AlertTriangle,
          label: 'Critical',
          badgeVariant: 'destructive' as const
        };
      case 'warning':
        return {
          color: 'text-yellow-600',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          progressColor: 'bg-yellow-500',
          icon: Clock,
          label: 'Warning',
          badgeVariant: 'secondary' as const
        };
      default:
        return {
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          progressColor: 'bg-green-500',
          icon: CheckCircle,
          label: 'Good',
          badgeVariant: 'secondary' as const
        };
    }
  };

  const config = getThresholdConfig();
  const Icon = config.icon;

  if (isUnlimited) {
    return (
      <Card className={cn('', className)}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Quota Usage</CardTitle>
          <Badge variant="secondary" className="bg-blue-50 text-blue-600">
            Unlimited
          </Badge>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold text-blue-600">{quota_used}</span>
              <div className="flex items-center space-x-1 text-sm text-blue-600">
                <CheckCircle className="h-4 w-4" />
                <span>Unlimited</span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Validations used this month
            </p>
            {showCost && (
              <div className="pt-2 border-t">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Total cost:</span>
                  <span className="font-medium">{formatCurrency(total_cost)}</span>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('transition-colors', config.bgColor, config.borderColor, className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Quota Usage</CardTitle>
        <Badge variant={config.badgeVariant} className="gap-1">
          <Icon className="h-3 w-3" />
          {config.label}
        </Badge>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Usage numbers */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <span className={cn('text-2xl font-bold', config.color)}>
                {quota_used}
              </span>
              <span className="text-sm text-muted-foreground">
                {quota_limit ? ` / ${quota_limit}` : ''}
              </span>
            </div>
            <div className="text-right">
              <div className={cn('text-sm font-medium', config.color)}>
                {quota_remaining !== null && quota_remaining >= 0
                  ? `${quota_remaining} remaining`
                  : 'Quota exceeded'
                }
              </div>
              <div className="text-xs text-muted-foreground">
                {percentage.toFixed(1)}% used
              </div>
            </div>
          </div>

          {/* Progress bar */}
          {quota_limit && (
            <div className="space-y-2">
              <Progress
                value={Math.min(percentage, 100)}
                className="h-2"
                indicatorClassName={config.progressColor}
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>0</span>
                <span>{quota_limit}</span>
              </div>
            </div>
          )}

          {/* Cost information */}
          {showCost && (
            <div className="pt-2 border-t">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Total cost this month:</span>
                <span className="font-medium">{formatCurrency(total_cost)}</span>
              </div>
            </div>
          )}

          {/* Warning messages */}
          {threshold === 'exceeded' && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <div className="flex items-center space-x-2 text-red-800">
                <XCircle className="h-4 w-4" />
                <span className="text-sm font-medium">Quota exceeded</span>
              </div>
              <p className="text-xs text-red-600 mt-1">
                You've exceeded your monthly quota. Consider upgrading your plan to continue validation services.
              </p>
            </div>
          )}

          {threshold === 'critical' && (
            <div className="p-3 bg-orange-50 border border-orange-200 rounded-md">
              <div className="flex items-center space-x-2 text-orange-800">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-sm font-medium">Nearing quota limit</span>
              </div>
              <p className="text-xs text-orange-600 mt-1">
                You're close to your monthly limit. Consider upgrading to avoid service interruption.
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// Compact version for use in headers or sidebars
export function QuotaMeterCompact({ usage, plan, className }: QuotaMeterProps) {
  const { quota_used, quota_limit } = usage;
  const isUnlimited = isUnlimitedPlan(plan);
  const threshold = getQuotaThreshold(quota_used, quota_limit);
  const percentage = quota_limit ? Math.min((quota_used / quota_limit) * 100, 100) : 0;

  const getStatusColor = () => {
    switch (threshold) {
      case 'exceeded':
        return 'text-red-600';
      case 'critical':
        return 'text-orange-600';
      case 'warning':
        return 'text-yellow-600';
      default:
        return 'text-green-600';
    }
  };

  if (isUnlimited) {
    return (
      <div className={cn('flex items-center space-x-2', className)}>
        <div className="flex-1">
          <div className="text-sm font-medium">{quota_used} validations</div>
          <div className="text-xs text-blue-600">Unlimited plan</div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('flex items-center space-x-2', className)}>
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">
            {quota_used} / {quota_limit}
          </span>
          <span className={cn('text-xs', getStatusColor())}>
            {percentage.toFixed(0)}%
          </span>
        </div>
        {quota_limit && (
          <Progress
            value={Math.min(percentage, 100)}
            className="h-1 mt-1"
            indicatorClassName={threshold === 'exceeded' ? 'bg-red-500' : threshold === 'critical' ? 'bg-orange-500' : 'bg-green-500'}
          />
        )}
      </div>
    </div>
  );
}
import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
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

interface KPICardProps {
  title: string;
  value: string | number;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  icon?: React.ReactNode;
  status?: 'good' | 'warning' | 'critical';
  loading?: boolean;
  className?: string;
}

export function KPICard({
  title,
  value,
  trend,
  trendValue,
  icon,
  status = 'good',
  loading = false,
  className
}: KPICardProps) {
  if (loading) {
    return (
      <Card className={cn('p-6', className)}>
        <CardContent className="p-0">
          <div className="flex items-center justify-between mb-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-5 w-5 rounded" />
          </div>
          <Skeleton className="h-8 w-20 mb-2" />
          <Skeleton className="h-4 w-16" />
        </CardContent>
      </Card>
    );
  }

  const statusColors = {
    good: 'border-green-200 bg-green-50',
    warning: 'border-yellow-200 bg-yellow-50',
    critical: 'border-red-200 bg-red-50'
  };

  const iconColors = {
    good: 'text-green-600',
    warning: 'text-yellow-600',
    critical: 'text-red-600'
  };

  const trendColors = {
    up: 'text-green-600',
    down: 'text-red-600',
    stable: 'text-gray-600'
  };

  const getTrendIcon = (trendType?: string) => {
    switch (trendType) {
      case 'up':
        return <TrendingUp className="w-4 h-4" />;
      case 'down':
        return <TrendingDown className="w-4 h-4" />;
      case 'stable':
        return <Minus className="w-4 h-4" />;
      default:
        return null;
    }
  };

  return (
    <Card className={cn(
      'transition-all duration-200 hover:shadow-md',
      statusColors[status],
      className
    )}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-gray-600">{title}</h3>
          {icon && (
            <div className={cn('p-2 rounded-lg bg-white', iconColors[status])}>
              {icon}
            </div>
          )}
        </div>

        <div className="space-y-1">
          <div className="text-2xl font-bold text-gray-900">
            {value}
          </div>

          {(trend || trendValue) && (
            <div className="flex items-center gap-1">
              {trend && (
                <span className={cn('flex items-center gap-1', trendColors[trend])}>
                  {getTrendIcon(trend)}
                </span>
              )}
              {trendValue && (
                <span className={cn(
                  'text-sm font-medium',
                  trend ? trendColors[trend] : 'text-gray-600'
                )}>
                  {trendValue}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Status indicator */}
        <div className="mt-3 flex items-center gap-2">
          <div className={cn(
            'w-2 h-2 rounded-full',
            status === 'good' && 'bg-green-500',
            status === 'warning' && 'bg-yellow-500',
            status === 'critical' && 'bg-red-500'
          )} />
          <span className="text-xs text-gray-500 capitalize">
            {status === 'good' && 'Healthy'}
            {status === 'warning' && 'Warning'}
            {status === 'critical' && 'Critical'}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
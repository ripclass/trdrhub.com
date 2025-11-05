/**
 * PlanCard component - displays current plan information and upgrade options
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ArrowUpRight, Crown, Zap, Building, Gift } from 'lucide-react';
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
import type { CompanyBillingInfo } from '@/types/billing';

interface PlanCardProps {
  billingInfo: CompanyBillingInfo;
  onUpgrade?: () => void;
  className?: string;
  showUpgradeButton?: boolean;
}

export function PlanCard({
  billingInfo,
  onUpgrade,
  className,
  showUpgradeButton = true
}: PlanCardProps) {
  const { plan } = billingInfo;
  const planDef = PLAN_DEFINITIONS[plan];
  const isUnlimited = isUnlimitedPlan(plan);

  const getPlanIcon = () => {
    switch (plan) {
      case PlanType.FREE:
        return <Gift className="h-5 w-5 text-gray-500" />;
      case PlanType.STARTER:
        return <Zap className="h-5 w-5 text-blue-500" />;
      case PlanType.PROFESSIONAL:
        return <Crown className="h-5 w-5 text-purple-500" />;
      case PlanType.ENTERPRISE:
        return <Building className="h-5 w-5 text-gold-500" />;
      default:
        return <Zap className="h-5 w-5 text-gray-500" />;
    }
  };

  const getPlanColor = () => {
    switch (plan) {
      case PlanType.FREE:
        return 'text-gray-600';
      case PlanType.STARTER:
        return 'text-blue-600';
      case PlanType.PROFESSIONAL:
        return 'text-purple-600';
      case PlanType.ENTERPRISE:
        return 'text-gold-600';
      default:
        return 'text-gray-600';
    }
  };

  const getPlanBadge = () => {
    switch (plan) {
      case PlanType.FREE:
        return (
          <Badge variant="secondary" className="bg-gray-100 text-gray-600">
            Free Plan
          </Badge>
        );
      case PlanType.STARTER:
        return (
          <Badge variant="default" className="bg-blue-100 text-blue-600">
            Starter
          </Badge>
        );
      case PlanType.PROFESSIONAL:
        return (
          <Badge variant="default" className="bg-purple-100 text-purple-600">
            Professional
          </Badge>
        );
      case PlanType.ENTERPRISE:
        return (
          <Badge variant="default" className="bg-gold-100 text-gold-600">
            Enterprise
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary">
            {getPlanDisplayName(plan)}
          </Badge>
        );
    }
  };

  const canUpgrade = plan !== PlanType.ENTERPRISE;

  const getNextBillingDate = () => {
    // This would typically come from the API
    // For now, we'll calculate next month
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    nextMonth.setDate(1);

    return nextMonth.toLocaleDateString('en-BD', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <Card className={cn('', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getPlanIcon()}
            <CardTitle className={cn('text-lg', getPlanColor())}>
              {getPlanDisplayName(plan)}
            </CardTitle>
          </div>
          {getPlanBadge()}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Plan pricing */}
        <div className="space-y-2">
          <div className="flex items-baseline space-x-2">
            {planDef.price > 0 ? (
              <>
                <span className="text-2xl font-bold">
                  {formatCurrency(planDef.price)}
                </span>
                <span className="text-sm text-muted-foreground">/month</span>
              </>
            ) : plan === PlanType.ENTERPRISE ? (
              <span className="text-xl font-semibold text-gold-600">
                Custom Pricing
              </span>
            ) : (
              <span className="text-2xl font-bold text-green-600">
                Free
              </span>
            )}
          </div>

          {/* Quota information */}
          <div className="text-sm text-muted-foreground">
            {isUnlimited ? (
              <span className="text-blue-600 font-medium">Unlimited validations</span>
            ) : (
              <span>
                {planDef.quota?.toLocaleString()} validations per month
              </span>
            )}
          </div>
        </div>

        <Separator />

        {/* Plan features */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">
            Plan Features
          </h4>
          <ul className="space-y-1">
            {planDef.features.slice(0, 3).map((feature, index) => (
              <li key={index} className="text-sm flex items-start space-x-2">
                <span className="text-green-500 mt-0.5">✓</span>
                <span>{feature}</span>
              </li>
            ))}
            {planDef.features.length > 3 && (
              <li className="text-sm text-muted-foreground">
                +{planDef.features.length - 3} more features
              </li>
            )}
          </ul>
        </div>

        {/* Next billing date */}
        {plan !== PlanType.FREE && (
          <>
            <Separator />
            <div className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Next billing:</span>
                <span className="font-medium">{getNextBillingDate()}</span>
              </div>
            </div>
          </>
        )}

        {/* Upgrade button */}
        {canUpgrade && showUpgradeButton && (
          <>
            <Separator />
            <Button
              onClick={onUpgrade}
              className="w-full"
              variant={plan === PlanType.FREE ? "default" : "outline"}
            >
              <ArrowUpRight className="h-4 w-4 mr-2" />
              {plan === PlanType.FREE ? 'Upgrade Plan' : 'Change Plan'}
            </Button>
          </>
        )}

        {/* Enterprise contact */}
        {plan === PlanType.ENTERPRISE && (
          <>
            <Separator />
            <div className="text-center space-y-2">
              <p className="text-sm text-muted-foreground">
                Need to modify your Enterprise plan?
              </p>
              <Button variant="outline" size="sm">
                Contact Sales
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// Compact version for use in headers or mobile
export function PlanCardCompact({
  billingInfo,
  onUpgrade,
  className
}: PlanCardProps) {
  const { plan } = billingInfo;
  const planDef = PLAN_DEFINITIONS[plan];

  const getPlanIcon = () => {
    switch (plan) {
      case PlanType.FREE:
        return <Gift className="h-4 w-4 text-gray-500" />;
      case PlanType.STARTER:
        return <Zap className="h-4 w-4 text-blue-500" />;
      case PlanType.PROFESSIONAL:
        return <Crown className="h-4 w-4 text-purple-500" />;
      case PlanType.ENTERPRISE:
        return <Building className="h-4 w-4 text-gold-500" />;
      default:
        return <Zap className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <div className={cn('flex items-center justify-between p-3 bg-muted rounded-lg', className)}>
      <div className="flex items-center space-x-2">
        {getPlanIcon()}
        <div>
          <div className="text-sm font-medium">
            {getPlanDisplayName(plan)}
          </div>
          <div className="text-xs text-muted-foreground">
            {planDef.price > 0 ? formatCurrency(planDef.price) + '/month' : 'Free'}
          </div>
        </div>
      </div>

      {plan !== PlanType.ENTERPRISE && onUpgrade && (
        <Button size="sm" variant="outline" onClick={onUpgrade}>
          <ArrowUpRight className="h-3 w-3 mr-1" />
          Upgrade
        </Button>
      )}
    </div>
  );
}
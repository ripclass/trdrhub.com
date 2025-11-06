import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CreditCard } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services";
import type { BillingPlan } from "@/lib/admin/types";

const service = getAdminService();

export default function Plans() {
  const enabled = isAdminFeatureEnabled("billing");
  const [plans, setPlans] = React.useState<BillingPlan[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!enabled) return;
    service
      .listBillingPlans()
      .then((data) => setPlans(data))
      .finally(() => setLoading(false));
  }, [enabled]);

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-amber-500/40 bg-amber-500/5 p-6">
        <h3 className="text-sm font-semibold text-amber-600">Billing preview disabled</h3>
        <p className="mt-2 text-sm text-amber-600/80">
          Toggle the billing feature flag to expose subscription management in the admin console.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Plans and pricing"
        description="Manage subscription tiers offered to banks, exporters and importers."
      />

      {loading ? (
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Card key={index} className="border-border/60">
              <CardHeader>
                <Skeleton className="h-5 w-24" />
                <Skeleton className="mt-2 h-7 w-32" />
              </CardHeader>
              <CardContent className="space-y-2">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : plans.length === 0 ? (
        <AdminEmptyState
          title="No plans configured"
          description="Define plan catalog to offer subscription tiers."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {plans.map((plan) => (
            <Card key={plan.id} className="border-border/60">
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-base">
                  <span>{plan.name}</span>
                  <Badge variant={plan.status === "active" ? "outline" : "secondary"}>{plan.status}</Badge>
                </CardTitle>
                <CardDescription>
                  <span className="text-2xl font-semibold text-foreground">
                    {plan.currency} {(plan.pricePerMonth / 100).toLocaleString(undefined, { minimumFractionDigits: 0 })}/mo
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1 text-sm text-muted-foreground">
                  <p className="font-medium text-foreground">Included features</p>
                  <ul className="space-y-1 text-xs">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-center gap-2">
                        <span className="text-emerald-500">•</span> {feature}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="space-y-1 text-xs text-muted-foreground">
                  <p className="font-medium text-foreground">Usage limits</p>
                  {Object.entries(plan.limits).map(([limit, value]) => (
                    <p key={limit}>
                      {limit}: {value as string | number}
                    </p>
                  ))}
                </div>
                <Button variant="outline" size="sm" className="w-full" disabled>
                  <CreditCard className="mr-2 h-4 w-4" /> Plan editing coming soon
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CreditCard, Edit } from 'lucide-react';

const mockPlans = [
  { name: 'Free', price: '$0/mo', users: 1245, revenue: '$0', features: ['Basic validation', '10 docs/month', 'Email support'] },
  { name: 'Professional', price: '$49/mo', users: 856, revenue: '$41,944', features: ['Advanced validation', '100 docs/month', 'Priority support'] },
  { name: 'Enterprise', price: '$299/mo', users: 124, revenue: '$37,076', features: ['Unlimited validation', 'Unlimited docs', '24/7 support', 'Custom integration'] },
];

export function BillingPlans() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Plans & Pricing</h2>
        <p className="text-muted-foreground">
          Manage subscription plans and pricing tiers
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {mockPlans.map((plan) => (
          <Card key={plan.name} className="shadow-soft border-0">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{plan.name}</span>
                <Badge variant="outline">{plan.users} users</Badge>
              </CardTitle>
              <CardDescription>
                <span className="text-2xl font-bold text-foreground">{plan.price}</span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Monthly Revenue</p>
                  <p className="text-lg font-semibold text-foreground">{plan.revenue}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">Features</p>
                  <ul className="space-y-1">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="text-sm text-muted-foreground flex items-center gap-2">
                        <span className="text-success">✓</span> {feature}
                      </li>
                    ))}
                  </ul>
                </div>
                <Button variant="outline" className="w-full">
                  <Edit className="w-4 h-4 mr-2" />
                  Edit Plan
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}


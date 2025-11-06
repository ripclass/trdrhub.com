import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CreditCard } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services/index";
import type { BillingPlan } from "@/lib/admin/types";

const service = getAdminService();

export function BillingPlans() {
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

export default BillingPlans;

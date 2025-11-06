import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { Globe } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services/index";
import type { ResidencyPolicy } from "@/lib/admin/types";

const service = getAdminService();

export function ComplianceResidency() {
  const enabled = isAdminFeatureEnabled("compliance");
  const { toast } = useToast();
  const [policies, setPolicies] = React.useState<ResidencyPolicy[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!enabled) return;
    service
      .listResidencyPolicies()
      .then((data) => setPolicies(data))
      .finally(() => setLoading(false));
  }, [enabled]);

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-sky-500/40 bg-sky-500/5 p-6 text-sm text-sky-600">
        Enable the <strong>compliance</strong> flag to manage data residency.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Data residency"
        description="Validate storage locations and document waivers."
      />

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-primary" /> Regional coverage
          </CardTitle>
          <CardDescription>Where customer data currently resides</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : policies.length === 0 ? (
            <AdminEmptyState
              title="No residency policies"
              description="Document regions to stay compliant with data sovereignty requirements."
            />
          ) : (
            policies.map((policy) => (
              <div
                key={policy.id}
                className="flex flex-col gap-4 rounded-lg border border-border/60 bg-card/60 p-4 md:flex-row md:items-center md:justify-between"
              >
                <div className="space-y-1 text-sm">
                  <p className="font-medium text-foreground">{policy.region}</p>
                  <p className="text-xs text-muted-foreground">Storage: {policy.storageLocation}</p>
                  {policy.notes && <p className="text-xs text-muted-foreground">Notes: {policy.notes}</p>}
                </div>
                <div className="flex items-center gap-3">
                  <Badge
                    variant={
                      policy.status === "compliant"
                        ? "default"
                        : policy.status === "waived"
                          ? "secondary"
                          : "destructive"
                    }
                  >
                    {policy.status}
                  </Badge>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => toast({ title: "Validation triggered", description: `Re-validating ${policy.region}` })}
                  >
                    Re-validate
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default ComplianceResidency;

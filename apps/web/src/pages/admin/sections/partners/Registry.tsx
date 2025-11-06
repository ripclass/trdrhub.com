import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { Building2, ToggleLeft, ToggleRight } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services/index";
import type { PartnerRecord } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();

export function PartnersRegistry() {
  const enabled = isAdminFeatureEnabled("partners");
  const { toast } = useToast();
  const [partners, setPartners] = React.useState<PartnerRecord[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);
  const audit = useAdminAudit("partners-registry");

  React.useEffect(() => {
    if (!enabled) return;
    service
      .listPartners()
      .then((data) => setPartners(data))
      .finally(() => setLoading(false));
  }, [enabled]);

  const toggleStatus = async (partner: PartnerRecord) => {
    const nextStatus = partner.status === "active" ? "inactive" : "active";
    setActionId(partner.id);
    const result = await service.setPartnerStatus(partner.id, nextStatus);
    setActionId(null);
    if (result.success) {
      toast({ title: "Partner updated", description: `${partner.name} set to ${nextStatus}` });
      setPartners((prev) => prev.map((item) => (item.id === partner.id ? { ...item, status: nextStatus } : item)));
      await audit("update_partner_status", { entityId: partner.id, metadata: { status: nextStatus } });
    } else {
      toast({ title: "Update failed", description: result.message, variant: "destructive" });
    }
  };

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-blue-500/40 bg-blue-500/5 p-6 text-sm text-blue-600">
        Enable the <strong>partners</strong> flag to expose registry management.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Partner registry"
        description="Central list of vendors and connectors powering LCopilot."
      />

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-primary" />
            Registered partners
          </CardTitle>
          <CardDescription>Status, markets served and last sync metadata</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : partners.length === 0 ? (
            <AdminEmptyState
              title="No partners"
              description="Add connectors to integrate third-party data providers."
            />
          ) : (
            partners.map((partner) => (
              <div
                key={partner.id}
                className="flex flex-col gap-4 rounded-lg border border-border/60 bg-card/60 p-4 md:flex-row md:items-center md:justify-between"
              >
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">{partner.name}</p>
                  <p className="text-xs text-muted-foreground">Category: {partner.category}</p>
                  <div className="flex flex-wrap gap-1 text-[10px] text-muted-foreground">
                    {partner.markets.map((market) => (
                      <Badge key={market} variant="outline">
                        {market}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">
                    Updated {new Date(partner.updatedAt).toLocaleString()}
                  </span>
                  <Badge variant={partner.status === "active" ? "default" : partner.status === "inactive" ? "secondary" : "outline"}>
                    {partner.status}
                  </Badge>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1"
                    onClick={() => toggleStatus(partner)}
                    disabled={actionId === partner.id}
                  >
                    {partner.status === "active" ? <ToggleLeft className="h-4 w-4" /> : <ToggleRight className="h-4 w-4" />}
                    {partner.status === "active" ? "Disable" : "Activate"}
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

export default PartnersRegistry;

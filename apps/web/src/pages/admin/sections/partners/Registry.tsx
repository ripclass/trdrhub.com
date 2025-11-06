import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { Building2, ToggleLeft, ToggleRight } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services";
import type { PartnerRecord } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();

export default function Registry() {
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Building, Plus } from 'lucide-react';

const mockPartners = [
  { id: 'part-001', name: 'Swift Network', type: 'Banking', status: 'active', integrations: 5, lastSync: '2 min ago' },
  { id: 'part-002', name: 'TradeConnect', type: 'Trade Finance', status: 'active', integrations: 3, lastSync: '1 hour ago' },
  { id: 'part-003', name: 'CustomsHub', type: 'Customs', status: 'inactive', integrations: 1, lastSync: '5 days ago' },
];

export function PartnersRegistry() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Partner Registry</h2>
        <p className="text-muted-foreground">
          Manage external partner integrations and connections
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building className="w-5 h-5" />
            Registered Partners
          </CardTitle>
          <CardDescription>Active partner integrations</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            Add Partner
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockPartners.map((partner) => (
              <div key={partner.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{partner.name}</p>
                  <p className="text-sm text-muted-foreground">{partner.type} • {partner.integrations} integrations</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">{partner.lastSync}</span>
                  <Badge variant={partner.status === 'active' ? 'default' : 'secondary'}>
                    {partner.status}
                  </Badge>
                  <Button variant="outline" size="sm">
                    Configure
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}


import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { Cable, Wrench } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services";
import type { ConnectorConfig } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();

export function PartnersConnectors() {
  const enabled = isAdminFeatureEnabled("partners");
  const { toast } = useToast();
  const [connectors, setConnectors] = React.useState<ConnectorConfig[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);
  const audit = useAdminAudit("partners-connectors");

  React.useEffect(() => {
    if (!enabled) return;
    service
      .listConnectors()
      .then((data) => setConnectors(data))
      .finally(() => setLoading(false));
  }, [enabled]);

  const toggleConnector = async (connector: ConnectorConfig) => {
    const next = connector.status === "enabled" ? "disabled" : "enabled";
    setActionId(connector.id);
    const result = await service.updateConnector(connector.id, { status: next });
    setActionId(null);
    if (result.success) {
      toast({ title: "Connector updated", description: `${connector.name} ${next}` });
      setConnectors((prev) => prev.map((item) => (item.id === connector.id ? { ...item, status: next } : item)));
      await audit("update_connector_status", { entityId: connector.id, metadata: { status: next } });
    } else {
      toast({ title: "Update failed", description: result.message, variant: "destructive" });
    }
  };

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-blue-500/40 bg-blue-500/5 p-6 text-sm text-blue-600">
        Partner connectors require the <strong>partners</strong> feature flag.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Integration connectors"
        description="Monitor external systems we interface with and control availability."
      />

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cable className="h-5 w-5 text-primary" /> Active connectors
          </CardTitle>
          <CardDescription>Enable or disable integrations at runtime</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : connectors.length === 0 ? (
            <AdminEmptyState
              title="No connectors"
              description="Add integrations to bring partner data into LCopilot."
            />
          ) : (
            connectors.map((connector) => (
              <div
                key={connector.id}
                className="flex flex-col gap-4 rounded-lg border border-border/60 bg-card/60 p-4 md:flex-row md:items-center md:justify-between"
              >
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">{connector.name}</p>
                  <p className="text-xs text-muted-foreground">
                    Provider: {connector.provider} • Auth: {connector.authType}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Last sync {connector.lastSyncAt ? new Date(connector.lastSyncAt).toLocaleString() : "—"}
                  </p>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    {connector.hasSecrets ? <Badge variant="secondary">Secrets stored</Badge> : <Badge variant="outline">No secrets</Badge>}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={connector.status === "enabled" ? "default" : connector.status === "error" ? "destructive" : "secondary"}>
                    {connector.status}
                  </Badge>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1"
                    onClick={() => toggleConnector(connector)}
                    disabled={actionId === connector.id}
                  >
                    <Wrench className="h-4 w-4" /> {connector.status === "enabled" ? "Disable" : "Enable"}
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

export default PartnersConnectors;

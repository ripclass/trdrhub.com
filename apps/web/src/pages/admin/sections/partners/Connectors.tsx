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

export default function Connectors() {
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Webhook, Plus } from 'lucide-react';

const mockConnectors = [
  { id: 'conn-001', name: 'SWIFT Gateway', type: 'API', status: 'healthy', requests: '12.4K/day', latency: '45ms' },
  { id: 'conn-002', name: 'Customs Portal', type: 'SOAP', status: 'healthy', requests: '3.2K/day', latency: '120ms' },
];

export function PartnersConnectors() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Connectors</h2>
        <p className="text-muted-foreground">
          Manage API connectors and integration endpoints
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Webhook className="w-5 h-5" />
            Active Connectors
          </CardTitle>
          <CardDescription>API and service connectors</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            Add Connector
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockConnectors.map((conn) => (
              <div key={conn.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{conn.name}</p>
                  <p className="text-sm text-muted-foreground">{conn.type} • {conn.requests} • {conn.latency} avg</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="default">{conn.status}</Badge>
                  <Button variant="outline" size="sm">
                    Test
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


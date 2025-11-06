import * as React from "react";

import { AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/use-toast";
import { Flag } from "lucide-react";

import {
  getAdminFeatureFlags,
  getAdminFeatureFlagsDefault,
  isAdminFeatureEnabled,
  resetAdminFeatureFlags,
  setAdminFeatureFlag,
} from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services/index";
import type { FeatureFlagRecord } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const MODULE_FLAGS: Array<{ flag: "billing" | "partners" | "llm" | "compliance"; label: string; description: string }> = [
  { flag: "billing", label: "Billing", description: "Expose monetization dashboards and overrides." },
  { flag: "partners", label: "Partners", description: "Manage registry, connectors and webhooks." },
  { flag: "llm", label: "LLM", description: "Show prompt library, budgets and evaluation results." },
  { flag: "compliance", label: "Compliance", description: "Enable residency, retention and legal hold views." },
];

export function SystemFeatureFlags() {
  const { toast } = useToast();
  const [remoteFlags, setRemoteFlags] = React.useState<FeatureFlagRecord[]>([]);
  const [moduleFlags, setModuleFlags] = React.useState(getAdminFeatureFlags());
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);
  const audit = useAdminAudit("system-feature-flags");

  React.useEffect(() => {
    service
      .listFeatureFlags()
      .then((data) => setRemoteFlags(data))
      .finally(() => setLoading(false));
  }, []);

  const toggleRemoteFlag = async (flag: FeatureFlagRecord) => {
    const nextStatus = flag.status === "enabled" ? "disabled" : "enabled";
    setActionId(flag.id);
    const result = await service.setFeatureFlagStatus(flag.id, nextStatus);
    setActionId(null);
    if (result.success) {
      toast({ title: `${flag.name} ${nextStatus}` });
      setRemoteFlags((prev) => prev.map((item) => (item.id === flag.id ? { ...item, status: nextStatus } : item)));
      await audit("toggle_remote_flag", { entityId: flag.id, metadata: { status: nextStatus } });
    } else {
      toast({ title: "Update failed", description: result.message, variant: "destructive" });
    }
  };

  const toggleModuleFlag = async (flag: keyof typeof moduleFlags) => {
    const next = !moduleFlags[flag];
    setModuleFlags((prev) => ({ ...prev, [flag]: next }));
    setAdminFeatureFlag(flag, next);
    toast({ title: `${flag} flag ${next ? "enabled" : "disabled"}` });
    await audit("toggle_module_flag", { metadata: { flag, enabled: next } });
  };

  const resetModuleToggles = async () => {
    resetAdminFeatureFlags();
    setModuleFlags(getAdminFeatureFlagsDefault());
    toast({ title: "Module flags reset" });
    await audit("reset_module_flags");
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Feature toggles"
        description="Control progressive delivery and internal preview modules."
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Flag className="h-5 w-5 text-primary" /> Platform flags
            </CardTitle>
            <CardDescription>Live feature flags synced from control plane</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 w-full" />
                ))}
              </div>
            ) : remoteFlags.length === 0 ? (
              <p className="text-xs text-muted-foreground">No platform flags defined.</p>
            ) : (
              remoteFlags.map((flag) => (
                <div key={flag.id} className="flex items-center justify-between rounded-lg border border-border/60 bg-card/60 p-3">
                  <div className="space-y-1">
                    <p className="font-mono text-sm text-foreground">{flag.name}</p>
                    <p className="text-xs text-muted-foreground">{flag.description}</p>
                    <div className="flex flex-wrap gap-1 text-[10px] text-muted-foreground">
                      {flag.tags?.map((tag) => (
                        <Badge key={tag} variant="outline">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={flag.status === "enabled" ? "default" : "secondary"}>{flag.status}</Badge>
                    <Switch
                      checked={flag.status === "enabled"}
                      onCheckedChange={() => toggleRemoteFlag(flag)}
                      disabled={actionId === flag.id}
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Flag className="h-5 w-5 text-primary" /> Admin modules
            </CardTitle>
            <CardDescription>Flags persisted locally for optional admin views</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {MODULE_FLAGS.map(({ flag, label, description }) => (
              <div key={flag} className="flex items-center justify-between rounded-lg border border-border/60 bg-card/60 p-3">
                <div>
                  <p className="text-sm font-medium text-foreground">{label}</p>
                  <p className="text-xs text-muted-foreground">{description}</p>
                </div>
                <Switch checked={moduleFlags[flag]} onCheckedChange={() => toggleModuleFlag(flag)} />
              </div>
            ))}
            <div className="flex justify-end">
              <Button variant="outline" size="sm" onClick={resetModuleToggles}>
                Reset defaults
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default SystemFeatureFlags;

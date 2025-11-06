import * as React from "react";

import { AdminToolbar } from "@/components/admin/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { getAdminService } from "@/lib/admin/services/index";
import type { AdminSettings } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();

export function SystemSettings() {
  const { toast } = useToast();
  const [settings, setSettings] = React.useState<AdminSettings | null>(null);
  const [baseline, setBaseline] = React.useState<AdminSettings | null>(null);
  const [saving, setSaving] = React.useState(false);
  const audit = useAdminAudit("system-settings");

  React.useEffect(() => {
    service.getSettings().then((data) => {
      setSettings(data);
      setBaseline(data);
    });
  }, []);

  const updateBranding = (key: keyof AdminSettings["branding"], value: string) => {
    setSettings((prev) => (prev ? { ...prev, branding: { ...prev.branding, [key]: value } } : prev));
  };

  const updateAuth = (key: keyof AdminSettings["authentication"], value: string | boolean | number) => {
    setSettings((prev) => (prev ? { ...prev, authentication: { ...prev.authentication, [key]: value } } : prev));
  };

  const updateNotifications = (key: keyof AdminSettings["notifications"], value: boolean | string) => {
    setSettings((prev) => (prev ? { ...prev, notifications: { ...prev.notifications, [key]: value } } : prev));
  };

  const reset = React.useCallback(async () => {
    if (baseline) {
      setSettings(baseline);
      await audit("reset_settings");
    }
  }, [audit, baseline]);

  const save = React.useCallback(async () => {
    if (!settings) return;
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(settings.branding.supportEmail)) {
      toast({ title: "Invalid support email", variant: "destructive" });
      return;
    }
    setSaving(true);
    const result = await service.updateSettings(settings);
    setSaving(false);
    if (result.success && result.data) {
      toast({ title: "Settings saved" });
      setBaseline(result.data);
      setSettings(result.data);
      if (baseline) {
        const changedSections: string[] = [];
        if (JSON.stringify(baseline.branding) !== JSON.stringify(result.data.branding)) changedSections.push("branding");
        if (JSON.stringify(baseline.authentication) !== JSON.stringify(result.data.authentication)) changedSections.push("authentication");
        if (JSON.stringify(baseline.notifications) !== JSON.stringify(result.data.notifications)) changedSections.push("notifications");
        await audit("save_settings", { metadata: { changedSections } });
      } else {
        await audit("save_settings");
      }
    } else {
      toast({ title: "Save failed", description: result.message, variant: "destructive" });
    }
  }, [audit, baseline, settings, toast]);

  if (!settings) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <Skeleton key={index} className="h-36 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="System settings"
        description="Branding, authentication and notification defaults across LCopilot."
      />

      <Tabs defaultValue="branding" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="branding">Branding</TabsTrigger>
          <TabsTrigger value="auth">Authentication</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="branding" className="mt-6 space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Primary color</Label>
              <Input value={settings.branding.primaryColor} onChange={(event) => updateBranding("primaryColor", event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Support email</Label>
              <Input value={settings.branding.supportEmail} onChange={(event) => updateBranding("supportEmail", event.target.value)} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Logo URL</Label>
            <Input value={settings.branding.logoUrl ?? ""} onChange={(event) => updateBranding("logoUrl", event.target.value)} placeholder="https://" />
          </div>
        </TabsContent>

        <TabsContent value="auth" className="mt-6 space-y-4">
          <div className="space-y-2">
            <Label>Password policy</Label>
            <Input value={settings.authentication.passwordPolicy} onChange={(event) => updateAuth("passwordPolicy", event.target.value)} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-center justify-between rounded-lg border border-border/60 bg-card/50 p-4">
              <div>
                <p className="text-sm font-medium text-foreground">Require MFA</p>
                <p className="text-xs text-muted-foreground">Enforce multi-factor authentication for admins</p>
              </div>
              <Switch checked={settings.authentication.mfaEnforced} onCheckedChange={(value) => updateAuth("mfaEnforced", value)} />
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border/60 bg-card/50 p-4">
              <div>
                <p className="text-sm font-medium text-foreground">Enable SSO</p>
                <p className="text-xs text-muted-foreground">Allow SAML/OIDC login</p>
              </div>
              <Switch checked={settings.authentication.ssoEnabled} onCheckedChange={(value) => updateAuth("ssoEnabled", value)} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Session timeout (minutes)</Label>
            <Input
              type="number"
              value={settings.authentication.sessionTimeoutMinutes}
              onChange={(event) => updateAuth("sessionTimeoutMinutes", Number(event.target.value))}
              className="w-40"
            />
          </div>
        </TabsContent>

        <TabsContent value="notifications" className="mt-6 space-y-4">
          <div className="flex items-center justify-between rounded-lg border border-border/60 bg-card/50 p-4">
            <div>
              <p className="text-sm font-medium text-foreground">Daily summaries</p>
              <p className="text-xs text-muted-foreground">Operations digest with key metrics</p>
            </div>
            <Switch checked={settings.notifications.dailySummary} onCheckedChange={(value) => updateNotifications("dailySummary", value)} />
          </div>
          <div className="flex items-center justify-between rounded-lg border border-border/60 bg-card/50 p-4">
            <div>
              <p className="text-sm font-medium text-foreground">Weekly insights</p>
              <p className="text-xs text-muted-foreground">Send Monday morning report</p>
            </div>
            <Switch checked={settings.notifications.weeklyInsights} onCheckedChange={(value) => updateNotifications("weeklyInsights", value)} />
          </div>
          <div className="flex items-center justify-between rounded-lg border border-border/60 bg-card/50 p-4">
            <div>
              <p className="text-sm font-medium text-foreground">Critical alerts</p>
              <p className="text-xs text-muted-foreground">Escalate outages to on-call</p>
            </div>
            <Switch checked={settings.notifications.criticalAlerts} onCheckedChange={(value) => updateNotifications("criticalAlerts", value)} />
          </div>
          <div className="space-y-2">
            <Label>Digest email</Label>
            <Input value={settings.notifications.digestEmail} onChange={(event) => updateNotifications("digestEmail", event.target.value)} />
          </div>
        </TabsContent>
      </Tabs>

      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={reset} disabled={!baseline || saving}>
          Reset
        </Button>
        <Button onClick={save} disabled={saving}>
          Save changes
        </Button>
      </div>
    </div>
  );
}

export default SystemSettings;

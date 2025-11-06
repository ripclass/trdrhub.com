import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { FolderLock, Lock, Unlock } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services";
import type { LegalHold } from "@/lib/admin/types";

const service = getAdminService();

export default function LegalHolds() {
  const enabled = isAdminFeatureEnabled("compliance");
  const { toast } = useToast();
  const [holds, setHolds] = React.useState<LegalHold[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [form, setForm] = React.useState({ name: "", owner: "legal@trdrhub.com", affected: "100" });

  React.useEffect(() => {
    if (!enabled) return;
    service
      .listLegalHolds()
      .then((data) => setHolds(data))
      .finally(() => setLoading(false));
  }, [enabled]);

  const createHold = async () => {
    if (!form.name.trim()) {
      toast({ title: "Hold name required", variant: "destructive" });
      return;
    }
    const payload = {
      name: form.name.trim(),
      owner: form.owner,
      affectedObjects: Number(form.affected) || 0,
    };
    const result = await service.createLegalHold(payload);
    if (result.success && result.data) {
      toast({ title: "Legal hold created" });
      setHolds((prev) => [result.data!, ...prev]);
      setDialogOpen(false);
      setForm({ name: "", owner: "legal@trdrhub.com", affected: "100" });
    } else {
      toast({ title: "Creation failed", description: result.message, variant: "destructive" });
    }
  };

  const releaseHold = async (id: string) => {
    setActionId(id);
    const result = await service.releaseLegalHold(id);
    setActionId(null);
    toast({
      title: result.success ? "Hold released" : "Release failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      setHolds((prev) => prev.map((item) => (item.id === id ? { ...item, status: "released", releasedAt: new Date().toISOString() } : item)));
    }
  };

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-rose-500/40 bg-rose-500/5 p-6 text-sm text-rose-600">
        Enable the <strong>compliance</strong> flag to manage legal holds.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Legal holds"
        description="Preserve data for litigation and regulatory investigations."
        actions={
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-2">
                <Lock className="h-4 w-4" /> New legal hold
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create legal hold</DialogTitle>
                <DialogDescription>Prevent data deletion for the specified case.</DialogDescription>
              </DialogHeader>
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Hold name</label>
                  <Input value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} placeholder="Investigation #2025-01" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Owner</label>
                  <Input value={form.owner} onChange={(event) => setForm((prev) => ({ ...prev, owner: event.target.value }))} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Estimated records affected</label>
                  <Input value={form.affected} onChange={(event) => setForm((prev) => ({ ...prev, affected: event.target.value }))} />
                </div>
              </div>
              <DialogFooter>
                <Button onClick={createHold}>Create hold</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      ) : holds.length === 0 ? (
        <AdminEmptyState
          title="No legal holds"
          description="Create a hold to freeze data for ongoing cases."
        />
      ) : (
        holds.map((hold) => (
          <div
            key={hold.id}
            className="flex flex-col gap-4 rounded-lg border border-border/60 bg-card/60 p-4 md:flex-row md:items-center md:justify-between"
          >
            <div className="space-y-1 text-sm">
              <p className="font-medium text-foreground">{hold.name}</p>
              <p className="text-xs text-muted-foreground">Owner: {hold.owner}</p>
              <p className="text-xs text-muted-foreground">Created {new Date(hold.createdAt).toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">Records: {hold.affectedObjects}</p>
              {hold.releasedAt && <p className="text-xs text-muted-foreground">Released {new Date(hold.releasedAt).toLocaleString()}</p>}
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={hold.status === "active" ? "default" : "secondary"}>{hold.status}</Badge>
              {hold.status === "active" ? (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1 text-rose-600"
                  onClick={() => releaseHold(hold.id)}
                  disabled={actionId === hold.id}
                >
                  <Unlock className="h-4 w-4" /> Release
                </Button>
              ) : (
                <span className="text-xs text-muted-foreground">Released</span>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Folder, Plus } from 'lucide-react';

const mockHolds = [
  { id: 'hold-001', case: 'Investigation #2024-05', entity: 'Acme Corp', records: 1234, created: '15 days ago', status: 'active' },
  { id: 'hold-002', case: 'Audit #2024-01', entity: 'Global Trading', records: 567, created: '45 days ago', status: 'active' },
];

export function ComplianceLegalHolds() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Legal Holds</h2>
        <p className="text-muted-foreground">
          Manage legal holds and preservation requests
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Folder className="w-5 h-5" />
            Active Legal Holds
          </CardTitle>
          <CardDescription>Data preservation orders</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            New Hold
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockHolds.map((hold) => (
              <div key={hold.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{hold.case}</p>
                  <p className="text-sm text-muted-foreground">{hold.entity} • {hold.records} records • Created {hold.created}</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="default">{hold.status}</Badge>
                  <Button variant="outline" size="sm">
                    View
                  </Button>
                  <Button variant="outline" size="sm" className="text-destructive">
                    Release
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


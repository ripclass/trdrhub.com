import * as React from "react";

import { AdminEmptyState, AdminToolbar, DataTable } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CreditCard, Plus, Table2, LayoutGrid, Users, DollarSign } from "lucide-react";
import { ColumnDef } from "@tanstack/react-table";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";
import type { BillingPlan } from "@/lib/admin/types";
import { createBillingAggregator } from "@/lib/billing/aggregator";
import { formatCurrencyAmount, type Currency } from "@/lib/billing/fx";

const service = getAdminService();

type ViewMode = "grid" | "table";

export function BillingPlans() {
  const enabled = isAdminFeatureEnabled("billing");
  const { toast } = useToast();
  const audit = useAdminAudit("billing-plans");
  const [plans, setPlans] = React.useState<BillingPlan[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [updatingId, setUpdatingId] = React.useState<string | null>(null);
  const [editingPlan, setEditingPlan] = React.useState<BillingPlan | null>(null);
  const [viewMode, setViewMode] = React.useState<ViewMode>("grid");
  const [planMetrics, setPlanMetrics] = React.useState<Map<string, { subscribers: number; mrr: number }>>(new Map());

  React.useEffect(() => {
    if (!enabled) return;
    service
      .listBillingPlans()
      .then((data) => {
        setPlans(data);
        // Fetch plan metrics from aggregator
        loadPlanMetrics(data);
      })
      .finally(() => setLoading(false));
  }, [enabled]);

  const loadPlanMetrics = async (plansList: BillingPlan[]) => {
    try {
      const aggregator = createBillingAggregator("USD");
      const subscriptions = await aggregator.listSubscriptions();
      
      const metrics = new Map<string, { subscribers: number; mrr: number }>();
      for (const plan of plansList) {
        const planSubs = subscriptions.items.filter(
          (sub) => sub.planName === plan.name && sub.status === "active"
        );
        const mrr = planSubs.reduce((sum, sub) => sum + sub.pricePerPeriod, 0);
        metrics.set(plan.id, {
          subscribers: planSubs.length,
          mrr,
        });
      }
      setPlanMetrics(metrics);
    } catch (error) {
      console.warn("Failed to load plan metrics", error);
    }
  };

  const handleEditPlan = async (plan: BillingPlan) => {
    setEditingPlan(plan);
  };

  const handleSavePlan = async () => {
    if (!editingPlan) return;

    const priceInput = document.getElementById("edit-price") as HTMLInputElement;
    const statusInput = document.getElementById("edit-status") as HTMLSelectElement;

    if (!priceInput || !statusInput) return;

    const price = Number(priceInput.value);
    if (Number.isNaN(price) || price < 0) {
      toast({ title: "Invalid price", description: "Enter a non-negative number", variant: "destructive" });
      return;
    }

    setUpdatingId(editingPlan.id);
    const result = await service.updateBillingPlan(editingPlan.id, {
      pricePerMonth: Math.round(price * 100),
      status: statusInput.value as BillingPlan["status"],
    });
    setUpdatingId(null);

    if (!result.success || !result.data) {
      toast({ title: "Plan update failed", description: result.message ?? "Unexpected error", variant: "destructive" });
      return;
    }

    const updatedPlan = result.data;
    setPlans((prev) => prev.map((item) => (item.id === editingPlan.id ? updatedPlan : item)));
    setEditingPlan(null);
    toast({ title: "Plan updated", description: `${updatedPlan.name} updated successfully` });
    await audit("update_plan", { entityId: editingPlan.id, metadata: { pricePerMonth: updatedPlan.pricePerMonth, status: updatedPlan.status } });
  };

  const tableColumns: ColumnDef<BillingPlan>[] = React.useMemo(
    () => [
      {
        accessorKey: "name",
        header: "Plan Name",
        cell: ({ row }) => (
          <div>
            <div className="font-medium">{row.original.name}</div>
            <div className="text-xs text-muted-foreground capitalize">{row.original.tier}</div>
          </div>
        ),
      },
      {
        accessorKey: "pricePerMonth",
        header: "Price",
        cell: ({ row }) => (
          <div className="font-medium">
            {formatCurrencyAmount(row.original.pricePerMonth, row.original.currency as Currency)}
            <span className="text-xs text-muted-foreground">/mo</span>
          </div>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <Badge variant={row.original.status === "active" ? "outline" : "secondary"}>
            {row.original.status}
          </Badge>
        ),
      },
      {
        id: "metrics",
        header: "Subscribers",
        cell: ({ row }) => {
          const metrics = planMetrics.get(row.original.id);
          return (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1 text-sm">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span>{metrics?.subscribers ?? 0}</span>
              </div>
              <div className="flex items-center gap-1 text-sm">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                <span>{metrics?.mrr ? formatCurrencyAmount(metrics.mrr, "USD") : "-"}</span>
              </div>
            </div>
          );
        },
      },
      {
        accessorKey: "features",
        header: "Features",
        cell: ({ row }) => (
          <div className="text-sm text-muted-foreground">{row.original.features.length} features</div>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleEditPlan(row.original)}
            disabled={updatingId === row.original.id}
          >
            <CreditCard className="mr-2 h-4 w-4" /> Edit
          </Button>
        ),
      },
    ],
    [planMetrics, updatingId]
  );

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
        actions={
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 rounded-lg border border-border/60 bg-background p-1">
              <Button
                variant={viewMode === "grid" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("grid")}
                className="h-8"
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === "table" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("table")}
                className="h-8"
              >
                <Table2 className="h-4 w-4" />
              </Button>
            </div>
            <Button variant="default" size="sm" className="gap-2">
              <Plus className="h-4 w-4" />
              Create Plan
            </Button>
          </div>
        }
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
          action={
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Create First Plan
            </Button>
          }
        />
      ) : viewMode === "table" ? (
        <DataTable columns={tableColumns} data={plans} />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {plans.map((plan) => {
            const metrics = planMetrics.get(plan.id);
            return (
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
                  {metrics && (
                    <div className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-sm">
                      <div className="flex items-center gap-1">
                        <Users className="h-4 w-4 text-muted-foreground" />
                        <span>{metrics.subscribers} subscribers</span>
                      </div>
                      <div className="flex items-center gap-1 font-medium">
                        <DollarSign className="h-4 w-4" />
                        <span>{formatCurrencyAmount(metrics.mrr, "USD")}/mo MRR</span>
                      </div>
                    </div>
                  )}
                  <div className="space-y-1 text-sm text-muted-foreground">
                    <p className="font-medium text-foreground">Included features</p>
                    <ul className="space-y-1 text-xs">
                      {plan.features.slice(0, 3).map((feature) => (
                        <li key={feature} className="flex items-center gap-2">
                          <span className="text-emerald-500">•</span> {feature}
                        </li>
                      ))}
                      {plan.features.length > 3 && (
                        <li className="text-xs text-muted-foreground">+{plan.features.length - 3} more</li>
                      )}
                    </ul>
                  </div>
                  <div className="space-y-1 text-xs text-muted-foreground">
                    <p className="font-medium text-foreground">Usage limits</p>
                    {Object.entries(plan.limits).slice(0, 2).map(([limit, value]) => (
                      <p key={limit}>
                        {limit}: {value as string | number}
                      </p>
                    ))}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => handleEditPlan(plan)}
                    disabled={updatingId === plan.id}
                  >
                    <CreditCard className="mr-2 h-4 w-4" /> Edit plan
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Edit Plan Dialog */}
      <Dialog open={editingPlan !== null} onOpenChange={(open) => !open && setEditingPlan(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Plan: {editingPlan?.name}</DialogTitle>
            <DialogDescription>Update plan pricing and status.</DialogDescription>
          </DialogHeader>
          {editingPlan && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit-price">Monthly Price ({editingPlan.currency})</Label>
                <Input
                  id="edit-price"
                  type="number"
                  min="0"
                  step="0.01"
                  defaultValue={Math.round(editingPlan.pricePerMonth / 100)}
                  placeholder="Enter monthly price"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-status">Status</Label>
                <Select defaultValue={editingPlan.status} id="edit-status">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="deprecated">Deprecated</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Plan Details</Label>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-sm">
                  <div className="space-y-1">
                    <p className="font-medium">Tier: {editingPlan.tier}</p>
                    <p className="text-muted-foreground">{editingPlan.features.length} features included</p>
                  </div>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingPlan(null)}>
              Cancel
            </Button>
            <Button onClick={handleSavePlan} disabled={updatingId !== null}>
              {updatingId ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default BillingPlans;

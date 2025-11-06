import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminEmptyState, AdminToolbar, DataTable } from "@/components/admin/ui";
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
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { DollarSign, Plus } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services";
import type { BillingAdjustment } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const PAGE_SIZE = 10;

export default function Adjustments() {
  const enabled = isAdminFeatureEnabled("billing");
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const audit = useAdminAudit("billing-adjustments");
  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("adjustmentsPage") ?? "1")));
  const [adjustments, setAdjustments] = React.useState<BillingAdjustment[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);

  const [createOpen, setCreateOpen] = React.useState(false);
  const [form, setForm] = React.useState({ customer: "", amount: "", reason: "", currency: "USD", type: "credit" as "credit" | "charge" });

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadAdjustments = React.useCallback(() => {
    if (!enabled) return;
    setLoading(true);
    service
      .listBillingAdjustments({ page, pageSize: PAGE_SIZE })
      .then((result) => {
        setAdjustments(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [enabled, page]);

  const updateQuery = React.useCallback(() => {
    const next = new URLSearchParams(searchParams);
    if (page === 1) next.delete("adjustmentsPage");
    else next.set("adjustmentsPage", String(page));
    setSearchParams(next, { replace: true });
  }, [page, searchParams, setSearchParams]);

  React.useEffect(() => {
    updateQuery();
    loadAdjustments();
  }, [updateQuery, loadAdjustments]);

  const handleCreate = async () => {
    const amount = Number(form.amount);
    if (!form.customer || Number.isNaN(amount)) {
      toast({ title: "Customer and amount required", variant: "destructive" });
      return;
    }
    const payload: BillingAdjustment = {
      id: "temp",
      customer: form.customer,
      amount: form.type === "credit" ? -Math.abs(amount * 100) : Math.abs(amount * 100),
      currency: form.currency,
      reason: form.reason || "Manual adjustment",
      createdAt: new Date().toISOString(),
      createdBy: "billing@trdrhub.com",
      status: "pending",
    };
    const result = await service.addBillingAdjustment(payload);
    if (result.success) {
      toast({ title: "Adjustment recorded" });
      setCreateOpen(false);
      setForm({ customer: "", amount: "", reason: "", currency: "USD", type: "credit" });
      loadAdjustments();
      await audit("create_adjustment", { metadata: { customer: form.customer, amount: payload.amount } });
    } else {
      toast({ title: "Failed to add adjustment", description: result.message, variant: "destructive" });
    }
  };

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-amber-500/40 bg-amber-500/5 p-6 text-sm text-amber-600">
        Enable the <strong>billing</strong> feature flag to manage manual adjustments.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Manual billing adjustments"
        description="Track credits and charges applied outside automated invoicing."
        actions={
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-2">
                <Plus className="h-4 w-4" /> New adjustment
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create adjustment</DialogTitle>
                <DialogDescription>Credit or charge a customer account.</DialogDescription>
              </DialogHeader>
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Customer</label>
                  <Input value={form.customer} onChange={(event) => setForm((prev) => ({ ...prev, customer: event.target.value }))} placeholder="Acme Corp" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Type</label>
                    <Select value={form.type} onValueChange={(value) => setForm((prev) => ({ ...prev, type: value as "credit" | "charge" }))}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="credit">Credit</SelectItem>
                        <SelectItem value="charge">Charge</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Currency</label>
                    <Select value={form.currency} onValueChange={(value) => setForm((prev) => ({ ...prev, currency: value }))}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="USD">USD</SelectItem>
                        <SelectItem value="EUR">EUR</SelectItem>
                        <SelectItem value="AED">AED</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Amount</label>
                  <Input value={form.amount} onChange={(event) => setForm((prev) => ({ ...prev, amount: event.target.value }))} placeholder="500" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Reason</label>
                  <Input value={form.reason} onChange={(event) => setForm((prev) => ({ ...prev, reason: event.target.value }))} placeholder="Service credit for downtime" />
                </div>
              </div>
              <DialogFooter>
                <Button onClick={handleCreate}>Submit</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      <DataTable
        columns={[
          {
            key: "customer",
            header: "Customer",
            render: (adjustment) => (
              <div className="space-y-1 text-sm">
                <p className="font-medium text-foreground">{adjustment.customer}</p>
                <p className="text-xs text-muted-foreground">Recorded {new Date(adjustment.createdAt).toLocaleString()}</p>
              </div>
            ),
          },
          {
            key: "amount",
            header: "Amount",
            render: (adjustment) => (
              <span className={`text-sm font-semibold ${adjustment.amount < 0 ? "text-emerald-600" : "text-rose-600"}`}>
                {adjustment.amount < 0 ? "-" : "+"}
                {adjustment.currency} {Math.abs(adjustment.amount / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
            ),
          },
          {
            key: "reason",
            header: "Reason",
            render: (adjustment) => <span className="text-sm text-muted-foreground">{adjustment.reason}</span>,
          },
          {
            key: "status",
            header: "Status",
            render: (adjustment) => (
              <Badge variant={adjustment.status === "posted" ? "default" : adjustment.status === "pending" ? "secondary" : "outline"}>
                {adjustment.status}
              </Badge>
            ),
          },
        ]}
        data={adjustments}
        loading={loading}
        emptyState={<AdminEmptyState title="No adjustments" description="No manual billing changes recorded." />}
        footer={
          total > PAGE_SIZE && (
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    className={page === 1 ? "pointer-events-none opacity-50" : undefined}
                    onClick={(event) => {
                      event.preventDefault();
                      if (page > 1) setPage(page - 1);
                    }}
                  />
                </PaginationItem>
                <PaginationItem>
                  <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
                </PaginationItem>
                <PaginationItem>
                  <PaginationNext
                    href="#"
                    className={page >= totalPages ? "pointer-events-none opacity-50" : undefined}
                    onClick={(event) => {
                      event.preventDefault();
                      if (page < totalPages) setPage(page + 1);
                    }}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          )
        }
      />

      {loading && adjustments.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      )}
    </div>
  );
}
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { DollarSign, Plus } from 'lucide-react';

const mockAdjustments = [
  { id: 'adj-001', company: 'Acme Corp', type: 'credit', amount: '$500', reason: 'Service disruption compensation', date: '2 days ago', status: 'applied' },
  { id: 'adj-002', company: 'Tech Solutions', type: 'charge', amount: '$200', reason: 'Additional API usage', date: '5 days ago', status: 'applied' },
  { id: 'adj-003', company: 'Global Trading', type: 'credit', amount: '$1,000', reason: 'Annual discount', date: '1 week ago', status: 'pending' },
];

export function BillingAdjustments() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Billing Adjustments</h2>
        <p className="text-muted-foreground">
          Manage credits, refunds, and manual billing adjustments
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="w-5 h-5" />
            Recent Adjustments
          </CardTitle>
          <CardDescription>Manual billing modifications and credits</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            New Adjustment
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockAdjustments.map((adjustment) => (
              <div key={adjustment.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{adjustment.company}</p>
                  <p className="text-sm text-muted-foreground mb-2">{adjustment.reason}</p>
                  <span className="text-xs text-muted-foreground">{adjustment.date}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={adjustment.type === 'credit' ? 'default' : 'secondary'}>
                    {adjustment.type}
                  </Badge>
                  <p className={`text-lg font-semibold ${adjustment.type === 'credit' ? 'text-success' : 'text-foreground'}`}>
                    {adjustment.type === 'credit' ? '-' : '+'}{adjustment.amount}
                  </p>
                  <Badge variant={adjustment.status === 'applied' ? 'default' : 'outline'}>
                    {adjustment.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}


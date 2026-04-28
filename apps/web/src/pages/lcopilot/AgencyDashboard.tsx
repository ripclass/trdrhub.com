/**
 * AgencyDashboard — Phase A5 rebuild.
 *
 * Real dashboard for sourcing/buying agents:
 *   - Dashboard view: KPI strip + recent activity table
 *   - Suppliers: list + CRUD + detail panel
 *   - Foreign Buyers: list + CRUD
 *
 * Behind isAgencyRealEnabled() — when off, falls through to a brief
 * stub. Bulk Inbox / Discrepancies / Reports / Active LCs land in
 * A6 + A7.
 */

import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  FileCheck,
  Globe2,
  LayoutDashboard,
  Pencil,
  Plus,
  Trash2,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { WorkspaceSwitcher } from "@/components/lcopilot/WorkspaceSwitcher";
import { isAgencyRealEnabled } from "@/lib/lcopilot/featureFlags";
import {
  createBuyer,
  createSupplier,
  deleteBuyer,
  deleteSupplier,
  getPortfolio,
  listBuyers,
  listSuppliers,
  updateBuyer,
  updateSupplier,
  type ForeignBuyer,
  type ForeignBuyerInput,
  type Supplier,
  type SupplierInput,
} from "@/lib/lcopilot/agencyApi";

type Section = "dashboard" | "suppliers" | "buyers";

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

function AgencySidebar({
  active,
  onChange,
  supplierCount,
  buyerCount,
}: {
  active: Section;
  onChange: (s: Section) => void;
  supplierCount: number;
  buyerCount: number;
}) {
  const items: Array<{
    key: Section;
    label: string;
    Icon: typeof LayoutDashboard;
    count?: number;
  }> = [
    { key: "dashboard", label: "Dashboard", Icon: LayoutDashboard },
    { key: "suppliers", label: "Suppliers", Icon: Building2, count: supplierCount },
    { key: "buyers", label: "Foreign Buyers", Icon: Globe2, count: buyerCount },
  ];
  return (
    <nav className="space-y-1 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground px-2 mb-2">
        Agency
      </p>
      {items.map(({ key, label, Icon, count }) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key)}
          className={`flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm transition-colors ${
            active === key
              ? "bg-neutral-200/70 dark:bg-neutral-800 text-foreground"
              : "text-muted-foreground hover:bg-neutral-100 dark:hover:bg-neutral-800/40 hover:text-foreground"
          }`}
        >
          <span className="flex items-center gap-2">
            <Icon className="w-4 h-4" />
            {label}
          </span>
          {count != null && (
            <span className="text-[10px] tabular-nums text-muted-foreground">
              {count}
            </span>
          )}
        </button>
      ))}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Dashboard panel
// ---------------------------------------------------------------------------

function KpiCard({
  label,
  value,
  Icon,
}: {
  label: string;
  value: number;
  Icon: typeof Building2;
}) {
  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
        <CardDescription>{label}</CardDescription>
        <Icon className="w-4 h-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <CardTitle className="text-3xl tabular-nums">{value}</CardTitle>
      </CardContent>
    </Card>
  );
}

function DashboardPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ["agency", "portfolio"],
    queryFn: getPortfolio,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-muted-foreground">
          Loading…
        </CardContent>
      </Card>
    );
  }
  if (!data) return null;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-4">
        <KpiCard label="Suppliers" value={data.supplier_count} Icon={Building2} />
        <KpiCard
          label="Foreign buyers"
          value={data.foreign_buyer_count}
          Icon={Globe2}
        />
        <KpiCard label="Active LCs" value={data.active_lc_count} Icon={Users} />
        <KpiCard
          label="Open discrepancies"
          value={data.open_discrepancy_count}
          Icon={Pencil}
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Recent activity</CardTitle>
          <CardDescription>
            Latest 10 validations across all suppliers ·{" "}
            {data.completed_this_month} completed this month
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.recent_activity.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No validations yet. Add a supplier and run an LC.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground">
                <tr>
                  <th className="pb-2 font-medium">Supplier</th>
                  <th className="pb-2 font-medium">Lifecycle</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_activity.map((row) => (
                  <tr
                    key={row.validation_session_id}
                    className="border-t border-border"
                  >
                    <td className="py-2">
                      {row.supplier_name ?? (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="py-2 text-muted-foreground">
                      {row.lifecycle_state ?? "—"}
                    </td>
                    <td className="py-2">{row.status}</td>
                    <td className="py-2 text-muted-foreground">
                      {new Date(row.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Supplier panel
// ---------------------------------------------------------------------------

function SupplierForm({
  initial,
  onSubmit,
  onCancel,
  submitting,
  buyers,
}: {
  initial?: Partial<SupplierInput>;
  onSubmit: (v: SupplierInput) => void;
  onCancel: () => void;
  submitting: boolean;
  buyers: ForeignBuyer[];
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [country, setCountry] = useState(initial?.country ?? "");
  const [contactName, setContactName] = useState(initial?.contact_name ?? "");
  const [contactEmail, setContactEmail] = useState(initial?.contact_email ?? "");
  const [contactPhone, setContactPhone] = useState(initial?.contact_phone ?? "");
  const [factoryAddress, setFactoryAddress] = useState(
    initial?.factory_address ?? "",
  );
  const [foreignBuyerId, setForeignBuyerId] = useState<string>(
    initial?.foreign_buyer_id ?? "",
  );
  const [notes, setNotes] = useState(initial?.notes ?? "");

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2 space-y-1">
        <Label htmlFor="sup-name">Supplier name</Label>
        <Input
          id="sup-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="sup-country">Country (ISO 2)</Label>
        <Input
          id="sup-country"
          maxLength={2}
          value={country ?? ""}
          onChange={(e) => setCountry(e.target.value.toUpperCase())}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="sup-buyer">Default foreign buyer</Label>
        <select
          id="sup-buyer"
          value={foreignBuyerId}
          onChange={(e) => setForeignBuyerId(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">— None —</option>
          {buyers.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1">
        <Label htmlFor="sup-cname">Contact name</Label>
        <Input
          id="sup-cname"
          value={contactName ?? ""}
          onChange={(e) => setContactName(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="sup-cemail">Contact email</Label>
        <Input
          id="sup-cemail"
          type="email"
          value={contactEmail ?? ""}
          onChange={(e) => setContactEmail(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="sup-cphone">Contact phone</Label>
        <Input
          id="sup-cphone"
          value={contactPhone ?? ""}
          onChange={(e) => setContactPhone(e.target.value)}
        />
      </div>
      <div className="sm:col-span-2 space-y-1">
        <Label htmlFor="sup-addr">Factory address</Label>
        <textarea
          id="sup-addr"
          rows={2}
          value={factoryAddress ?? ""}
          onChange={(e) => setFactoryAddress(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        />
      </div>
      <div className="sm:col-span-2 space-y-1">
        <Label htmlFor="sup-notes">Notes</Label>
        <textarea
          id="sup-notes"
          rows={2}
          value={notes ?? ""}
          onChange={(e) => setNotes(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        />
      </div>
      <DialogFooter className="sm:col-span-2">
        <Button variant="ghost" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button
          disabled={submitting || !name.trim()}
          onClick={() =>
            onSubmit({
              name: name.trim(),
              country: country?.trim() || null,
              contact_name: contactName?.trim() || null,
              contact_email: contactEmail?.trim() || null,
              contact_phone: contactPhone?.trim() || null,
              factory_address: factoryAddress?.trim() || null,
              foreign_buyer_id: foreignBuyerId || null,
              notes: notes?.trim() || null,
            })
          }
        >
          {submitting ? "Saving…" : "Save"}
        </Button>
      </DialogFooter>
    </div>
  );
}

function SupplierPanel({ buyers }: { buyers: ForeignBuyer[] }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: suppliers = [], isLoading } = useQuery({
    queryKey: ["agency", "suppliers"],
    queryFn: listSuppliers,
  });
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [selected, setSelected] = useState<Supplier | null>(null);
  const [error, setError] = useState<string | null>(null);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["agency"] });
  };

  const createMutation = useMutation({
    mutationFn: createSupplier,
    onSuccess: () => {
      invalidate();
      setCreateOpen(false);
    },
    onError: (err: Error) => setError(err.message ?? "Failed to create"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<SupplierInput> }) =>
      updateSupplier(id, patch),
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
    onError: (err: Error) => setError(err.message ?? "Failed to update"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSupplier,
    onSuccess: () => {
      invalidate();
      setSelected(null);
    },
    onError: (err: Error) => setError(err.message ?? "Failed to delete"),
  });

  const buyersById = useMemo(
    () => Object.fromEntries(buyers.map((b) => [b.id, b])),
    [buyers],
  );

  const submitting =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Suppliers</h2>
          <p className="text-sm text-muted-foreground">
            Domestic factories you source from for foreign buyers.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="w-4 h-4 mr-1" />
          New supplier
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      {isLoading ? (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            Loading…
          </CardContent>
        </Card>
      ) : suppliers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Building2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">
              No suppliers yet. Add your first to start tracking LCs.
            </p>
            <Button className="mt-4" onClick={() => setCreateOpen(true)}>
              <Plus className="w-4 h-4 mr-1" />
              Add supplier
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground border-b">
                <tr>
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Country</th>
                  <th className="px-4 py-3 font-medium">Default buyer</th>
                  <th className="px-4 py-3 font-medium tabular-nums">
                    Active LCs
                  </th>
                  <th className="px-4 py-3 font-medium tabular-nums">Open</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {suppliers.map((s) => (
                  <tr
                    key={s.id}
                    className={`border-t border-border ${
                      selected?.id === s.id
                        ? "bg-neutral-50 dark:bg-neutral-800/50"
                        : ""
                    }`}
                  >
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => setSelected(s)}
                        className="hover:underline"
                      >
                        {s.name}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {s.country ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {s.foreign_buyer_id
                        ? buyersById[s.foreign_buyer_id]?.name ?? "—"
                        : "—"}
                    </td>
                    <td className="px-4 py-3 tabular-nums">{s.active_lc_count}</td>
                    <td className="px-4 py-3 tabular-nums">
                      {s.open_discrepancy_count}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setEditing(s)}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={submitting}
                        onClick={() => {
                          if (
                            confirm(
                              `Delete ${s.name}? Their past LCs will stay un-attributed.`,
                            )
                          ) {
                            deleteMutation.mutate(s.id);
                          }
                        }}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {selected && (
        <Card>
          <CardHeader>
            <CardTitle>{selected.name}</CardTitle>
            <CardDescription>
              {selected.country ?? "Unknown country"} ·{" "}
              {selected.contact_email ?? "no contact"}
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            <p>
              <span className="text-muted-foreground">Address:</span>{" "}
              {selected.factory_address ?? "—"}
            </p>
            <p>
              <span className="text-muted-foreground">Contact:</span>{" "}
              {selected.contact_name ?? "—"} · {selected.contact_phone ?? "—"}
            </p>
            <p>
              <span className="text-muted-foreground">Default buyer:</span>{" "}
              {selected.foreign_buyer_id
                ? buyersById[selected.foreign_buyer_id]?.name ?? "—"
                : "—"}
            </p>
            {selected.notes && (
              <p className="text-muted-foreground italic">{selected.notes}</p>
            )}
            <p>
              <span className="text-muted-foreground">Active LCs:</span>{" "}
              {selected.active_lc_count} ·{" "}
              <span className="text-muted-foreground">Open discrepancies:</span>{" "}
              {selected.open_discrepancy_count}
            </p>
            <div className="flex gap-2 pt-2">
              <Button
                size="sm"
                onClick={() =>
                  navigate(
                    `/lcopilot/upload-lc?supplier_id=${encodeURIComponent(selected.id)}`,
                  )
                }
              >
                <FileCheck className="w-3.5 h-3.5 mr-1" />
                Validate LC for this supplier
              </Button>
              <Button variant="outline" size="sm" onClick={() => setEditing(selected)}>
                <Pencil className="w-3.5 h-3.5 mr-1" />
                Edit
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setSelected(null)}>
                Close
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>New supplier</DialogTitle>
            <DialogDescription>
              Track a domestic factory you source from for one or more foreign
              buyers.
            </DialogDescription>
          </DialogHeader>
          <SupplierForm
            buyers={buyers}
            onCancel={() => setCreateOpen(false)}
            submitting={submitting}
            onSubmit={(v) => createMutation.mutate(v)}
          />
        </DialogContent>
      </Dialog>

      <Dialog
        open={editing !== null}
        onOpenChange={(o) => !o && setEditing(null)}
      >
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit supplier</DialogTitle>
            <DialogDescription>{editing?.name}</DialogDescription>
          </DialogHeader>
          {editing && (
            <SupplierForm
              buyers={buyers}
              initial={editing}
              onCancel={() => setEditing(null)}
              submitting={submitting}
              onSubmit={(v) =>
                updateMutation.mutate({ id: editing.id, patch: v })
              }
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Foreign buyer panel
// ---------------------------------------------------------------------------

function BuyerForm({
  initial,
  onSubmit,
  onCancel,
  submitting,
}: {
  initial?: Partial<ForeignBuyerInput>;
  onSubmit: (v: ForeignBuyerInput) => void;
  onCancel: () => void;
  submitting: boolean;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [country, setCountry] = useState(initial?.country ?? "");
  const [contactName, setContactName] = useState(initial?.contact_name ?? "");
  const [contactEmail, setContactEmail] = useState(initial?.contact_email ?? "");
  const [contactPhone, setContactPhone] = useState(initial?.contact_phone ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2 space-y-1">
        <Label htmlFor="bu-name">Buyer name</Label>
        <Input
          id="bu-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="bu-country">Country (ISO 2)</Label>
        <Input
          id="bu-country"
          maxLength={2}
          value={country ?? ""}
          onChange={(e) => setCountry(e.target.value.toUpperCase())}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="bu-cname">Contact name</Label>
        <Input
          id="bu-cname"
          value={contactName ?? ""}
          onChange={(e) => setContactName(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="bu-cemail">Contact email</Label>
        <Input
          id="bu-cemail"
          type="email"
          value={contactEmail ?? ""}
          onChange={(e) => setContactEmail(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="bu-cphone">Contact phone</Label>
        <Input
          id="bu-cphone"
          value={contactPhone ?? ""}
          onChange={(e) => setContactPhone(e.target.value)}
        />
      </div>
      <div className="sm:col-span-2 space-y-1">
        <Label htmlFor="bu-notes">Notes</Label>
        <textarea
          id="bu-notes"
          rows={2}
          value={notes ?? ""}
          onChange={(e) => setNotes(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        />
      </div>
      <DialogFooter className="sm:col-span-2">
        <Button variant="ghost" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button
          disabled={submitting || !name.trim()}
          onClick={() =>
            onSubmit({
              name: name.trim(),
              country: country?.trim() || null,
              contact_name: contactName?.trim() || null,
              contact_email: contactEmail?.trim() || null,
              contact_phone: contactPhone?.trim() || null,
              notes: notes?.trim() || null,
            })
          }
        >
          {submitting ? "Saving…" : "Save"}
        </Button>
      </DialogFooter>
    </div>
  );
}

function BuyerPanel() {
  const queryClient = useQueryClient();
  const { data: buyers = [], isLoading } = useQuery({
    queryKey: ["agency", "buyers"],
    queryFn: listBuyers,
  });
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<ForeignBuyer | null>(null);
  const [error, setError] = useState<string | null>(null);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["agency"] });
  };

  const createMutation = useMutation({
    mutationFn: createBuyer,
    onSuccess: () => {
      invalidate();
      setCreateOpen(false);
    },
    onError: (err: Error) => setError(err.message ?? "Failed to create"),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      patch,
    }: {
      id: string;
      patch: Partial<ForeignBuyerInput>;
    }) => updateBuyer(id, patch),
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
    onError: (err: Error) => setError(err.message ?? "Failed to update"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBuyer,
    onSuccess: () => invalidate(),
    onError: (err: Error) => setError(err.message ?? "Failed to delete"),
  });

  const submitting =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Foreign buyers</h2>
          <p className="text-sm text-muted-foreground">
            Overseas counterparties LCs are issued for.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="w-4 h-4 mr-1" />
          New buyer
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      {isLoading ? (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            Loading…
          </CardContent>
        </Card>
      ) : buyers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Globe2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No foreign buyers yet.</p>
            <Button className="mt-4" onClick={() => setCreateOpen(true)}>
              <Plus className="w-4 h-4 mr-1" />
              Add buyer
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground border-b">
                <tr>
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Country</th>
                  <th className="px-4 py-3 font-medium">Contact</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {buyers.map((b) => (
                  <tr key={b.id} className="border-t border-border">
                    <td className="px-4 py-3">{b.name}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {b.country ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {b.contact_email ?? b.contact_name ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setEditing(b)}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={submitting}
                        onClick={() => {
                          if (confirm(`Delete ${b.name}?`)) {
                            deleteMutation.mutate(b.id);
                          }
                        }}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>New foreign buyer</DialogTitle>
            <DialogDescription>
              The international counterparty an LC is issued for.
            </DialogDescription>
          </DialogHeader>
          <BuyerForm
            onCancel={() => setCreateOpen(false)}
            submitting={submitting}
            onSubmit={(v) => createMutation.mutate(v)}
          />
        </DialogContent>
      </Dialog>

      <Dialog
        open={editing !== null}
        onOpenChange={(o) => !o && setEditing(null)}
      >
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit buyer</DialogTitle>
            <DialogDescription>{editing?.name}</DialogDescription>
          </DialogHeader>
          {editing && (
            <BuyerForm
              initial={editing}
              onCancel={() => setEditing(null)}
              submitting={submitting}
              onSubmit={(v) =>
                updateMutation.mutate({ id: editing.id, patch: v })
              }
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Legacy stub (when flag is off)
// ---------------------------------------------------------------------------

function LegacyAgencyStub() {
  return (
    <div className="space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold">Agency Workspace</h1>
        <p className="text-muted-foreground">
          The full agency build is gated behind VITE_LCOPILOT_AGENCY_REAL.
          Enable it in apps/web/.env to use the rebuilt dashboard.
        </p>
      </header>
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Coming soon.</p>
          <Button asChild className="mt-4">
            <Link to="/lcopilot">Back to LCopilot</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Top-level page
// ---------------------------------------------------------------------------

export default function AgencyDashboard() {
  const enabled = isAgencyRealEnabled();
  const [section, setSection] = useState<Section>("dashboard");

  // Buyers are read at the top level so the supplier form can use them
  // for the default-buyer dropdown without a separate query in the form.
  const { data: buyers = [] } = useQuery({
    queryKey: ["agency", "buyers"],
    queryFn: listBuyers,
    enabled,
  });
  const { data: portfolio } = useQuery({
    queryKey: ["agency", "portfolio"],
    queryFn: getPortfolio,
    enabled,
  });

  if (!enabled) {
    return (
      <DashboardLayout
        sidebar={null}
        breadcrumbs={[
          { label: "LCopilot", href: "/lcopilot" },
          { label: "Agency" },
        ]}
        workspaceSwitcher={<WorkspaceSwitcher />}
      >
        <LegacyAgencyStub />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      sidebar={
        <AgencySidebar
          active={section}
          onChange={setSection}
          supplierCount={portfolio?.supplier_count ?? 0}
          buyerCount={portfolio?.foreign_buyer_count ?? 0}
        />
      }
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Agency" },
      ]}
      workspaceSwitcher={<WorkspaceSwitcher />}
    >
      <div className="container mx-auto p-6">
        {section === "dashboard" && <DashboardPanel />}
        {section === "suppliers" && <SupplierPanel buyers={buyers} />}
        {section === "buyers" && <BuyerPanel />}
      </div>
    </DashboardLayout>
  );
}

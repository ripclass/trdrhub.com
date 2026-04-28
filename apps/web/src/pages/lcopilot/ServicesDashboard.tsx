/**
 * ServicesDashboard — Phases A8 + A9.
 *
 * Mirrors the agency dashboard shape. Sections: Dashboard, Clients,
 * Time, Invoice. Behind isServicesRealEnabled() — when off, the page
 * renders a brief stub with an enable-flag hint.
 */

import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart3,
  Briefcase,
  Clock,
  Download,
  FileCheck,
  FileText,
  LayoutDashboard,
  Loader2,
  Pencil,
  Plus,
  Receipt,
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
import { Switch } from "@/components/ui/switch";
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
import { isServicesRealEnabled } from "@/lib/lcopilot/featureFlags";
import {
  createServicesClient,
  createTimeEntry,
  deleteServicesClient,
  deleteTimeEntry,
  downloadInvoicePdf,
  generateInvoicePreview,
  getServicesPortfolio,
  listServicesClients,
  listTimeEntries,
  updateServicesClient,
  type InvoicePreview,
  type ServicesClient,
  type ServicesClientInput,
  type TimeEntry,
  type TimeEntryInput,
} from "@/lib/lcopilot/servicesApi";

type Section = "dashboard" | "clients" | "time" | "invoice";

function num(v: number | string | null | undefined): number {
  if (v == null || v === "") return 0;
  const n = typeof v === "number" ? v : parseFloat(v);
  return Number.isFinite(n) ? n : 0;
}

function formatHours(v: number | string | null | undefined): string {
  return num(v).toFixed(2);
}

function formatMoney(v: number | string | null | undefined): string {
  return num(v).toFixed(2);
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

function ServicesSidebar({
  active,
  onChange,
  clientCount,
}: {
  active: Section;
  onChange: (s: Section) => void;
  clientCount: number;
}) {
  const items: Array<{
    key: Section;
    label: string;
    Icon: typeof LayoutDashboard;
    count?: number;
  }> = [
    { key: "dashboard", label: "Dashboard", Icon: LayoutDashboard },
    { key: "clients", label: "Clients", Icon: Briefcase, count: clientCount },
    { key: "time", label: "Time", Icon: Clock },
    { key: "invoice", label: "Invoice", Icon: Receipt },
  ];
  return (
    <nav className="space-y-1 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground px-2 mb-2">
        Services
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
  value: string | number;
  Icon: typeof Users;
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
    queryKey: ["services", "portfolio"],
    queryFn: getServicesPortfolio,
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
        <KpiCard label="Clients" value={data.client_count} Icon={Briefcase} />
        <KpiCard label="Active LCs" value={data.active_lc_count} Icon={Users} />
        <KpiCard
          label="Open discrepancies"
          value={data.open_discrepancy_count}
          Icon={Pencil}
        />
        <KpiCard
          label="Hours this month"
          value={formatHours(data.hours_this_month)}
          Icon={Clock}
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Recent activity</CardTitle>
          <CardDescription>
            Latest 10 validations across all clients ·{" "}
            {data.completed_this_month} completed this month ·{" "}
            {formatHours(data.billable_hours_unbilled)} billable hours unbilled
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.recent_activity.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No validations yet. Add a client and run an LC.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground">
                <tr>
                  <th className="pb-2 font-medium">Client</th>
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
                      {row.client_name ?? (
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
// Client form + panel
// ---------------------------------------------------------------------------

function ClientForm({
  initial,
  onSubmit,
  onCancel,
  submitting,
}: {
  initial?: Partial<ServicesClientInput>;
  onSubmit: (v: ServicesClientInput) => void;
  onCancel: () => void;
  submitting: boolean;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [country, setCountry] = useState(initial?.country ?? "");
  const [contactName, setContactName] = useState(initial?.contact_name ?? "");
  const [contactEmail, setContactEmail] = useState(initial?.contact_email ?? "");
  const [contactPhone, setContactPhone] = useState(initial?.contact_phone ?? "");
  const [billingRate, setBillingRate] = useState<string>(
    initial?.billing_rate != null ? String(initial.billing_rate) : "",
  );
  const [retainer, setRetainer] = useState(Boolean(initial?.retainer_active));
  const [retainerHours, setRetainerHours] = useState<string>(
    initial?.retainer_hours_per_month != null
      ? String(initial.retainer_hours_per_month)
      : "",
  );
  const [notes, setNotes] = useState(initial?.notes ?? "");

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2 space-y-1">
        <Label htmlFor="cl-name">Client name</Label>
        <Input
          id="cl-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="cl-country">Country (ISO 2)</Label>
        <Input
          id="cl-country"
          maxLength={2}
          value={country ?? ""}
          onChange={(e) => setCountry(e.target.value.toUpperCase())}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="cl-rate">Billing rate (per hour)</Label>
        <Input
          id="cl-rate"
          type="number"
          step="0.01"
          value={billingRate}
          onChange={(e) => setBillingRate(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="cl-cname">Contact name</Label>
        <Input
          id="cl-cname"
          value={contactName ?? ""}
          onChange={(e) => setContactName(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="cl-cemail">Contact email</Label>
        <Input
          id="cl-cemail"
          type="email"
          value={contactEmail ?? ""}
          onChange={(e) => setContactEmail(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="cl-cphone">Contact phone</Label>
        <Input
          id="cl-cphone"
          value={contactPhone ?? ""}
          onChange={(e) => setContactPhone(e.target.value)}
        />
      </div>
      <label className="flex items-center gap-2 sm:col-span-2 mt-1">
        <Switch checked={retainer} onCheckedChange={setRetainer} />
        <span className="text-sm">Retainer active</span>
      </label>
      {retainer && (
        <div className="space-y-1">
          <Label htmlFor="cl-rhrs">Retainer hours / month</Label>
          <Input
            id="cl-rhrs"
            type="number"
            step="0.5"
            value={retainerHours}
            onChange={(e) => setRetainerHours(e.target.value)}
          />
        </div>
      )}
      <div className="sm:col-span-2 space-y-1">
        <Label htmlFor="cl-notes">Notes</Label>
        <textarea
          id="cl-notes"
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
              billing_rate: billingRate ? Number(billingRate) : null,
              retainer_active: retainer,
              retainer_hours_per_month:
                retainer && retainerHours ? Number(retainerHours) : null,
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

function ClientPanel() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: clients = [], isLoading } = useQuery({
    queryKey: ["services", "clients"],
    queryFn: listServicesClients,
  });
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<ServicesClient | null>(null);
  const [error, setError] = useState<string | null>(null);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["services"] });

  const createMutation = useMutation({
    mutationFn: createServicesClient,
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
      patch: Partial<ServicesClientInput>;
    }) => updateServicesClient(id, patch),
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
    onError: (err: Error) => setError(err.message ?? "Failed to update"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteServicesClient,
    onSuccess: invalidate,
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
          <h2 className="text-xl font-semibold">Clients</h2>
          <p className="text-sm text-muted-foreground">
            Companies you manage LCs for. Hours logged here roll up into
            invoices.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="w-4 h-4 mr-1" />
          New client
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
      ) : clients.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No clients yet. Add your first.</p>
            <Button className="mt-4" onClick={() => setCreateOpen(true)}>
              <Plus className="w-4 h-4 mr-1" />
              Add client
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
                  <th className="px-4 py-3 font-medium">Rate</th>
                  <th className="px-4 py-3 font-medium tabular-nums">Active LCs</th>
                  <th className="px-4 py-3 font-medium tabular-nums">
                    Hrs this mo.
                  </th>
                  <th className="px-4 py-3 font-medium tabular-nums">Unbilled</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {clients.map((c) => (
                  <tr key={c.id} className="border-t border-border">
                    <td className="px-4 py-3">
                      <div className="font-medium">{c.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {c.contact_email ?? c.country ?? "—"}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {c.billing_rate != null
                        ? `${formatMoney(c.billing_rate)}/h`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 tabular-nums">
                      {c.active_lc_count}
                    </td>
                    <td className="px-4 py-3 tabular-nums">
                      {formatHours(c.hours_this_month)}
                    </td>
                    <td className="px-4 py-3 tabular-nums">
                      {formatHours(c.billable_hours_unbilled)}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <Button
                        size="sm"
                        variant="ghost"
                        title="Validate LC for this client"
                        onClick={() =>
                          navigate(
                            `/lcopilot/upload-lc?services_client_id=${encodeURIComponent(
                              c.id,
                            )}`,
                          )
                        }
                      >
                        <FileCheck className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setEditing(c)}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={submitting}
                        onClick={() => {
                          if (confirm(`Delete ${c.name}?`)) {
                            deleteMutation.mutate(c.id);
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
            <DialogTitle>New client</DialogTitle>
            <DialogDescription>
              Track a client you manage LCs for.
            </DialogDescription>
          </DialogHeader>
          <ClientForm
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
            <DialogTitle>Edit client</DialogTitle>
            <DialogDescription>{editing?.name}</DialogDescription>
          </DialogHeader>
          {editing && (
            <ClientForm
              initial={{
                name: editing.name,
                country: editing.country ?? undefined,
                contact_name: editing.contact_name ?? undefined,
                contact_email: editing.contact_email ?? undefined,
                contact_phone: editing.contact_phone ?? undefined,
                billing_rate:
                  editing.billing_rate != null
                    ? Number(editing.billing_rate)
                    : undefined,
                retainer_active: editing.retainer_active,
                retainer_hours_per_month:
                  editing.retainer_hours_per_month != null
                    ? Number(editing.retainer_hours_per_month)
                    : undefined,
                notes: editing.notes ?? undefined,
              }}
              onCancel={() => setEditing(null)}
              submitting={submitting}
              onSubmit={(v) => updateMutation.mutate({ id: editing.id, patch: v })}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Time entry panel
// ---------------------------------------------------------------------------

function TimePanel() {
  const queryClient = useQueryClient();
  const [filterClient, setFilterClient] = useState<string>("");
  const [onlyUnbilled, setOnlyUnbilled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: clients = [] } = useQuery({
    queryKey: ["services", "clients"],
    queryFn: listServicesClients,
  });
  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["services", "time", filterClient, onlyUnbilled],
    queryFn: () =>
      listTimeEntries({
        clientId: filterClient || undefined,
        onlyUnbilled,
        limit: 200,
      }),
  });

  const createMutation = useMutation({
    mutationFn: createTimeEntry,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      setForm((f) => ({ ...f, hours: "", description: "" }));
    },
    onError: (err: Error) => setError(err.message ?? "Failed to log time"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTimeEntry,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["services"] }),
    onError: (err: Error) => setError(err.message ?? "Failed to delete"),
  });

  const [form, setForm] = useState<{
    clientId: string;
    hours: string;
    description: string;
    billable: boolean;
  }>({
    clientId: "",
    hours: "",
    description: "",
    billable: true,
  });

  const totalHours = useMemo(
    () => entries.reduce((acc, e) => acc + num(e.hours), 0),
    [entries],
  );

  const submitTimeEntry = () => {
    if (!form.clientId || !form.hours) return;
    createMutation.mutate({
      services_client_id: form.clientId,
      hours: Number(form.hours),
      description: form.description || null,
      billable: form.billable,
    } satisfies TimeEntryInput);
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Time</h2>
        <p className="text-sm text-muted-foreground">
          Log billable + non-billable hours. Filter and roll up into the
          invoice generator.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Log new entry</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-[1fr_auto_2fr_auto_auto] sm:items-end">
          <div className="space-y-1">
            <Label>Client</Label>
            <select
              value={form.clientId}
              onChange={(e) => setForm({ ...form, clientId: e.target.value })}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">— Pick a client —</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <Label>Hours</Label>
            <Input
              type="number"
              step="0.25"
              value={form.hours}
              onChange={(e) => setForm({ ...form, hours: e.target.value })}
              className="w-24"
            />
          </div>
          <div className="space-y-1">
            <Label>Description</Label>
            <Input
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
              placeholder="What did you do?"
            />
          </div>
          <label className="flex items-center gap-2">
            <Switch
              checked={form.billable}
              onCheckedChange={(v) => setForm({ ...form, billable: v })}
            />
            <span className="text-sm">Billable</span>
          </label>
          <Button
            onClick={submitTimeEntry}
            disabled={
              !form.clientId || !form.hours || createMutation.isPending
            }
          >
            {createMutation.isPending ? "Saving…" : "Log"}
          </Button>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <select
            value={filterClient}
            onChange={(e) => setFilterClient(e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">All clients</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm">
            <Switch checked={onlyUnbilled} onCheckedChange={setOnlyUnbilled} />
            <span className="text-muted-foreground">Unbilled only</span>
          </label>
        </div>
        <p className="text-sm text-muted-foreground tabular-nums">
          Total: {totalHours.toFixed(2)} h
        </p>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            Loading…
          </CardContent>
        </Card>
      ) : entries.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Clock className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No time entries match.</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground border-b">
                <tr>
                  <th className="px-4 py-2 font-medium">Date</th>
                  <th className="px-4 py-2 font-medium">Client</th>
                  <th className="px-4 py-2 font-medium tabular-nums">Hours</th>
                  <th className="px-4 py-2 font-medium">Description</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {entries.map((e: TimeEntry) => {
                  const client = clients.find(
                    (c) => c.id === e.services_client_id,
                  );
                  const date = e.performed_on ?? e.created_at;
                  return (
                    <tr key={e.id} className="border-t border-border">
                      <td className="px-4 py-2 text-muted-foreground">
                        {date ? new Date(date).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-4 py-2">
                        {client?.name ?? (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2 tabular-nums">
                        {formatHours(e.hours)}
                      </td>
                      <td className="px-4 py-2 text-muted-foreground line-clamp-1 max-w-[40ch]">
                        {e.description ?? "—"}
                      </td>
                      <td className="px-4 py-2 text-xs">
                        {!e.billable ? (
                          <span className="text-muted-foreground">non-billable</span>
                        ) : e.billed ? (
                          <span className="text-emerald-700">billed</span>
                        ) : (
                          <span className="text-amber-700">unbilled</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={deleteMutation.isPending}
                          onClick={() => {
                            if (confirm("Delete this time entry?")) {
                              deleteMutation.mutate(e.id);
                            }
                          }}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Invoice panel (Phase A9)
// ---------------------------------------------------------------------------

function InvoicePanel() {
  const { data: clients = [] } = useQuery({
    queryKey: ["services", "clients"],
    queryFn: listServicesClients,
  });
  const today = new Date();
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  const firstOfNext = new Date(today.getFullYear(), today.getMonth() + 1, 1);
  const [clientId, setClientId] = useState("");
  const [start, setStart] = useState(firstOfMonth.toISOString().slice(0, 10));
  const [end, setEnd] = useState(firstOfNext.toISOString().slice(0, 10));
  const [rateOverride, setRateOverride] = useState("");
  const [markBilled, setMarkBilled] = useState(false);
  const [preview, setPreview] = useState<InvoicePreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buildBody = () => ({
    client_id: clientId,
    period_start: new Date(start).toISOString(),
    period_end: new Date(end).toISOString(),
    rate_override: rateOverride ? Number(rateOverride) : null,
    mark_billed: markBilled,
  });

  const handlePreview = async () => {
    if (!clientId) return;
    setBusy(true);
    setError(null);
    try {
      const p = await generateInvoicePreview({
        ...buildBody(),
        mark_billed: false,
      });
      setPreview(p);
    } catch (err) {
      setError((err as Error).message ?? "Failed to preview invoice");
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async () => {
    if (!clientId) return;
    setBusy(true);
    setError(null);
    try {
      const client = clients.find((c) => c.id === clientId);
      const slug =
        (client?.name ?? "client").replace(/[^a-zA-Z0-9-_]+/g, "-").slice(0, 40) ||
        "client";
      await downloadInvoicePdf(buildBody(), `invoice-${slug}.pdf`);
      // Refresh preview to reflect mark_billed
      if (markBilled) await handlePreview();
    } catch (err) {
      setError((err as Error).message ?? "Failed to download invoice");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Invoice</h2>
        <p className="text-sm text-muted-foreground">
          Pull a client&rsquo;s billable hours for a period, preview, and
          download as PDF. Optionally mark the rolled-up entries as billed.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      <Card>
        <CardContent className="grid gap-3 sm:grid-cols-5 sm:items-end py-4">
          <div className="space-y-1">
            <Label>Client</Label>
            <select
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">— Pick a client —</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <Label>From</Label>
            <Input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>To</Label>
            <Input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>Rate override</Label>
            <Input
              type="number"
              step="0.01"
              value={rateOverride}
              onChange={(e) => setRateOverride(e.target.value)}
              placeholder={
                clients.find((c) => c.id === clientId)?.billing_rate != null
                  ? formatMoney(
                      clients.find((c) => c.id === clientId)?.billing_rate,
                    )
                  : "—"
              }
            />
          </div>
          <label className="flex items-center gap-2">
            <Switch checked={markBilled} onCheckedChange={setMarkBilled} />
            <span className="text-sm">Mark billed</span>
          </label>
        </CardContent>
        <CardContent className="flex items-center justify-end gap-2 pt-0">
          <Button variant="outline" onClick={handlePreview} disabled={busy || !clientId}>
            {busy && !preview ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <FileText className="w-4 h-4 mr-1" />
            )}
            Preview
          </Button>
          <Button onClick={handleDownload} disabled={busy || !clientId}>
            {busy ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <Download className="w-4 h-4 mr-1" />
            )}
            Download PDF
          </Button>
        </CardContent>
      </Card>

      {preview && (
        <Card>
          <CardHeader>
            <CardTitle>{preview.client_name}</CardTitle>
            <CardDescription>
              {new Date(preview.period_start).toLocaleDateString()} –{" "}
              {new Date(preview.period_end).toLocaleDateString()} · Rate{" "}
              {formatMoney(preview.rate)}/h ·{" "}
              {formatHours(preview.total_hours)} hrs ·{" "}
              <strong>{formatMoney(preview.total_amount)}</strong> total
            </CardDescription>
          </CardHeader>
          <CardContent>
            {preview.lines.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">
                No billable, unbilled time entries in this period.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-muted-foreground border-b">
                  <tr>
                    <th className="px-4 py-2 font-medium">Date</th>
                    <th className="px-4 py-2 font-medium">Description</th>
                    <th className="px-4 py-2 font-medium tabular-nums">Hours</th>
                    <th className="px-4 py-2 font-medium tabular-nums">Rate</th>
                    <th className="px-4 py-2 font-medium tabular-nums">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.lines.map((line) => (
                    <tr key={line.time_entry_id} className="border-t border-border">
                      <td className="px-4 py-2 text-muted-foreground">
                        {line.performed_on
                          ? new Date(line.performed_on).toLocaleDateString()
                          : "—"}
                      </td>
                      <td className="px-4 py-2 text-muted-foreground">
                        {line.description ?? "—"}
                      </td>
                      <td className="px-4 py-2 tabular-nums">
                        {formatHours(line.hours)}
                      </td>
                      <td className="px-4 py-2 tabular-nums">
                        {formatMoney(line.rate)}
                      </td>
                      <td className="px-4 py-2 tabular-nums">
                        {formatMoney(line.line_total)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Top-level page
// ---------------------------------------------------------------------------

function LegacyServicesStub() {
  return (
    <div className="space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold">Services Workspace</h1>
        <p className="text-muted-foreground">
          The full services build is gated behind VITE_LCOPILOT_SERVICES_REAL.
          Enable it in apps/web/.env to use the rebuilt dashboard.
        </p>
      </header>
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Coming soon.</p>
          <Button asChild className="mt-4">
            <Link to="/lcopilot">Back to LCopilot</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ServicesDashboard() {
  const enabled = isServicesRealEnabled();
  const [section, setSection] = useState<Section>("dashboard");

  const { data: clients = [] } = useQuery({
    queryKey: ["services", "clients"],
    queryFn: listServicesClients,
    enabled,
  });

  if (!enabled) {
    return (
      <DashboardLayout
        sidebar={null}
        breadcrumbs={[
          { label: "LCopilot", href: "/lcopilot" },
          { label: "Services" },
        ]}
        workspaceSwitcher={<WorkspaceSwitcher />}
      >
        <LegacyServicesStub />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      sidebar={
        <ServicesSidebar
          active={section}
          onChange={setSection}
          clientCount={clients.length}
        />
      }
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Services" },
      ]}
      workspaceSwitcher={<WorkspaceSwitcher />}
    >
      <div className="container mx-auto p-6">
        {section === "dashboard" && <DashboardPanel />}
        {section === "clients" && <ClientPanel />}
        {section === "time" && <TimePanel />}
        {section === "invoice" && <InvoicePanel />}
      </div>
    </DashboardLayout>
  );
}

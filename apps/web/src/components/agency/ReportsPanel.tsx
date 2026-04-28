/**
 * ReportsPanel — Phase A7 slice 3.
 *
 * Two flavors of report:
 *   - Per-supplier — totals + discrepancy rate + recent sessions.
 *   - Per-buyer — supplier-by-supplier roll-up for the buyer.
 *
 * The agent picks one entity from the dropdown, sees the structured
 * data inline, and downloads the PDF rendition with one click.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FileText, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  downloadBuyerReportPdf,
  downloadSupplierReportPdf,
  getBuyerReport,
  getSupplierReport,
  listBuyers,
  listSuppliers,
} from "@/lib/lcopilot/agencyApi";

type ReportKind = "supplier" | "buyer";

function safeFilename(name: string, prefix: string): string {
  const slug =
    name
      .replace(/[^a-zA-Z0-9-_]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 64) || prefix;
  return `${prefix}-${slug}.pdf`;
}

export function ReportsPanel() {
  const [kind, setKind] = useState<ReportKind>("supplier");
  const [selectedId, setSelectedId] = useState<string>("");
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: suppliers = [] } = useQuery({
    queryKey: ["agency", "suppliers"],
    queryFn: listSuppliers,
  });
  const { data: buyers = [] } = useQuery({
    queryKey: ["agency", "buyers"],
    queryFn: listBuyers,
  });

  const supplierReport = useQuery({
    queryKey: ["agency", "supplier-report", selectedId],
    queryFn: () => getSupplierReport(selectedId),
    enabled: kind === "supplier" && Boolean(selectedId),
  });
  const buyerReport = useQuery({
    queryKey: ["agency", "buyer-report", selectedId],
    queryFn: () => getBuyerReport(selectedId),
    enabled: kind === "buyer" && Boolean(selectedId),
  });

  const handleDownload = async () => {
    if (!selectedId) return;
    setDownloading(true);
    setError(null);
    try {
      if (kind === "supplier") {
        const name =
          suppliers.find((s) => s.id === selectedId)?.name ?? "supplier";
        await downloadSupplierReportPdf(
          selectedId,
          safeFilename(name, "supplier-report"),
        );
      } else {
        const name = buyers.find((b) => b.id === selectedId)?.name ?? "buyer";
        await downloadBuyerReportPdf(
          selectedId,
          safeFilename(name, "buyer-report"),
        );
      }
    } catch (err) {
      setError((err as Error).message ?? "Failed to download PDF");
    } finally {
      setDownloading(false);
    }
  };

  const supplierData = supplierReport.data;
  const buyerData = buyerReport.data;
  const loading =
    (kind === "supplier" && supplierReport.isLoading) ||
    (kind === "buyer" && buyerReport.isLoading);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Reports</h2>
        <p className="text-sm text-muted-foreground">
          Per-supplier and per-buyer summaries: throughput, discrepancy rate,
          recent activity. Download as PDF to share or archive.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      <Card>
        <CardContent className="grid gap-3 py-4 sm:grid-cols-3 sm:items-end">
          <div className="space-y-1">
            <Label htmlFor="report-kind">Report type</Label>
            <select
              id="report-kind"
              value={kind}
              onChange={(e) => {
                setKind(e.target.value as ReportKind);
                setSelectedId("");
              }}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="supplier">Supplier</option>
              <option value="buyer">Foreign buyer</option>
            </select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="report-target">
              {kind === "supplier" ? "Supplier" : "Foreign buyer"}
            </Label>
            <select
              id="report-target"
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">— Pick one —</option>
              {(kind === "supplier" ? suppliers : buyers).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </div>
          <Button onClick={handleDownload} disabled={!selectedId || downloading}>
            {downloading ? (
              <>
                <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                Downloading…
              </>
            ) : (
              <>
                <Download className="w-4 h-4 mr-1" />
                Download PDF
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {!selectedId && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">
              Pick a {kind === "supplier" ? "supplier" : "foreign buyer"} above
              to preview the report.
            </p>
          </CardContent>
        </Card>
      )}

      {selectedId && loading && (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            Loading…
          </CardContent>
        </Card>
      )}

      {kind === "supplier" && supplierData && (
        <Card>
          <CardHeader>
            <CardTitle>{supplierData.supplier_name}</CardTitle>
            <CardDescription>
              {supplierData.country ?? "—"} ·{" "}
              {supplierData.contact_email ?? "no contact"} ·{" "}
              Generated {new Date(supplierData.generated_at).toLocaleString()}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <Stat label="Total LCs" value={supplierData.total_sessions} />
              <Stat label="Active" value={supplierData.active_sessions} />
              <Stat
                label="This month"
                value={supplierData.completed_this_month}
              />
              <Stat
                label="Disc. rate"
                value={supplierData.discrepancy_rate.toFixed(2)}
              />
              <Stat
                label="Discrepancies"
                value={supplierData.total_discrepancies}
              />
              <Stat label="Open" value={supplierData.open_discrepancies} />
              <Stat
                label="Re-paper sent"
                value={supplierData.repaper_requests}
              />
              <Stat
                label="Re-paper open"
                value={supplierData.repaper_open}
              />
            </div>

            <div>
              <h3 className="text-sm font-semibold mb-2">Recent activity</h3>
              {supplierData.recent_sessions.length === 0 ? (
                <p className="text-sm text-muted-foreground italic">
                  No validations yet.
                </p>
              ) : (
                <table className="w-full text-xs">
                  <thead className="text-left text-[10px] text-muted-foreground border-b">
                    <tr>
                      <th className="py-1 font-medium">Created</th>
                      <th className="py-1 font-medium">Lifecycle</th>
                      <th className="py-1 font-medium">Status</th>
                      <th className="py-1 font-medium tabular-nums">Findings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {supplierData.recent_sessions.map((r) => (
                      <tr
                        key={r.validation_session_id}
                        className="border-t border-border/40"
                      >
                        <td className="py-1.5">
                          {new Date(r.created_at).toLocaleString()}
                        </td>
                        <td className="py-1.5 text-muted-foreground">
                          {r.lifecycle_state ?? "—"}
                        </td>
                        <td className="py-1.5">{r.status}</td>
                        <td className="py-1.5 tabular-nums">
                          {r.findings_count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {kind === "buyer" && buyerData && (
        <Card>
          <CardHeader>
            <CardTitle>{buyerData.buyer_name}</CardTitle>
            <CardDescription>
              {buyerData.country ?? "—"} ·{" "}
              {buyerData.contact_email ?? "no contact"} ·{" "}
              Generated {new Date(buyerData.generated_at).toLocaleString()}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <Stat label="Suppliers" value={buyerData.supplier_count} />
              <Stat label="Total LCs" value={buyerData.total_sessions} />
              <Stat label="Active" value={buyerData.active_sessions} />
              <Stat label="Open" value={buyerData.open_discrepancies} />
            </div>

            <div>
              <h3 className="text-sm font-semibold mb-2">Suppliers</h3>
              {buyerData.suppliers.length === 0 ? (
                <p className="text-sm text-muted-foreground italic">
                  No suppliers ship to this buyer yet.
                </p>
              ) : (
                <table className="w-full text-xs">
                  <thead className="text-left text-[10px] text-muted-foreground border-b">
                    <tr>
                      <th className="py-1 font-medium">Supplier</th>
                      <th className="py-1 font-medium">Country</th>
                      <th className="py-1 font-medium tabular-nums">LCs</th>
                      <th className="py-1 font-medium tabular-nums">Active</th>
                      <th className="py-1 font-medium tabular-nums">Open</th>
                    </tr>
                  </thead>
                  <tbody>
                    {buyerData.suppliers.map((s) => (
                      <tr
                        key={s.supplier_id}
                        className="border-t border-border/40"
                      >
                        <td className="py-1.5">{s.supplier_name}</td>
                        <td className="py-1.5 text-muted-foreground">
                          {s.country ?? "—"}
                        </td>
                        <td className="py-1.5 tabular-nums">
                          {s.total_sessions}
                        </td>
                        <td className="py-1.5 tabular-nums">
                          {s.active_sessions}
                        </td>
                        <td className="py-1.5 tabular-nums">
                          {s.open_discrepancies}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded border border-border bg-neutral-50 dark:bg-neutral-800/40 px-3 py-2">
      <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
      <p className="text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}

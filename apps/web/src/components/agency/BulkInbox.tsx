/**
 * BulkInbox — Phase A6 slice 2.
 *
 * Drag a folder of supplier presentations onto the page; each top-
 * level directory is treated as one bulk item. The user picks the
 * matching supplier (or "skip") for each, then we kick a single
 * /api/bulk-validate job covering all selected items.
 *
 * Folder upload uses the `webkitdirectory` attribute. Browsers other
 * than Chromium-based ones get a single multi-file picker fallback;
 * the same grouping logic still works as long as filenames carry
 * a relative path via `File.webkitRelativePath`.
 */

import { Fragment, useCallback, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  CircleDashed,
  FolderUp,
  History,
  Inbox,
  Loader2,
  Play,
  XCircle,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/api/client";
import { listSuppliers, type Supplier } from "@/lib/lcopilot/agencyApi";

interface BulkJobItem {
  id: string;
  lc_identifier: string;
  status: string;
  attempts: number;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  last_error: string | null;
  error_code: string | null;
  result_summary: Record<string, unknown> | null;
}

interface BulkJob {
  id: string;
  name: string;
  description: string | null;
  status: string;
  total_items: number;
  processed_items: number;
  succeeded_items: number;
  failed_items: number;
  skipped_items: number;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  created_at: string;
  items: BulkJobItem[];
}

async function listRecentBulkJobs(): Promise<BulkJob[]> {
  const { data } = await api.get<BulkJob[]>("/api/bulk-validate?limit=20");
  return data ?? [];
}

function StatusPill({ status }: { status: string }) {
  const norm = status.toLowerCase();
  let Icon = CircleDashed;
  let cls = "text-muted-foreground bg-neutral-200/40";
  if (norm === "succeeded" || norm === "complete" || norm === "completed") {
    Icon = CheckCircle2;
    cls = "text-emerald-700 bg-emerald-100";
  } else if (norm === "failed") {
    Icon = XCircle;
    cls = "text-rose-700 bg-rose-100";
  } else if (norm === "running" || norm === "processing") {
    Icon = Loader2;
    cls = "text-blue-700 bg-blue-100";
  } else if (norm === "partial") {
    Icon = CircleDashed;
    cls = "text-amber-700 bg-amber-100";
  }
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${cls}`}
    >
      <Icon className={`w-3 h-3 ${norm === "running" ? "animate-spin" : ""}`} />
      {status}
    </span>
  );
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function RecentJobsPanel() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["agency", "bulk-jobs"],
    queryFn: listRecentBulkJobs,
    // Auto-refresh while there's a running/processing job so the agent
    // sees progress without manually refreshing. (TanStack Query v4
    // signature: callback receives the cached data directly.)
    refetchInterval: (data) => {
      const list = (data as BulkJob[] | undefined) ?? [];
      const live = list.some((j) =>
        ["running", "processing", "pending"].includes(
          (j.status ?? "").toLowerCase(),
        ),
      );
      return live ? 5_000 : false;
    },
  });
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-muted-foreground">
          Loading…
        </CardContent>
      </Card>
    );
  }
  if (jobs.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardContent className="p-0">
        <div className="border-b px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold">Recent bulk jobs</h3>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              queryClient.invalidateQueries({ queryKey: ["agency", "bulk-jobs"] })
            }
          >
            Refresh
          </Button>
        </div>
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-muted-foreground border-b">
            <tr>
              <th className="px-4 py-2 font-medium">Job</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium tabular-nums">Items</th>
              <th className="px-4 py-2 font-medium tabular-nums">Duration</th>
              <th className="px-4 py-2 font-medium">Created</th>
              <th className="px-4 py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => {
              const expanded = expandedJobId === job.id;
              return (
                <Fragment key={job.id}>
                  <tr
                    className="border-t border-border hover:bg-neutral-50 dark:hover:bg-neutral-800/40 cursor-pointer"
                    onClick={() =>
                      setExpandedJobId(expanded ? null : job.id)
                    }
                  >
                    <td className="px-4 py-2 font-medium truncate max-w-[20ch]">
                      {job.name}
                    </td>
                    <td className="px-4 py-2">
                      <StatusPill status={job.status} />
                    </td>
                    <td className="px-4 py-2 tabular-nums">
                      {job.succeeded_items}/{job.total_items}
                      {job.failed_items > 0 && (
                        <span className="ml-1 text-rose-600">
                          ({job.failed_items} failed)
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 tabular-nums text-muted-foreground">
                      {formatDuration(job.duration_seconds)}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/lcopilot/_bulk-test?job_id=${job.id}`);
                        }}
                      >
                        Live progress
                      </Button>
                    </td>
                  </tr>
                  {expanded && job.items.length > 0 && (
                    <tr className="bg-neutral-50/60 dark:bg-neutral-800/20">
                      <td colSpan={6} className="px-4 py-3">
                        <table className="w-full text-xs">
                          <thead className="text-left text-[10px] text-muted-foreground">
                            <tr>
                              <th className="pb-1 font-medium">Item</th>
                              <th className="pb-1 font-medium">Status</th>
                              <th className="pb-1 font-medium">Verdict</th>
                              <th className="pb-1 font-medium">Findings</th>
                              <th className="pb-1 font-medium" />
                            </tr>
                          </thead>
                          <tbody>
                            {job.items.map((item) => {
                              const summary = item.result_summary ?? {};
                              const verdict =
                                (summary.verdict as string | undefined) ??
                                (summary.bank_verdict as string | undefined) ??
                                "—";
                              const findings =
                                (summary.findings_count as number | undefined) ??
                                (summary.findings as number | undefined) ??
                                "—";
                              const sessionId =
                                (summary.validation_session_id as
                                  | string
                                  | undefined) ??
                                (summary.session_id as string | undefined);
                              return (
                                <tr
                                  key={item.id}
                                  className="border-t border-border/40"
                                >
                                  <td className="py-1.5">
                                    {item.lc_identifier}
                                  </td>
                                  <td className="py-1.5">
                                    <StatusPill status={item.status} />
                                  </td>
                                  <td className="py-1.5 text-muted-foreground">
                                    {String(verdict)}
                                  </td>
                                  <td className="py-1.5 tabular-nums text-muted-foreground">
                                    {String(findings)}
                                  </td>
                                  <td className="py-1.5 text-right">
                                    {sessionId && (
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() =>
                                          navigate(
                                            `/exporter/results/${sessionId}`,
                                          )
                                        }
                                      >
                                        Open
                                      </Button>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

interface FolderGroup {
  /** Top-level dir name (or "_root_" if files were dropped without a folder). */
  folder: string;
  files: File[];
  /** Selected supplier id; empty string = unassigned, "skip" = explicitly drop. */
  supplierId: string;
}

interface CreateBulkJobResponse {
  id: string;
  name: string;
  status: string;
}

function groupFilesByTopLevelDir(files: FileList | File[]): FolderGroup[] {
  const buckets = new Map<string, File[]>();
  for (const f of Array.from(files)) {
    const rel = (f as File & { webkitRelativePath?: string }).webkitRelativePath || "";
    const top = rel.split("/")[0] || "_root_";
    const existing = buckets.get(top);
    if (existing) {
      existing.push(f);
    } else {
      buckets.set(top, [f]);
    }
  }
  return Array.from(buckets.entries()).map(([folder, files]) => ({
    folder,
    files,
    supplierId: "",
  }));
}

function autoMatchSupplier(
  folder: string,
  suppliers: Supplier[],
): string {
  const norm = folder.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
  if (!norm) return "";
  for (const s of suppliers) {
    if (
      s.name.trim().toLowerCase().replace(/[^a-z0-9]/g, "") === norm
    ) {
      return s.id;
    }
  }
  return "";
}

export function BulkInbox() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [groups, setGroups] = useState<FolderGroup[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(
    null,
  );

  const { data: suppliers = [] } = useQuery({
    queryKey: ["agency", "suppliers"],
    queryFn: listSuppliers,
  });

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) {
        setGroups([]);
        return;
      }
      const next = groupFilesByTopLevelDir(files);
      // Auto-match folder names to existing suppliers
      for (const g of next) {
        const matched = autoMatchSupplier(g.folder, suppliers);
        if (matched) g.supplierId = matched;
      }
      setGroups(next);
      setError(null);
    },
    [suppliers],
  );

  const setSupplierFor = (folder: string, supplierId: string) => {
    setGroups((prev) =>
      prev.map((g) => (g.folder === folder ? { ...g, supplierId } : g)),
    );
  };

  const removeGroup = (folder: string) => {
    setGroups((prev) => prev.filter((g) => g.folder !== folder));
  };

  const submittable = useMemo(
    () => groups.filter((g) => g.supplierId && g.supplierId !== "skip" && g.files.length > 0),
    [groups],
  );

  const submit = useCallback(async () => {
    if (submittable.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      // 1. Create the bulk job
      const { data: job } = await api.post<CreateBulkJobResponse>(
        "/api/bulk-validate/",
        {
          name: `Agency bulk · ${new Date().toLocaleString()}`,
          description: `${submittable.length} supplier(s)`,
        },
      );

      setProgress({ done: 0, total: submittable.length });

      // 2. Upload each group as one item
      let done = 0;
      for (const g of submittable) {
        const supplier = suppliers.find((s) => s.id === g.supplierId);
        const lcIdentifier = supplier?.name || g.folder;
        const formData = new FormData();
        formData.append("lc_identifier", lcIdentifier.slice(0, 128));
        formData.append("supplier_id", g.supplierId);
        for (const f of g.files) {
          formData.append("files", f, f.name);
        }
        await api.post(`/api/bulk-validate/${job.id}/items`, formData);
        done += 1;
        setProgress({ done, total: submittable.length });
      }

      // 3. Kick the run
      await api.post(`/api/bulk-validate/${job.id}/run`);

      // 4. Navigate to the bulk-test page (existing UI we have for now;
      // a dedicated bulk results page lands in slice 3).
      navigate(`/lcopilot/_bulk-test?job_id=${job.id}`);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })
        ?.response?.data?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : (detail as { message?: string } | undefined)?.message ??
            (err as Error).message ??
            "Failed to create bulk job";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }, [submittable, suppliers, navigate]);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Bulk Inbox</h2>
        <p className="text-sm text-muted-foreground">
          Drag a folder where each subfolder is a supplier presentation. We
          auto-match folder names to your supplier roster; pick the right
          supplier for any that don&rsquo;t match, then kick a single bulk
          validation job.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      <Card>
        <CardContent className="py-8">
          <div className="flex flex-col items-center gap-3 text-center">
            <FolderUp className="w-10 h-10 text-muted-foreground" />
            <p className="text-sm">
              {groups.length === 0
                ? "Pick a folder to get started."
                : `Loaded ${groups.length} folder(s).`}
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              // @ts-expect-error — non-standard but shipped in Chromium browsers
              webkitdirectory=""
              directory=""
              accept="application/pdf"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={submitting}
            >
              <FolderUp className="w-4 h-4 mr-1" />
              {groups.length === 0 ? "Choose folder" : "Replace folder"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {groups.length > 0 && (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground border-b">
                <tr>
                  <th className="px-4 py-3 font-medium">Folder</th>
                  <th className="px-4 py-3 font-medium tabular-nums">Files</th>
                  <th className="px-4 py-3 font-medium">Supplier</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {groups.map((g) => {
                  const matched = g.supplierId && g.supplierId !== "skip";
                  return (
                    <tr key={g.folder} className="border-t border-border">
                      <td className="px-4 py-3 font-medium">{g.folder}</td>
                      <td className="px-4 py-3 tabular-nums text-muted-foreground">
                        {g.files.length}
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={g.supplierId}
                          onChange={(e) => setSupplierFor(g.folder, e.target.value)}
                          disabled={submitting}
                          className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
                        >
                          <option value="">— Pick a supplier —</option>
                          {suppliers.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.name}
                            </option>
                          ))}
                          <option value="skip">Skip this folder</option>
                        </select>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {matched && (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 inline-block mr-2" />
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => removeGroup(g.folder)}
                          disabled={submitting}
                        >
                          <X className="w-3.5 h-3.5" />
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

      {groups.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {submittable.length} of {groups.length} folder(s) ready to validate.
            {progress && ` ${progress.done}/${progress.total} uploaded.`}
          </p>
          <Button
            disabled={submittable.length === 0 || submitting}
            onClick={submit}
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                Creating job…
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-1" />
                Validate {submittable.length} item(s)
              </>
            )}
          </Button>
        </div>
      )}

      {groups.length === 0 && !submitting && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Inbox className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">
              No folder loaded yet. Each top-level subfolder will become one
              bulk item attributed to its matched supplier.
            </p>
          </CardContent>
        </Card>
      )}

      <RecentJobsPanel />
    </div>
  );
}

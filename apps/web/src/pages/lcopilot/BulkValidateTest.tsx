/**
 * Bulk LC Validation — QA test surface.
 *
 * Phase A1 part 2 (2026-04-26). Throwaway tool, NOT customer-facing
 * production UI. Lives behind VITE_LCOPILOT_BULK_VALIDATION so it
 * doesn't show up in the dashboard nav.
 *
 * Workflow:
 *   1. Pick a job name and click Create.
 *   2. Drop one folder per LC into the dropzone (each folder = one LC's
 *      package: the LC PDF plus supporting docs).
 *   3. Click Run; the SSE stream renders per-item progress live.
 *
 * The full customer dashboard surface lands in a later phase once we've
 * smoke-tested the backend infra against the stress corpus. This page
 * exists to drive that smoke test.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Navigate } from "react-router-dom";

import { isBulkValidationEnabled } from "../../lib/lcopilot/featureFlags";
import { api } from "../../api/client";

interface BulkItemRow {
  item_id: string;
  lc_identifier: string;
  status: string;
  duration_ms?: number | null;
  last_error?: string | null;
  result_summary?: Record<string, unknown> | null;
}

interface BulkJobView {
  id: string;
  name: string;
  status: string;
  total_items: number;
  succeeded_items: number;
  failed_items: number;
  skipped_items: number;
  items: BulkItemRow[];
}

interface PendingItem {
  lc_identifier: string;
  files: File[];
}

const TERMINAL_JOB_STATUSES = new Set([
  "succeeded",
  "failed",
  "partial",
  "cancelled",
]);

export default function BulkValidateTest() {
  if (!isBulkValidationEnabled()) {
    return <Navigate to="/lcopilot/exporter-dashboard" replace />;
  }

  const [jobName, setJobName] = useState("Bulk QA test");
  const [jobId, setJobId] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingItem[]>([]);
  const [jobView, setJobView] = useState<BulkJobView | null>(null);
  const [streamEvents, setStreamEvents] = useState<
    { ts: string; type: string; payload: Record<string, unknown> }[]
  >([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // ------------------------------------------------------------------
  // Lifecycle
  // ------------------------------------------------------------------

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  // ------------------------------------------------------------------
  // Job creation
  // ------------------------------------------------------------------

  const createJob = useCallback(async () => {
    setError(null);
    try {
      const response = await api.post("/api/bulk-validate/", {
        name: jobName,
      });
      setJobId(response.data.job_id);
      setStreamEvents([]);
      setJobView(null);
    } catch (err) {
      setError((err as Error).message ?? "Failed to create job");
    }
  }, [jobName]);

  // ------------------------------------------------------------------
  // Item staging (folder-drop)
  //
  // Each folder maps to one BulkItem. The folder name becomes
  // lc_identifier. All files inside become the item's PDF set.
  // ------------------------------------------------------------------

  const onFolderDrop = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(event.target.files ?? []);
      if (!files.length) return;

      // group by top-level folder via webkitRelativePath
      const groups = new Map<string, File[]>();
      for (const file of files) {
        const rel = (file as File & { webkitRelativePath?: string })
          .webkitRelativePath;
        const folder = rel ? rel.split("/")[0] : "(loose-files)";
        if (!groups.has(folder)) groups.set(folder, []);
        groups.get(folder)!.push(file);
      }

      const next: PendingItem[] = [];
      groups.forEach((groupFiles, folder) => {
        next.push({ lc_identifier: folder, files: groupFiles });
      });
      setPending(next);
    },
    []
  );

  const uploadAllPending = useCallback(async () => {
    if (!jobId || !pending.length) return;
    setIsUploading(true);
    setError(null);
    try {
      for (const item of pending) {
        const formData = new FormData();
        formData.append("lc_identifier", item.lc_identifier);
        for (const file of item.files) {
          formData.append("files", file, file.name);
        }
        await api.post(
          `/api/bulk-validate/${jobId}/items`,
          formData,
          { headers: { "Content-Type": "multipart/form-data" } }
        );
      }
      setPending([]);
      await refreshJob();
    } catch (err) {
      setError((err as Error).message ?? "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }, [jobId, pending]);

  // ------------------------------------------------------------------
  // Run + SSE wiring
  // ------------------------------------------------------------------

  const refreshJob = useCallback(async () => {
    if (!jobId) return;
    try {
      const response = await api.get(`/api/bulk-validate/${jobId}`);
      setJobView(response.data);
    } catch (err) {
      setError((err as Error).message ?? "Refresh failed");
    }
  }, [jobId]);

  const openSseStream = useCallback(() => {
    if (!jobId || eventSourceRef.current) return;
    const baseUrl =
      import.meta.env.VITE_API_URL ?? window.location.origin;
    const url = `${baseUrl.replace(/\/$/, "")}/api/bulk-validate/${jobId}/stream`;
    const es = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = es;

    const onAny = (event: MessageEvent, type: string) => {
      try {
        const payload = JSON.parse(event.data);
        setStreamEvents((prev) => [
          { ts: new Date().toISOString(), type, payload },
          ...prev.slice(0, 199),
        ]);
        if (
          type === "item_completed" ||
          type === "item_failed" ||
          type === "job_completed" ||
          type === "job_failed"
        ) {
          refreshJob();
        }
        if (type === "job_completed" || type === "job_failed") {
          setIsRunning(false);
          es.close();
          eventSourceRef.current = null;
        }
      } catch {
        // SSE payload that wasn't JSON — ignore
      }
    };

    [
      "ready",
      "job_started",
      "item_started",
      "item_completed",
      "item_failed",
      "item_skipped",
      "job_completed",
      "job_failed",
      "cancel_requested",
    ].forEach((type) => {
      es.addEventListener(type, (event) => onAny(event as MessageEvent, type));
    });

    es.onerror = () => {
      // Keep the stream open even on transient errors; SSE auto-reconnects.
    };
  }, [jobId, refreshJob]);

  const runJob = useCallback(async () => {
    if (!jobId) return;
    setError(null);
    setIsRunning(true);
    try {
      // Open the SSE stream BEFORE kicking the worker so we don't miss
      // the very first item_started event.
      openSseStream();
      await api.post(`/api/bulk-validate/${jobId}/run`);
      await refreshJob();
    } catch (err) {
      setIsRunning(false);
      setError((err as Error).message ?? "Run failed");
    }
  }, [jobId, openSseStream, refreshJob]);

  const cancelJob = useCallback(async () => {
    if (!jobId) return;
    try {
      await api.post(`/api/bulk-validate/${jobId}/cancel`);
      await refreshJob();
    } catch (err) {
      setError((err as Error).message ?? "Cancel failed");
    }
  }, [jobId, refreshJob]);

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  const isJobTerminal = useMemo(() => {
    return jobView?.status
      ? TERMINAL_JOB_STATUSES.has(jobView.status)
      : false;
  }, [jobView?.status]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <header className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-neutral-500">
          Phase A1 part 2 — QA only
        </p>
        <h1 className="text-2xl font-semibold">Bulk LC validation tester</h1>
        <p className="text-sm text-neutral-600">
          Throwaway tool for stress-testing the bulk pipeline. Each
          dropped folder = one LC (folder name becomes the LC identifier;
          contents are the LC PDF plus supporting docs).
        </p>
      </header>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Step 1 — create */}
      <section className="rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="mb-2 text-sm font-medium">1. Create job</h2>
        <div className="flex gap-2">
          <input
            value={jobName}
            onChange={(e) => setJobName(e.target.value)}
            disabled={!!jobId}
            className="flex-1 rounded border border-neutral-300 px-2 py-1 text-sm"
          />
          <button
            onClick={createJob}
            disabled={!!jobId || !jobName.trim()}
            className="rounded bg-neutral-900 px-3 py-1 text-sm text-white disabled:opacity-50"
          >
            Create
          </button>
        </div>
        {jobId && (
          <p className="mt-2 text-xs text-neutral-500">
            Job: <code>{jobId}</code>
          </p>
        )}
      </section>

      {/* Step 2 — drop folders */}
      {jobId && (
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-medium">
            2. Drop a parent folder containing one subfolder per LC
          </h2>
          <input
            type="file"
            // @ts-expect-error — webkitdirectory is non-standard but widely supported
            webkitdirectory="true"
            multiple
            onChange={onFolderDrop}
            className="text-sm"
          />
          {pending.length > 0 && (
            <div className="mt-3 space-y-1">
              <p className="text-xs text-neutral-600">
                {pending.length} item(s) staged:
              </p>
              <ul className="text-xs">
                {pending.map((p) => (
                  <li key={p.lc_identifier}>
                    <code>{p.lc_identifier}</code> — {p.files.length} file(s)
                  </li>
                ))}
              </ul>
              <button
                onClick={uploadAllPending}
                disabled={isUploading}
                className="mt-2 rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
              >
                {isUploading ? "Uploading…" : "Upload to job"}
              </button>
            </div>
          )}
        </section>
      )}

      {/* Step 3 — run */}
      {jobId && (jobView?.total_items ?? 0) > 0 && !isJobTerminal && (
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-medium">3. Run</h2>
          <div className="flex gap-2">
            <button
              onClick={runJob}
              disabled={isRunning}
              className="rounded bg-emerald-600 px-3 py-1 text-sm text-white disabled:opacity-50"
            >
              {isRunning ? "Running…" : `Validate ${jobView?.total_items} item(s)`}
            </button>
            {isRunning && (
              <button
                onClick={cancelJob}
                className="rounded border border-red-400 px-3 py-1 text-sm text-red-700"
              >
                Cancel
              </button>
            )}
          </div>
        </section>
      )}

      {/* Live stream */}
      {jobId && streamEvents.length > 0 && (
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-medium">Live progress</h2>
          <ol className="max-h-64 space-y-1 overflow-auto text-xs font-mono">
            {streamEvents.map((e, idx) => (
              <li key={`${e.ts}-${idx}`}>
                <span className="text-neutral-400">{e.ts.slice(11, 19)}</span>{" "}
                <span className="font-semibold">{e.type}</span>{" "}
                <span className="text-neutral-700">
                  {JSON.stringify(e.payload)}
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* Item table */}
      {jobView && (
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-medium">
            Job status: <span className="font-mono">{jobView.status}</span>{" "}
            ({jobView.succeeded_items}✓ / {jobView.failed_items}✗ /{" "}
            {jobView.skipped_items}⤬)
          </h2>
          <table className="w-full text-xs">
            <thead className="text-left text-neutral-500">
              <tr>
                <th className="py-1">LC</th>
                <th className="py-1">Status</th>
                <th className="py-1">Duration</th>
                <th className="py-1">Result / Error</th>
              </tr>
            </thead>
            <tbody>
              {jobView.items.map((i) => (
                <tr key={i.item_id} className="border-t border-neutral-100">
                  <td className="py-1 font-mono">{i.lc_identifier}</td>
                  <td className="py-1">{i.status}</td>
                  <td className="py-1">
                    {i.duration_ms ? `${i.duration_ms} ms` : "—"}
                  </td>
                  <td className="py-1">
                    {i.last_error
                      ? i.last_error
                      : i.result_summary
                        ? JSON.stringify(i.result_summary)
                        : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

/**
 * Re-papering recipient page — Phase A2.
 *
 * Public-by-token: NOT auth-gated. The URL is /repaper/{token} where
 * token is the long random string emailed to the recipient when an
 * exporter / importer asked them to fix a flagged document.
 *
 * Surface intentionally narrow:
 *   - Show the discrepancy description + the requester's message.
 *   - Let the recipient post a comment (no account required).
 *   - Let the recipient upload corrected PDFs.
 *
 * No mention of other discrepancies. No session detail. No login.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";

import { API_BASE_URL } from "../../api/client";

interface RepaperView {
  discrepancy_description: string;
  requester_email: string | null;
  message: string | null;
  state: string;
  submitted_at: string | null;
}

const STATE_COPY: Record<string, string> = {
  requested: "Pending — please review the request below",
  in_progress: "In progress — open and ready for upload",
  corrected: "Corrected — uploaded files received",
  resolved: "Resolved — discrepancy cleared",
  cancelled: "Cancelled by the requester",
};

export default function RepaperRecipient() {
  const { token } = useParams<{ token: string }>();
  const [view, setView] = useState<RepaperView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [authorEmail, setAuthorEmail] = useState("");
  const [authorName, setAuthorName] = useState("");
  const [comment, setComment] = useState("");
  const [submittingComment, setSubmittingComment] = useState(false);

  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadDone, setUploadDone] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const baseUrl = API_BASE_URL?.replace(/\/$/, "") ?? "";

  const fetchView = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${baseUrl}/api/repaper/${token}`);
      setView(response.data);
    } catch (err) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? (err as Error).message ?? "Failed to load request";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [token, baseUrl]);

  useEffect(() => {
    fetchView();
  }, [fetchView]);

  const submitComment = useCallback(async () => {
    if (!token || !comment.trim() || !authorEmail.trim()) return;
    setSubmittingComment(true);
    setError(null);
    try {
      await axios.post(`${baseUrl}/api/repaper/${token}/comment`, {
        body: comment,
        author_email: authorEmail,
        author_display_name: authorName || undefined,
      });
      setComment("");
    } catch (err) {
      setError((err as Error).message ?? "Failed to post comment");
    } finally {
      setSubmittingComment(false);
    }
  }, [token, comment, authorEmail, authorName, baseUrl]);

  const onFilesPicked = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setFiles(Array.from(event.target.files ?? []));
    },
    []
  );

  const submitUpload = useCallback(async () => {
    if (!token || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      for (const f of files) {
        formData.append("files", f, f.name);
      }
      await axios.post(`${baseUrl}/api/repaper/${token}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadDone(true);
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await fetchView();
    } catch (err) {
      setError((err as Error).message ?? "Upload failed");
    } finally {
      setUploading(false);
    }
  }, [token, files, baseUrl, fetchView]);

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center text-sm text-neutral-500">
        Loading request…
      </div>
    );
  }

  if (error && !view) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12">
        <div className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!view) return null;

  const isTerminal = view.state === "resolved" || view.state === "cancelled";

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-8">
      <header className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-neutral-500">
          TRDR Hub — document correction request
        </p>
        <h1 className="text-2xl font-semibold">Please review and respond</h1>
        <p className="text-sm text-neutral-600">
          {STATE_COPY[view.state] ?? view.state}
        </p>
      </header>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <section className="rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="mb-1 text-sm font-medium">Discrepancy</h2>
        <p className="text-sm text-neutral-800">{view.discrepancy_description}</p>
      </section>

      {(view.requester_email || view.message) && (
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="mb-1 text-sm font-medium">Note from requester</h2>
          {view.requester_email && (
            <p className="text-xs text-neutral-500">{view.requester_email}</p>
          )}
          {view.message && (
            <p className="mt-2 whitespace-pre-wrap text-sm text-neutral-800">
              {view.message}
            </p>
          )}
        </section>
      )}

      {!isTerminal && (
        <>
          <section className="rounded-lg border border-neutral-200 bg-white p-4">
            <h2 className="mb-2 text-sm font-medium">Comment</h2>
            <input
              type="email"
              placeholder="Your email"
              value={authorEmail}
              onChange={(e) => setAuthorEmail(e.target.value)}
              className="mb-2 w-full rounded border border-neutral-300 px-2 py-1 text-sm"
            />
            <input
              type="text"
              placeholder="Your name (optional)"
              value={authorName}
              onChange={(e) => setAuthorName(e.target.value)}
              className="mb-2 w-full rounded border border-neutral-300 px-2 py-1 text-sm"
            />
            <textarea
              placeholder="Type a reply…"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={4}
              className="w-full rounded border border-neutral-300 px-2 py-1 text-sm"
            />
            <button
              onClick={submitComment}
              disabled={submittingComment || !comment.trim() || !authorEmail.trim()}
              className="mt-2 rounded bg-neutral-900 px-3 py-1 text-sm text-white disabled:opacity-50"
            >
              {submittingComment ? "Posting…" : "Post comment"}
            </button>
          </section>

          <section className="rounded-lg border border-neutral-200 bg-white p-4">
            <h2 className="mb-2 text-sm font-medium">Upload corrected document(s)</h2>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="application/pdf"
              onChange={onFilesPicked}
              className="text-sm"
            />
            {files.length > 0 && (
              <p className="mt-2 text-xs text-neutral-600">
                {files.length} file(s) selected
              </p>
            )}
            <button
              onClick={submitUpload}
              disabled={uploading || files.length === 0}
              className="mt-2 rounded bg-emerald-600 px-3 py-1 text-sm text-white disabled:opacity-50"
            >
              {uploading
                ? "Uploading…"
                : `Submit ${files.length || "0"} file(s)`}
            </button>
            {uploadDone && (
              <p className="mt-2 text-xs text-emerald-700">
                Submitted. The requester has been notified and will re-validate.
              </p>
            )}
          </section>
        </>
      )}

      {isTerminal && (
        <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-600">
          This request is closed. No further action required.
        </div>
      )}
    </div>
  );
}

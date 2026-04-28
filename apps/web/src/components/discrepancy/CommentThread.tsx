/**
 * CommentThread — collapsed-by-default comment list under a finding.
 *
 * Lists DiscrepancyComment rows oldest-first; the input posts a new
 * user comment. Recipient + system comments come from the same
 * endpoint and render with a small source badge.
 */

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { MessageSquare, Send } from "lucide-react";
import {
  isPersistedDiscrepancyId,
  listComments,
  postComment,
  type DiscrepancyComment,
} from "@/lib/lcopilot/discrepancyApi";

interface CommentThreadProps {
  discrepancyId: string | null | undefined;
}

const SOURCE_LABEL: Record<DiscrepancyComment["source"], string> = {
  user: "You",
  recipient: "Recipient",
  system: "System",
};

const SOURCE_COLOR: Record<DiscrepancyComment["source"], string> = {
  user: "text-neutral-700",
  recipient: "text-blue-700",
  system: "text-amber-700",
};

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function CommentThread({ discrepancyId }: CommentThreadProps) {
  const [expanded, setExpanded] = useState(false);
  const [comments, setComments] = useState<DiscrepancyComment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const valid = isPersistedDiscrepancyId(discrepancyId);
  const id = valid ? (discrepancyId as string) : null;

  const refresh = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const rows = await listComments(id);
      setComments(rows);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })
        ?.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : (err as Error).message ?? "Failed to load comments",
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (expanded) {
      void refresh();
    }
  }, [expanded, refresh]);

  if (!valid) return null;

  const handlePost = async () => {
    if (!id || !draft.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await postComment(id, draft.trim());
      setComments((prev) => [...prev, created]);
      setDraft("");
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })
        ?.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : (err as Error).message ?? "Failed to post comment",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="border-t border-neutral-200 pt-3 mt-3">
      <Button
        size="sm"
        variant="ghost"
        onClick={() => setExpanded((v) => !v)}
        className="text-xs h-7 text-muted-foreground hover:text-foreground"
      >
        <MessageSquare className="w-3.5 h-3.5 mr-1" />
        {expanded ? "Hide comments" : `Comments${comments.length ? ` (${comments.length})` : ""}`}
      </Button>

      {expanded && (
        <div className="mt-3 space-y-3">
          {loading && (
            <p className="text-xs text-muted-foreground">Loading…</p>
          )}

          {!loading && comments.length === 0 && !error && (
            <p className="text-xs text-muted-foreground italic">
              No comments yet.
            </p>
          )}

          {comments.length > 0 && (
            <ul className="space-y-2">
              {comments.map((c) => (
                <li
                  key={c.id}
                  className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className={`text-[10px] font-semibold uppercase tracking-wider ${SOURCE_COLOR[c.source]}`}>
                      {SOURCE_LABEL[c.source]}
                      {c.author_email && c.source !== "user" && (
                        <span className="ml-1 normal-case font-normal text-neutral-500">
                          {c.author_display_name || c.author_email}
                        </span>
                      )}
                    </span>
                    <span className="text-[10px] text-neutral-400">
                      {formatTimestamp(c.created_at)}
                    </span>
                  </div>
                  <p className="text-sm text-neutral-800 whitespace-pre-wrap">
                    {c.body}
                  </p>
                </li>
              ))}
            </ul>
          )}

          {error && <p className="text-xs text-rose-600">{error}</p>}

          <div className="space-y-2">
            <textarea
              rows={2}
              placeholder="Add a comment…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={submitting}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
            />
            <div className="flex justify-end">
              <Button
                size="sm"
                onClick={handlePost}
                disabled={submitting || !draft.trim()}
              >
                <Send className="w-3.5 h-3.5 mr-1" />
                {submitting ? "Posting…" : "Post"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

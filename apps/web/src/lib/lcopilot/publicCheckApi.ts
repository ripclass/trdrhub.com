/**
 * Client for the public, no-auth LC checker — POST /api/check.
 *
 * This is the free lead-magnet endpoint: it runs the full validation pipeline
 * anonymously and returns a trimmed result (verdict + finding count + the top
 * two findings). The full report / PDF / complete finding list are gated behind
 * sign-up. Rate-limited server-side to one run per IP per 24 h, so a second
 * attempt within the window returns HTTP 429.
 *
 * Deliberately uses plain `fetch` (not the authenticated axios client): the
 * endpoint is public, CSRF-exempt, and must work for a logged-out visitor.
 */

import { API_BASE_URL } from "@/api/client";

export interface PublicCheckFinding {
  title: string;
  severity: string;
}

export interface PublicCheckResult {
  verdict: string;
  verdict_label: string | null;
  verdict_color: string | null;
  finding_count: number;
  top_findings: PublicCheckFinding[];
  signup_cta: boolean;
}

export interface PublicCheckAvailability {
  available: boolean;
  retry_after_seconds?: number;
  signup_cta?: boolean;
}

export class PublicCheckRateLimitedError extends Error {
  retryAfterSeconds: number;
  constructor(message: string, retryAfterSeconds: number) {
    super(message);
    this.name = "PublicCheckRateLimitedError";
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export class PublicCheckError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "PublicCheckError";
    this.status = status;
  }
}

const CHECK_TIMEOUT_MS = 6 * 60 * 1000; // validation can take a couple of minutes

function detailMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const msg = (detail as { message?: unknown }).message;
    if (typeof msg === "string" && msg.trim()) return msg;
  }
  const msg = (body as { message?: unknown }).message;
  if (typeof msg === "string" && msg.trim()) return msg;
  return fallback;
}

function retryAfterFrom(body: unknown, headerValue: string | null): number {
  const fromHeader = headerValue ? parseInt(headerValue, 10) : NaN;
  if (Number.isFinite(fromHeader) && fromHeader > 0) return fromHeader;
  if (body && typeof body === "object") {
    const detail = (body as { detail?: { retry_after_seconds?: unknown } }).detail;
    const fromDetail =
      detail && typeof detail === "object" ? Number(detail.retry_after_seconds) : NaN;
    if (Number.isFinite(fromDetail) && fromDetail > 0) return fromDetail;
  }
  return 24 * 60 * 60;
}

/** Non-consuming probe — has this visitor already used today's free run? */
export async function getCheckAvailability(): Promise<PublicCheckAvailability> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/check/availability`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    if (res.status === 404) {
      // Feature disabled server-side — treat as available; the POST will 404 too.
      return { available: true };
    }
    if (!res.ok) return { available: true };
    return (await res.json()) as PublicCheckAvailability;
  } catch {
    return { available: true };
  }
}

/**
 * Run a free, anonymous LC check.
 *
 * @param files  The LC plus any supporting documents (PDFs / images).
 * @throws {PublicCheckRateLimitedError} on HTTP 429 (free run already used).
 * @throws {PublicCheckError}             on any other non-2xx response.
 */
export async function runPublicCheck(files: File[]): Promise<PublicCheckResult> {
  if (!files.length) {
    throw new PublicCheckError("Attach at least the Letter of Credit.", 400);
  }

  const form = new FormData();
  for (const file of files) {
    form.append("files", file, file.name);
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), CHECK_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/api/check`, {
      method: "POST",
      body: form,
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new PublicCheckError(
        "The check is taking longer than expected. Please try again with the document set.",
        408,
      );
    }
    throw new PublicCheckError("Network error — could not reach the checker. Please try again.", 0);
  }
  clearTimeout(timer);

  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }

  if (res.status === 429) {
    throw new PublicCheckRateLimitedError(
      detailMessage(
        body,
        "You've used today's free LC check. Create a free account to run more checks and export the full report.",
      ),
      retryAfterFrom(body, res.headers.get("Retry-After")),
    );
  }
  if (!res.ok) {
    throw new PublicCheckError(
      detailMessage(body, "We couldn't finish checking that document set. Please try again."),
      res.status,
    );
  }

  return body as PublicCheckResult;
}

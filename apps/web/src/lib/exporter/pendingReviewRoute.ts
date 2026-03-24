const PENDING_EXPORTER_REVIEW_ROUTE_KEY = "trdrhub_pending_exporter_review_route";
const EXPORTER_RESULTS_SECTIONS = new Set([
  "reviews",
  "documents",
  "issues",
  "extracted-data",
  "history",
  "customs",
]);

function normalizePendingExporterReviewRoute(candidate: string): string | null {
  try {
    const url = new URL(candidate, "https://trdrhub.local");
    if (url.pathname !== "/lcopilot/exporter-dashboard") {
      return null;
    }

    const section = url.searchParams.get("section");
    const jobId = url.searchParams.get("jobId");
    if (!section || !EXPORTER_RESULTS_SECTIONS.has(section) || !jobId?.trim()) {
      return null;
    }

    const normalizedSearch = url.searchParams.toString();
    return normalizedSearch ? `${url.pathname}?${normalizedSearch}` : url.pathname;
  } catch {
    return null;
  }
}

export function isPendingExporterReviewRoute(candidate: string): boolean {
  return normalizePendingExporterReviewRoute(candidate) !== null;
}

export function persistPendingExporterReviewRoute(candidate: string): void {
  if (typeof window === "undefined") {
    return;
  }

  const normalized = normalizePendingExporterReviewRoute(candidate);
  if (!normalized) {
    return;
  }

  window.sessionStorage.setItem(PENDING_EXPORTER_REVIEW_ROUTE_KEY, normalized);
}

export function readPendingExporterReviewRoute(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const stored = window.sessionStorage.getItem(PENDING_EXPORTER_REVIEW_ROUTE_KEY);
  if (!stored) {
    return null;
  }

  const normalized = normalizePendingExporterReviewRoute(stored);
  if (!normalized) {
    window.sessionStorage.removeItem(PENDING_EXPORTER_REVIEW_ROUTE_KEY);
    return null;
  }

  return normalized;
}

export function clearPendingExporterReviewRoute(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(PENDING_EXPORTER_REVIEW_ROUTE_KEY);
}

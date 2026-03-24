import { beforeEach, describe, expect, it } from "vitest";

import {
  clearPendingExporterReviewRoute,
  isPendingExporterReviewRoute,
  persistPendingExporterReviewRoute,
  readPendingExporterReviewRoute,
} from "@/lib/exporter/pendingReviewRoute";

describe("pending review route helpers", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("recognizes only exporter dashboard results routes with a job id", () => {
    expect(
      isPendingExporterReviewRoute(
        "/lcopilot/exporter-dashboard?section=reviews&jobId=job-123",
      ),
    ).toBe(true);
    expect(
      isPendingExporterReviewRoute(
        "/lcopilot/exporter-dashboard?section=documents&jobId=job-123",
      ),
    ).toBe(true);
    expect(isPendingExporterReviewRoute("/lcopilot/exporter-dashboard")).toBe(false);
    expect(
      isPendingExporterReviewRoute(
        "/lcopilot/exporter-dashboard?section=reviews",
      ),
    ).toBe(false);
    expect(
      isPendingExporterReviewRoute(
        "/lcopilot/importer-dashboard?section=reviews&jobId=job-123",
      ),
    ).toBe(false);
  });

  it("persists, reads, and clears a pending review route", () => {
    persistPendingExporterReviewRoute(
      "/lcopilot/exporter-dashboard?section=reviews&jobId=job-123&tab=documents",
    );

    expect(readPendingExporterReviewRoute()).toBe(
      "/lcopilot/exporter-dashboard?section=reviews&jobId=job-123&tab=documents",
    );

    clearPendingExporterReviewRoute();

    expect(readPendingExporterReviewRoute()).toBeNull();
  });

  it("ignores invalid routes and clears malformed stored values", () => {
    persistPendingExporterReviewRoute("/lcopilot/exporter-dashboard?section=overview");
    expect(readPendingExporterReviewRoute()).toBeNull();

    sessionStorage.setItem("trdrhub_pending_exporter_review_route", "not a route");
    expect(readPendingExporterReviewRoute()).toBeNull();
  });
});

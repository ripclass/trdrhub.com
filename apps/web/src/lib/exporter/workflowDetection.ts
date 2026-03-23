export type WorkflowDetectionSummary = {
  lc_type?: string;
  confidence?: number;
  reason?: string;
  source?: string;
  confidence_mode?: string;
  detection_basis?: string;
  is_draft?: boolean;
};

const isEstimatedWorkflowDetection = (detection?: WorkflowDetectionSummary | null): boolean =>
  Boolean(
    detection &&
      (String(detection.confidence_mode || "").toLowerCase() === "estimated" ||
        String(detection.detection_basis || "").toLowerCase() === "lane_only_context" ||
        /treating this as an (import|export) lc unless stronger contrary evidence appears/i.test(
          String(detection.reason || ""),
        )),
  );

export function formatWorkflowConfidenceBadgeLabel(
  confidence?: number | null,
  detection?: WorkflowDetectionSummary | null,
): string {
  if (isEstimatedWorkflowDetection(detection)) {
    return "Estimated workflow match";
  }
  if (typeof confidence !== "number" || Number.isNaN(confidence) || confidence <= 0) {
    return "Workflow confidence unavailable";
  }
  return `Workflow confidence: ${Math.round(confidence * 100)}%`;
}

export function getWorkflowDetectionStatusBadge(
  detection?: WorkflowDetectionSummary | null,
): string | null {
  if (!detection) return null;
  if (isEstimatedWorkflowDetection(detection)) {
    return "Workflow lane inferred";
  }
  return null;
}

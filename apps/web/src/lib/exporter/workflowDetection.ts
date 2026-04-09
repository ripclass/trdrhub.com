export type WorkflowDetectionSubtype = {
  primary_label?: string;
  labels?: string[];
  payment_mode?: "sight" | "usance" | "deferred" | "mixed" | "unknown";
  usance_days?: number | null;
  form?: "irrevocable" | "transferable" | "revolving" | "standby" | "unknown";
  confirmed?: boolean;
  rule_set?: string;
  standby?: boolean;
  transferable?: boolean;
  revolving?: boolean;
};

export type WorkflowDetectionSummary = {
  lc_type?: string;
  confidence?: number;
  reason?: string;
  source?: string;
  confidence_mode?: string;
  detection_basis?: string;
  is_draft?: boolean;
  subtype?: WorkflowDetectionSubtype | null;
};

/** Return the most specific human label we can emit for this LC's workflow.
 *
 * Falls back progressively: "Sight Export LC" -> "Export LC" -> "LC".
 */
export function getWorkflowPrimaryLabel(
  detection?: WorkflowDetectionSummary | null,
): string {
  if (!detection) return "LC";
  const subtype = detection.subtype;
  if (subtype && subtype.primary_label && subtype.primary_label.trim()) {
    return subtype.primary_label;
  }
  const lcType = String(detection.lc_type || "").toLowerCase();
  if (lcType === "export") return "Export LC";
  if (lcType === "import") return "Import LC";
  return "LC";
}

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

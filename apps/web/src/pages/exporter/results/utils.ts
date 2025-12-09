/**
 * Utility functions and constants for ExporterResults page
 * Extracted to reduce file size and improve maintainability
 */

// ============================================================================
// CONSTANTS
// ============================================================================

export const DOCUMENT_LABELS: Record<string, string> = {
  letter_of_credit: "Letter of Credit",
  commercial_invoice: "Commercial Invoice",
  bill_of_lading: "Bill of Lading",
  packing_list: "Packing List",
  insurance_certificate: "Insurance Certificate",
  certificate_of_origin: "Certificate of Origin",
  inspection_certificate: "Inspection Certificate",
  supporting_documents: "Supporting Documents",
};

// ============================================================================
// STRING FORMATTING UTILITIES
// ============================================================================

/**
 * Convert snake_case or kebab-case to Title Case
 */
export const humanizeLabel = (value: string): string =>
  value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());

/**
 * Safely convert any value to a displayable string - prevents React Error #31
 */
export const safeString = (value: any): string => {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "object") {
    if ("types" in value && Array.isArray(value.types)) {
      return value.types.join(", ");
    }
    return JSON.stringify(value);
  }
  return String(value);
};

/**
 * Format any extracted value to a human-readable string
 */
export const formatExtractedValue = (value: any): string => {
  if (value === null || value === undefined) {
    return "N/A";
  }
  if (Array.isArray(value)) {
    if (value.every((v) => typeof v === "string" || typeof v === "number")) {
      return value.join(", ");
    }
    return value.map((item) => formatExtractedValue(item)).join("; ");
  }
  if (typeof value === "object") {
    if ("types" in value && Array.isArray(value.types)) {
      return value.types.join(", ");
    }
    if ("text" in value && typeof value.text === "string") {
      return value.text;
    }
    if (("value" in value || "amount" in value) && "currency" in value) {
      const amt = value.value ?? value.amount ?? "";
      const cur = value.currency ?? "";
      return `${cur} ${Number(amt).toLocaleString()}`.trim();
    }
    if ("name" in value && typeof value.name === "string") {
      return value.name.replace(/\n+/g, ", ");
    }
    if ("loading" in value || "discharge" in value) {
      const parts = [];
      if (value.loading) parts.push(`Loading: ${value.loading}`);
      if (value.discharge) parts.push(`Discharge: ${value.discharge}`);
      return parts.join(" → ") || "N/A";
    }
    const entries = Object.entries(value).filter(([k, v]) => 
      v != null && typeof v !== "object" && !k.startsWith("_")
    );
    if (entries.length > 0 && entries.length <= 4) {
      return entries.map(([k, v]) => `${k}: ${v}`).join(", ");
    }
    try {
      const str = JSON.stringify(value);
      if (str.length > 200) {
        return `[Complex data - ${Object.keys(value).length} fields]`;
      }
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }
  return String(value);
};

/**
 * Format long text as bullet points
 * Splits by numbered items (1), 2), etc.), dashes, or newlines
 */
export const formatAsBulletPoints = (text: any): string[] => {
  if (!text) return [];
  
  const str = typeof text === "string" ? text : 
              typeof text === "object" && text.text ? text.text :
              typeof text === "object" && text.value ? text.value :
              String(text);
  
  // Check for numbered items: 1) 2) or 1. 2. patterns
  const numberedPattern = /(?:^|\n)\s*\d+[.)]\s*/;
  if (numberedPattern.test(str)) {
    return str
      .split(/(?:^|\n)\s*\d+[.)]\s*/)
      .map((s: string) => s.trim())
      .filter((s: string) => s.length > 0);
  }
  
  // Check for dash/bullet items
  if (str.includes('\n-') || str.includes('\n•') || str.includes('\n*')) {
    return str
      .split(/\n[-•*]\s*/)
      .map((s: string) => s.trim())
      .filter((s: string) => s.length > 0);
  }
  
  // Check for uppercase labeled items (e.g., "PACKING: ..." or "MARKING: ...")
  const labelPattern = /(?:^|\n)([A-Z][A-Z\s]+:)/;
  if (labelPattern.test(str)) {
    return str
      .split(/(?=(?:^|\n)[A-Z][A-Z\s]+:)/)
      .map((s: string) => s.trim())
      .filter((s: string) => s.length > 0);
  }
  
  // Check for period-separated sentences if text is long
  if (str.length > 200 && str.includes('. ')) {
    const sentences = str
      .split(/\.\s+(?=[A-Z])/)
      .map((s: string) => s.trim().replace(/\.$/, ''))
      .filter((s: string) => s.length > 10);
    if (sentences.length > 1) return sentences;
  }
  
  // Return as single item if no splitting pattern found
  return str.length > 0 ? [str] : [];
};

/**
 * Format additional conditions as a readable list
 * Handles multiple formats:
 * - Array of strings: ["condition 1", "condition 2"]
 * - Array of objects: [{text: "condition 1"}, {text: "condition 2"}]
 * - Single string (pipe or semicolon separated)
 */
export const formatConditions = (conditions: any): string[] => {
  if (!conditions) return [];
  
  // Handle single string (pipe or semicolon separated)
  if (typeof conditions === "string") {
    const delimiter = conditions.includes("|") ? "|" : 
                      conditions.includes(";") ? ";" : "\n";
    return conditions
      .split(delimiter)
      .map((s: string) => s.trim())
      .filter((s: string) => s.length > 0);
  }
  
  if (!Array.isArray(conditions)) return [];
  
  return conditions
    .map((c: any) => {
      // Handle plain strings
      if (typeof c === "string") return c.trim();
      // Handle objects with text property
      if (c && typeof c.text === "string") return c.text.trim();
      // Handle objects with value property
      if (c && typeof c.value === "string") return c.value.trim();
      // Handle objects with condition property
      if (c && typeof c.condition === "string") return c.condition.trim();
      return null;
    })
    .filter((c: string | null): c is string => c !== null && c.length > 0);
};

/**
 * Format amount value with currency
 */
export const formatAmountValue = (amount: any): string => {
  if (!amount) {
    return "";
  }
  if (typeof amount === "object") {
    const value = amount.value ?? amount.amount ?? amount.text ?? "";
    const currency = amount.currency ?? amount.curr ?? amount.ccy ?? "";
    const normalized = [value, currency].filter(Boolean).join(" ").trim();
    if (normalized) {
      return normalized;
    }
  }
  return formatExtractedValue(amount);
};

// ============================================================================
// SEVERITY UTILITIES
// ============================================================================

/**
 * Normalize discrepancy severity to standard values
 */
export const normalizeDiscrepancySeverity = (
  severity?: string | null
): "critical" | "major" | "minor" => {
  const value = (severity ?? "").toLowerCase();
  if (["critical", "fail", "error", "high"].includes(value)) {
    return "critical";
  }
  if (["warning", "warn", "major", "medium"].includes(value)) {
    return "major";
  }
  return "minor";
};

// ============================================================================
// FIELD CONFIDENCE UTILITIES
// ============================================================================

/**
 * Get status color class based on confidence/status
 */
export const getStatusColor = (
  confidence?: number,
  status?: string
): string => {
  if (status === 'trusted') return 'bg-emerald-500';
  if (status === 'review') return 'bg-amber-500';
  if (status === 'untrusted') return 'bg-red-500';
  if (confidence !== undefined) {
    if (confidence >= 0.8) return 'bg-emerald-500';
    if (confidence >= 0.5) return 'bg-amber-500';
    return 'bg-red-500';
  }
  return 'bg-gray-400';
};

/**
 * Get status label based on confidence/status
 */
export const getStatusLabel = (
  confidence?: number,
  status?: string
): string => {
  if (status === 'trusted') return 'Verified';
  if (status === 'review') return 'Review';
  if (status === 'untrusted') return 'Low Confidence';
  if (confidence !== undefined) {
    return `${Math.round(confidence * 100)}%`;
  }
  return '';
};

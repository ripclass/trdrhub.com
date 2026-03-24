/**
 * Document Details Drawer
 * 
 * Shows extracted fields for a document in a side drawer.
 * Used when clicking "View Details" on a document card.
 */

import { useEffect, useMemo, useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  FileText,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface DocumentForDrawer {
  id: string;
  name: string;
  filename?: string;
  type: string;
  documentType?: string;
  typeKey?: string;
  status: "success" | "warning" | "error";
  extractionStatus?: string;
  issuesCount: number;
  extractedFields: Record<string, any>;
  fieldDetails?: Record<string, any>;
  warningReasons?: string[];
  reviewReasons?: string[];
  criticalFieldStates?: Record<string, any>;
  fieldDiagnostics?: Record<string, any>;
  missingRequiredFields?: string[];
  rawText?: string;
  ocrConfidence?: number;
  sourceFormat?: string;
  isElectronicBL?: boolean;
  extractionResolution?: {
    required: boolean;
    unresolvedCount: number;
    summary: string;
    fields: Array<{
      fieldName: string;
      label: string;
      verification?: string;
      candidateValue?: unknown;
      normalizedValue?: unknown;
      evidenceSnippet?: string | null;
      evidenceSource?: string | null;
      page?: number | null;
      reason?: string;
      origin?: string | null;
    }>;
  };
  resolutionItems?: Array<{
    documentId: string;
    filename?: string;
    fieldName: string;
    label: string;
    verification: string;
    candidateValue?: unknown;
    normalizedValue?: unknown;
    evidenceSnippet?: string | null;
    evidenceSource?: string | null;
    page?: number | null;
    reason?: string;
    origin?: string | null;
  }>;
}

interface DocumentDetailsDrawerProps {
  document: DocumentForDrawer | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveFieldOverride?: (payload: {
    documentId: string;
    fieldName: string;
    overrideValue: string;
    verification?: "operator_confirmed" | "operator_rejected";
    note?: string;
  }) => Promise<void>;
  isSavingFieldOverride?: boolean;
}

const StatusIcon = ({ status }: { status: string }) => {
  switch (status) {
    case "success":
      return <CheckCircle className="w-4 h-4 text-success" />;
    case "warning":
      return <AlertTriangle className="w-4 h-4 text-warning" />;
    case "error":
      return <XCircle className="w-4 h-4 text-destructive" />;
    default:
      return <FileText className="w-4 h-4 text-muted-foreground" />;
  }
};

// Fields that should be displayed as bullet lists
const BULLET_LIST_FIELDS = [
  "goods_description",
  "goods",
  "description",
  "documents_required",
  "documents",
  "required",
  "additional_conditions",
  "conditions",
  "clauses",
  "requirements",
  "instructions",
  "47a",
  "terms",
  "charges",
];

// Parse a single item, cleaning up any array-like formatting
const cleanItemText = (item: string): string => {
  return item
    .replace(/^\[['"]?|['"]?\]$/g, '') // Remove array brackets
    .replace(/^['"]|['"]$/g, '')        // Remove quotes
    .replace(/^[•\-\*]\s*/, '')         // Remove existing bullets
    .replace(/^\d+[.)]\s*/, '')         // Remove numbered prefixes
    .trim();
};

const formatFieldValue = (value: any, fieldKey?: string): string | string[] => {
  if (value === null || value === undefined) return "—";
  
  // Handle string values
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return "—";
    
    // Check if it looks like a stringified array: ['item1', 'item2']
    if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
      try {
        const parsed = JSON.parse(trimmed.replace(/'/g, '"'));
        if (Array.isArray(parsed)) {
          return parsed.map(v => cleanItemText(String(v))).filter(Boolean);
        }
      } catch {
        // Not valid JSON, continue with string parsing
      }
    }
    
    // Split long text by common delimiters for better readability
    if (trimmed.length > 150) {
      // Try splitting by periods followed by space and capital letter (sentences)
      const sentencePattern = /\.\s+(?=[A-Z0-9])/;
      // Try splitting by numbered items
      const numberedPattern = /\s*\d+[.)]\s+/;
      // Try splitting by semicolons
      const semicolonPattern = /;\s*/;
      
      if (numberedPattern.test(trimmed)) {
        const parts = trimmed.split(numberedPattern).map(cleanItemText).filter(s => s.length > 0);
        if (parts.length > 1) return parts;
      }
      
      if (semicolonPattern.test(trimmed) && trimmed.split(semicolonPattern).length > 2) {
        const parts = trimmed.split(semicolonPattern).map(cleanItemText).filter(s => s.length > 0);
        if (parts.length > 1) return parts;
      }
    }
    
    return trimmed;
  }
  
  if (typeof value === "number") return value.toLocaleString();
  if (typeof value === "boolean") return value ? "Yes" : "No";
  
  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    // Return as array for bullet rendering
    const items = value.map(v => {
      if (typeof v === "string") return cleanItemText(v);
      if (v && typeof v.text === "string") return cleanItemText(v.text);
      if (v && typeof v.value === "string") return cleanItemText(v.value);
      if (v && typeof v.condition === "string") return cleanItemText(v.condition);
      return cleanItemText(String(v));
    }).filter(s => s.length > 0);
    
    return items.length > 0 ? items : "—";
  }
  
  if (typeof value === "object") {
    // Handle common nested structures
    if ("value" in value) return formatFieldValue(value.value, fieldKey);
    if ("name" in value) return formatFieldValue(value.name, fieldKey);
    if ("text" in value) return formatFieldValue(value.text, fieldKey);
    // Otherwise show as JSON
    return JSON.stringify(value, null, 2);
  }
  
  return String(value);
};

// Check if a field should be displayed as a bullet list
const shouldBeBulletList = (key: string, value: any): boolean => {
  // Always bullet arrays with multiple items
  if (Array.isArray(value) && value.length > 1) return true;
  
  // Check if field name suggests it should be a list
  const keyLower = key.toLowerCase();
  return BULLET_LIST_FIELDS.some(f => keyLower.includes(f));
};

const humanizeFieldName = (key: string): string => {
  // Common field name mappings
  const mappings: Record<string, string> = {
    lc_number: "LC Number",
    lc_type: "LC Type",
    bl_number: "B/L Number",
    bl_date: "B/L Date",
    port_of_loading: "Port of Loading",
    port_of_discharge: "Port of Discharge",
    goods_description: "Goods Description",
    total_amount: "Total Amount",
    invoice_number: "Invoice Number",
    invoice_date: "Invoice Date",
    hs_code: "HS Code",
    hs_codes: "HS Codes",
    shipper: "Shipper",
    consignee: "Consignee",
    notify_party: "Notify Party",
    vessel_name: "Vessel Name",
    voyage_number: "Voyage Number",
    container_number: "Container Number",
    seal_number: "Seal Number",
    gross_weight: "Gross Weight",
    net_weight: "Net Weight",
    measurement: "Measurement",
    number_of_packages: "Number of Packages",
    package_type: "Package Type",
    marks_and_numbers: "Marks & Numbers",
    packing_size_breakdown: "Packing Size Breakdown",
    dimensions: "Dimensions",
    exporter_bin: "Exporter BIN",
    exporter_tin: "Exporter TIN",
    freight_prepaid: "Freight Prepaid",
    on_board_date: "On Board Date",
    issue_date: "Issue Date",
    expiry_date: "Expiry Date",
    latest_shipment: "Latest Shipment",
    latest_shipment_date: "Latest Shipment Date",
    additional_conditions: "Additional Conditions (47A)",
    documents_required: "Required Documents",
    requirement_conditions: "Document Presentation Conditions",
    unmapped_requirements: "Requirement Text Needing Mapping",
    ucp_reference: "UCP Reference",
    incoterm: "Incoterm",
    beneficiary: "Beneficiary",
    applicant: "Applicant",
    issuing_bank: "Issuing Bank",
    advising_bank: "Advising Bank",
  };

  if (mappings[key]) return mappings[key];

  // Fallback: convert snake_case to Title Case
  return key
    .replace(/([A-Z])/g, " $1")
    .replace(/_/g, " ")
    .trim()
    .split(" ")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
};

type ReviewReasonContext = {
  docType?: string;
  rawText?: string;
  criticalFieldStates?: Record<string, any>;
  fieldDiagnostics?: Record<string, any>;
  missingRequiredFields?: string[];
};

const normalizeReviewFieldKey = (value: unknown): string =>
  String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");

const INVOICE_FAMILY_DOCUMENT_TYPES = new Set([
  "commercial_invoice",
  "proforma_invoice",
  "draft_bill_of_exchange",
  "promissory_note",
  "payment_receipt",
  "debit_note",
  "credit_note",
]);

const TRANSPORT_FAMILY_DOCUMENT_TYPES = new Set([
  "bill_of_lading",
  "ocean_bill_of_lading",
  "charter_party_bill_of_lading",
  "house_bill_of_lading",
  "master_bill_of_lading",
  "sea_waybill",
  "air_waybill",
  "multimodal_transport_document",
  "combined_transport_document",
  "railway_consignment_note",
  "road_transport_document",
  "courier_or_post_receipt_or_certificate_of_posting",
  "forwarders_certificate_of_receipt",
  "forwarder_certificate_of_receipt",
  "delivery_order",
  "mates_receipt",
  "shipping_company_certificate",
  "warehouse_receipt",
  "cargo_manifest",
]);

const resolvePreferredOverrideFieldKey = (
  docType: string | undefined,
  fieldName: string,
  extractedFields: Record<string, any>,
  fieldDetails: Record<string, any>,
): string => {
  const normalizedDocType = normalizeReviewFieldKey(docType);
  const normalizedField = normalizeReviewFieldKey(fieldName);
  const hasField = (candidate: string) =>
    Object.prototype.hasOwnProperty.call(fieldDetails || {}, candidate) ||
    Object.prototype.hasOwnProperty.call(extractedFields || {}, candidate);

  if (normalizedField === "issue_date") {
    if (INVOICE_FAMILY_DOCUMENT_TYPES.has(normalizedDocType) && hasField("invoice_date")) {
      return "invoice_date";
    }
    if (normalizedDocType === "packing_list" && hasField("document_date")) {
      return "document_date";
    }
    if (TRANSPORT_FAMILY_DOCUMENT_TYPES.has(normalizedDocType) && hasField("bl_date")) {
      return "bl_date";
    }
  }

  return normalizedField;
};

const textHasAnyPattern = (text: string, patterns: RegExp[]): boolean =>
  patterns.some((pattern) => pattern.test(text));

const isFieldMarkedMissing = (context: ReviewReasonContext, fieldName: string): boolean => {
  const key = normalizeReviewFieldKey(fieldName);
  const missingRequiredFields = Array.isArray(context.missingRequiredFields) ? context.missingRequiredFields : [];
  if (missingRequiredFields.some((field) => normalizeReviewFieldKey(field) === key)) {
    return true;
  }
  const criticalState = String((context.criticalFieldStates || {})[key] || "").trim().toLowerCase();
  if (criticalState === "missing" || criticalState === "failed") {
    return true;
  }
  const diagnosticState = String(((context.fieldDiagnostics || {})[key] || {}).state || "")
    .trim()
    .toLowerCase();
  return diagnosticState === "missing" || diagnosticState === "failed";
};

const buildSpecificFieldMissingReasons = (context: ReviewReasonContext): string[] => {
  const docType = normalizeReviewFieldKey(context.docType);
  const rawText = String(context.rawText || "");
  const reasons: string[] = [];

  if (INVOICE_FAMILY_DOCUMENT_TYPES.has(docType)) {
    const missingIssueDate = isFieldMarkedMissing(context, "issue_date");
    const missingGrossWeight = isFieldMarkedMissing(context, "gross_weight");
    const missingNetWeight = isFieldMarkedMissing(context, "net_weight");

    if (missingIssueDate) {
      reasons.push(
        textHasAnyPattern(rawText, [/\binvoice\s*date\b/i, /\bdate\b/i, /\bdated\b/i])
          ? "Invoice date could not be confirmed from the extracted content."
          : "Source invoice does not show an invoice date.",
      );
    }

    if (missingGrossWeight || missingNetWeight) {
      reasons.push(
        textHasAnyPattern(rawText, [/\bgross\s*weight\b/i, /\bgross\s*wt\b/i, /\bg\/w\b/i, /\bnet\s*weight\b/i, /\bnet\s*wt\b/i, /\bn\/w\b/i])
          ? "Gross or net weight could not be confirmed from the invoice extraction."
          : "This workflow confirms gross/net weight from the packing list or bill of lading, not from the invoice.",
      );
    }
  }

  if (docType === "packing_list" && isFieldMarkedMissing(context, "issue_date")) {
    reasons.push(
      textHasAnyPattern(rawText, [/\bpacking\s*list\s*date\b/i, /\bdate\b/i, /\bdated\b/i])
        ? "Packing-list date could not be confirmed from the extracted content."
        : "Source packing list does not clearly show a document date.",
    );
  }

  if (docType === "certificate_of_origin") {
    const missingExporter = isFieldMarkedMissing(context, "exporter_name");
    const missingImporter = isFieldMarkedMissing(context, "importer_name");
    const missingGoods = isFieldMarkedMissing(context, "goods_description");
    if (missingExporter || missingImporter || missingGoods) {
      const sourceShowsPartyOrGoods = textHasAnyPattern(rawText, [
        /\bexporter\b/i,
        /\bimporter\b/i,
        /\bgoods\s*description\b/i,
        /\bdescription\s+of\s+goods\b/i,
        /\bgoods\b/i,
        /\bcommodity\b/i,
      ]);
      reasons.push(
        sourceShowsPartyOrGoods
          ? "Exporter, importer, or goods details were present in the certificate but could not be fully confirmed from extraction."
          : "Certificate of origin is missing one or more core party or goods details required for review.",
      );
    }
  }

  return Array.from(new Set(reasons));
};

const humanizeReviewReason = (reason: string, context: ReviewReasonContext): string | null => {
  const key = String(reason || "").trim();
  const normalizedDocType = normalizeReviewFieldKey(context.docType);
  const specificMissingReasons = buildSpecificFieldMissingReasons(context);

  if (!key) {
    return null;
  }
  if (key === "LOW_CONFIDENCE_CRITICAL") {
    if (normalizedDocType === "packing_list") return "Packing-list detail needs manual review before clean presentation.";
    if (normalizedDocType === "beneficiary_certificate") return "Beneficiary certificate wording was recognized, but structured extraction is incomplete.";
    if (normalizedDocType === "weight_list" || normalizedDocType === "weight_certificate") return "Weight values were found, but document structure still needs manual confirmation.";
    if (normalizedDocType === "certificate_of_origin") return "Certificate of origin details need manual confirmation before clean presentation.";
    if (normalizedDocType === "insurance_certificate" || normalizedDocType === "insurance_policy") return "Insurance coverage details need manual confirmation before clean presentation.";
    if (TRANSPORT_FAMILY_DOCUMENT_TYPES.has(normalizedDocType)) return "Transport-document details need manual review before clean presentation.";
    return "Key required fields need manual review before clean presentation.";
  }
  if (key === "OCR_AUTH_ERROR") {
    if (TRANSPORT_FAMILY_DOCUMENT_TYPES.has(normalizedDocType)) return "Transport-document text extraction confidence is limited; visually confirm carrier, routing, and shipment wording.";
    if (normalizedDocType === "packing_list") return "Packing-list text extraction confidence is limited; visually confirm package, quantity, and weight details.";
    if (normalizedDocType === "certificate_of_origin") return "Certificate of origin text extraction confidence is limited; visually confirm origin and certifier details.";
    if (normalizedDocType === "beneficiary_certificate") return "Beneficiary certificate text extraction confidence is limited; visually confirm the required declaration wording.";
    if (normalizedDocType === "insurance_certificate" || normalizedDocType === "insurance_policy") return "Insurance text extraction confidence is limited; visually confirm coverage amount, risks, and certificate wording.";
    return "Text extraction confidence is limited; visually confirm the critical presentation fields.";
  }
  if (key === "LOW_CONFIDENCE") {
    if (TRANSPORT_FAMILY_DOCUMENT_TYPES.has(normalizedDocType)) return "Transport-document fields were extracted with limited confidence and need manual confirmation.";
    if (normalizedDocType === "packing_list") return "Packing-list fields were extracted with limited confidence and need manual confirmation.";
    return "Extraction confidence is limited for this document and needs manual confirmation.";
  }
  if (key === "REVIEW_REQUIRED") {
    return "This document requires manual review before clean presentation.";
  }
  if (key === "FIELD_NOT_FOUND" || /^field not found$/i.test(key)) {
    return specificMissingReasons[0] || "A required field could not be confirmed from the extracted content.";
  }
  if (key === "critical_issue_date_missing") {
    return specificMissingReasons.find((entry) => /date/i.test(entry)) || "Document date could not be confirmed from this file.";
  }
  if (key === "critical_gross_weight_missing" || key === "critical_net_weight_missing") {
    return (
      specificMissingReasons.find((entry) => /gross\/net weight|gross or net weight|gross weight|net weight/i.test(entry))
      || "Weight details could not be confirmed from this document."
    );
  }
  if (key.startsWith("missing:")) {
    const fieldName = key.split(":", 2)[1] || "";
    const fieldSpecific = specificMissingReasons.find((entry) =>
      entry.toLowerCase().includes(fieldName.replace(/_/g, " ")),
    );
    if (fieldSpecific) {
      return fieldSpecific;
    }
    return `${humanizeFieldName(fieldName)} could not be confirmed from this document.`;
  }
  return key.replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());
};

const buildDisplayFieldChecks = (
  criticalFieldStates: Record<string, any>,
  context: ReviewReasonContext,
): Array<[string, string]> => {
  const docType = normalizeReviewFieldKey(context.docType);

  return Object.entries(criticalFieldStates).flatMap(([key, value]) => {
    const normalizedKey = normalizeReviewFieldKey(key);
    const normalizedState = normalizeReviewFieldKey(value);

    if (!normalizedState) {
      return [];
    }

    if (INVOICE_FAMILY_DOCUMENT_TYPES.has(docType) && ["gross_weight", "net_weight", "issue_date"].includes(normalizedKey) && normalizedState === "missing") {
      return [];
    }
    if (docType === "packing_list" && normalizedKey === "issue_date" && normalizedState === "missing") {
      return [];
    }

    const label =
      normalizedState === "found"
        ? "confirmed"
        : normalizedState === "parse_failed"
        ? "needs review"
        : normalizedState === "missing" || normalizedState === "failed"
        ? "not confirmed"
        : String(value).replace(/_/g, " ");

    return [[key, label]];
  });
};

// Filter out internal/technical fields
const shouldShowField = (key: string): boolean => {
  const hiddenFields = [
    "_extraction_confidence",
    "_extraction_method",
    "_ai_provider",
    "_ai_confidence",
    "_field_details",
    "_status_counts",
    "_ensemble_metadata",
    "_source_format",
    "_is_electronic_bl",
    "mt700",
    "mt700_raw",
    "source",
    "timeline",
    "blocks",
    "raw",
    "raw_text",
    "lc_type_source",
    "lc_classification",
    "version",
  ];
  return !hiddenFields.includes(key) && !key.startsWith("_");
};

const buildFieldEvidenceNote = (detail: Record<string, any> | undefined): string | null => {
  if (!detail || typeof detail !== "object") {
    return null;
  }

  const verification = String(detail.verification || "").trim().toLowerCase();
  const evidence = detail.evidence && typeof detail.evidence === "object" ? detail.evidence : null;
  const snippet = typeof evidence?.snippet === "string" ? evidence.snippet.trim() : "";
  const source = typeof evidence?.source === "string" ? evidence.source.trim() : typeof detail.source === "string" ? detail.source.trim() : "";

  if (snippet && verification === "confirmed") {
    return `Confirmed from ${source || "source text"}: ${snippet}`;
  }
  if (snippet && verification === "text_supported") {
    return `Supported by ${source || "source text"}: ${snippet}`;
  }
  if (verification === "model_suggested") {
    return "Model suggested this value, but the source text did not confirm it directly.";
  }
  if (verification === "operator_confirmed") {
    return snippet
      ? `Operator confirmed for this session: ${snippet}`
      : "Confirmed by an operator for this validation session.";
  }
  if (verification === "operator_rejected") {
    return snippet
      ? `Operator rejected this suggested value for this session: ${snippet}`
      : "Operator rejected this suggested value for the current validation session.";
  }
  if (verification === "not_found") {
    return "The extraction pipeline did not confirm a value for this field.";
  }
  return snippet ? `${source || "Source evidence"}: ${snippet}` : null;
};

const isFactResolutionBackedDocument = (docType: string | undefined): boolean => {
  const normalized = normalizeReviewFieldKey(docType);
  return [
    "commercial_invoice",
    "proforma_invoice",
    "draft_bill_of_exchange",
    "promissory_note",
    "payment_receipt",
    "debit_note",
    "credit_note",
    "bill_of_lading",
    "ocean_bill_of_lading",
    "charter_party_bill_of_lading",
    "house_bill_of_lading",
    "master_bill_of_lading",
    "sea_waybill",
    "air_waybill",
    "multimodal_transport_document",
    "combined_transport_document",
    "railway_consignment_note",
    "road_transport_document",
    "forwarders_certificate_of_receipt",
    "forwarder_certificate_of_receipt",
    "delivery_order",
    "mates_receipt",
    "shipping_company_certificate",
    "warehouse_receipt",
    "cargo_manifest",
    "courier_or_post_receipt_or_certificate_of_posting",
    "packing_list",
    "certificate_of_origin",
    "gsp_form_a",
    "eur1_movement_certificate",
    "customs_declaration",
    "export_license",
    "import_license",
    "phytosanitary_certificate",
    "fumigation_certificate",
    "health_certificate",
    "veterinary_certificate",
    "sanitary_certificate",
    "cites_permit",
    "radiation_certificate",
    "insurance_certificate",
    "insurance_policy",
    "beneficiary_certificate",
    "beneficiary_statement",
    "manufacturer_certificate",
    "manufacturers_certificate",
    "conformity_certificate",
    "certificate_of_conformity",
    "non_manipulation_certificate",
    "halal_certificate",
    "kosher_certificate",
    "organic_certificate",
    "inspection_certificate",
    "pre_shipment_inspection",
    "quality_certificate",
    "weight_certificate",
    "weight_list",
    "measurement_certificate",
    "analysis_certificate",
    "lab_test_report",
    "sgs_certificate",
    "bureau_veritas_certificate",
    "intertek_certificate",
  ].includes(normalized);
};

const buildResolutionItemEvidenceNote = (
  item:
    | {
        evidenceSnippet?: string | null;
        evidenceSource?: string | null;
        verification?: string;
      }
    | undefined,
): string | null => {
  if (!item) return null;
  const verification = normalizeReviewFieldKey(item.verification);
  const snippet = typeof item.evidenceSnippet === "string" ? item.evidenceSnippet.trim() : "";
  const source = typeof item.evidenceSource === "string" ? item.evidenceSource.trim() : "";

  if (snippet && verification === "operator_confirmed") {
    return `Operator confirmed for this session: ${snippet}`;
  }
  if (snippet && verification === "operator_rejected") {
    return `Operator rejected this suggested value for this session: ${snippet}`;
  }
  if (snippet && verification === "confirmed") {
    return `Confirmed from ${source || "source text"}: ${snippet}`;
  }
  if (snippet) {
    return `${source || "Source evidence"}: ${snippet}`;
  }
  if (verification === "model_suggested") {
    return "Model suggested this value, but the source text did not confirm it directly.";
  }
  if (verification === "not_found" || verification === "unconfirmed") {
    return "The extraction pipeline did not confirm a value for this field.";
  }
  return null;
};

const buildManualResolutionGuidance = (
  fieldName: string,
  docType: string | undefined,
): string => {
  const normalizedField = normalizeReviewFieldKey(fieldName);
  const normalizedDocType = normalizeReviewFieldKey(docType);

  if (normalizedField.includes("date")) {
    return "Check the document header, title block, or any dated line near the top of the file. Only enter a date if the document shows it clearly.";
  }
  if (
    normalizedField.includes("issuer")
    || normalizedField.includes("bank")
    || normalizedField.includes("exporter")
    || normalizedField.includes("importer")
    || normalizedField.includes("beneficiary")
    || normalizedField.includes("applicant")
  ) {
    return "Check the named party blocks, signature area, or certifier section. Only enter the party name if it is clearly written in the source document.";
  }
  if (
    normalizedField.includes("amount")
    || normalizedField.includes("currency")
    || normalizedField.includes("price")
    || normalizedField.includes("value")
  ) {
    return "Check the totals section, amount line, or currency label. Only enter a value if the number and currency are clearly shown together.";
  }
  if (normalizedField.includes("weight") || normalizedField.includes("quantity")) {
    return "Check the totals or packing summary area where quantity, net weight, or gross weight are listed. Only enter the value if the label is clear.";
  }
  if (normalizedField.includes("lc_number") || normalizedField.includes("reference")) {
    return "Check the reference block or the document header for the LC number or document reference. Only enter it if the identifier is clearly labeled.";
  }
  if (TRANSPORT_FAMILY_DOCUMENT_TYPES.has(normalizedDocType)) {
    return "Review the main shipment summary, carrier block, and routing section. Only enter the value if the transport document shows it clearly.";
  }
  if (normalizedDocType === "certificate_of_origin") {
    return "Review the certificate body and certifier section. Only enter the value if the certificate states it clearly.";
  }
  return "Review the source document for a clearly labeled value before entering anything manually. If the file does not show it clearly, leave it unresolved for now.";
};

export function DocumentDetailsDrawer({
  document,
  open,
  onOpenChange,
  onSaveFieldOverride,
  isSavingFieldOverride = false,
}: DocumentDetailsDrawerProps) {
  const [showRawJson, setShowRawJson] = useState(false);
  const [copied, setCopied] = useState(false);
  const [selectedResolutionField, setSelectedResolutionField] = useState<string | null>(null);
  const [overrideValue, setOverrideValue] = useState("");
  const [overrideNote, setOverrideNote] = useState("");
  const [showManualOverrideEditor, setShowManualOverrideEditor] = useState(false);
  const resolvedDocument: DocumentForDrawer = document ?? {
    id: "",
    name: "",
    type: "",
    status: "warning",
    issuesCount: 0,
    extractedFields: {},
    fieldDetails: {},
    warningReasons: [],
    reviewReasons: [],
    criticalFieldStates: {},
    fieldDiagnostics: {},
    missingRequiredFields: [],
    rawText: "",
  };

  const extractedFields = resolvedDocument.extractedFields || {};
  const mergedFieldDetails =
    resolvedDocument.fieldDetails ||
    (extractedFields._field_details as Record<string, any> | undefined) ||
    {};
  const extractedFieldsWithMetadata =
    mergedFieldDetails && Object.keys(mergedFieldDetails).length > 0
      ? { ...extractedFields, _field_details: mergedFieldDetails }
      : extractedFields;
  const fieldEntries = Object.entries(extractedFieldsWithMetadata).filter(([key]) =>
    shouldShowField(key)
  );
  const warningReasons = (resolvedDocument.warningReasons || []).filter(Boolean);
  const reviewReasons = (resolvedDocument.reviewReasons || []).filter(Boolean);
  const criticalFieldStates = resolvedDocument.criticalFieldStates || {};
  const fieldDiagnostics = resolvedDocument.fieldDiagnostics || {};
  const reasonContext: ReviewReasonContext = {
    docType: resolvedDocument.typeKey || resolvedDocument.type,
    rawText: resolvedDocument.rawText,
    criticalFieldStates,
    fieldDiagnostics,
    missingRequiredFields: resolvedDocument.missingRequiredFields,
  };
  const reviewNotes = Array.from(
    new Set(
      [...warningReasons, ...reviewReasons]
        .map((reason) => humanizeReviewReason(String(reason), reasonContext))
        .filter((reason): reason is string => Boolean(reason)),
    ),
  );
  const displayFieldChecks = buildDisplayFieldChecks(criticalFieldStates, reasonContext);
  const hasQueueBackedResolution =
    isFactResolutionBackedDocument(resolvedDocument.documentType || resolvedDocument.typeKey || resolvedDocument.type) &&
    Array.isArray(resolvedDocument.resolutionItems);
  const resolvableFields = useMemo(() => {
    if (hasQueueBackedResolution) {
      return (resolvedDocument.resolutionItems || []).map((item) => ({
        key: normalizeReviewFieldKey(item.fieldName),
        currentValue:
          item.normalizedValue === null || item.normalizedValue === undefined
            ? item.candidateValue === null || item.candidateValue === undefined
              ? ""
              : String(item.candidateValue)
            : String(item.normalizedValue),
        label: item.label || humanizeFieldName(item.fieldName),
        verification: item.verification,
      }));
    }

    const candidates = new Map<string, { key: string; currentValue: string; label: string; verification: string }>();
    const addCandidate = (fieldName: string, verification = "not_found") => {
      const normalized = resolvePreferredOverrideFieldKey(
        resolvedDocument.documentType || resolvedDocument.typeKey || resolvedDocument.type,
        fieldName,
        extractedFields,
        mergedFieldDetails,
      );
      if (!normalized) return;
      const detail = mergedFieldDetails?.[normalized];
      const currentValueRaw =
        detail?.value ??
        extractedFields?.[normalized] ??
        extractedFields?.[fieldName];
      const currentValue =
        currentValueRaw === null || currentValueRaw === undefined ? "" : String(currentValueRaw);
      candidates.set(normalized, {
        key: normalized,
        currentValue,
        label: humanizeFieldName(normalized),
        verification,
      });
    };

    (resolvedDocument.extractionResolution?.fields || []).forEach((field) =>
      addCandidate(field.fieldName, field.verification || "not_found"),
    );
    (resolvedDocument.missingRequiredFields || []).forEach((field) => addCandidate(String(field), "not_found"));
    Object.entries(criticalFieldStates).forEach(([fieldName, state]) => {
      if (isFieldMarkedMissing({ ...reasonContext, criticalFieldStates }, fieldName)) {
        addCandidate(fieldName, String(state || "not_found"));
      }
    });
    Object.entries(mergedFieldDetails || {}).forEach(([fieldName, detail]) => {
      const verification = normalizeReviewFieldKey((detail as Record<string, any>)?.verification);
      if (verification && !["confirmed", "operator_confirmed"].includes(verification)) {
        addCandidate(fieldName, verification);
      }
    });

    return Array.from(candidates.values());
  }, [
    criticalFieldStates,
    extractedFields,
    hasQueueBackedResolution,
    mergedFieldDetails,
    reasonContext,
    resolvedDocument.missingRequiredFields,
    resolvedDocument.resolutionItems,
  ]);

  const activeResolutionField =
    (selectedResolutionField && resolvableFields.find((entry) => entry.key === selectedResolutionField)) ||
    resolvableFields[0] ||
    null;
  const activeResolutionDetail =
    activeResolutionField && mergedFieldDetails && typeof mergedFieldDetails === "object"
      ? mergedFieldDetails[activeResolutionField.key]
      : undefined;
  const activeResolutionItem =
    activeResolutionField && Array.isArray(resolvedDocument.resolutionItems)
      ? resolvedDocument.resolutionItems.find(
          (item) => normalizeReviewFieldKey(item.fieldName) === activeResolutionField.key,
        )
      : undefined;
  const activeResolutionEvidenceNote =
    buildResolutionItemEvidenceNote({
      evidenceSnippet: activeResolutionItem?.evidenceSnippet,
      evidenceSource: activeResolutionItem?.evidenceSource,
      verification: activeResolutionItem?.verification,
    }) || buildFieldEvidenceNote(activeResolutionDetail);
  const activeResolutionCandidateValue = useMemo(() => {
    const rawValue =
      activeResolutionItem?.normalizedValue ??
      activeResolutionItem?.candidateValue ??
      activeResolutionDetail?.value ??
      activeResolutionField?.currentValue ??
      "";
    return rawValue === null || rawValue === undefined ? "" : String(rawValue).trim();
  }, [activeResolutionDetail, activeResolutionField, activeResolutionItem]);
  const activeResolutionHasCandidate = activeResolutionCandidateValue.length > 0;
  const activeResolutionVerificationLabel = useMemo(() => {
    const verification = normalizeReviewFieldKey(
      activeResolutionItem?.verification || activeResolutionDetail?.verification || activeResolutionField?.verification,
    );
    if (verification === "text_supported") return "Text-supported candidate";
    if (verification === "model_suggested") return "Model-suggested candidate";
    if (verification === "operator_confirmed") return "Operator-confirmed value";
    if (verification === "operator_rejected") return "Rejected candidate";
    if (verification === "not_found") return "No candidate value found";
    return verification ? humanizeFieldName(verification) : "Unresolved field";
  }, [activeResolutionDetail, activeResolutionField, activeResolutionItem]);
  const activeResolutionManualGuidance = useMemo(
    () =>
      activeResolutionField
        ? buildManualResolutionGuidance(
            activeResolutionField.key,
            resolvedDocument.documentType || resolvedDocument.typeKey || resolvedDocument.type,
          )
        : "",
    [
      activeResolutionField,
      resolvedDocument.documentType,
      resolvedDocument.type,
      resolvedDocument.typeKey,
    ],
  );

  useEffect(() => {
    if (!open) {
      return;
    }
    if (!activeResolutionField) {
      setSelectedResolutionField(null);
      setOverrideValue("");
      setOverrideNote("");
      return;
    }
    if (selectedResolutionField !== activeResolutionField.key) {
      setSelectedResolutionField(activeResolutionField.key);
      setOverrideValue(activeResolutionField.currentValue ?? "");
      setOverrideNote("");
      setShowManualOverrideEditor(false);
    }
  }, [activeResolutionField, open, selectedResolutionField]);

  const handleSelectResolutionField = (fieldName: string) => {
    const nextField = resolvableFields.find((entry) => entry.key === fieldName);
    setSelectedResolutionField(fieldName);
    setOverrideValue(nextField?.currentValue ?? "");
    setOverrideNote("");
    setShowManualOverrideEditor(false);
  };

  const persistFieldOverride = async (
    value: string,
    verification: "operator_confirmed" | "operator_rejected" = "operator_confirmed",
  ) => {
    if (!resolvedDocument.id || !activeResolutionField || !onSaveFieldOverride) {
      return;
    }
    const trimmedValue = value.trim();
    if (!trimmedValue) {
      return;
    }
    await onSaveFieldOverride({
      documentId: resolvedDocument.id,
      fieldName: activeResolutionField.key,
      overrideValue: trimmedValue,
      verification,
      note: overrideNote.trim() || undefined,
    });
    setOverrideNote("");
  };

  const handleSaveFieldOverride = async () => {
    await persistFieldOverride(overrideValue);
  };

  const handleConfirmSuggestedValue = async () => {
    await persistFieldOverride(activeResolutionCandidateValue);
  };

  const handleRejectSuggestedValue = async () => {
    await persistFieldOverride(activeResolutionCandidateValue, "operator_rejected");
  };

  const extractionStatus = (resolvedDocument.extractionStatus ?? '').toLowerCase();
  const extractionModeLabel = (() => {
    if (extractionStatus === 'text_only') return 'Text extraction';
    if (['success', 'partial', 'structured'].includes(extractionStatus)) return 'Structured extraction';
    if (['error', 'failed', 'empty'].includes(extractionStatus)) return 'Extraction failed';
    return null;
  })();
  const extractionModeClass =
    extractionStatus === 'text_only'
      ? 'bg-amber-500/10 text-amber-600 border-amber-500/30'
      : ['error', 'failed', 'empty'].includes(extractionStatus)
      ? 'bg-destructive/10 text-destructive border-destructive/30'
      : 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30';

  // Group fields by category
  const identificationFields = fieldEntries.filter(([key]) =>
    ["lc_number", "bl_number", "invoice_number", "reference", "number"].some(k =>
      key.toLowerCase().includes(k)
    )
  );
  const dateFields = fieldEntries.filter(([key]) =>
    key.toLowerCase().includes("date")
  );
  const partyFields = fieldEntries.filter(([key]) =>
    ["applicant", "beneficiary", "shipper", "consignee", "notify", "bank"].some(
      k => key.toLowerCase().includes(k)
    )
  );
  const locationFields = fieldEntries.filter(([key]) =>
    ["port", "place", "country", "origin", "destination"].some(k =>
      key.toLowerCase().includes(k)
    )
  );
  const otherFields = fieldEntries.filter(
    ([key]) =>
      !identificationFields.some(([k]) => k === key) &&
      !dateFields.some(([k]) => k === key) &&
      !partyFields.some(([k]) => k === key) &&
      !locationFields.some(([k]) => k === key)
  );

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(extractedFields, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderFieldGroup = (
    title: string,
    fields: [string, any][],
    defaultOpen = true
  ) => {
    if (fields.length === 0) return null;

    return (
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
          {title}
        </h4>
        <div className="space-y-2">
          {fields.map(([key, value]) => {
            const formatted = formatFieldValue(value, key);
            const fieldDetail =
              mergedFieldDetails && typeof mergedFieldDetails === "object"
                ? mergedFieldDetails[key]
                : undefined;
            const evidenceNote = buildFieldEvidenceNote(fieldDetail);
            const isBulletField = shouldBeBulletList(key, value);
            
            // Determine if we should render as bullet list
            const bulletItems: string[] = Array.isArray(formatted) 
              ? formatted 
              : (isBulletField && typeof formatted === "string" && formatted.length > 100)
                ? [formatted] // Single long item still gets special treatment
                : [];
            
            const showAsBullets = bulletItems.length > 1;
            
            return (
              <div
                key={key}
                className="flex flex-col gap-1 p-3 rounded-md bg-muted/30 hover:bg-muted/50 transition-colors"
              >
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  {humanizeFieldName(key)}
                </span>
                {showAsBullets ? (
                  <ul className="text-sm space-y-2 mt-1">
                    {bulletItems.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-primary mt-1.5 flex-shrink-0">•</span>
                        <span className="break-words leading-relaxed">{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-sm break-words whitespace-pre-wrap leading-relaxed">
                    {Array.isArray(formatted) ? formatted.join(", ") : formatted}
                  </span>
                )}
                {evidenceNote && (
                  <span className="text-xs text-muted-foreground leading-relaxed">
                    {evidenceNote}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  if (!document) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-hidden flex flex-col">
        <SheetHeader className="space-y-3">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "p-2 rounded-lg",
                resolvedDocument.status === "success" && "bg-success/10",
                resolvedDocument.status === "warning" && "bg-warning/10",
                resolvedDocument.status === "error" && "bg-destructive/10"
              )}
            >
              <StatusIcon status={resolvedDocument.status} />
            </div>
            <div className="flex-1 min-w-0">
              <SheetTitle className="truncate">{resolvedDocument.name}</SheetTitle>
              <SheetDescription className="truncate">
                {resolvedDocument.type}
              </SheetDescription>
            </div>
          </div>

          {/* Status badges */}
          <div className="flex flex-wrap gap-2">
            <Badge
              variant={resolvedDocument.status === "success" ? "default" : "outline"}
              className={cn(
                resolvedDocument.status === "success" &&
                  "bg-success/10 text-success border-success/20",
                resolvedDocument.status === "warning" &&
                  "bg-warning/10 text-warning border-warning/20",
                resolvedDocument.status === "error" &&
                  "bg-destructive/10 text-destructive border-destructive/20"
              )}
            >
              {resolvedDocument.status === "success"
                ? "Verified"
                : resolvedDocument.status === "warning"
                ? "Review"
                : "Issues"}
            </Badge>
            {resolvedDocument.issuesCount > 0 && (
              <Badge variant="outline" className="border-warning/30 text-warning">
                {resolvedDocument.issuesCount} issue{resolvedDocument.issuesCount > 1 ? "s" : ""}
              </Badge>
            )}
            {extractionModeLabel && (
              <Badge variant="outline" className={cn("text-xs", extractionModeClass)}>
                {extractionModeLabel}
              </Badge>
            )}
            {resolvedDocument.sourceFormat && (
              <Badge
                variant="outline"
                className={cn(
                  "text-xs",
                  resolvedDocument.isElectronicBL
                    ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
                    : resolvedDocument.sourceFormat.includes("ISO")
                    ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
                    : resolvedDocument.sourceFormat.includes("MT")
                    ? "bg-blue-500/10 text-blue-600 border-blue-500/30"
                    : "bg-gray-500/10"
                )}
              >
                {document.isElectronicBL ? "🔗 " : ""}
                {document.sourceFormat}
              </Badge>
            )}
            {resolvedDocument.ocrConfidence && resolvedDocument.ocrConfidence < 100 && (
              <Badge variant="outline" className="text-xs">
                OCR: {Math.round(resolvedDocument.ocrConfidence)}%
              </Badge>
            )}
          </div>
        </SheetHeader>

        <Separator className="my-4" />

        <ScrollArea className="flex-1 -mx-6 px-6">
          <div className="space-y-6 pb-6">
            {reviewNotes.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                  Review Notes
                </h4>
                <div className="flex flex-wrap gap-2">
                  {reviewNotes.map((reason, idx) => (
                    <Badge key={`reason-${idx}`} variant="outline" className="border-amber-500/30 text-amber-700 bg-amber-500/5">
                      {reason}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {displayFieldChecks.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                  Field Checks
                </h4>
                <div className="space-y-2">
                  {displayFieldChecks.map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between p-3 rounded-md bg-muted/30">
                      <span className="text-sm font-medium">{humanizeFieldName(key)}</span>
                      <Badge variant="outline" className="text-xs">{String(value)}</Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {resolvableFields.length > 0 && onSaveFieldOverride && (
              <div className="space-y-3 rounded-lg border border-dashed border-primary/30 bg-primary/5 p-4">
                <div className="space-y-1">
                  <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                    Confirm Unresolved Fields
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Confirm or correct only the fields the system could not confidently establish from the uploaded source. Saving updates this same session and refreshes the results without starting a new paid validation run.
                  </p>
                </div>
                {resolvedDocument.extractionResolution?.summary && (
                  <div className="rounded-md border border-primary/20 bg-background/70 p-3 text-sm text-muted-foreground">
                    {resolvedDocument.extractionResolution.summary}
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  {resolvableFields.map((field) => (
                    <Button
                      key={field.key}
                      type="button"
                      variant={activeResolutionField?.key === field.key ? "default" : "outline"}
                      size="sm"
                      onClick={() => handleSelectResolutionField(field.key)}
                    >
                      {field.label}
                    </Button>
                  ))}
                </div>
                {activeResolutionField && (
                  <div className="space-y-3">
                    <div className="rounded-md border border-border/60 bg-background/70 p-3 space-y-1">
                      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Source Basis
                      </p>
                      <p className="text-sm">
                        {activeResolutionEvidenceNote || "No direct source snippet was confirmed yet. Review the source document and enter the value you can verify."}
                      </p>
                    </div>
                    {activeResolutionHasCandidate && !showManualOverrideEditor && (
                      <div className="rounded-md border border-primary/20 bg-background/70 p-3 space-y-3">
                        <div className="flex items-center justify-between gap-3 flex-wrap">
                          <div>
                            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                              Suggested value
                            </p>
                            <p className="text-sm font-semibold">{activeResolutionCandidateValue}</p>
                          </div>
                          <Badge variant="outline" className="border-primary/20 text-primary">
                            {activeResolutionVerificationLabel}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          If this matches the source document, confirm it directly. If it does not, reject the suggestion or edit the value before saving.
                        </p>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            onClick={handleConfirmSuggestedValue}
                            disabled={isSavingFieldOverride}
                          >
                            {isSavingFieldOverride ? "Saving..." : "Confirm suggested value"}
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => {
                              setOverrideValue(activeResolutionCandidateValue);
                              setShowManualOverrideEditor(true);
                            }}
                              disabled={isSavingFieldOverride}
                            >
                              Edit value instead
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              onClick={handleRejectSuggestedValue}
                              disabled={isSavingFieldOverride}
                            >
                              {isSavingFieldOverride ? "Saving..." : "Reject suggested value"}
                            </Button>
                          </div>
                        </div>
                      )}
                    {!activeResolutionHasCandidate && !showManualOverrideEditor && (
                      <div className="rounded-md border border-primary/20 bg-background/70 p-3 space-y-3">
                        <div className="flex items-center justify-between gap-3 flex-wrap">
                          <div>
                            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                              No suggested value yet
                            </p>
                            <p className="text-sm">
                              The system could not propose a reliable value for this field from the uploaded document.
                            </p>
                          </div>
                          <Badge variant="outline" className="border-primary/20 text-primary">
                            {activeResolutionVerificationLabel}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {activeResolutionManualGuidance}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          If you cannot clearly confirm this value from the source document, leave it unresolved for now and continue with the other fields.
                        </p>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => setShowManualOverrideEditor(true)}
                            disabled={isSavingFieldOverride}
                          >
                            Enter value manually
                          </Button>
                        </div>
                      </div>
                    )}
                    {showManualOverrideEditor && (
                      <div className="space-y-2">
                        <Label htmlFor="field-override-value">
                          {activeResolutionHasCandidate ? "Edit confirmed value" : "Confirmed value"}
                        </Label>
                        <Input
                          id="field-override-value"
                          value={overrideValue}
                          onChange={(event) => setOverrideValue(event.target.value)}
                          placeholder={
                            activeResolutionHasCandidate
                              ? `Enter ${activeResolutionField.label.toLowerCase()}`
                              : `Enter only if you can confirm ${activeResolutionField.label.toLowerCase()} from the source`
                          }
                        />
                      </div>
                    )}
                    {(activeResolutionHasCandidate || showManualOverrideEditor) && (
                      <div className="space-y-2">
                        <Label htmlFor="field-override-note">Operator note</Label>
                        <Textarea
                          id="field-override-note"
                          value={overrideNote}
                          onChange={(event) => setOverrideNote(event.target.value)}
                          placeholder="Optional note about how this value was confirmed from the source."
                          rows={3}
                        />
                      </div>
                    )}
                    {showManualOverrideEditor && (
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          onClick={handleSaveFieldOverride}
                          disabled={!overrideValue.trim() || isSavingFieldOverride}
                        >
                          {isSavingFieldOverride ? "Saving..." : activeResolutionHasCandidate ? "Save edited value" : "Confirm field value"}
                        </Button>
                        {!activeResolutionHasCandidate && (
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => {
                              setOverrideValue("");
                              setOverrideNote("");
                              setShowManualOverrideEditor(false);
                            }}
                            disabled={isSavingFieldOverride}
                          >
                            Back to source guidance
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {fieldEntries.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-2">
                  No structured fields extracted
                </p>
                <p className="text-sm text-muted-foreground">
                  {extractionStatus === 'text_only'
                    ? "Text-only extraction is available. Review the raw document for details."
                    : "This document may be a scanned image or unsupported format."}
                </p>
              </div>
            ) : (
              <>
                {renderFieldGroup("Identification", identificationFields)}
                {renderFieldGroup("Dates", dateFields)}
                {renderFieldGroup("Parties", partyFields)}
                {renderFieldGroup("Locations", locationFields)}
                {renderFieldGroup("Other Details", otherFields)}
              </>
            )}

            {/* Raw JSON toggle */}
            {fieldEntries.length > 0 && (
              <div className="pt-4">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-between text-muted-foreground"
                  onClick={() => setShowRawJson(!showRawJson)}
                >
                  <span>View Raw JSON</span>
                  {showRawJson ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </Button>
                {showRawJson && (
                  <div className="mt-2 relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute top-2 right-2 h-8 w-8 p-0"
                      onClick={handleCopyJson}
                    >
                      {copied ? (
                        <Check className="w-4 h-4 text-success" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                    <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto max-h-64 whitespace-pre-wrap">
                      {JSON.stringify(extractedFields, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

export default DocumentDetailsDrawer;


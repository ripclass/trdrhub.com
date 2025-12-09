/**
 * Document Details Drawer
 * 
 * Shows extracted fields for a document in a side drawer.
 * Used when clicking "View Details" on a document card.
 */

import { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
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
  typeKey?: string;
  status: "success" | "warning" | "error";
  extractionStatus?: string;
  issuesCount: number;
  extractedFields: Record<string, any>;
  ocrConfidence?: number;
  sourceFormat?: string;
  isElectronicBL?: boolean;
}

interface DocumentDetailsDrawerProps {
  document: DocumentForDrawer | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
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
  "documents_required",
  "additional_conditions",
  "conditions",
  "clauses",
  "requirements",
  "instructions",
];

const formatFieldValue = (value: any): string | string[] => {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value.trim() || "—";
  if (typeof value === "number") return value.toLocaleString();
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    // Return as array for bullet rendering
    return value.map(v => {
      if (typeof v === "string") return v.trim();
      if (v && typeof v.text === "string") return v.text.trim();
      if (v && typeof v.value === "string") return v.value.trim();
      return String(v);
    }).filter(Boolean);
  }
  if (typeof value === "object") {
    // Handle common nested structures
    if ("value" in value) return formatFieldValue(value.value);
    if ("name" in value) return formatFieldValue(value.name);
    if ("text" in value) return formatFieldValue(value.text);
    // Otherwise show as JSON
    return JSON.stringify(value, null, 2);
  }
  return String(value);
};

// Parse long text into bullet points
const parseTextToBullets = (text: string): string[] => {
  if (!text || text.length < 100) return [];
  
  // Check for numbered items: 1) 2) or 1. 2. patterns
  const numberedPattern = /(?:^|\n)\s*\d+[.)]\s*/;
  if (numberedPattern.test(text)) {
    return text
      .split(/(?:^|\n)\s*\d+[.)]\s*/)
      .map(s => s.trim())
      .filter(s => s.length > 0);
  }
  
  // Check for uppercase labeled items
  const labelPattern = /(?:^|\n)([A-Z][A-Z\s]+:)/;
  if (labelPattern.test(text)) {
    return text
      .split(/(?=(?:^|\n)[A-Z][A-Z\s]+:)/)
      .map(s => s.trim())
      .filter(s => s.length > 0);
  }
  
  return [];
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
    freight_prepaid: "Freight Prepaid",
    on_board_date: "On Board Date",
    issue_date: "Issue Date",
    expiry_date: "Expiry Date",
    latest_shipment: "Latest Shipment",
    additional_conditions: "Additional Conditions (47A)",
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

export function DocumentDetailsDrawer({
  document,
  open,
  onOpenChange,
}: DocumentDetailsDrawerProps) {
  const [showRawJson, setShowRawJson] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!document) return null;

  const extractedFields = document.extractedFields || {};
  const fieldEntries = Object.entries(extractedFields).filter(([key]) =>
    shouldShowField(key)
  );

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
            const formatted = formatFieldValue(value);
            const isBulletField = BULLET_LIST_FIELDS.some(f => key.toLowerCase().includes(f));
            
            // Check if we should render as bullet list
            let bulletItems: string[] = [];
            if (Array.isArray(formatted)) {
              bulletItems = formatted;
            } else if (isBulletField && typeof formatted === "string") {
              bulletItems = parseTextToBullets(formatted);
            }
            
            return (
              <div
                key={key}
                className="flex flex-col gap-1 p-2 rounded-md bg-muted/30 hover:bg-muted/50 transition-colors"
              >
                <span className="text-xs text-muted-foreground">
                  {humanizeFieldName(key)}
                </span>
                {bulletItems.length > 1 ? (
                  <ul className="text-sm font-medium space-y-1 list-disc list-inside pl-1">
                    {bulletItems.map((item, idx) => (
                      <li key={idx} className="break-words">{item}</li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-sm font-medium break-words whitespace-pre-wrap">
                    {Array.isArray(formatted) ? formatted.join(", ") : formatted}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-hidden flex flex-col">
        <SheetHeader className="space-y-3">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "p-2 rounded-lg",
                document.status === "success" && "bg-success/10",
                document.status === "warning" && "bg-warning/10",
                document.status === "error" && "bg-destructive/10"
              )}
            >
              <StatusIcon status={document.status} />
            </div>
            <div className="flex-1 min-w-0">
              <SheetTitle className="truncate">{document.name}</SheetTitle>
              <SheetDescription className="truncate">
                {document.type}
              </SheetDescription>
            </div>
          </div>

          {/* Status badges */}
          <div className="flex flex-wrap gap-2">
            <Badge
              variant={document.status === "success" ? "default" : "outline"}
              className={cn(
                document.status === "success" &&
                  "bg-success/10 text-success border-success/20",
                document.status === "warning" &&
                  "bg-warning/10 text-warning border-warning/20",
                document.status === "error" &&
                  "bg-destructive/10 text-destructive border-destructive/20"
              )}
            >
              {document.status === "success"
                ? "Verified"
                : document.status === "warning"
                ? "Review"
                : "Issues"}
            </Badge>
            {document.issuesCount > 0 && (
              <Badge variant="outline" className="border-warning/30 text-warning">
                {document.issuesCount} issue{document.issuesCount > 1 ? "s" : ""}
              </Badge>
            )}
            {document.sourceFormat && (
              <Badge
                variant="outline"
                className={cn(
                  "text-xs",
                  document.isElectronicBL
                    ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
                    : document.sourceFormat.includes("ISO")
                    ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
                    : document.sourceFormat.includes("MT")
                    ? "bg-blue-500/10 text-blue-600 border-blue-500/30"
                    : "bg-gray-500/10"
                )}
              >
                {document.isElectronicBL ? "🔗 " : ""}
                {document.sourceFormat}
              </Badge>
            )}
            {document.ocrConfidence && document.ocrConfidence < 100 && (
              <Badge variant="outline" className="text-xs">
                OCR: {Math.round(document.ocrConfidence)}%
              </Badge>
            )}
          </div>
        </SheetHeader>

        <Separator className="my-4" />

        <ScrollArea className="flex-1 -mx-6 px-6">
          <div className="space-y-6 pb-6">
            {fieldEntries.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-2">
                  No structured fields extracted
                </p>
                <p className="text-sm text-muted-foreground">
                  This document may be a scanned image or unsupported format.
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


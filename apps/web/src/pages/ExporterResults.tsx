import { useState, useEffect, useMemo, useRef, useCallback, type ReactElement } from "react";
import { Link, useSearchParams, useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { logger } from "@/lib/logger";

// Module-specific logger for LCopilot results
const resultsLogger = logger.createLogger('LCopilot');
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/ui/status-badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { 
  FileText, 
  Download, 
  ArrowLeft, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Eye,
  RefreshCw,
  Share2,
  PrinterIcon,
  Clock,
  Package,
  TrendingUp,
  Receipt,
  Send,
  History,
  Building2,
  FileCheck,
  X,
  Loader2,
  Lightbulb,
  ShieldCheck,
  Sparkles
} from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { format } from "date-fns";
import { exporterApi, type BankSubmissionRead, type SubmissionEventRead, type GuardrailCheckResponse, type CustomsPackManifest } from "@/api/exporter";
import { useCanonicalJobResult } from "@/hooks/use-lcopilot";
import type {
  ValidationResults,
  IssueCard,
  AIEnrichmentPayload,
  ReferenceIssue,
  LcClassification,
  LcClassificationRequiredDocument,
} from "@/types/lcopilot";
import { isExporterFeatureEnabled } from "@/config/exporterFeatureFlags";
import { ExporterIssueCard } from "@/components/exporter/ExporterIssueCard";
import { ReviewFindingCard, type ReviewFindingCardData } from "@/components/exporter/ReviewFindingCard";
// LcHeader removed - LC info now shown inline in SummaryStrip
// RiskPanel removed - action items now only in Issues tab
import SummaryStrip from "@/components/lcopilot/SummaryStrip";
import { getExporterOverviewTruth, getExporterPresentationTruth } from "@/lib/exporter/overviewTruth";
// Extracted components and utilities from ExporterResults
import {
  BankVerdictCard,
  BankProfileBadge,
  OCRConfidenceWarning,
  AmendmentCard,
  ToleranceBadge,
  SubmissionHistoryCard,
  // Utilities
  DOCUMENT_LABELS,
  humanizeLabel,
  safeString,
  formatExtractedValue,
  formatConditions,
  formatAmountValue,
  normalizeDiscrepancySeverity,
  getStatusColor,
  getStatusLabel,
  // Types
  type BankVerdict,
  type BankVerdictActionItem,
  type BankProfile,
  type ExtractionConfidence,
  type Amendment,
  type AmendmentsAvailable,
  type AmendmentFieldChange,
  type ToleranceApplied,
} from "./exporter/results";
import { HistoryTab, AnalyticsTab, IssuesTab } from "./exporter/results/tabs";
import type { EmailDraftContext } from "@/components/exporter/HowToFixSection";
import { EmailDraftDialog } from "@/components/exporter/EmailDraftDialog";
import { DEFAULT_TAB, isResultsTab, type ResultsTab } from "@/components/lcopilot/dashboardTabs";
import { cn } from "@/lib/utils";
import { BlockedValidationCard } from "@/components/validation/ValidationStatusBanner";
import { DocumentDetailsDrawer, type DocumentForDrawer } from "@/components/lcopilot/DocumentDetailsDrawer";
import { deriveValidationState } from "@/lib/validation/validationState";
import { getCanonicalResultTruth } from "@/lib/lcopilot/resultTruth";
import {
  SPECIAL_CONDITIONS_PLACEHOLDER_TEXT,
  summarizeSpecialConditions,
} from "@/lib/exporter/specialConditions";

type ExporterResultsProps = {
  embedded?: boolean;
  jobId?: string;
  lcNumber?: string;
  initialTab?: ResultsTab;
  onTabChange?: (tab: ResultsTab) => void;
};

const getTruthfulDocumentTypeLabel = (filename: string | undefined, typeKey: string): string => {
  const safeFilename = (filename || '').toLowerCase();

  if (typeKey === 'letter_of_credit') {
    return 'Primary Letter of Credit';
  }
  if (typeKey === 'duplicate_lc_candidate') {
    return 'Duplicate LC Candidate';
  }
  if (typeKey === 'lc_related_document') {
    return 'LC-Related Document';
  }
  if (/beneficiary[_\s-]?certificate|beneficiary[_\s-]?cert|beneficiary\b/.test(safeFilename)) {
    return 'Beneficiary Certificate';
  }
  if (/weight[_\s-]?list/.test(safeFilename)) {
    return 'Weight List';
  }
  if (/weight[_\s-]?certificate|weight[_\s-]?cert/.test(safeFilename)) {
    return 'Weight Certificate';
  }

  return DOCUMENT_LABELS[typeKey] ?? humanizeLabel(typeKey);
};

type ReviewReasonContext = {
  docType?: string;
  rawText?: string;
  criticalFieldStates?: Record<string, any>;
  fieldDiagnostics?: Record<string, any>;
  missingRequiredFields?: unknown[];
};

const _normalizeFieldKey = (value: unknown): string =>
  String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_');

const _textHasAny = (text: string, patterns: RegExp[]): boolean =>
  patterns.some((pattern) => pattern.test(text));

const _isFieldMarkedMissing = (context: ReviewReasonContext, fieldName: string): boolean => {
  const key = _normalizeFieldKey(fieldName);
  const missingRequiredFields = Array.isArray(context.missingRequiredFields) ? context.missingRequiredFields : [];
  if (missingRequiredFields.some((field) => _normalizeFieldKey(field) === key)) {
    return true;
  }
  const criticalState = String((context.criticalFieldStates || {})[key] || '').trim().toLowerCase();
  if (criticalState === 'missing' || criticalState === 'failed') {
    return true;
  }
  const diagnosticState = String(((context.fieldDiagnostics || {})[key] || {}).state || '').trim().toLowerCase();
  return diagnosticState === 'missing' || diagnosticState === 'failed';
};

const _buildSpecificFieldMissingReasons = (context: ReviewReasonContext): string[] => {
  const docType = _normalizeFieldKey(context.docType);
  const rawText = String(context.rawText || '');
  const reasons: string[] = [];

  if (docType === 'commercial_invoice') {
    const missingIssueDate = _isFieldMarkedMissing(context, 'issue_date');
    const missingGrossWeight = _isFieldMarkedMissing(context, 'gross_weight');
    const missingNetWeight = _isFieldMarkedMissing(context, 'net_weight');

    if (missingIssueDate) {
      reasons.push(
        _textHasAny(rawText, [/\binvoice\s*date\b/i, /\bdate\b/i, /\bdated\b/i])
          ? 'Invoice date could not be confirmed from the extracted content.'
          : 'Source invoice does not show an invoice date.',
      );
    }

    if (missingGrossWeight || missingNetWeight) {
      reasons.push(
        _textHasAny(rawText, [/\bgross\s*weight\b/i, /\bgross\s*wt\b/i, /\bg\/w\b/i, /\bnet\s*weight\b/i, /\bnet\s*wt\b/i, /\bn\/w\b/i])
          ? 'Gross or net weight could not be confirmed from the invoice extraction.'
          : 'This workflow confirms gross/net weight from the packing list or bill of lading, not from the invoice.',
      );
    }
  }

  if (docType === 'packing_list') {
    if (_isFieldMarkedMissing(context, 'issue_date')) {
      reasons.push(
        _textHasAny(rawText, [/\bpacking\s*list\s*date\b/i, /\bdate\b/i, /\bdated\b/i])
          ? 'Packing-list date could not be confirmed from the extracted content.'
          : 'Source packing list does not clearly show a document date.',
      );
    }
  }

  if (docType === 'certificate_of_origin') {
    const missingExporter = _isFieldMarkedMissing(context, 'exporter_name');
    const missingImporter = _isFieldMarkedMissing(context, 'importer_name');
    const missingGoods = _isFieldMarkedMissing(context, 'goods_description');
    if (missingExporter || missingImporter || missingGoods) {
      const sourceShowsPartyOrGoods = _textHasAny(rawText, [
        /\bexporter\b/i,
        /\bimporter\b/i,
        /\bgoods\s*description\b/i,
        /\bdescription\s+of\s+goods\b/i,
        /\bgoods\b/i,
        /\bcommodity\b/i,
      ]);
      reasons.push(
        sourceShowsPartyOrGoods
          ? 'Exporter, importer, or goods details were present in the certificate but could not be fully confirmed from extraction.'
          : 'Certificate of origin is missing one or more core party or goods details required for review.',
      );
    }
  }

  return Array.from(new Set(reasons));
};

const _humanizeDocumentReviewReason = (reason: string, context: ReviewReasonContext): string | null => {
  const key = String(reason || '').trim();
  const normalizedDocType = _normalizeFieldKey(context.docType);
  const specificMissingReasons = _buildSpecificFieldMissingReasons(context);

  if (!key) {
    return null;
  }
  if (key === 'LOW_CONFIDENCE_CRITICAL') {
    if (normalizedDocType === 'packing_list') return 'Packing-list detail needs manual review before clean presentation.';
    if (normalizedDocType === 'beneficiary_certificate') return 'Beneficiary certificate wording was recognized, but structured extraction is incomplete.';
    if (normalizedDocType === 'weight_list' || normalizedDocType === 'weight_certificate') return 'Weight values were found, but document structure still needs manual confirmation.';
    if (normalizedDocType === 'certificate_of_origin') return 'Certificate of origin details need manual confirmation before clean presentation.';
    if (normalizedDocType === 'insurance_certificate' || normalizedDocType === 'insurance_policy') return 'Insurance coverage details need manual confirmation before clean presentation.';
    if (normalizedDocType === 'bill_of_lading') return 'Bill of lading details need manual review before clean presentation.';
    return 'Key required fields need manual review before clean presentation.';
  }
  if (key === 'critical_bin_tin_low_confidence') {
    return 'Exporter BIN/TIN was not confidently confirmed on this document.';
  }
  if (key === 'OCR_AUTH_ERROR') {
    if (normalizedDocType === 'bill_of_lading') return 'Bill of lading text extraction confidence is limited; visually confirm vessel, ports, and shipment wording.';
    if (normalizedDocType === 'packing_list') return 'Packing-list text extraction confidence is limited; visually confirm package, quantity, and weight details.';
    if (normalizedDocType === 'certificate_of_origin') return 'Certificate of origin text extraction confidence is limited; visually confirm origin and certifier details.';
    if (normalizedDocType === 'beneficiary_certificate') return 'Beneficiary certificate text extraction confidence is limited; visually confirm the required declaration wording.';
    if (normalizedDocType === 'insurance_certificate' || normalizedDocType === 'insurance_policy') return 'Insurance text extraction confidence is limited; visually confirm coverage amount, risks, and certificate wording.';
    return 'Text extraction confidence is limited; visually confirm the critical presentation fields.';
  }
  if (key === 'LOW_CONFIDENCE') {
    if (normalizedDocType === 'bill_of_lading') return 'Bill of lading fields were extracted with limited confidence and need manual confirmation.';
    if (normalizedDocType === 'packing_list') return 'Packing-list fields were extracted with limited confidence and need manual confirmation.';
    return 'Extraction confidence is limited for this document and needs manual confirmation.';
  }
  if (key === 'REVIEW_REQUIRED') {
    return 'This document requires manual review before clean presentation.';
  }
  if (key === 'FIELD_NOT_FOUND') {
    return specificMissingReasons[0] || 'A required field could not be confirmed from the extracted content.';
  }
  if (key === 'critical_issue_date_missing') {
    return specificMissingReasons.find((entry) => /date/i.test(entry)) || 'Document date could not be confirmed from this file.';
  }
  if (key === 'critical_gross_weight_missing' || key === 'critical_net_weight_missing') {
    return (
      specificMissingReasons.find((entry) => /gross or net weight|gross weight|net weight/i.test(entry))
      || 'Weight details could not be confirmed from this document.'
    );
  }
  if (key.startsWith('missing:')) {
    const fieldName = key.split(':', 2)[1] || '';
    const fieldSpecific = specificMissingReasons.find((entry) => entry.toLowerCase().includes(fieldName.replace(/_/g, ' ')));
    if (fieldSpecific) {
      return fieldSpecific;
    }
    return `${humanizeLabel(fieldName)} could not be confirmed from this document.`;
  }
  if (/^field not found$/i.test(key)) {
    return specificMissingReasons[0] || 'A required field could not be confirmed from the extracted content.';
  }
  return key.replace(/_/g, ' ').toLowerCase().replace(/^./, (c) => c.toUpperCase());
};

const buildWarningReasons = ({
  extractionStatus,
  issuesCount,
  missingRequiredFields,
  parseComplete,
  reviewReasons,
  docType,
  rawText,
  criticalFieldStates,
  fieldDiagnostics,
}: {
  extractionStatus: string;
  issuesCount: number;
  missingRequiredFields: unknown[];
  parseComplete: boolean | undefined;
  reviewReasons: unknown[];
  docType?: string;
  rawText?: string;
  criticalFieldStates?: Record<string, any>;
  fieldDiagnostics?: Record<string, any>;
}): string[] => {
  const reasons: string[] = [];
  const normalizedDocType = String(docType || '').toLowerCase();
  const reasonContext: ReviewReasonContext = {
    docType,
    rawText,
    criticalFieldStates,
    fieldDiagnostics,
    missingRequiredFields,
  };
  const specificMissingReasons = _buildSpecificFieldMissingReasons(reasonContext);
  const humanizeField = (field: unknown) =>
    String(field || '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())
      .trim();

  if (specificMissingReasons.length > 0) {
    reasons.push(...specificMissingReasons);
  }
  if (['partial', 'pending', 'text_only'].includes(extractionStatus)) {
    if (specificMissingReasons.length > 0) {
      // Prefer the source-aware reason over generic extraction wording when we can explain the gap.
    } else if (normalizedDocType === 'insurance_certificate' || normalizedDocType === 'insurance_policy') {
      reasons.push('Insurance coverage fields are incomplete and need manual confirmation before presentation.');
    } else if (normalizedDocType === 'certificate_of_origin') {
      reasons.push('Certificate of origin details are only partially extracted and need manual confirmation.');
    } else if (normalizedDocType === 'packing_list') {
      reasons.push('Packing-list details are only partially extracted and need manual confirmation.');
    } else if (normalizedDocType === 'bill_of_lading') {
      reasons.push('Bill of lading details need manual confirmation before clean presentation.');
    } else {
      reasons.push(`Document extraction is ${extractionStatus.replace('_', ' ')} and needs manual confirmation.`);
    }
  }
  if (parseComplete === false && specificMissingReasons.length === 0) {
    reasons.push('Structured extraction is incomplete for this document.');
  }
  if (specificMissingReasons.length === 0 && Array.isArray(missingRequiredFields) && missingRequiredFields.length > 0) {
    const formattedFields = missingRequiredFields
      .map(humanizeField)
      .filter(Boolean)
      .slice(0, 3);
    if (formattedFields.length === 1) {
      reasons.push(`${formattedFields[0]} was not confidently extracted from this document.`);
    } else if (formattedFields.length > 1) {
      const extraCount = missingRequiredFields.length - formattedFields.length;
      reasons.push(
        `${formattedFields.join(', ')}${extraCount > 0 ? ` and ${extraCount} more field${extraCount > 1 ? 's' : ''}` : ''} were not confidently extracted from this document.`,
      );
    }
  }
  if (issuesCount > 0) {
    reasons.push(`This document still has ${issuesCount} linked issue${issuesCount > 1 ? 's' : ''} to resolve before clean presentation.`);
  }
  if (Array.isArray(reviewReasons)) {
    for (const rawReason of reviewReasons) {
      const humanized = _humanizeDocumentReviewReason(String(rawReason || '').trim(), reasonContext);
      if (humanized) {
        reasons.push(humanized);
      }
    }
  }

  return Array.from(new Set(reasons));
};

const WORKFLOW_LABEL_MAP: Record<string, string> = {
  import: "Import LC",
  export: "Export LC",
  domestic: "Domestic LC",
  intermediary_or_trader: "Intermediary/Trader LC",
  unknown: "Unknown",
};

const INSTRUMENT_LABEL_MAP: Record<string, string> = {
  documentary_credit: "Documentary Credit",
  standby_letter_of_credit: "Standby Letter of Credit",
  demand_guarantee: "Demand Guarantee",
  counter_undertaking_or_counter_guarantee: "Counter Guarantee",
  documentary_collection: "Documentary Collection",
  other_or_unknown_undertaking: "Other/Unknown Undertaking",
};

const normalizeLcEnumLabel = (value: string): string =>
  value
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());

type RequirementChecklistStatus = 'matched' | 'partial' | 'missing';
type RequirementChecklistReviewState = 'ready' | 'needs_review' | 'blocked' | 'awaiting_document';

type RequirementChecklistSummary = {
  matched: number;
  partial: number;
  missing: number;
  ready: number;
  needsReview: number;
  blocked: number;
  awaitingDocument: number;
};

const REQUIREMENT_STATUS_META: Record<
  RequirementChecklistStatus,
  { label: string; badgeStatus: 'success' | 'warning' | 'error' }
> = {
  matched: { label: 'Matched', badgeStatus: 'success' },
  partial: { label: 'Partial', badgeStatus: 'warning' },
  missing: { label: 'Missing', badgeStatus: 'error' },
};

const REVIEW_STATE_META: Record<
  RequirementChecklistReviewState,
  { label: string; badgeStatus: 'success' | 'warning' | 'error' }
> = {
  ready: { label: 'Ready', badgeStatus: 'success' },
  needs_review: { label: 'Review required', badgeStatus: 'warning' },
  blocked: { label: 'Blocked', badgeStatus: 'error' },
  awaiting_document: { label: 'Awaiting document', badgeStatus: 'warning' },
};

type RequirementReviewFinding = ReviewFindingCardData;

const REQUIREMENT_TYPE_EQUIVALENTS: Record<string, string[]> = {
  bill_of_lading: ['ocean_bill_of_lading', 'charter_party_bill_of_lading'],
  ocean_bill_of_lading: ['bill_of_lading', 'charter_party_bill_of_lading'],
  charter_party_bill_of_lading: ['bill_of_lading', 'ocean_bill_of_lading'],
  insurance_certificate: ['insurance_policy'],
  insurance_policy: ['insurance_certificate'],
  beneficiary_certificate: ['beneficiary_statement'],
  beneficiary_statement: ['beneficiary_certificate'],
  courier_or_post_receipt_or_certificate_of_posting: ['courier_receipt', 'post_receipt', 'certificate_of_posting'],
  courier_receipt: ['courier_or_post_receipt_or_certificate_of_posting'],
};

const normalizeRequirementCode = (value: unknown): string | null => {
  const normalized = String(value || '').trim().toLowerCase().replace(/[\s-]+/g, '_');
  return normalized.length > 0 ? normalized : null;
};

const buildRequirementTypeCandidates = (code: string | null): string[] => {
  if (!code) return [];
  const candidates = new Set<string>([code]);
  const equivalent = REQUIREMENT_TYPE_EQUIVALENTS[code] || [];
  equivalent.forEach((item) => candidates.add(item));
  for (const [base, aliases] of Object.entries(REQUIREMENT_TYPE_EQUIVALENTS)) {
    if (aliases.includes(code)) {
      candidates.add(base);
      aliases.forEach((item) => candidates.add(item));
    }
  }
  return Array.from(candidates);
};

const buildCanonicalLcDrawerFields = (lcStructured: Record<string, any> | null): Record<string, any> => {
  if (!lcStructured || typeof lcStructured !== "object") {
    return {};
  }

  const existing = lcStructured.extracted_fields;
  if (existing && typeof existing === "object" && Object.keys(existing).length > 0) {
    return existing as Record<string, any>;
  }

  const lcClassification =
    lcStructured.lc_classification && typeof lcStructured.lc_classification === "object"
      ? (lcStructured.lc_classification as Record<string, any>)
      : {};
  const dates =
    lcStructured.dates && typeof lcStructured.dates === "object"
      ? (lcStructured.dates as Record<string, any>)
      : {};
  const ports =
    lcStructured.ports && typeof lcStructured.ports === "object"
      ? (lcStructured.ports as Record<string, any>)
      : {};

  const normalizeTextList = (values: unknown): string[] => {
    if (!Array.isArray(values)) return [];
    const seen = new Set<string>();
    const items: string[] = [];
    values.forEach((value) => {
      const text =
        typeof value === "string"
          ? value.trim()
          : value && typeof value === "object"
          ? String(
              (value as Record<string, unknown>).raw_text ||
                (value as Record<string, unknown>).display_name ||
                (value as Record<string, unknown>).code ||
                "",
            ).trim()
          : "";
      if (!text) return;
      const key = text.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      items.push(text);
    });
    return items;
  };

  const pickFirst = (...values: unknown[]) =>
    values.find((value) => value !== null && value !== undefined && (typeof value !== "string" || value.trim().length > 0));

  const requiredDocuments = normalizeTextList(
    lcStructured.required_documents_detailed ?? lcClassification.required_documents,
  );
  const requirementConditions = normalizeTextList(
    lcStructured.requirement_conditions ?? lcClassification.requirement_conditions,
  );
  const unmappedRequirements = normalizeTextList(
    lcStructured.unmapped_requirements ?? lcClassification.unmapped_requirements,
  );
  const additionalConditions = normalizeTextList(lcStructured.additional_conditions);

  return Object.fromEntries(
    Object.entries({
      lc_number: pickFirst(lcStructured.lc_number, lcStructured.number, lcStructured.reference),
      issue_date: pickFirst(lcStructured.issue_date, dates.issue, dates.issue_date),
      expiry_date: pickFirst(lcStructured.expiry_date, dates.expiry, dates.expiry_date),
      latest_shipment_date: pickFirst(
        lcStructured.latest_shipment_date,
        lcStructured.latest_shipment,
        dates.latest_shipment,
        dates.latest_shipment_date,
      ),
      place_of_expiry: pickFirst(lcStructured.place_of_expiry, dates.place_of_expiry),
      applicant: lcStructured.applicant,
      beneficiary: lcStructured.beneficiary,
      issuing_bank: lcStructured.issuing_bank,
      advising_bank: lcStructured.advising_bank,
      port_of_loading: pickFirst(lcStructured.port_of_loading, ports.loading, ports.port_of_loading),
      port_of_discharge: pickFirst(lcStructured.port_of_discharge, ports.discharge, ports.port_of_discharge),
      amount: lcStructured.amount,
      currency: lcStructured.currency,
      incoterm: lcStructured.incoterm,
      ucp_reference: lcStructured.ucp_reference,
      goods_description: lcStructured.goods_description,
      exporter_bin: lcStructured.exporter_bin,
      exporter_tin: lcStructured.exporter_tin,
      documents_required: requiredDocuments,
      requirement_conditions: requirementConditions,
      unmapped_requirements: unmappedRequirements,
      additional_conditions: additionalConditions,
    }).filter(([, value]) => value !== null && value !== undefined && value !== "" && (!Array.isArray(value) || value.length > 0)),
  );
};

// NOTE: Components, types, and utilities are now imported from ./exporter/results

export default function ExporterResults({
  embedded = false,
  jobId: jobIdProp,
  lcNumber: lcNumberProp,
  initialTab,
  onTabChange,
}: ExporterResultsProps = {}) {
  // Debug hook for development - automatically stripped in production
  resultsLogger.debug('Component mounted', { jobIdProp, lcNumberProp });
  const [searchParams, setSearchParams] = useSearchParams();
  const params = useParams<{ jobId?: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  // Prioritize props over searchParams for remounting support
  const jobIdParam = jobIdProp || searchParams.get('jobId');
  const sessionParam = searchParams.get('session');
  const jobIdFromPath = params.jobId;
  const validationSessionId = jobIdParam || sessionParam || jobIdFromPath || null;
  
  const {
    jobStatus,
    jobError,
    results: resultData,
    isLoading: resultsLoading,
    resultsError,
    refreshResults,
    isFinalizingResults = false,
    terminalResultsTimedOut = false,
  } = useCanonicalJobResult(validationSessionId);
  
  const lcNumberParam = lcNumberProp || searchParams.get('lc') || undefined;
  const tabParamRaw = searchParams.get("tab");
  const tabParam = isResultsTab(tabParamRaw) ? tabParamRaw : null;

// Field confidence indicator component (uses imported getStatusColor/getStatusLabel)
const FieldConfidenceIndicator = ({ 
  confidence, 
  status 
}: { 
  confidence?: number; 
  status?: 'trusted' | 'review' | 'untrusted' | 'missing' | string;
}) => {
  if (!confidence && !status) return null;
  
  return (
    <span 
      className={cn(
        "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium text-white",
        getStatusColor(confidence, status)
      )}
      title={confidence !== undefined ? `Extraction confidence: ${Math.round(confidence * 100)}%` : `Status: ${status}`}
    >
      {getStatusLabel(confidence, status)}
    </span>
  );
};

// Enhanced field row with confidence
const buildFieldRows = (fields: { label: string; value: any; confidence?: number; status?: string }[], keyPrefix: string): ReactElement[] => {
  return fields
    .map((field) => {
      if (field.value === undefined || field.value === null || field.value === "") {
        return null;
      }
      const formatted = formatExtractedValue(field.value);
      if (!formatted || formatted === "N/A") {
        return null;
      }
      return (
        <div key={`${keyPrefix}-${field.label}`} className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground uppercase tracking-wide">{field.label}</span>
            {(field.confidence !== undefined || field.status) && (
              <FieldConfidenceIndicator confidence={field.confidence} status={field.status as any} />
            )}
          </div>
          <span className="font-medium whitespace-pre-wrap break-words">{formatted}</span>
        </div>
      );
    })
    .filter((node): node is ReactElement => Boolean(node));
};

const buildFieldRowsFromObject = (
  source: Record<string, any> | null | undefined,
  prefix: string,
): ReactElement[] => {
  if (!source || typeof source !== "object") {
    return [];
  }
  
  // Extract field details if available (for confidence/status)
  const fieldDetails = source._field_details as Record<string, { confidence?: number; status?: string; value?: any }> | undefined;
  const twoStageValidation = source._two_stage_validation as { fields?: Record<string, { status?: string; final_confidence?: number }> } | undefined;
  
  const entries = Object.entries(source)
    .filter(([key]) => !key.startsWith('_')) // Skip internal fields
    .map(([key, rawValue]) => {
      // Check if value is a complex object with value/confidence
      let value = rawValue;
      let confidence: number | undefined;
      let status: string | undefined;
      
      // Handle complex value objects: { value: "...", confidence: 0.8 }
      if (typeof rawValue === 'object' && rawValue !== null && 'value' in rawValue) {
        value = rawValue.value;
        confidence = typeof rawValue.confidence === 'number' ? rawValue.confidence : undefined;
        status = rawValue.status;
      }
      
      // Try to get confidence from _field_details
      if (fieldDetails?.[key]) {
        confidence = confidence ?? fieldDetails[key].confidence;
        status = status ?? fieldDetails[key].status;
      }
      
      // Try to get from _two_stage_validation
      if (twoStageValidation?.fields?.[key]) {
        confidence = confidence ?? twoStageValidation.fields[key].final_confidence;
        status = status ?? twoStageValidation.fields[key].status;
      }
      
      return {
        label: humanizeLabel(key),
        value,
        confidence,
        status,
      };
    });
    
  return buildFieldRows(entries, prefix);
};

const renderPartyCard = (label: string, party: any, keyPrefix: string): ReactElement | null => {
  if (!party || typeof party !== "object") {
    return null;
  }
  const rows = buildFieldRows(
    [
      { label: "Name", value: party.name },
      { label: "Address", value: party.address },
      { label: "Country", value: party.country },
      { label: "Contact", value: party.contact },
    ],
    keyPrefix,
  );
  if (!rows.length) {
    return null;
  }
  return (
    <div key={`${keyPrefix}-card`} className="border rounded-lg p-3 space-y-2 bg-background">
      <p className="text-sm font-semibold">{label}</p>
      <div className="space-y-2 text-sm">{rows}</div>
    </div>
  );
};

const renderPortsCard = (ports: any): ReactElement | null => {
  if (!ports || typeof ports !== "object") {
    return null;
  }
  const rows = buildFieldRows(
    [
      { label: "Port of Loading", value: ports.port_of_loading ?? ports.loading },
      { label: "Port of Discharge", value: ports.port_of_discharge ?? ports.discharge },
    ],
    "lc-ports",
  );
  if (!rows.length) {
    return null;
  }
  return (
    <div className="border rounded-lg p-3 space-y-2 bg-background">
      <p className="text-sm font-semibold">Shipping Ports</p>
      <div className="grid gap-3 md:grid-cols-2">{rows}</div>
    </div>
  );
};

const renderGoodsItemsList = (items: any[]): ReactElement | null => {
  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }
  const cards = items
    .map((item, idx) => {
      const rows = buildFieldRows(
        [
          { label: "Description", value: item.description },
          { label: "HS Code", value: item.hs_code },
          { label: "Quantity", value: item.quantity },
          { label: "Unit", value: item.uom },
          { label: "Unit Price", value: item.unit_price },
        ],
        `goods-${idx}`,
      );
      if (!rows.length) {
        return null;
      }
      return (
        <div key={`goods-${idx}`} className="border rounded-lg p-3 space-y-2 text-sm bg-background">
          {rows}
        </div>
      );
    })
    .filter((node): node is ReactElement => Boolean(node));

  if (!cards.length) {
    return null;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold">Goods Items</p>
      <div className="space-y-2">{cards}</div>
    </div>
  );
};

const renderGenericExtractedSection = (key: string, data: Record<string, any>) => {
  if (!data || typeof data !== "object") {
    return null;
  }
  const label = DOCUMENT_LABELS[key] ?? humanizeLabel(key);
  const rows = buildFieldRowsFromObject(data, `extracted-${key}`);

  return (
    <div key={key} className="space-y-2">
      <h3 className="font-semibold text-lg">{label} Data</h3>
      {rows.length ? (
        <div className="grid gap-4 md:grid-cols-2">{rows}</div>
      ) : (
        <p className="text-sm text-muted-foreground">No structured fields extracted for this document.</p>
      )}
      <details className="text-xs text-muted-foreground">
        <summary className="cursor-pointer">View Raw JSON</summary>
        <pre className="text-xs overflow-auto max-h-[400px] whitespace-pre-wrap mt-2">
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
    </div>
  );
};
  
  const fetchResults = useCallback(async () => {
    if (!validationSessionId) {
      resultsLogger.debug('Skip manual refresh: missing session id');
      return;
    }

    resultsLogger.debug('Manual results refresh', { validationSessionId });
    await refreshResults('manual');
  }, [refreshResults, validationSessionId]);

  const [activeTab, setActiveTab] = useState<ResultsTab>(initialTab ?? tabParam ?? DEFAULT_TAB);
  const [showBankSelector, setShowBankSelector] = useState(false);
  const [showManifestPreview, setShowManifestPreview] = useState(false);
  const [selectedBankId, setSelectedBankId] = useState<string>("");
  const [selectedBankName, setSelectedBankName] = useState<string>("");
  const [submissionNote, setSubmissionNote] = useState<string>("");
  const [manifestConfirmed, setManifestConfirmed] = useState(false);
  const [manifestData, setManifestData] = useState<CustomsPackManifest | null>(null);
  const [issueFilter, setIssueFilter] = useState<"all" | "critical" | "major" | "minor">("all");
  const [emailDraftContext, setEmailDraftContext] = useState<EmailDraftContext | null>(null);
  const [showEmailDraftDialog, setShowEmailDraftDialog] = useState(false);
  const [showRawLcJson, setShowRawLcJson] = useState(false);
  const [selectedDocumentForDrawer, setSelectedDocumentForDrawer] = useState<DocumentForDrawer | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  
  useEffect(() => {
    if (!initialTab) {
      return;
    }
    if (initialTab !== activeTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab, activeTab]);

  useEffect(() => {
    if (embedded) return;
    if (!initialTab && tabParam && tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
  }, [embedded, initialTab, tabParam, activeTab]);

  const handleActiveTabChange = (next: ResultsTab) => {
    setActiveTab(next);
    onTabChange?.(next);
    if (!embedded) {
      const params = new URLSearchParams(searchParams);
      params.set("tab", next);
      setSearchParams(params, { replace: true });
    }
  };

  // Feature flags
  const enableBankSubmission = isExporterFeatureEnabled("exporter_bank_submission");
  const enableCustomsPackPDF = isExporterFeatureEnabled("exporter_customs_pack_pdf");
  
  // Guardrails check
  const structuredResult = resultData?.structured_result;
  const structuredLcNumber =
    (structuredResult?.lc_structured?.mt700?.blocks?.["20"] as string | undefined) ??
    (structuredResult?.lc_structured?.mt700?.blocks?.["27"] as string | undefined) ??
    null;
  const resolvedLcNumber =
    lcNumberParam ??
    structuredLcNumber ??
    jobStatus?.lcNumber ??
    null;
  const lcNumber = resolvedLcNumber ?? 'LC-UNKNOWN';
  const guardrailsQueryEnabled = !!validationSessionId && !!resolvedLcNumber && enableBankSubmission;
  
  const { data: guardrails, isLoading: guardrailsLoading } = useQuery({
    queryKey: ['exporter-guardrails', validationSessionId, resolvedLcNumber],
    queryFn: () => exporterApi.checkGuardrails({ validation_session_id: validationSessionId, lc_number: resolvedLcNumber }),
    enabled: guardrailsQueryEnabled,
    refetchInterval: 30000, // Check every 30 seconds
  });
  
  // Submission history
  const { data: submissionsData, isLoading: submissionsLoading } = useQuery({
    queryKey: ['exporter-submissions', resolvedLcNumber, validationSessionId],
    queryFn: () => exporterApi.listBankSubmissions({ 
      lc_number: resolvedLcNumber, 
      validation_session_id: validationSessionId 
    }),
    enabled: !!resolvedLcNumber && enableBankSubmission,
  });
  
  // Poll submission status (Phase 7)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  useEffect(() => {
    if (submissionsData?.items) {
      const pendingSubmissions = submissionsData.items.filter(s => s.status === 'pending');
      if (pendingSubmissions.length > 0 && enableBankSubmission) {
        // Poll every 5 seconds for pending submissions
        pollingIntervalRef.current = setInterval(() => {
          queryClient.invalidateQueries({ queryKey: ['exporter-submissions'] });
        }, 5000);
      } else {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      }
    }
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [submissionsData, queryClient, enableBankSubmission]);
  
  // Check if result has invoiceId (future enhancement)
  const invoiceId = (resultData as any)?.invoiceId;
  
  // Generate idempotency key (Phase 7)
  const generateIdempotencyKey = () => {
    return `${validationSessionId}-${Date.now()}`;
  };

  // Generate customs pack mutation (Phase 2)
  const generateCustomsPackMutation = useMutation({
    mutationFn: () => exporterApi.generateCustomsPack({
      validation_session_id: validationSessionId,
      lc_number: lcNumber,
    }),
    onSuccess: (data) => {
      const hasManifest = Boolean(data?.manifest?.documents?.length);
      if (!hasManifest) {
        setManifestData(null);
        toast({
          title: "Generation Failed",
          description: "Customs pack manifest was empty. Please try again.",
          variant: "destructive",
        });
        return;
      }
      setManifestData(data.manifest);
      toast({
        title: "Customs Pack Generated",
        description: "Your customs pack has been prepared successfully.",
      });
      // Track telemetry (Phase 6)
      resultsLogger.info('Telemetry: customs_pack_generated', { lcNumber });
    },
    onError: (error: any) => {
      toast({
        title: "Generation Failed",
        description: error?.response?.data?.detail || "Failed to generate customs pack. Please try again.",
        variant: "destructive",
      });
    },
  });
  
  // Download customs pack (Phase 2)
  const downloadCustomsPackMutation = useMutation({
    mutationFn: () => exporterApi.downloadCustomsPack(validationSessionId),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Customs_Pack_${lcNumber}_${format(new Date(), 'yyyyMMdd_HHmmss')}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast({
        title: "Download Started",
        description: "Your customs pack is downloading.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Download Failed",
        description: error?.response?.data?.detail || "Failed to download customs pack. Please try again.",
        variant: "destructive",
      });
    },
  });
  
  // Create bank submission mutation (Phase 2, 7)
  const createSubmissionMutation = useMutation({
    mutationFn: (data: { bank_id?: string; bank_name?: string; note?: string }) => {
      return exporterApi.createBankSubmission({
        validation_session_id: validationSessionId,
        lc_number: lcNumber,
        bank_id: data.bank_id,
        bank_name: data.bank_name,
        note: data.note,
        idempotency_key: generateIdempotencyKey(), // Phase 7: Idempotency
      });
    },
    onSuccess: (submission) => {
      toast({
        title: "Submitted to Bank",
        description: `LC ${lcNumber} has been successfully submitted to ${submission.bank_name || 'the bank'} for review.`,
      });
      setShowBankSelector(false);
      setShowManifestPreview(false);
      setSelectedBankId("");
      setSelectedBankName("");
      setSubmissionNote("");
      setManifestConfirmed(false);
      
      // Invalidate and refetch submissions
      queryClient.invalidateQueries({ queryKey: ['exporter-submissions'] });
      
      // Track telemetry (Phase 6)
      resultsLogger.info('Telemetry: bank_submit_requested', { lcNumber, bank: submission.bank_name });
    },
    onError: (error: any) => {
      toast({
        title: "Submission Failed",
        description: error?.response?.data?.detail || "Failed to submit to bank. Please try again.",
        variant: "destructive",
      });
    },
  });

  // Define variables with safe defaults BEFORE any early returns to ensure hooks are always called
  const structuredDocumentsPayload =
    structuredResult?.documents_structured ??
    structuredResult?.lc_structured?.documents_structured ??
    [];
  const summary =
    resultData?.summary ??
    (structuredResult as any)?.processing_summary_v2 ??
    structuredResult?.processing_summary;
  const lcStructured = structuredResult?.lc_structured ?? null;
  const extractionDocumentsPayload =
    (structuredResult as any)?.document_extraction_v1?.documents ?? structuredDocumentsPayload;
  const extractionStatus = useMemo(() => {
    // Check document-level extraction statuses first
    const docStatuses = extractionDocumentsPayload.map(
      (doc) => (doc.extraction_status || "unknown").toLowerCase()
    );
    const hasSuccess = docStatuses.some((s) => s === "success");
    const hasError = docStatuses.some((s) => s === "error" || s === "failed");
    
    // If we have document statuses, use them
    if (docStatuses.length > 0 && (hasSuccess || hasError)) {
      if (hasError && !hasSuccess) return "error";
      if (hasSuccess && hasError) return "partial";
      if (hasSuccess) return "success";
    }
    
    // Fall back to summary counts if available
    if (summary) {
      const successExtractions = Number(summary.successful_extractions ?? summary.verified ?? 0);
      const failedExtractions = Number(summary.failed_extractions ?? summary.errors ?? 0);
      const totalDocs = Number(summary.total_documents ?? summary.documents ?? 0);
      
      // If we have documents processed, assume success
      if (totalDocs > 0 && failedExtractions === 0) {
        return "success";
      }
      if (successExtractions > 0 && failedExtractions === 0) {
        return "success";
      }
      if (successExtractions > 0 && failedExtractions > 0) {
        return "partial";
      }
      if (successExtractions === 0 && failedExtractions > 0) {
        return "error";
      }
    }
    
    // If LC data exists, extraction worked
    if (lcStructured && Object.keys(lcStructured).length > 0) {
      return "success";
    }
    
    return "unknown";
  }, [summary, extractionDocumentsPayload, lcStructured]);
  const fallbackDocuments = useMemo(() => {
    return extractionDocumentsPayload.map((doc, index) => {
      const docAny = doc as Record<string, any>;
      const documentId = String(doc.document_id ?? docAny.id ?? index);
      const filename = doc.filename ?? docAny.name ?? `Document ${index + 1}`;
      const typeKeyRaw = doc.document_type ?? docAny.documentType ?? docAny.type ?? "supporting_document";
      const typeKey = (typeKeyRaw || "supporting_document").toString();
      // Check multiple keys - backend sends discrepancyCount (camelCase)
      const issuesCount = Number(doc.discrepancyCount ?? doc.issues_count ?? docAny.discrepancyCount ?? docAny.issues ?? docAny.discrepancy_count ?? 0);
      const extractionStatus = (doc.extraction_status ?? docAny.extractionStatus ?? "unknown").toString().toLowerCase();
      const rawStatus = docAny.status;
      const normalizedStatus = typeof rawStatus === "string" ? rawStatus.toLowerCase() : null;
      const status: "success" | "warning" | "error" = (() => {
        if (normalizedStatus === "success" || normalizedStatus === "warning" || normalizedStatus === "error") {
          return normalizedStatus as "success" | "warning" | "error";
        }
        if (extractionStatus === "error" || extractionStatus === "failed" || extractionStatus === "empty") return "error";
        if (extractionStatus === "partial" || extractionStatus === "pending" || extractionStatus === "text_only") return "warning";
        const exempt = ["letter_of_credit", "insurance_certificate"];
        if (issuesCount > 0 && !exempt.includes(typeKey)) return "warning";
        return "success";
      })();
      // Ensure type is always a string to prevent React Error #31
      const parseComplete = typeof docAny.parse_complete === "boolean" ? docAny.parse_complete : docAny.parseComplete;
      const missingRequiredFields = docAny.missing_required_fields ?? [];
      const reviewReasons = docAny.review_reasons ?? docAny.reviewReasons ?? [];
      const typeLabel = safeString(doc.document_type_label ?? docAny.document_type_label ?? getTruthfulDocumentTypeLabel(filename, typeKey));
      return {
        id: documentId,
        documentId,
        name: filename,
        filename,
        type: safeString(typeLabel),
        typeKey,
        extractionStatus,
        status,
        issuesCount,
        parseComplete,
        parseCompleteness: docAny.parse_completeness ?? docAny.parseCompleteness,
        missingRequiredFields,
        warningReasons: buildWarningReasons({
          extractionStatus,
          issuesCount,
          missingRequiredFields,
          parseComplete,
          reviewReasons,
          docType: typeKey,
          rawText: docAny.extraction_artifacts_v1?.raw_text ?? docAny.raw_text ?? docAny.rawText ?? '',
          criticalFieldStates: docAny.critical_field_states ?? docAny.criticalFieldStates ?? {},
          fieldDiagnostics: docAny.extraction_artifacts_v1?.field_diagnostics ?? docAny.extractionDebug?.field_diagnostics ?? {},
        }),
        reviewReasons,
        criticalFieldStates: docAny.critical_field_states ?? docAny.criticalFieldStates ?? {},
        fieldDiagnostics: docAny.extraction_artifacts_v1?.field_diagnostics ?? docAny.extractionDebug?.field_diagnostics ?? {},
        rawText: docAny.extraction_artifacts_v1?.raw_text ?? docAny.raw_text ?? docAny.rawText ?? '',
        requiredFieldsFound: docAny.required_fields_found,
        requiredFieldsTotal: docAny.required_fields_total,
        extractedFields: doc.extracted_fields ?? docAny.extractedFields ?? {},
      };
    });
  }, [extractionDocumentsPayload]);
  const documents = resultData?.documents?.length ? resultData.documents : fallbackDocuments;
  resultsLogger.debug('Documents loaded', { count: documents.length });
  const issueCards = resultData?.issues ?? [];
  const analyticsData = resultData?.analytics ?? null;
  const timelineEvents = resultData?.timeline ?? [];
  const totalDocuments = summary?.total_documents ?? documents.length ?? 0;
  const backendIssueCount = Math.max(summary?.total_issues ?? 0, issueCards.length);
  const severityBreakdown = summary?.severity_breakdown ?? {
    critical: 0,
    major: 0,
    medium: 0,
    minor: 0,
  };
  const extractedDocumentsMap = useMemo(() => {
    const map: Record<string, any> = {};
    documents.forEach((doc, idx) => {
      const key = doc.typeKey || doc.filename || `doc_${idx}`;
      map[key] = doc.extractedFields ?? {};
    });
    return map;
  }, [documents]);
  const extractedDocuments = useMemo(
    () =>
      documents.map((doc) => ({
        filename: doc.filename,
        name: doc.filename,
        document_type: doc.typeKey,
        extraction_status: doc.extractionStatus,
        extractionStatus: doc.extractionStatus,
        extracted_fields: doc.extractedFields ?? {},
        extractedFields: doc.extractedFields ?? {},
      })),
    [documents],
  );
  // lcStructured is already defined above (line ~730) to avoid temporal dead zone issues
  const lcData = lcStructured as Record<string, any> | null;
  const lcSummaryRows = lcData
    ? buildFieldRows(
        [
          { label: "LC Number", value: lcData.number ?? lcData.lc_number },
          { label: "LC Amount", value: formatAmountValue(lcData.amount) },
          { label: "Incoterm", value: lcData.incoterm },
          { label: "UCP Reference", value: lcData.ucp_reference },
          { label: "Goods Description", value: lcData.goods_description },
        ],
        "lc-summary",
      )
    : [];
  const lcDateRows = lcData
    ? buildFieldRows(
        [
          { label: "Issue Date", value: lcData.dates?.issue },
          { label: "Expiry Date", value: lcData.dates?.expiry },
          { label: "Latest Shipment", value: lcData.dates?.latest_shipment },
          { label: "Place of Expiry", value: lcData.dates?.place_of_expiry },
        ],
        "lc-dates",
      )
    : [];
  const lcPrimaryDocument = documents.find((doc) => String(doc.typeKey || '').toLowerCase() === 'letter_of_credit');
  const lcPrimaryExtractedFields = (lcPrimaryDocument?.extractedFields ?? {}) as Record<string, any>;
  const lcGoodsItems = lcData && Array.isArray(lcData.goods_items) ? lcData.goods_items : [];
  const lcApplicantCard = lcData ? renderPartyCard("Applicant", lcData.applicant, "lc-applicant") : null;
  const lcBeneficiaryCard = lcData ? renderPartyCard("Beneficiary", lcData.beneficiary, "lc-beneficiary") : null;
  const lcPortsCard = lcData ? renderPortsCard(lcData.ports) : null;
  const lcGoodsItemsList = lcData ? renderGoodsItemsList(lcGoodsItems) : null;
  const lcAdditionalConditions = lcData?.additional_conditions;
  const lcAdditionalConditionSummary = useMemo(
    () => summarizeSpecialConditions(formatConditions(lcAdditionalConditions)),
    [lcAdditionalConditions],
  );
  const referenceIssues: ReferenceIssue[] = Array.isArray(structuredResult?.reference_issues)
    ? (structuredResult?.reference_issues as ReferenceIssue[])
    : [];
  const rawAiInsights = structuredResult?.ai_enrichment ?? null;
  const aiInsights = useMemo<AIEnrichmentPayload | null>(() => {
    if (!rawAiInsights) {
      return null;
    }
    if (typeof (rawAiInsights as AIEnrichmentPayload).summary === "string" || Array.isArray((rawAiInsights as AIEnrichmentPayload).suggestions)) {
      return rawAiInsights as AIEnrichmentPayload;
    }
    const notes = Array.isArray((rawAiInsights as any).notes) ? (rawAiInsights as any).notes : [];
    if (!notes.length) {
      return null;
    }
    return {
      summary: notes.join("\n"),
      suggestions: notes as string[],
    };
  }, [rawAiInsights]);
  const hasIssueCards = issueCards.length > 0;
  const lcStructuredData = structuredResult?.lc_structured as Record<string, any> | null;
  const canonicalLcDrawerFields = useMemo(
    () => buildCanonicalLcDrawerFields(lcStructuredData),
    [lcStructuredData],
  );
  const lcClassification = (lcStructuredData?.lc_classification ?? null) as LcClassification | null;
  const workflowOrientation = String(
    lcClassification?.workflow_orientation ?? "unknown",
  ).toLowerCase();
  const instrumentType = String(lcClassification?.instrument_type ?? "other_or_unknown_undertaking").toLowerCase();
  const revocability = String(lcClassification?.attributes?.revocability ?? "unknown").toLowerCase();
  // Keep confidence display backward-compatible while workflow/instrument are read from lc_classification.
  const rawConfidence = structuredResult?.lc_type_confidence ?? lcStructuredData?.lc_type_confidence;
  const lcTypeConfidenceValue =
    typeof rawConfidence === "number"
      ? Math.round(rawConfidence * 100)
      : null;
  const workflowLabel = WORKFLOW_LABEL_MAP[workflowOrientation] ?? WORKFLOW_LABEL_MAP.unknown;
  const lcInstrumentLabel =
    INSTRUMENT_LABEL_MAP[instrumentType] ??
    (instrumentType && instrumentType !== "other_or_unknown_undertaking"
      ? normalizeLcEnumLabel(instrumentType)
      : "Unknown");
  const lcTypeLabel =
    revocability !== 'unknown' && lcInstrumentLabel !== 'Unknown'
      ? `${normalizeLcEnumLabel(revocability)} ${lcInstrumentLabel}`
      : lcInstrumentLabel;
  const lcTypeCaption = revocability !== 'unknown' || lcInstrumentLabel !== 'Unknown'
    ? 'LC SEMANTICS'
    : 'LC TYPE';

  // All hooks must be called BEFORE any conditional returns
  const documentStatusMap = useMemo(() => {
    const map = new Map<string, { status?: string; type?: string }>();
    documents.forEach((doc) => {
      if (doc.name) {
        map.set(doc.name, { status: doc.status, type: doc.type });
      }
    });
    return map;
  }, [documents]);
  const documentStatusCounts = useMemo(
    () =>
      documents.reduce(
        (acc, doc) => {
          const key = doc.status ?? 'warning';
          if (!(key in acc)) {
            acc[key as keyof typeof acc] = 0;
          }
          acc[key as keyof typeof acc] += 1;
          return acc;
        },
        { success: 0, warning: 0, error: 0 } as Record<'success' | 'warning' | 'error', number>,
      ),
    [documents],
  );
  const severityCounts = useMemo(
    () =>
      issueCards.reduce(
        (acc, card) => {
          const countClass = String((card as any).count_class ?? 'documentary_discrepancy');
          if (countClass !== 'documentary_discrepancy') {
            return acc;
          }
          const severity = normalizeDiscrepancySeverity(card.severity);
          acc[severity] = (acc[severity] || 0) + 1;
          return acc;
        },
        { critical: 0, major: 0, minor: 0 } as Record<"critical" | "major" | "minor", number>
      ),
    [issueCards]
  );
  const laneCounts = useMemo(
    () =>
      issueCards.reduce(
        (acc, card) => {
          const workflowLane = String((card as any).workflow_lane ?? 'documentary_review');
          if (workflowLane === 'compliance_review') acc.compliance += 1;
          else if (workflowLane === 'manual_review') acc.manual += 1;
          else acc.documentary += 1;
          return acc;
        },
        { documentary: 0, compliance: 0, manual: 0 },
      ),
    [issueCards],
  );
  const filteredIssueCards = useMemo(() => {
    if (issueFilter === "all") return issueCards;
    return issueCards.filter(
      (card) => normalizeDiscrepancySeverity(card.severity) === issueFilter
    );
  }, [issueCards, issueFilter]);
  const showSkeletonLayout = Boolean(
    validationSessionId && !resultData && resultsLoading && !(jobError || resultsError),
  );
  const normalizedJobStatus = String(jobStatus?.status ?? '').trim().toLowerCase();
  const isTerminalJobStatus = ['completed', 'failed', 'error'].includes(normalizedJobStatus);
  const isResultsPending = !resultData && resultsLoading && !(jobError || resultsError);
  const shouldBridgeFinalizingResults =
    !resultData &&
    isTerminalJobStatus &&
    !(jobError || resultsError) &&
    !terminalResultsTimedOut &&
    (isFinalizingResults || !isResultsPending);
  const { successCount, warningCount, successRate, extractionRate, extractionSuccessful } = useMemo(() => {
    // Use authoritative document_status from backend (same source as SummaryStrip)
    const statusDistribution = 
      analyticsData?.document_status_distribution ?? 
      summary?.document_status ?? 
      summary?.status_counts ?? 
      {};
    
    const fromDistSuccess = typeof statusDistribution.success === 'number' ? statusDistribution.success : 0;
    const fromDistWarning = typeof statusDistribution.warning === 'number' ? statusDistribution.warning : 0;
    const fromDistError = typeof statusDistribution.error === 'number' ? statusDistribution.error : 0;
    
    // Check if we have real distribution data
    const hasDistribution = fromDistSuccess > 0 || fromDistWarning > 0 || fromDistError > 0;
    
    let resolvedSuccessCount: number;
    let resolvedErrorCount: number;
    let resolvedWarningCount: number;
    
    if (hasDistribution) {
      // Use backend's authoritative counts
      resolvedSuccessCount = fromDistSuccess;
      resolvedErrorCount = fromDistError;
      resolvedWarningCount = fromDistWarning;
    } else {
      // Fall back to the normalized document list so overview matches the Documents tab.
      resolvedSuccessCount = documentStatusCounts.success;
      resolvedErrorCount = documentStatusCounts.error;
      resolvedWarningCount = documentStatusCounts.warning;
    }

    // Validation success rate (based on validation status)
    const resolvedSuccessRate =
      totalDocuments > 0 ? Math.round((resolvedSuccessCount / totalDocuments) * 100) : 0;

    // Extraction success rate (OCR extraction - separate from validation)
    // This measures how many docs were successfully extracted, regardless of validation status
    const derivedExtractionSuccess = documents.filter((doc) => (doc.extractionStatus ?? "").toLowerCase() === "success").length;
    const extractionSuccessful = 
      typeof summary?.successful_extractions === "number" 
        ? summary.successful_extractions 
        : typeof summary?.failed_extractions === "number"
        ? Math.max(0, totalDocuments - summary.failed_extractions)
        : derivedExtractionSuccess;
    const extractionRate = totalDocuments > 0 
      ? Math.round((extractionSuccessful / totalDocuments) * 100) 
      : 0;

    return {
      successCount: resolvedSuccessCount,
      errorCount: resolvedErrorCount,
      warningCount: resolvedWarningCount,
      successRate: resolvedSuccessRate,
      extractionRate, // New: for Document Extraction progress bar
      extractionSuccessful,
    };
  }, [
    documents,
    summary?.successful_extractions,
    summary?.failed_extractions,
    summary?.document_status,
    summary?.status_counts,
    analyticsData?.document_status_distribution,
    documentStatusCounts.success,
    documentStatusCounts.warning,
    documentStatusCounts.error,
    totalDocuments,
  ]);
  const complianceScore = useMemo(
    () => analyticsData?.compliance_score ?? analyticsData?.lc_compliance_score ?? summary?.compliance_rate ?? successRate,
    [analyticsData?.compliance_score, analyticsData?.lc_compliance_score, summary?.compliance_rate, successRate],
  );
  const lcComplianceScore = complianceScore;
  
  // V2 Validation State Machine
  const validationState = useMemo(() => {
    if (!structuredResult) return null;
    return deriveValidationState(structuredResult as unknown as Record<string, unknown>);
  }, [structuredResult]);
  const canonicalResultTruth = useMemo(
    () => getCanonicalResultTruth(resultData ?? null),
    [resultData],
  );
  
  const documentRisk = useMemo(
    () =>
      analyticsData?.document_risk ??
      documents.map((doc) => ({
        document_id: doc.documentId,
        filename: doc.name,
        risk: doc.issuesCount >= 3 ? "high" : doc.issuesCount > 0 ? "medium" : "low",
      })),
    [analyticsData?.document_risk, documents],
  );
  const extractionAccuracy = useMemo(() => extractionRate, [extractionRate]);
  const canonicalRequiredDocs = useMemo(() => {
    const candidates = [
      Array.isArray(lcClassification?.required_documents)
        ? (lcClassification.required_documents as LcClassificationRequiredDocument[])
        : [],
      Array.isArray(lcData?.required_documents_detailed)
        ? (lcData.required_documents_detailed as LcClassificationRequiredDocument[])
        : [],
      Array.isArray(lcPrimaryExtractedFields?.required_documents_detailed)
        ? (lcPrimaryExtractedFields.required_documents_detailed as LcClassificationRequiredDocument[])
        : [],
    ];
    for (const candidate of candidates) {
      if (candidate.length > 0) {
        return candidate;
      }
    }
    return [] as LcClassificationRequiredDocument[];
  }, [lcClassification?.required_documents, lcData?.required_documents_detailed, lcPrimaryExtractedFields?.required_documents_detailed]);
  const lcRequirementTypes = useMemo(() => {
    const canonicalCodes = canonicalRequiredDocs
      .map((doc) => String(doc?.code || "").trim().toLowerCase())
      .filter((code) => code.length > 0);
    if (canonicalCodes.length > 0) {
      return canonicalCodes;
    }
    const candidates = [
      lcData?.required_document_types,
      lcData?.requiredDocumentTypes,
      lcPrimaryExtractedFields?.required_document_types,
      lcPrimaryExtractedFields?.requiredDocumentTypes,
    ];
    for (const candidate of candidates) {
      if (Array.isArray(candidate) && candidate.length > 0) {
        return candidate
          .map((item) => String(item || '').trim().toLowerCase())
          .filter((item) => item.length > 0);
      }
    }
    return [] as string[];
  }, [canonicalRequiredDocs, lcData, lcPrimaryExtractedFields]);
  const lcRequirementConditions = useMemo(() => {
    const candidates = [
      lcClassification?.requirement_conditions,
      lcData?.requirement_conditions,
      lcPrimaryExtractedFields?.requirement_conditions,
    ];
    for (const candidate of candidates) {
      const formatted = formatConditions(candidate);
      if (formatted.length > 0) {
        return formatted;
      }
    }
    return [] as string[];
  }, [lcClassification?.requirement_conditions, lcData, lcPrimaryExtractedFields]);
  const lcUnmappedRequirements = useMemo(() => {
    const candidates = [
      lcClassification?.unmapped_requirements,
      lcData?.unmapped_requirements,
      lcPrimaryExtractedFields?.unmapped_requirements,
    ];
    for (const candidate of candidates) {
      const formatted = formatConditions(candidate);
      if (formatted.length > 0) {
        return formatted;
      }
    }
    return [] as string[];
  }, [lcClassification?.unmapped_requirements, lcData, lcPrimaryExtractedFields]);

  const requirementChecklist = useMemo(() => {
    const normalizedDocs = documents.map((doc) => ({
      ...doc,
      normalizedType: String(doc.typeKey || '').toLowerCase(),
      warningReasons: (((doc as any).warningReasons ?? []) as string[])
        .map((reason) =>
          _humanizeDocumentReviewReason(String(reason), {
            docType: String(doc.typeKey || ''),
            rawText: String((doc as any).rawText ?? ''),
            criticalFieldStates: (doc as any).criticalFieldStates ?? {},
            fieldDiagnostics: (doc as any).fieldDiagnostics ?? {},
            missingRequiredFields: (doc as any).missingRequiredFields ?? [],
          }),
        )
        .filter((reason): reason is string => Boolean(reason)),
      reviewReasons: (((doc as any).reviewReasons ?? []) as string[])
        .map((reason) =>
          _humanizeDocumentReviewReason(String(reason), {
            docType: String(doc.typeKey || ''),
            rawText: String((doc as any).rawText ?? ''),
            criticalFieldStates: (doc as any).criticalFieldStates ?? {},
            fieldDiagnostics: (doc as any).fieldDiagnostics ?? {},
            missingRequiredFields: (doc as any).missingRequiredFields ?? [],
          }),
        )
        .filter((reason): reason is string => Boolean(reason)),
    }));

    type RequirementRowSeed = {
      key: string;
      label: string;
      requirementText: string;
      code: string | null;
      typeCandidates: string[];
    };

    const requirementSeeds: RequirementRowSeed[] = [];
    const seenKeys = new Set<string>();
    const pushRequirementSeed = (seed: RequirementRowSeed): void => {
      if (seenKeys.has(seed.key)) return;
      seenKeys.add(seed.key);
      requirementSeeds.push(seed);
    };

    canonicalRequiredDocs.forEach((doc, index) => {
      const code = normalizeRequirementCode(doc?.code);
      const label =
        String(doc?.display_name || '').trim() ||
        (code ? humanizeLabel(code) : `Required Document ${index + 1}`);
      const requirementText =
        String(doc?.raw_text || '').trim() ||
        String(doc?.display_name || '').trim() ||
        (code ? humanizeLabel(code) : label);
      const key = code || `required_document_${index + 1}`;
      pushRequirementSeed({
        key,
        label,
        requirementText,
        code,
        typeCandidates: buildRequirementTypeCandidates(code),
      });
    });

    if (requirementSeeds.length === 0) {
      lcRequirementTypes.forEach((rawType) => {
        const code = normalizeRequirementCode(rawType);
        if (!code) return;
        pushRequirementSeed({
          key: code,
          label: humanizeLabel(code),
          requirementText: humanizeLabel(code),
          code,
          typeCandidates: buildRequirementTypeCandidates(code),
        });
      });
    }

    const items = requirementSeeds
      .map((seed) => {
        const requirementTextLower = seed.requirementText.toLowerCase();
        const matchedDoc = normalizedDocs.find((doc) => {
          if (seed.typeCandidates.includes(doc.normalizedType)) return true;
          if (!seed.typeCandidates.length) {
            const normalizedTypeLabel = doc.normalizedType.replace(/_/g, ' ');
            return requirementTextLower.includes(normalizedTypeLabel) || requirementTextLower.includes(String(doc.name || '').toLowerCase());
          }
          return false;
        });
        const rawMatchedRequirementStatus = matchedDoc?.requirementStatus;
        const hasMissingFields = Boolean(
          matchedDoc && Array.isArray(matchedDoc.missingRequiredFields) && matchedDoc.missingRequiredFields.length > 0,
        );
        const hasReviewSignals = Boolean(
          matchedDoc &&
            ((matchedDoc.warningReasons ?? []).length > 0 ||
              (matchedDoc.reviewReasons ?? []).length > 0 ||
              matchedDoc.reviewState === 'needs_review' ||
              matchedDoc.reviewState === 'blocked'),
        );
        const requirementStatus: RequirementChecklistStatus = !matchedDoc
          ? 'missing'
          : rawMatchedRequirementStatus === 'matched'
          ? 'matched'
          : rawMatchedRequirementStatus === 'missing'
          ? 'partial'
          : rawMatchedRequirementStatus === 'partial'
          ? 'partial'
          : hasMissingFields || hasReviewSignals
          ? 'partial'
          : 'matched';
        const reviewState: RequirementChecklistReviewState = !matchedDoc
          ? 'awaiting_document'
          : matchedDoc.reviewState === 'blocked'
          ? 'blocked'
          : matchedDoc.reviewState === 'needs_review' || requirementStatus === 'partial'
          ? 'needs_review'
          : 'ready';
        const synthesizedReviewNotes = matchedDoc
          ? _buildSpecificFieldMissingReasons({
              docType: String(matchedDoc.typeKey || ''),
              rawText: String((matchedDoc as any).rawText ?? ''),
              criticalFieldStates: (matchedDoc as any).criticalFieldStates ?? {},
              fieldDiagnostics: (matchedDoc as any).fieldDiagnostics ?? {},
              missingRequiredFields: (matchedDoc as any).missingRequiredFields ?? [],
            })
          : [];
        const reviewNotes = matchedDoc
          ? [...matchedDoc.warningReasons, ...matchedDoc.reviewReasons].filter(Boolean)
          : ['Document not uploaded yet'];

        if (
          matchedDoc &&
          requirementStatus === 'partial' &&
          reviewNotes.length === 0 &&
          Array.isArray(matchedDoc.missingRequiredFields) &&
          matchedDoc.missingRequiredFields.length > 0
        ) {
          if (synthesizedReviewNotes.length > 0) {
            reviewNotes.push(...synthesizedReviewNotes);
          } else {
            reviewNotes.push(
              `Missing required fields: ${matchedDoc.missingRequiredFields
                .slice(0, 3)
                .map((field) => humanizeLabel(String(field)))
                .join(', ')}`,
            );
          }
        }

        if (matchedDoc && reviewNotes.length === 0) {
          if (reviewState === 'blocked') {
            reviewNotes.push('This document is blocked from clean presentation until extraction or validation issues are resolved.');
          } else if (reviewState === 'needs_review') {
            reviewNotes.push('This document requires manual review before clean presentation.');
          }
        }

        return {
          key: seed.key,
          label: seed.label,
          requirementStatus,
          reviewState,
          matchedDoc,
          reviewNotes,
          requirementText: seed.requirementText,
        };
      })
      .filter(Boolean) as Array<{
        key: string;
        label: string;
        requirementStatus: RequirementChecklistStatus;
        reviewState: RequirementChecklistReviewState;
        matchedDoc: (typeof normalizedDocs)[number] | undefined;
        reviewNotes: string[];
        requirementText: string;
      }>;

    return items;
  }, [documents, canonicalRequiredDocs, lcRequirementTypes]);
  const requirementChecklistSummary = useMemo<RequirementChecklistSummary>(() => {
    return requirementChecklist.reduce(
      (acc, item) => {
        acc[item.requirementStatus] += 1;
        if (item.reviewState === 'ready') acc.ready += 1;
        if (item.reviewState === 'needs_review') acc.needsReview += 1;
        if (item.reviewState === 'blocked') acc.blocked += 1;
        if (item.reviewState === 'awaiting_document') acc.awaitingDocument += 1;
        return acc;
      },
      {
        matched: 0,
        partial: 0,
        missing: 0,
        ready: 0,
        needsReview: 0,
        blocked: 0,
        awaitingDocument: 0,
      },
    );
  }, [requirementChecklist]);
  const lcRequiredDocumentTypeSet = useMemo(() => {
    const requiredTypes = new Set<string>(['letter_of_credit']);
    canonicalRequiredDocs.forEach((doc) => {
      buildRequirementTypeCandidates(normalizeRequirementCode(doc?.code)).forEach((candidate) => requiredTypes.add(candidate));
    });
    if (canonicalRequiredDocs.length === 0) {
      lcRequirementTypes.forEach((rawType) => {
        buildRequirementTypeCandidates(normalizeRequirementCode(rawType)).forEach((candidate) => requiredTypes.add(candidate));
      });
    }
    return requiredTypes;
  }, [canonicalRequiredDocs, lcRequirementTypes]);
  const checklistReviewFindings = useMemo<RequirementReviewFinding[]>(() => {
    const classifyFindingCategory = ({
      matchedDoc,
      requirementStatus,
      reviewState,
      reviewNotes,
    }: {
      matchedDoc?: (typeof requirementChecklist)[number]['matchedDoc'];
      requirementStatus: RequirementChecklistStatus;
      reviewState: RequirementChecklistReviewState;
      reviewNotes: string[];
    }): string => {
      if (!matchedDoc) return 'Missing required document';
      const combined = reviewNotes.join(' ').toLowerCase();
      if (combined.includes('does not show') || combined.includes('does not clearly show') || combined.includes('missing one or more core')) {
        return 'Source-document absence';
      }
      if (combined.includes('could not be confirmed') || combined.includes('confidence') || combined.includes('extraction')) {
        return 'Extraction uncertainty';
      }
      if (reviewState === 'blocked') {
        return 'Presentation block';
      }
      if (requirementStatus === 'partial') {
        return 'Requirement coverage gap';
      }
      return 'Manual review';
    };

    const buildWhyItMatters = ({
      category,
      matchedDoc,
      label,
      reviewState,
    }: {
      category: string;
      matchedDoc?: (typeof requirementChecklist)[number]['matchedDoc'];
      label: string;
      reviewState: RequirementChecklistReviewState;
    }): string => {
      if (!matchedDoc) {
        return `This LC-required ${label.toLowerCase()} is not currently available in the document set, so the case cannot be treated as presentation-ready.`;
      }
      if (category === 'Presentation block') {
        return `This matched ${label.toLowerCase()} is currently blocked from clean presentation until the review issue is cleared.`;
      }
      if (category === 'Source-document absence') {
        return `The ${label.toLowerCase()} is uploaded, but the required information does not appear clearly enough in the source document to treat coverage as complete.`;
      }
      if (category === 'Extraction uncertainty') {
        return `The ${label.toLowerCase()} may contain the required information, but extraction could not confirm it strongly enough to clear the review.`;
      }
      if (reviewState === 'needs_review') {
        return `The ${label.toLowerCase()} is present, but the workflow still requires human review before it can be treated as clean for presentation.`;
      }
      return `The uploaded ${label.toLowerCase()} does not yet satisfy the full LC-required coverage.`;
    };

    const buildRecommendedAction = ({
      category,
      matchedDoc,
      label,
      requirementText,
      reviewNote,
    }: {
      category: string;
      matchedDoc?: (typeof requirementChecklist)[number]['matchedDoc'];
      label: string;
      requirementText: string;
      reviewNote: string;
    }): string => {
      if (!matchedDoc) {
        return `Upload a ${label.toLowerCase()} that satisfies this LC requirement: ${requirementText}`;
      }
      if (category === 'Source-document absence') {
        return `Confirm whether the bank will accept the current ${label.toLowerCase()} as presented, or obtain an amended document that shows the missing information clearly.`;
      }
      if (category === 'Extraction uncertainty') {
        return `Visually review the ${label.toLowerCase()} and confirm the required content before presentation.`;
      }
      if (category === 'Presentation block') {
        return `Clear the blocking review on the ${label.toLowerCase()} before treating the set as presentation-ready.`;
      }
      if (category === 'Manual review') {
        return `Review the ${label.toLowerCase()} against the LC wording before presentation.`;
      }
      if (/missing required fields/i.test(reviewNote)) {
        return `Amend or reissue the ${label.toLowerCase()} so it includes the missing required wording or fields, then revalidate.`;
      }
      return `Complete the ${label.toLowerCase()} review and confirm it fully covers the LC requirement before presentation.`;
    };

    const buildSourceBasis = ({
      category,
      matchedDoc,
    }: {
      category: string;
      matchedDoc?: (typeof requirementChecklist)[number]['matchedDoc'];
    }): string => {
      if (!matchedDoc) return 'LC required-document checklist';
      if (category === 'Source-document absence') return 'Source document content review';
      if (category === 'Extraction uncertainty') return 'Extraction review note';
      if (category === 'Presentation block') return 'Document review block';
      return 'LC requirement coverage + document review';
    };

    return requirementChecklist.flatMap((item) => {
      const reviewNote =
        item.reviewNotes[0] ||
        (item.matchedDoc
          ? 'This document still needs review before it can be treated as clean for presentation.'
          : item.requirementText);
      const category = classifyFindingCategory({
        matchedDoc: item.matchedDoc,
        requirementStatus: item.requirementStatus,
        reviewState: item.reviewState,
        reviewNotes: item.reviewNotes,
      });
      const baseFinding = {
        category,
        whyItMatters: buildWhyItMatters({
          category,
          matchedDoc: item.matchedDoc,
          label: item.label,
          reviewState: item.reviewState,
        }),
        evidence: item.matchedDoc
          ? `Matched file: ${item.matchedDoc.name}. ${reviewNote}`
          : `LC requirement: ${item.requirementText}`,
        recommendedAction: buildRecommendedAction({
          category,
          matchedDoc: item.matchedDoc,
          label: item.label,
          requirementText: item.requirementText,
          reviewNote,
        }),
        sourceBasis: buildSourceBasis({
          category,
          matchedDoc: item.matchedDoc,
        }),
        documentName: item.matchedDoc?.name,
        documentType: item.matchedDoc?.type,
        requirementText: item.requirementText,
      } satisfies Omit<RequirementReviewFinding, 'key' | 'title' | 'detail' | 'severity'>;

      if (item.requirementStatus === 'missing') {
        return [
          {
            key: `${item.key}-missing`,
            title: item.matchedDoc ? `Complete ${item.label} requirement coverage` : `Upload ${item.label}`,
            detail:
              item.matchedDoc
                ? item.reviewNotes[0] || 'A matching file exists, but the required declaration or clause coverage is still unresolved.'
                : item.requirementText,
            severity: 'critical',
            ...baseFinding,
          },
        ];
      }
      if (item.reviewState === 'blocked') {
        return [
          {
            key: `${item.key}-blocked`,
            title: `Clear ${item.label} review block`,
            detail:
              item.reviewNotes[0] || 'This document is blocked from clean presentation until the review issue is cleared.',
            severity: 'critical',
            ...baseFinding,
          },
        ];
      }
      if (item.requirementStatus === 'partial') {
        return [
          {
            key: `${item.key}-partial`,
            title: `Complete ${item.label} requirement coverage`,
            detail:
              item.reviewNotes[0] || 'This matched document still has missing required elements against the LC requirement.',
            severity: 'major',
            ...baseFinding,
          },
        ];
      }
      if (item.reviewState === 'needs_review') {
        return [
          {
            key: `${item.key}-review`,
            title: `Complete review for ${item.label}`,
            detail: item.reviewNotes[0] || 'This document requires manual review before submission.',
            severity: 'major',
            ...baseFinding,
          },
        ];
      }
      return [];
    });
  }, [requirementChecklist]);
  const surfaceFindingsCount = issueCards.length > 0 ? backendIssueCount : checklistReviewFindings.length;
  const totalDiscrepancies = surfaceFindingsCount;
  const performanceInsights = useMemo(
    () => [
      extractionSuccessful + "/" + (totalDocuments || 0) + " documents extracted successfully",
      totalDiscrepancies + " issue" + (totalDiscrepancies === 1 ? "" : "s") + " detected",
      "Compliance score " + complianceScore + "%",
    ],
    [extractionSuccessful, totalDocuments, totalDiscrepancies, complianceScore],
  );
  const exporterPresentationTruth = useMemo(
    () =>
      getExporterPresentationTruth({
        canonicalResultTruth,
        checklistTruth: {
          missingRequirements: requirementChecklistSummary.missing,
          partialRequirements: requirementChecklistSummary.partial,
          blockedReviews: requirementChecklistSummary.blocked,
          reviewRequired: requirementChecklistSummary.needsReview,
          awaitingDocuments: requirementChecklistSummary.awaitingDocument,
        },
        totalIssues: surfaceFindingsCount,
      }),
    [canonicalResultTruth, requirementChecklistSummary, surfaceFindingsCount],
  );
  const actionEngine = useMemo(() => {
    const actions: Array<{ priority: 'critical' | 'major' | 'minor'; title: string; detail: string }> = [];

    checklistReviewFindings.forEach((finding) => {
      actions.push({
        priority: finding.severity,
        title: finding.title,
        detail: finding.detail,
      });
    });

    issueCards.slice(0, 5).forEach((issue) => {
      const workflowLane = String((issue as any).workflow_lane ?? '');
      const nextAction = safeString((issue as any).next_action || issue.suggestion || issue.description || 'Review this issue before submission.');
      const actionTitle =
        workflowLane === 'compliance_review'
          ? `Route ${safeString(issue.title || 'compliance alert')} to internal compliance review`
          : workflowLane === 'manual_review'
          ? `Complete manual review for ${safeString(issue.title || 'document review item')}`
          : safeString(issue.title || (issue as any).message || 'Resolve documentary issue');
      actions.push({
        priority: normalizeDiscrepancySeverity(issue.severity) === 'critical' ? 'critical' : 'major',
        title: actionTitle,
        detail: nextAction,
      });
    });

    const unique = new Map<string, { priority: 'critical' | 'major' | 'minor'; title: string; detail: string }>();
    actions.forEach((action) => {
      if (!unique.has(action.title)) unique.set(action.title, action);
    });

    return Array.from(unique.values()).sort((a, b) => {
      const rank = { critical: 0, major: 1, minor: 2 };
      return rank[a.priority] - rank[b.priority];
    });
  }, [checklistReviewFindings, issueCards]);
  const additionalActionItems = useMemo(() => {
    const reviewFindingTitles = new Set(checklistReviewFindings.map((finding) => finding.title));
    return actionEngine.filter((action) => !reviewFindingTitles.has(action.title));
  }, [actionEngine, checklistReviewFindings]);
  const displayBankVerdict = useMemo<BankVerdict | null>(() => {
    const baseVerdict = (structuredResult?.bank_verdict as BankVerdict | null) ?? null;
    const normalizedVerdict = String(baseVerdict?.verdict ?? '').trim().toUpperCase();

    if (exporterPresentationTruth.presentationStatus === 'ready') {
      return baseVerdict;
    }

    if (baseVerdict && normalizedVerdict && normalizedVerdict !== 'SUBMIT') {
      return baseVerdict;
    }

    const checklistCriticalCount = checklistReviewFindings.filter((finding) => finding.severity === 'critical').length;
    const checklistMajorCount = checklistReviewFindings.length - checklistCriticalCount;
    const actionItems: BankVerdictActionItem[] = actionEngine.slice(0, 5).map((action) => ({
      priority: action.priority === 'critical' ? 'critical' : action.priority === 'major' ? 'high' : 'medium',
      issue: action.title,
      action: action.detail,
    }));

    if (exporterPresentationTruth.presentationStatus === 'not_ready') {
      return {
        verdict: 'HOLD',
        verdict_color: 'orange',
        verdict_message: 'Review is blocking clean presentation',
        recommendation: 'Resolve missing or blocked checklist items before treating this case as submission-ready.',
        can_submit: false,
        will_be_rejected: false,
        estimated_discrepancy_fee: baseVerdict?.estimated_discrepancy_fee ?? 0,
        issue_summary: {
          critical: checklistCriticalCount,
          major: checklistMajorCount,
          minor: 0,
          total: checklistReviewFindings.length,
        },
        action_items: actionItems,
        action_items_count: actionEngine.length,
      };
    }

    return {
      verdict: 'CAUTION',
      verdict_color: 'yellow',
      verdict_message: 'Review required before bank submission',
      recommendation: 'Complete the unresolved checklist reviews before treating this case as submission-ready.',
      can_submit: false,
      will_be_rejected: false,
      estimated_discrepancy_fee: baseVerdict?.estimated_discrepancy_fee ?? 0,
      issue_summary: {
        critical: checklistCriticalCount,
        major: checklistMajorCount,
        minor: 0,
        total: checklistReviewFindings.length,
      },
      action_items: actionItems,
      action_items_count: actionEngine.length,
    };
  }, [actionEngine, checklistReviewFindings, exporterPresentationTruth.presentationStatus, structuredResult?.bank_verdict]);
  const customsPackReadiness = useMemo(() => {
    const derivedBlockers = requirementChecklist.filter(
      (item) => item.requirementStatus === 'missing' || item.reviewState === 'blocked',
    );
    const derivedReviews = requirementChecklist.filter(
      (item) => item.requirementStatus === 'partial' || item.reviewState === 'needs_review',
    );
    const ownerBuckets = {
      beneficiary: 0,
      thirdParty: 0,
      mixed: 0,
      compliance: 0,
      waiver: 0,
    };
    issueCards.forEach((issue) => {
      const owner = String(
        (issue as any).fix_owner ?? (issue as any).remediation_owner ?? (issue as any).fixOwner ?? '',
      ).toLowerCase();
      if (owner.includes('beneficiary')) ownerBuckets.beneficiary += 1;
      else if (owner.includes('third')) ownerBuckets.thirdParty += 1;
      else if (owner.includes('mixed')) ownerBuckets.mixed += 1;
      else if (owner.includes('compliance')) ownerBuckets.compliance += 1;
      else if (owner.includes('waiver')) ownerBuckets.waiver += 1;
    });
    return {
      status: exporterPresentationTruth.presentationStatus,
      summary: exporterPresentationTruth.presentationSummary,
      blockers: exporterPresentationTruth.presentationStatus === 'not_ready' ? derivedBlockers : [],
      reviews: exporterPresentationTruth.presentationStatus === 'ready' ? [] : derivedReviews,
      ownerBuckets,
      source: 'shared',
    };
  }, [requirementChecklist, issueCards, exporterPresentationTruth]);
  const customsPack = structuredResult?.customs_pack;
  const packGenerated = Boolean(manifestData?.documents?.length);
  const processingSummaryExtras =
    (structuredResult as any)?.processing_summary_v2 ??
    (structuredResult?.processing_summary as Record<string, any> | undefined);
  const analyticsExtras = structuredResult?.analytics as Record<string, any> | undefined;
  const processingTime =
    processingSummaryExtras?.processing_time_display ||
    analyticsExtras?.processing_time_display ||
    "-";
  const overviewTruth = useMemo(
    () =>
      getExporterOverviewTruth({
        totalDocuments,
        totalIssues: surfaceFindingsCount,
        complianceScore,
        extractionAccuracy,
        processingTime,
        successCount,
        warningCount,
        packGenerated,
        performanceInsights,
        canonicalResultTruth,
        checklistTruth: {
          missingRequirements: requirementChecklistSummary.missing,
          partialRequirements: requirementChecklistSummary.partial,
          blockedReviews: requirementChecklistSummary.blocked,
          reviewRequired: requirementChecklistSummary.needsReview,
          awaitingDocuments: requirementChecklistSummary.awaitingDocument,
        },
      }),
    [
      totalDocuments,
      surfaceFindingsCount,
      complianceScore,
      extractionAccuracy,
      processingTime,
      successCount,
      warningCount,
      packGenerated,
      performanceInsights,
      canonicalResultTruth,
      requirementChecklistSummary,
    ],
  );
  const submissionEligibility = canonicalResultTruth.submissionEligibility;
  const canSubmitFromValidation = canonicalResultTruth.canSubmitFromValidation;
  const canGenerateCustomsPack = exporterPresentationTruth.presentationStatus !== 'not_ready';
  const isReadyToSubmit = useMemo(() => {
    if (!enableBankSubmission) return false;
    if (guardrailsQueryEnabled && guardrailsLoading) return false;
    if (!canSubmitFromValidation) return false;
    if (exporterPresentationTruth.presentationStatus !== 'ready') return false;
    if (!guardrails) {
      return canSubmitFromValidation;
    }
    return guardrails.can_submit && guardrails.high_severity_discrepancies === 0;
  }, [
    enableBankSubmission,
    guardrails,
    guardrailsLoading,
    guardrailsQueryEnabled,
    canSubmitFromValidation,
    exporterPresentationTruth.presentationStatus,
  ]);

  // Contract Validation warnings (Output-First layer)
  const contractWarnings = resultData?.contractWarnings ?? [];
  const hasContractWarnings = contractWarnings.length > 0;
  const contractWarningsByLevel = useMemo(() => {
    const errors = contractWarnings.filter((w) => w.severity === 'error');
    const warnings = contractWarnings.filter((w) => w.severity === 'warning');
    const infos = contractWarnings.filter((w) => w.severity === 'info');
    return { errors, warnings, infos };
  }, [contractWarnings]);

  // Early returns AFTER all hooks are called
  if (!resultData) {
    if (!validationSessionId) {
      return (
        <div className="flex items-center justify-center min-h-[60vh] p-6">
          <Card className="max-w-xl mx-auto text-center">
            <CardHeader>
              <CardTitle>Upload Required</CardTitle>
              <CardDescription>
                Upload an LC package from the Exporter Dashboard to see validation results.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={() => navigate("/lcopilot/exporter-dashboard?section=upload")}>
                Go to Upload
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    if (jobError || resultsError) {
      const errorMessage =
        jobError?.message ||
        resultsError?.message ||
        "Failed to load validation results.";
      return (
        <div className="flex items-center justify-center min-h-[60vh]">
          <Card className="max-w-lg mx-auto">
            <CardHeader>
              <CardTitle>Unable to load validation results</CardTitle>
              <CardDescription>{errorMessage}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button variant="outline" onClick={() => window.location.reload()}>
                Retry
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    const statusLabel = jobStatus?.status
      ? jobStatus.status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
      : "Processing";

    if (shouldBridgeFinalizingResults) {
      return (
        <div className="min-h-[60vh] p-6">
          <Card className="max-w-2xl mx-auto border border-border/60 shadow-soft">
            <CardHeader>
              <CardTitle>Validation finished. Preparing your results...</CardTitle>
              <CardDescription>
                The validation job is complete, and we&apos;re loading the final results package for this case. This usually takes a few seconds.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-muted/20 p-4">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <div>
                  <p className="font-medium">Finalizing the review workspace</p>
                  <p className="text-sm text-muted-foreground">
                    We&apos;re retrying the canonical results payload automatically so you can land directly in the finished case.
                  </p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                If this takes longer than expected, a manual retry option will appear automatically.
              </p>
            </CardContent>
          </Card>
        </div>
      );
    }

    if (isTerminalJobStatus && terminalResultsTimedOut && !isResultsPending) {
      return (
        <div className="min-h-[60vh] p-6">
          <Card className="max-w-2xl mx-auto border border-border/60 shadow-soft">
            <CardHeader>
              <CardTitle>Results are taking longer than expected</CardTitle>
              <CardDescription>
                The validation job reached a terminal state ({statusLabel}), but this page still has not received the final results payload.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Automatic loading is still retrying</AlertTitle>
                <AlertDescription>
                  This should not happen for a normal successful run. Retry loading the results now, or return to the dashboard and reopen the case if the payload still does not appear.
                </AlertDescription>
              </Alert>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => refreshResults('manual')} disabled={!validationSessionId || resultsLoading}>
                  {resultsLoading ? 'Fetching...' : 'Retry loading results'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    const params = new URLSearchParams(searchParams);
                    params.set('section', 'reviews');
                    setSearchParams(params, { replace: true });
                  }}
                >
                  Return to dashboard
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return (
      <div className="min-h-[60vh] p-6">
        <div className="flex flex-col items-center justify-center space-y-4 pb-8">
          <Loader2 className="w-10 h-10 animate-spin text-primary" />
          <div className="text-center">
            <p className="text-lg font-semibold">Validation in progress</p>
            <p className="text-sm text-muted-foreground">Current status: {statusLabel}</p>
          </div>
        </div>
        {showSkeletonLayout && renderLoadingSkeletons()}
      </div>
    );
  }

  if (!structuredResult) {
    return null;
  }

  function renderLoadingSkeletons() {
    return (
      <div className="space-y-6">
        <div className="grid gap-6 md:grid-cols-2">
          {[0, 1].map((index) => (
            <Card key={`overview-skeleton-${index}`} className="border border-border/60 shadow-soft">
              <CardContent className="space-y-3 p-6">
                <Skeleton className="h-5 w-48" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-4 w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {[0, 1].map((index) => (
            <Card key={`document-skeleton-${index}`} className="border border-border/60 shadow-soft">
              <CardContent className="space-y-4 p-6">
                <Skeleton className="h-5 w-56" />
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-4 w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {[0, 1].map((index) => (
            <Card key={`issue-skeleton-${index}`} className="border border-border/60 shadow-soft">
              <CardContent className="space-y-3 p-6">
                <Skeleton className="h-5 w-64" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {[0, 1].map((index) => (
            <Card key={`analytics-skeleton-${index}`} className="border border-border/60 shadow-soft">
              <CardContent className="space-y-4 p-6">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-4/5" />
                <Skeleton className="h-4 w-2/5" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const renderAIInsightsCard = () => {
    // Show AI insights if available
    if (aiInsights?.summary) {
      return (
        <Card className="shadow-soft border border-primary/20 bg-primary/5">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/20">
                <Lightbulb className="w-5 h-5 text-primary" />
              </div>
              <div>
                <CardTitle className="flex items-center gap-2">
                  AI Risk Insights
                  <Badge variant="outline" className="text-xs bg-primary/10 text-primary border-primary/30">
                    AI-Powered
                  </Badge>
                </CardTitle>
                <CardDescription>
                  Context-aware guidance generated for this LC package.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-foreground leading-relaxed">{aiInsights.summary}</p>
            {Array.isArray(aiInsights.suggestions) && aiInsights.suggestions.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">Recommended Actions</p>
                <ul className="space-y-2">
                  {aiInsights.suggestions.map((suggestion, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm">
                      <CheckCircle className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                      <span>{suggestion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {aiInsights.rule_references && aiInsights.rule_references.length > 0 && (
              <div className="pt-2 border-t border-primary/20">
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium">References:</span>{' '}
                  {aiInsights.rule_references.map((ref, idx) => (
                    <span key={idx}>
                      {idx > 0 && ', '}
                      {typeof ref === 'string' ? ref : ref.rule_code}
                    </span>
                  ))}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      );
    }
    
    // AI insights placeholder removed - feature is enabled but backend integration pending
    // The issues are already validated with AI through the AI Validation layer
    
    return null;
  };

  const renderReferenceIssuesCard = () => {
    if (!referenceIssues.length) {
      return null;
    }

    return (
      <Card className="shadow-soft border border-dashed border-muted">
        <CardHeader>
          <CardTitle className="text-base">Technical References</CardTitle>
          <CardDescription>
            Underlying rule citations retained for audit (hidden from SME view).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          {referenceIssues.map((issue, index) => (
            <div key={index} className="p-3 rounded-lg bg-secondary/20 border border-secondary/40">
              <p className="font-medium text-foreground">
                {issue.title || issue.rule || `Rule ${index + 1}`}
              </p>
              <p className="text-xs uppercase tracking-wide mt-1">
                Severity: {issue.severity || "reference"} - {issue.ruleset_domain || "rulebook"}
              </p>
              {issue.article && (
                <p className="text-xs mt-1">
                  Article: <span className="font-medium">{issue.article}</span>
                </p>
              )}
              {issue.message && <p className="mt-2">{issue.message}</p>}
            </div>
          ))}
        </CardContent>
      </Card>
    );
  };
  const hasTimeline = timelineEvents.length > 0;
  const timelineDisplay = hasTimeline
    ? timelineEvents.map((event) => ({
        ...event,
        title: event.title ?? 'Milestone',
      }))
    : [];
  const documentProcessingList = documents.map((doc) => {
    const riskEntry = documentRisk.find(
      (entry) => entry.document_id === doc.documentId || entry.filename === doc.name,
    );
    const riskLabel = riskEntry?.risk ?? (doc.issuesCount > 0 ? 'medium' : 'low');
    return {
      name: doc.name,
      type: doc.type,
      status: doc.status,
      risk: riskLabel,
      issues: doc.issuesCount,
    };
  });
  const analyticsAvailable = Boolean(structuredResult?.analytics);
  // Mock banks list (in production, fetch from API)
  const banks = [
    { id: "bank-1", name: "Standard Chartered Bank" },
    { id: "bank-2", name: "HSBC Bank" },
    { id: "bank-3", name: "Citibank" },
    { id: "bank-4", name: "Deutsche Bank" },
  ];

  
  const handleDownloadCustomsPack = async () => {
    try {
      let hasManifest = Boolean(manifestData?.documents?.length);
      // First generate if not already generated
      if (!hasManifest) {
        const response = await generateCustomsPackMutation.mutateAsync();
        hasManifest = Boolean(response?.manifest?.documents?.length);
      }
      if (!hasManifest) {
        return;
      }
      // Then download
      await downloadCustomsPackMutation.mutateAsync();
    } catch (error) {
      // Error handling is done in mutations
    }
  };

  // Handle draft email request from HowToFix section
  const handleDraftEmail = (context: EmailDraftContext) => {
    setEmailDraftContext(context);
    setShowEmailDraftDialog(true);
  };
  
  const handleSubmitToBank = async () => {
    if (!enableBankSubmission) {
      toast({
        title: "Feature Disabled",
        description: "Bank submission is currently disabled.",
        variant: "destructive",
      });
      return;
    }
    if (!isReadyToSubmit) {
      toast({
        title: "Submission Blocked",
        description: "Resolve validation issues before submitting to the bank.",
        variant: "destructive",
      });
      return;
    }
    
    // Phase 3: Show bank selector first
    setShowBankSelector(true);
  };
  
  const handleBankSelected = () => {
    if (!selectedBankName) {
      toast({
        title: "Bank Required",
        description: "Please select a bank.",
        variant: "destructive",
      });
      return;
    }
    setShowBankSelector(false);
    // Phase 3: Show manifest preview
    if (manifestData) {
      setShowManifestPreview(true);
    } else {
      // Generate manifest first
      generateCustomsPackMutation.mutate();
      setShowManifestPreview(true);
    }
  };
  
  const handleConfirmManifest = () => {
    if (!manifestConfirmed) {
      toast({
        title: "Confirmation Required",
        description: "Please confirm that the manifest contents are accurate.",
        variant: "destructive",
      });
      return;
    }
    if (!isReadyToSubmit) {
      toast({
        title: "Submission Blocked",
        description: "Resolve validation issues before submitting to the bank.",
        variant: "destructive",
      });
      return;
    }
    setShowManifestPreview(false);
    // Phase 2: Create submission
    createSubmissionMutation.mutate({
      bank_id: selectedBankId || undefined,
      bank_name: selectedBankName,
      note: submissionNote || undefined,
    });
  };

  const containerClass = embedded
    ? "mx-auto w-full max-w-6xl py-4"
    : "container mx-auto px-4 py-8 max-w-6xl";

  return (
    <div className={embedded ? "bg-transparent" : "bg-background min-h-screen"}>
      {/* Header */}
      {!embedded && (
        <header className="bg-card border-b border-gray-200">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Link to="/lcopilot/exporter-dashboard">
                  <Button variant="outline" size="sm">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Dashboard
                  </Button>
                </Link>
                <div className="flex items-center gap-3">
                  <div className="bg-gradient-exporter p-2 rounded-lg">
                    <FileText className="w-6 h-6 text-primary-foreground" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-foreground">Export LC Validation Results</h1>
                    <p className="text-sm text-muted-foreground">Review the results of your latest document validation</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => fetchResults()}
                  disabled={!validationSessionId || resultsLoading}
                  className="rounded-md border px-3 py-1 text-sm hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {resultsLoading ? 'Fetching...' : 'Fetch Results'}
                </button>
              </div>
            </div>
          </div>
        </header>
      )}

      <div className={containerClass}>
        <div className="mb-8">
          {/* Only show BlockedValidationCard when validation is blocked */}
          {validationState?.isBlocked && (
            <BlockedValidationCard 
              state={validationState} 
              onRetry={() => navigate("/lcopilot/exporter-dashboard?section=upload")}
            />
          )}
          
          {/* Single clean summary card - matches reference layout */}
          <SummaryStrip 
            data={resultData ?? null} 
            lcTypeLabel={lcTypeLabel}
            lcTypeCaption={lcTypeCaption}
            lcTypeConfidence={lcTypeConfidenceValue}
            packGenerated={overviewTruth.packGenerated}
            overallStatus={overviewTruth.overallStatus}
            actualIssuesCount={surfaceFindingsCount}
            complianceScore={complianceScore}
            readinessLabel={overviewTruth.readinessLabel}
            readinessSummary={overviewTruth.readinessSummary}
          />
          {lcClassification && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge variant="outline">Workflow: {workflowLabel}</Badge>
              <Badge variant="outline">Instrument: {lcInstrumentLabel}</Badge>
              {revocability !== 'unknown' && (
                <Badge variant="outline">Terms: {normalizeLcEnumLabel(revocability)}</Badge>
              )}
            </div>
          )}
          
          {/* Bank Profile Badge */}
          {structuredResult?.bank_profile && (
            <div className="flex items-center gap-2 mt-2">
              <BankProfileBadge profile={structuredResult.bank_profile as BankProfile} />
              {structuredResult?.tolerances_applied && Object.keys(structuredResult.tolerances_applied).length > 0 && (
                <span className="text-xs text-muted-foreground">
                  • Tolerances applied: {Object.keys(structuredResult.tolerances_applied).join(", ")}
                </span>
              )}
            </div>
          )}
          
          {/* Bank Submission Verdict Card */}
          {displayBankVerdict && (
            <BankVerdictCard verdict={displayBankVerdict} />
          )}
          
          {/* OCR Confidence Warning */}
          {structuredResult?.extraction_confidence && (
            <OCRConfidenceWarning confidence={structuredResult.extraction_confidence as ExtractionConfidence} />
          )}
          
          {/* Amendment Availability */}
          {structuredResult?.amendments_available && (structuredResult.amendments_available as AmendmentsAvailable).count > 0 && (
            <AmendmentCard 
              amendments={structuredResult.amendments_available as AmendmentsAvailable}
              onDownloadMT707={(amendment) => {
                // Download SWIFT MT707 as text file
                const blob = new Blob([amendment.swift_mt707_text], { type: "text/plain" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `MT707_Amendment_${amendment.field.tag}.txt`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
              }}
              onDownloadISO20022={(amendment) => {
                // Download ISO20022 XML file
                if (!amendment.iso20022_xml) return;
                const blob = new Blob([amendment.iso20022_xml], { type: "application/xml" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `ISO20022_trad002_Amendment_${amendment.field.tag}.xml`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
              }}
            />
          )}
        </div>

        {/* Detailed Results */}
        <Tabs
          value={activeTab}
          onValueChange={(value) => {
            if (isResultsTab(value)) {
              handleActiveTabChange(value);
            }
          }}
          className="space-y-6"
        >
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="documents">Documents ({totalDocuments})</TabsTrigger>
            <TabsTrigger value="discrepancies" className="relative">
              Issues ({totalDiscrepancies})
              {totalDiscrepancies > 0 && (
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-warning rounded-full"></div>
              )}
            </TabsTrigger>
            <TabsTrigger value="customs">Customs Pack</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            {/* Contract Validation Warnings (Output-First Layer) */}
            {hasContractWarnings && (
              <Alert variant={contractWarningsByLevel.errors.length > 0 ? "destructive" : "default"} className="border-amber-500/50 bg-amber-500/5">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle className="font-semibold">
                  Extraction Notice
                  {contractWarningsByLevel.errors.length > 0 && (
                    <Badge variant="destructive" className="ml-2 text-xs">{contractWarningsByLevel.errors.length} critical</Badge>
                  )}
                  {contractWarningsByLevel.warnings.length > 0 && (
                    <Badge variant="outline" className="ml-2 text-xs border-amber-500/50 text-amber-600">{contractWarningsByLevel.warnings.length} warning{contractWarningsByLevel.warnings.length > 1 ? 's' : ''}</Badge>
                  )}
                </AlertTitle>
                <AlertDescription className="mt-2">
                  <ul className="space-y-1 text-sm">
                    {contractWarningsByLevel.errors.map((w, i) => (
                      <li key={`err-${i}`} className="flex items-start gap-2">
                        <XCircle className="w-3.5 h-3.5 mt-0.5 text-destructive shrink-0" />
                        <span>{w.message}</span>
                      </li>
                    ))}
                    {contractWarningsByLevel.warnings.map((w, i) => (
                      <li key={`warn-${i}`} className="flex items-start gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 mt-0.5 text-amber-500 shrink-0" />
                        <span>{w.message}</span>
                      </li>
                    ))}
                  </ul>
                  {contractWarningsByLevel.infos.length > 0 && (
                    <details className="mt-2 text-xs text-muted-foreground">
                      <summary className="cursor-pointer">Show {contractWarningsByLevel.infos.length} info message{contractWarningsByLevel.infos.length > 1 ? 's' : ''}</summary>
                      <ul className="mt-1 space-y-0.5 pl-2">
                        {contractWarningsByLevel.infos.map((w, i) => (
                          <li key={`info-${i}`}>• {w.message}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </AlertDescription>
              </Alert>
            )}
            <div className={cn("grid gap-6", hasTimeline ? "xl:grid-cols-[1.1fr_0.9fr]" : "md:grid-cols-1")}>
              {hasTimeline && (
                <Card className="shadow-soft border border-border/60">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg font-semibold flex items-center gap-2">
                      <Clock className="w-5 h-5" />
                      Validation Timeline
                    </CardTitle>
                    <CardDescription className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      Recent steps from this validation run
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {timelineDisplay.map((event, index) => {
                      const statusClass =
                        event.status === "error"
                          ? "bg-destructive"
                          : event.status === "warning"
                          ? "bg-warning"
                          : "bg-success";
                      return (
                        <div
                          key={`${event.title}-${index}`}
                          className="flex items-center gap-3 text-sm"
                        >
                          <div className={`w-3 h-3 rounded-full ${statusClass}`}></div>
                          <div className="flex-1">
                            <p className="font-medium">{event.title}</p>
                            {event.timestamp ? (
                              <p className="text-xs text-muted-foreground">
                                {format(new Date(event.timestamp), "HH:mm")}
                                {event.description ? ` - ${event.description}` : ''}
                              </p>
                            ) : event.description ? (
                              <p className="text-xs text-muted-foreground">{event.description}</p>
                            ) : null}
                          </div>
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              )}
              <Card className="shadow-soft border border-border/60">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-semibold">Case At A Glance</CardTitle>
                  <CardDescription className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    These metrics explain the current review state. They do not replace it.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {overviewTruth.summaryMetrics.map((metric) => {
                      const toneClass =
                        metric.tone === 'success'
                          ? 'text-success'
                          : metric.tone === 'warning'
                          ? 'text-warning'
                          : metric.tone === 'destructive'
                          ? 'text-destructive'
                          : metric.tone === 'primary'
                          ? 'text-primary'
                          : 'text-foreground';
                      return (
                        <div key={metric.label} className="rounded-lg border border-border/60 p-3">
                          <p className="text-xs text-muted-foreground uppercase tracking-wide">{metric.label}</p>
                          <p className={`text-2xl font-semibold ${toneClass}`}>{metric.value}</p>
                        </div>
                      );
                    })}
                  </div>
                  <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
                    <div className="grid grid-cols-2 gap-3">
                      {overviewTruth.supportMetrics.map((metric) => {
                        const toneClass =
                          metric.tone === 'success'
                            ? 'text-success'
                            : metric.tone === 'warning'
                            ? 'text-warning'
                            : metric.tone === 'destructive'
                            ? 'text-destructive'
                            : metric.tone === 'primary'
                            ? 'text-primary'
                            : 'text-foreground';
                        return (
                          <div key={metric.label} className="rounded-lg border border-border/60 p-3">
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">{metric.label}</p>
                            <p className={`text-2xl font-semibold ${toneClass}`}>{metric.value}</p>
                          </div>
                        );
                      })}
                    </div>
                    <div className="space-y-3">
                      {overviewTruth.progressMetrics.map((metric) => (
                        <div key={metric.label}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm">{metric.label}</span>
                            <span className="text-sm font-medium">{metric.value}%</span>
                          </div>
                          <Progress value={metric.value} className="h-2" />
                        </div>
                      ))}
                    </div>
                  </div>
                    <div className="rounded-lg border border-border/60 p-3 bg-muted/20">
                      <div className="flex items-center gap-2 mb-2">
                        <TrendingUp className="w-4 h-4 text-primary" />
                        <span className="text-sm font-medium text-primary">What Happened In This Run</span>
                      </div>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      {overviewTruth.performanceInsights.map((insight, idx) => (
                        <li key={idx}>• {insight}</li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Required-doc checklist + action engine */}
            <div className="grid gap-6 md:grid-cols-2">
              <Card className="shadow-soft border border-border/60">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-semibold">Required Document Checklist</CardTitle>
                  <CardDescription className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    Tracks LC document coverage first, then whether each matched document still needs review
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    <div className="rounded-lg border border-border/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Matched</p>
                      <p className="text-xl font-semibold text-success">{requirementChecklistSummary.matched}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Partial</p>
                      <p className="text-xl font-semibold text-warning">{requirementChecklistSummary.partial}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 p-3 col-span-2 sm:col-span-1">
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Missing</p>
                      <p className="text-xl font-semibold text-destructive">{requirementChecklistSummary.missing}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span className="inline-flex items-center gap-1 rounded-full border border-border/60 px-2.5 py-1">Ready: <span className="font-medium text-foreground">{requirementChecklistSummary.ready}</span></span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-border/60 px-2.5 py-1">Review: <span className="font-medium text-foreground">{requirementChecklistSummary.needsReview}</span></span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-border/60 px-2.5 py-1">Blocked: <span className="font-medium text-foreground">{requirementChecklistSummary.blocked}</span></span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-border/60 px-2.5 py-1">Awaiting doc: <span className="font-medium text-foreground">{requirementChecklistSummary.awaitingDocument}</span></span>
                  </div>
                  {requirementChecklist.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No explicit LC requirements were parsed into checklist items yet.</p>
                  ) : (
                    requirementChecklist.map((item) => {
                      const requirementMeta = REQUIREMENT_STATUS_META[item.requirementStatus];
                      const reviewMeta = REVIEW_STATE_META[item.reviewState];

                      return (
                        <div key={item.key} className="rounded-lg border border-border/60 p-4 space-y-3">
                          <div className="space-y-1">
                            <p className="font-medium text-sm">{item.label}</p>
                            <p className="text-xs text-muted-foreground">{item.requirementText}</p>
                          </div>
                          <div className="grid gap-3 sm:grid-cols-2">
                            <div className="rounded-md border border-border/60 p-3 bg-muted/10">
                              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">LC requirement match</p>
                              <div className="flex items-center justify-between gap-2">
                                <StatusBadge status={requirementMeta.badgeStatus}>
                                  {requirementMeta.label}
                                </StatusBadge>
                                <span className="text-xs text-muted-foreground text-right">
                                  {item.matchedDoc ? (
                                    <>Matched to <span className="font-medium text-foreground">{item.matchedDoc.name}</span></>
                                  ) : (
                                    'No matching upload yet'
                                  )}
                                </span>
                              </div>
                            </div>
                            <div className="rounded-md border border-border/60 p-3 bg-muted/10">
                              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">Current review status</p>
                              <div className="flex items-center justify-between gap-2">
                                <StatusBadge status={reviewMeta.badgeStatus}>
                                  {reviewMeta.label}
                                </StatusBadge>
                                <span className="text-xs text-muted-foreground text-right">
                                  {item.reviewState === 'ready'
                                    ? 'No current review hold'
                                    : item.reviewState === 'awaiting_document'
                                    ? 'Needs supporting upload'
                                    : item.reviewState === 'blocked'
                                    ? 'Blocks clean presentation'
                                    : 'Manual review still required'}
                                </span>
                              </div>
                            </div>
                          </div>
                          {item.reviewNotes.length > 0 && (
                            <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
                              <p className="text-[10px] uppercase tracking-wide text-amber-700 mb-2">Why this still matters</p>
                              <ul className="text-xs text-amber-700 space-y-1 list-disc list-inside">
                                {item.reviewNotes.slice(0, 2).map((issue, idx) => (
                                  <li key={`${item.key}-issue-${idx}`}>{issue}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                  {(lcRequirementConditions.length > 0 || lcUnmappedRequirements.length > 0) && (
                    <div className="space-y-3">
                      {lcRequirementConditions.length > 0 && (
                        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 space-y-2">
                          <p className="text-sm font-semibold">Document Presentation Conditions</p>
                          <ul className="text-xs text-amber-700 space-y-1 list-disc list-inside">
                            {lcRequirementConditions.map((condition, idx) => (
                              <li key={`requirement-condition-${idx}`}>{condition}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {lcUnmappedRequirements.length > 0 && (
                        <div className="rounded-lg border border-border/60 bg-muted/10 p-4 space-y-2">
                          <p className="text-sm font-semibold">Requirement Text Needing Mapping</p>
                          <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                            {lcUnmappedRequirements.map((requirement, idx) => (
                              <li key={`unmapped-requirement-${idx}`}>{requirement}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
              <Card className="shadow-soft border border-border/60">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-semibold">What To Do Next</CardTitle>
                  <CardDescription className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    The most important next steps for this case
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span className="inline-flex items-center gap-1 rounded-full border border-border/60 px-2.5 py-1">Critical: <span className="font-medium text-foreground">{actionEngine.filter((action) => action.priority === 'critical').length}</span></span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-border/60 px-2.5 py-1">Major: <span className="font-medium text-foreground">{actionEngine.filter((action) => action.priority === 'major').length}</span></span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-border/60 px-2.5 py-1">Minor: <span className="font-medium text-foreground">{actionEngine.filter((action) => action.priority === 'minor').length}</span></span>
                  </div>
                  {actionEngine.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No immediate actions generated from the current validation state.</p>
                  ) : (
                    <div className="space-y-3">
                      {checklistReviewFindings.slice(0, 3).map((finding) => (
                        <ReviewFindingCard
                          key={`overview-finding-${finding.key}`}
                          finding={finding}
                          variant="compact"
                        />
                      ))}
                      {additionalActionItems.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                            Additional discrepancy actions
                          </p>
                          {additionalActionItems.slice(0, 3).map((action, idx) => (
                            <div key={`${action.title}-${idx}`} className="rounded-lg border border-border/60 p-3 flex items-start justify-between gap-3">
                              <div>
                                <p className="font-medium text-sm">{action.title}</p>
                                <p className="text-xs text-muted-foreground mt-1">{action.detail}</p>
                              </div>
                              <Badge variant={action.priority === 'critical' ? 'destructive' : 'outline'} className={action.priority === 'major' ? 'border-amber-500/30 text-amber-700 bg-amber-500/5' : ''}>
                                {action.priority}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

          </TabsContent>
          <TabsContent value="customs" className="space-y-6">
            <Card className="shadow-soft border border-border/60">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  Customs Pack
                </CardTitle>
                <CardDescription className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Manifest, readiness, and downloads
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="p-4 rounded-lg border border-border/60 space-y-2">
                    <p className="text-xs uppercase text-muted-foreground tracking-wide">Status</p>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={packGenerated ? "success" : "warning"}>
                        {packGenerated ? "Ready" : "Pending"}
                      </StatusBadge>
                      <Badge variant="outline">{customsPack?.format ?? "zip"}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {packGenerated
                        ? "Customs pack generated and ready to download."
                        : "Generate your customs pack to create the manifest and bundle documents."}
                    </p>
                  </div>
                  <div className="p-4 rounded-lg border border-border/60 space-y-2">
                    <p className="text-xs uppercase text-muted-foreground tracking-wide">Submission Readiness</p>
                    <div className="flex items-center gap-3 flex-wrap">
                      <div className={cn(
                        "text-2xl font-semibold",
                        customsPackReadiness.status === 'ready'
                          ? 'text-success'
                          : customsPackReadiness.status === 'review_required'
                          ? 'text-warning'
                          : 'text-destructive'
                      )}>
                        {customsPackReadiness.status === 'ready'
                          ? 'Ready'
                          : customsPackReadiness.status === 'review_required'
                          ? 'Review needed'
                          : 'Blocked'}
                      </div>
                      <Badge variant="outline">
                        {customsPackReadiness.source === 'shared'
                          ? 'Same readiness across tabs'
                          : 'Derived readiness'}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{customsPackReadiness.summary}</p>
                  </div>
                  <div className="p-4 rounded-lg border border-border/60 space-y-2">
                    <p className="text-xs uppercase text-muted-foreground tracking-wide">Actions</p>
                    <div className="flex flex-col gap-2">
                      {/* Generate Pack Button - different text based on state */}
                      <Button
                        size="sm"
                        variant={manifestData ? "outline" : "default"}
                        className="w-full"
                        onClick={() => generateCustomsPackMutation.mutate()}
                        disabled={generateCustomsPackMutation.isPending || !canGenerateCustomsPack}
                      >
                        <RefreshCw className={cn("w-4 h-4 mr-2", generateCustomsPackMutation.isPending && "animate-spin")} />
                        {generateCustomsPackMutation.isPending 
                          ? "Generating..." 
                          : "Generate Customs Pack"}
                      </Button>
                      {!canGenerateCustomsPack && (
                        <p className="text-xs text-muted-foreground">
                          Resolve blocked required-document or review states before generating a customs pack.
                        </p>
                      )}
                      {/* Show Download only when manifest exists (pack was generated) */}
                      {manifestData && (
                        <Button
                          size="sm"
                          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
                          onClick={handleDownloadCustomsPack}
                          disabled={downloadCustomsPackMutation.isPending}
                        >
                          <Download className="w-4 h-4 mr-2" />
                          {downloadCustomsPackMutation.isPending ? "Downloading..." : "Download Customs Pack"}
                        </Button>
                      )}
                      {isReadyToSubmit && enableBankSubmission && (
                        <Button
                          size="sm"
                          className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                          onClick={handleSubmitToBank}
                          disabled={createSubmissionMutation.isPending || guardrailsLoading}
                        >
                          {createSubmissionMutation.isPending ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Submitting...
                            </>
                          ) : (
                            <>
                              <Send className="w-4 h-4 mr-2" />
                              Submit to Bank
                            </>
                          )}
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full"
                        onClick={() => setShowManifestPreview(true)}
                        disabled={!manifestData}
                      >
                        Preview Manifest
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-lg border border-border/60 p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Submission Readiness</p>
                      <p className="text-lg font-semibold">
                        {customsPackReadiness.status === 'ready' ? 'Ready for presentation' : customsPackReadiness.status === 'review_required' ? 'Review before presentation' : 'Not ready for presentation'}
                      </p>
                      <p className="text-sm text-muted-foreground mt-2">{customsPackReadiness.summary}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Blockers</p>
                      <p className="text-2xl font-semibold">{customsPackReadiness.blockers.length}</p>
                      <p className="text-sm text-muted-foreground mt-2">Missing requirements or blocked reviews that prevent clean submission.</p>
                    </div>
                    <div className="rounded-lg border border-border/60 p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Review Queue</p>
                      <p className="text-2xl font-semibold">{customsPackReadiness.reviews.length + actionEngine.length}</p>
                      <p className="text-sm text-muted-foreground mt-2">Open review or follow-up items that do not hard-block presentation.</p>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-5">
                    <div className="rounded-lg border border-border/60 p-3 text-center">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Beneficiary</p>
                      <p className="text-lg font-semibold">{customsPackReadiness.ownerBuckets.beneficiary}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 p-3 text-center">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Third Party</p>
                      <p className="text-lg font-semibold">{customsPackReadiness.ownerBuckets.thirdParty}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 p-3 text-center">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Mixed</p>
                      <p className="text-lg font-semibold">{customsPackReadiness.ownerBuckets.mixed}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 p-3 text-center">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Compliance</p>
                      <p className="text-lg font-semibold">{customsPackReadiness.ownerBuckets.compliance}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 p-3 text-center">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Waiver</p>
                      <p className="text-lg font-semibold">{customsPackReadiness.ownerBuckets.waiver}</p>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold">Submission Checklist</p>
                      <Badge variant="outline">{requirementChecklist.length} tracked</Badge>
                    </div>
                    <div className="rounded-lg border border-border/60 p-4 space-y-3">
                      {requirementChecklist.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No required-document checklist available yet.</p>
                      ) : (
                        requirementChecklist.map((item) => {
                          const requirementMeta = REQUIREMENT_STATUS_META[item.requirementStatus];
                          const reviewMeta = REVIEW_STATE_META[item.reviewState];

                          return (
                            <div key={`customs-${item.key}`} className="flex items-start justify-between gap-3 border-b border-border/40 pb-3 last:border-b-0 last:pb-0">
                              <div>
                                <p className="text-sm font-medium">{item.label}</p>
                                <p className="text-xs text-muted-foreground">{item.matchedDoc ? `Matched: ${item.matchedDoc.name}` : 'Not uploaded yet'}</p>
                              </div>
                              <div className="flex flex-col items-end gap-2">
                                <StatusBadge status={requirementMeta.badgeStatus}>
                                  Requirement: {requirementMeta.label}
                                </StatusBadge>
                                <StatusBadge status={reviewMeta.badgeStatus}>
                                  Review: {reviewMeta.label}
                                </StatusBadge>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                    <div className="rounded-lg border border-border/60 p-4 space-y-2">
                      <p className="text-sm font-semibold">Action Queue</p>
                      {actionEngine.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No action items currently blocking the customs pack.</p>
                      ) : (
                        <div className="space-y-3">
                          {checklistReviewFindings.slice(0, 4).map((finding) => (
                            <ReviewFindingCard
                              key={`customs-finding-${finding.key}`}
                              finding={finding}
                              variant="compact"
                            />
                          ))}
                          {additionalActionItems.length > 0 && (
                            <div className="space-y-2">
                              <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                                Additional discrepancy actions
                              </p>
                              <ul className="space-y-2 text-sm">
                                {additionalActionItems.slice(0, 3).map((action, idx) => (
                                  <li key={`customs-action-${idx}`} className="flex items-start gap-2">
                                    <AlertTriangle className={cn('w-4 h-4 mt-0.5 shrink-0', action.priority === 'critical' ? 'text-destructive' : 'text-amber-500')} />
                                    <div>
                                      <p className="font-medium">{action.title}</p>
                                      <p className="text-xs text-muted-foreground">{action.detail}</p>
                                    </div>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold">Manifest</p>
                      {manifestData && (
                        <Badge variant="outline" className="text-xs bg-emerald-500/10 text-emerald-600 border-emerald-500/30">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Generated
                        </Badge>
                      )}
                    </div>
                    {manifestData ? (
                      <div className="rounded-lg border border-border/60 p-4 space-y-3">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">LC Number</p>
                            <p className="font-medium">{manifestData.lc_number}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">Generated</p>
                            <p className="font-medium">
                              {format(new Date(manifestData.generated_at), "MMM d, yyyy HH:mm")}
                            </p>
                          </div>
                        </div>
                        <Separator />
                        <div className="space-y-2">
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">
                            Documents Included ({manifestData.documents.length})
                          </p>
                          <ul className="divide-y divide-border/60 rounded-lg border border-border/60">
                            {manifestData.documents.map((doc, idx) => (
                              <li key={`${doc.name}-${idx}`} className="flex items-center justify-between px-3 py-2 text-sm">
                                <div className="flex items-center gap-2">
                                  <FileText className="w-4 h-4 text-muted-foreground" />
                                  <span className="font-medium">{doc.name}</span>
                                </div>
                                <Badge variant="outline">{safeString(doc.type)}</Badge>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ) : (
                      <Card className="border-dashed bg-muted/20">
                        <CardContent className="py-8 text-center">
                          <Package className="w-8 h-8 mx-auto mb-3 text-muted-foreground" />
                          <p className="text-sm text-muted-foreground mb-1">No manifest generated yet</p>
                          <p className="text-xs text-muted-foreground">
                            Click "Generate Customs Pack" above to create your customs manifest.
                          </p>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* Submission History (moved from separate tab) */}
            <Card className="shadow-soft border border-border/60">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <History className="w-5 h-5" />
                  Submission History
                </CardTitle>
                <CardDescription className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Bank submission timeline
                </CardDescription>
              </CardHeader>
              <CardContent>
                {submissionsLoading ? (
                  <div className="text-center py-8">
                    <Loader2 className="w-8 h-8 mx-auto text-muted-foreground mb-4 animate-spin" />
                    <p className="text-muted-foreground">Loading submission history...</p>
                  </div>
                ) : !submissionsData || submissionsData.items.length === 0 ? (
                  <div className="text-center py-8">
                    <Building2 className="w-10 h-10 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground mb-1">No submissions yet</p>
                    <p className="text-sm text-muted-foreground">
                      Submit this LC to a bank to track its submission history
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {submissionsData.items.map((submission) => (
                      <SubmissionHistoryCard 
                        key={submission.id} 
                        submission={submission}
                        validationSessionId={validationSessionId || ''}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="documents" className="space-y-4">
            {documents.map((document) => {
              const fieldEntries = Object.entries(document.extractedFields || {});
              const hasFieldEntries = fieldEntries.length > 0;
              const parseComplete = (document as any).parseComplete;
              const parseCompleteness = (document as any).parseCompleteness;
              const requiredFieldsFound = (document as any).requiredFieldsFound;
              const requiredFieldsTotal = (document as any).requiredFieldsTotal;
              const discrepancyCount = document.issuesCount ?? 0;
              const normalizedDocumentType = String(document.typeKey || '').toLowerCase();
              const warningReasons = ((document as any).warningReasons ?? []) as string[];
              const reviewReasons = ((document as any).reviewReasons ?? []) as string[];
              const requirementStatus = document.requirementStatus ?? 'matched';
              const reviewState = document.reviewState ?? 'ready';
              const isLcRequiredDocument = lcRequiredDocumentTypeSet.has(normalizedDocumentType);
              const isOptionalSupportingDocument =
                normalizedDocumentType !== 'letter_of_credit' && !isLcRequiredDocument;
              const effectiveWarningReasons =
                isOptionalSupportingDocument && discrepancyCount === 0 ? [] : warningReasons;
              const effectiveReviewReasons =
                isOptionalSupportingDocument && discrepancyCount === 0 ? [] : reviewReasons;
              const effectiveReviewState: typeof reviewState =
                isOptionalSupportingDocument && discrepancyCount === 0 ? 'ready' : reviewState;
              const extractionLabel =
                document.status === 'success'
                  ? 'Structured read complete'
                  : document.status === 'error'
                  ? 'Extraction blocked'
                  : 'Extraction needs review';
              const requirementMeta =
                isOptionalSupportingDocument
                  ? { label: 'Extra upload', status: 'pending' as const, note: 'Uploaded as supporting evidence, but this LC does not require this document type.' }
                  : requirementStatus === 'matched'
                  ? { label: 'Covers LC requirement', status: 'success' as const, note: 'This upload covers the required LC document type.' }
                  : requirementStatus === 'missing'
                  ? { label: 'Does not cover LC requirement', status: 'error' as const, note: 'This upload does not currently satisfy the required LC document coverage.' }
                  : { label: 'Partially covers requirement', status: 'warning' as const, note: 'This upload only partially satisfies the required LC document coverage.' };
              const reviewMeta =
                isOptionalSupportingDocument && discrepancyCount === 0
                  ? { label: 'Informational only', status: 'pending' as const, note: 'This extra supporting document does not block clean presentation.' }
                  : effectiveReviewState === 'ready'
                  ? { label: 'No review hold', status: 'success' as const, note: 'No active review hold is attached to this document.' }
                  : effectiveReviewState === 'blocked'
                  ? { label: 'Review blocked', status: 'error' as const, note: 'This document currently blocks clean presentation.' }
                  : effectiveReviewState === 'needs_review'
                  ? { label: 'Needs manual review', status: 'warning' as const, note: 'This document needs manual review before clean presentation.' }
                  : { label: 'Waiting for matching upload', status: 'warning' as const, note: 'A matching supporting document is still required before clean presentation.' };
              
              return (
                <Card
                  key={document.id}
                  className="shadow-soft border border-border/60 transition duration-200 hover:-translate-y-0.5 hover:border-primary/40"
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-muted/50">
                          <FileText className="w-5 h-5 text-muted-foreground" />
                        </div>
                        <div>
                          <CardTitle className="text-lg font-semibold">{document.name}</CardTitle>
                          <CardDescription className="text-sm text-muted-foreground">
                            {safeString(document.type)}
                          </CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusBadge status={document.status}>
                          {extractionLabel}
                        </StatusBadge>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => {
                            setSelectedDocumentForDrawer({
                              id: document.id,
                              name: document.name,
                              filename: document.filename,
                              type: document.type,
                              typeKey: document.typeKey,
                              status: document.status,
                              extractionStatus: document.extractionStatus,
                              issuesCount: document.issuesCount,
                              extractedFields:
                                String(document.typeKey || "").toLowerCase() === "letter_of_credit" &&
                                Object.keys(canonicalLcDrawerFields).length > 0
                                  ? canonicalLcDrawerFields
                                  : document.extractedFields,
                              warningReasons: (document as any).warningReasons ?? [],
                              reviewReasons: (document as any).reviewReasons ?? [],
                              criticalFieldStates: (document as any).criticalFieldStates ?? {},
                              fieldDiagnostics: (document as any).fieldDiagnostics ?? {},
                              missingRequiredFields: (document as any).missingRequiredFields ?? [],
                              rawText: (document as any).rawText ?? '',
                              ocrConfidence: (document.extractedFields as any)?._extraction_confidence,
                              sourceFormat: (document.extractedFields as any)?._source_format,
                              isElectronicBL: (document.extractedFields as any)?._is_electronic_bl,
                            });
                            setIsDrawerOpen(true);
                          }}
                        >
                          <Eye className="w-4 h-4 mr-2" />
                          View Details
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="mb-4 grid gap-3 md:grid-cols-3">
                      <div className="rounded-md border border-border/60 p-3 bg-muted/10">
                        <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">What we read from this file</p>
                        <div className="flex items-center justify-between gap-2">
                          <StatusBadge status={document.status}>{extractionLabel}</StatusBadge>
                          <span className="text-xs text-muted-foreground text-right">
                            {typeof parseComplete === "boolean"
                              ? `Structured read ${parseComplete ? 'complete' : 'partial'}`
                              : (document.extractionStatus ?? 'unknown').replace(/_/g, ' ')}
                          </span>
                        </div>
                        {(typeof requiredFieldsFound === 'number' && typeof requiredFieldsTotal === 'number') || typeof parseCompleteness === 'number' ? (
                          <p className="mt-2 text-xs text-muted-foreground">
                            {typeof requiredFieldsFound === 'number' && typeof requiredFieldsTotal === 'number'
                              ? `${requiredFieldsFound}/${requiredFieldsTotal} extraction-required fields found`
                              : `Parse completeness ${Math.round((parseCompleteness ?? 0) * 100)}%`}
                          </p>
                        ) : null}
                      </div>
                      <div className="rounded-md border border-border/60 p-3 bg-muted/10">
                        <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">LC requirement match</p>
                        <div className="flex items-center justify-between gap-2">
                          <StatusBadge status={requirementMeta.status}>{requirementMeta.label}</StatusBadge>
                          <span className="text-xs text-muted-foreground text-right">
                            {discrepancyCount > 0 ? `${discrepancyCount} linked issue${discrepancyCount > 1 ? 's' : ''}` : 'No linked issues'}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground">{requirementMeta.note}</p>
                      </div>
                      <div className="rounded-md border border-border/60 p-3 bg-muted/10">
                        <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">Current review status</p>
                        <div className="flex items-center justify-between gap-2">
                          <StatusBadge status={reviewMeta.status}>{reviewMeta.label}</StatusBadge>
                          <span className="text-xs text-muted-foreground text-right">
                            {effectiveReviewReasons.length > 0 ? `${effectiveReviewReasons.length} review note${effectiveReviewReasons.length > 1 ? 's' : ''}` : 'No review notes'}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground">{reviewMeta.note}</p>
                      </div>
                    </div>
                    {effectiveWarningReasons.length > 0 && (
                      <div className="mb-3 space-y-2">
                        <div className="flex flex-wrap gap-2">
                          {effectiveWarningReasons.map((reason, idx) => (
                            <Badge key={`${document.id}-reason-${idx}`} variant="outline" className="text-xs border-amber-500/30 text-amber-700 bg-amber-500/5">
                              {reason}
                            </Badge>
                          ))}
                        </div>
                        <p className="text-xs text-amber-700">
                          {effectiveWarningReasons[0]}
                        </p>
                      </div>
                    )}
                    {hasFieldEntries ? (
                      document.typeKey === "letter_of_credit" && lcData ? (
                        <div className="space-y-4">
                          <div className="flex items-center justify-between gap-3 flex-wrap">
                            <p className="text-sm font-semibold">Letter of Credit Snapshot</p>
                            <Button variant="ghost" size="sm" onClick={() => setShowRawLcJson((prev) => !prev)}>
                              {showRawLcJson ? "Hide raw JSON" : "View raw JSON"}
                            </Button>
                          </div>
                          <div className="rounded-md border bg-card/50 p-4 space-y-4">
                            {lcSummaryRows.length > 0 && (
                              <div className="grid gap-4 md:grid-cols-2">{lcSummaryRows}</div>
                            )}
                            {lcDateRows.length > 0 && (
                              <div>
                                <p className="text-sm font-semibold mb-2">Key Dates</p>
                                <div className="grid gap-4 md:grid-cols-2">{lcDateRows}</div>
                              </div>
                            )}
                            <div className="grid gap-4 md:grid-cols-2">
                              {lcApplicantCard}
                              {lcBeneficiaryCard}
                            </div>
                            {lcPortsCard}
                            {lcGoodsItemsList}
                            {(lcAdditionalConditionSummary.items.length > 0 ||
                              lcAdditionalConditionSummary.placeholderOnly) && (
                              <div>
                                <p className="text-sm font-semibold mb-2">Additional Conditions (47A)</p>
                                {lcAdditionalConditionSummary.items.length > 0 ? (
                                  <ul className="text-sm space-y-1.5 list-disc list-inside">
                                    {lcAdditionalConditionSummary.items.map((condition, idx) => (
                                      <li key={idx} className="text-muted-foreground">{condition}</li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="text-sm text-muted-foreground">
                                    {SPECIAL_CONDITIONS_PLACEHOLDER_TEXT}
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                          {showRawLcJson && (
                            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-md">
                              <Table>
                                <TableBody>
                                  {Object.entries(lcData || {}).map(([key, val]) => (
                                    <TableRow key={key}>
                                      <TableCell className="font-medium capitalize w-1/3">
                                        {key.replace(/([A-Z])/g, " $1").trim()}
                                      </TableCell>
                                      <TableCell className="text-sm">
                                        {typeof val === "object" && val !== null
                                          ? JSON.stringify(val, null, 2)
                                          : String(val || "")}
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                          {fieldEntries.map(([key, value]) => {
                            const displayValue = formatExtractedValue(value);
                            return (
                              <div key={key} className="space-y-1">
                                <p className="text-xs text-muted-foreground font-medium capitalize">
                                  {key.replace(/([A-Z])/g, " $1").trim()}
                                </p>
                                <p className="text-sm font-medium text-foreground whitespace-pre-wrap break-words">
                                  {displayValue}
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      )
                    ) : (
                      <div className="rounded-md border border-dashed border-muted-foreground/30 p-4 text-sm text-muted-foreground">
                        {['partial', 'text_only', 'pending', 'unknown', 'error', 'failed', 'empty'].includes((document.extractionStatus ?? '').toLowerCase())
                          ? 'This document could not be fully parsed. Preview text is available for manual review.'
                          : 'No structured fields were extracted for this document.'}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </TabsContent>

          <TabsContent value="discrepancies" className="space-y-4">
            <IssuesTab
              hasIssueCards={hasIssueCards}
              issueCards={issueCards}
              filteredIssueCards={filteredIssueCards}
              reviewFindings={checklistReviewFindings}
              severityCounts={severityCounts}
              laneCounts={laneCounts}
              issueFilter={issueFilter}
              setIssueFilter={setIssueFilter}
              documentStatusMap={documentStatusMap}
              renderAIInsightsCard={renderAIInsightsCard}
              renderReferenceIssuesCard={renderReferenceIssuesCard}
              lcNumber={lcNumber}
              onDraftEmail={handleDraftEmail}
            />
          </TabsContent>
        </Tabs>
        
        {/* Document Details Drawer */}
        <DocumentDetailsDrawer
          document={selectedDocumentForDrawer}
          open={isDrawerOpen}
          onOpenChange={setIsDrawerOpen}
        />

        {/* Bank Selector Dialog (Phase 3) */}
        <Dialog open={showBankSelector} onOpenChange={setShowBankSelector}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Building2 className="w-5 h-5" />
                Select Bank
              </DialogTitle>
              <DialogDescription>
                Choose the bank to submit LC {lcNumber} to
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="bank-select">Bank</Label>
                <Select value={selectedBankId} onValueChange={(value) => {
                  const bank = banks.find(b => b.id === value);
                  setSelectedBankId(value);
                  setSelectedBankName(bank?.name || "");
                }}>
                  <SelectTrigger id="bank-select">
                    <SelectValue placeholder="Select a bank" />
                  </SelectTrigger>
                  <SelectContent>
                    {banks.map((bank) => (
                      <SelectItem key={bank.id} value={bank.id}>
                        {bank.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="submission-note">Note (Optional)</Label>
                <Textarea
                  id="submission-note"
                  placeholder="Add any notes for the bank..."
                  value={submissionNote}
                  onChange={(e) => setSubmissionNote(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowBankSelector(false)}>
                Cancel
              </Button>
              <Button onClick={handleBankSelected} disabled={!selectedBankName}>
                Continue
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Manifest Preview Dialog (Phase 3) */}
        <Dialog open={showManifestPreview} onOpenChange={setShowManifestPreview}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileCheck className="w-5 h-5" />
                Review Manifest
              </DialogTitle>
              <DialogDescription>
                Review the contents of your customs pack before submission
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {manifestData ? (
                <>
                  <div className="p-4 bg-muted rounded-lg space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">LC Number:</span>
                      <span className="font-medium">{manifestData.lc_number}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Generated:</span>
                      <span className="font-medium">{format(new Date(manifestData.generated_at), "MMM d, yyyy 'at' HH:mm")}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Documents:</span>
                      <span className="font-medium">{manifestData.documents.length}</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Documents Included:</Label>
                    <div className="border rounded-lg p-4 space-y-2 max-h-64 overflow-y-auto">
                      {manifestData.documents.map((doc, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm py-2 border-b last:border-0">
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-muted-foreground" />
                            <span className="font-medium">{doc.name}</span>
                          </div>
                          <Badge variant="outline">{safeString(doc.type)}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 p-4 border rounded-lg">
                    <Checkbox
                      id="manifest-confirm"
                      checked={manifestConfirmed}
                      onCheckedChange={(checked) => setManifestConfirmed(checked === true)}
                    />
                    <Label htmlFor="manifest-confirm" className="cursor-pointer">
                      I confirm that the manifest contents are accurate and ready for submission
                    </Label>
                  </div>
                </>
              ) : (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 mx-auto text-muted-foreground mb-4 animate-spin" />
                  <p className="text-muted-foreground">Generating manifest...</p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowManifestPreview(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleConfirmManifest} 
                disabled={!manifestConfirmed || !manifestData || createSubmissionMutation.isPending}
                className="bg-green-600 hover:bg-green-700"
              >
                {createSubmissionMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    Submit to Bank
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* Email Draft Dialog for How to Fix section */}
        <EmailDraftDialog
          open={showEmailDraftDialog}
          onOpenChange={setShowEmailDraftDialog}
          context={emailDraftContext}
          lcNumber={lcNumber}
        />
      </div>
    </div>
  );
}

// SubmissionHistoryCard is now imported from ./exporter/results

import { useState, useCallback, useEffect, useMemo, type ChangeEvent } from "react";
import { useDropzone } from "react-dropzone";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useValidate, type ValidationError } from "@/hooks/use-lcopilot";
import { ExtractionReview } from "@/pages/exporter/ExtractionReview";
import { useValidationProgress, type UseValidationProgressState } from "@/hooks/useValidationProgress";
import { cn } from "@/lib/utils";
import { useDrafts, type FileMeta, type FileData } from "@/hooks/use-drafts";
import { useVersions } from "@/hooks/use-versions";
import { useLcopilotQuota } from "@/hooks/use-lcopilot-quota";
import { RateLimitNotice } from "@/components/RateLimitNotice";
import { BlockedUploadModal } from "@/components/validation";
import { QuotaLimitModal } from "@/components/billing/QuotaLimitModal";
import { LcopilotQuotaBanner } from "@/components/billing/LcopilotQuotaBanner";
import { PreparationGuide } from "@/components/exporter/PreparationGuide";
import { smeTemplatesApi } from "@/api/sme-templates";
import { buildTemplateUploadPrefill } from "@/lib/exporter/templatePrefill";
import {
  SPECIAL_CONDITIONS_PLACEHOLDER_TEXT,
  summarizeSpecialConditions,
} from "@/lib/exporter/specialConditions";
import { getUploadRequirementsModel } from "@/lib/exporter/uploadRequirements";
import {
  formatWorkflowConfidenceBadgeLabel,
  getWorkflowDetectionStatusBadge,
  getWorkflowPrimaryLabel,
  type WorkflowDetectionSummary,
} from "@/lib/exporter/workflowDetection";
import type { LcClassificationRequiredDocument } from "@/types/lcopilot";
// Shared document types - SINGLE SOURCE OF TRUTH
import { 
  DOCUMENT_TYPES, 
  DOCUMENT_TYPE_VALUES,
  DOCUMENT_CATEGORIES,
  normalizeDocumentType,
  getDocumentTypeIcon,
  type DocumentTypeValue,
} from "@shared/types";
import { 
  FileText, 
  Upload, 
  X, 
  FileCheck, 
  AlertTriangle,
  ArrowLeft,
  Eye,
  Trash2,
  Plus,
  CheckCircle,
  Lock,
  Sparkles
} from "lucide-react";

interface UploadedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  status: "pending" | "uploading" | "completed" | "error";
  progress: number;
  preview?: string;
  documentType?: string; // Selected document type
  manualDocumentType?: boolean;
  // Auto-detection fields
  detectedType?: string;
  detectedConfidence?: number;
  isTradeDocument?: boolean;
  relevanceWarning?: string;
}

interface LCIntakeState {
  status: "idle" | "uploading" | "resolved" | "invalid" | "ambiguous";
  file: File | null;
  message?: string;
  continuationAllowed?: boolean;
  isLc?: boolean;
  jobId?: string;
  lcSummary?: Record<string, any>;
  lcDetection?: {
    lc_type?: string;
    confidence?: number;
    reason?: string;
    is_draft?: boolean;
    source?: string;
    confidence_mode?: string;
    detection_basis?: string;
  };
  requiredDocumentTypes?: string[];
  documentsRequired?: string[];
  requiredDocumentsDetailed?: LcClassificationRequiredDocument[];
  requirementConditions?: string[];
  unmappedRequirements?: string[];
  specialConditions?: string[];
  detectedDocuments?: Array<{ type: string; filename?: string; document_type_resolution?: string }>;
  error?: {
    error_code?: string;
    title?: string;
    message?: string;
    detail?: string;
    action?: string;
    redirect_url?: string;
    help_text?: string;
  };
}

type RestoredFileData = FileData & {
  tag?: string;
  manualDocumentType?: boolean;
  detectedType?: string;
  detectedConfidence?: number;
  isTradeDocument?: boolean;
  relevanceWarning?: string;
};

// Generate document type options from SHARED TYPES - SINGLE SOURCE OF TRUTH
// This ensures frontend and backend always use the same values
const exportDocumentTypes = Object.values(DOCUMENT_TYPES)
  .filter(info => info.value !== DOCUMENT_TYPE_VALUES.UNKNOWN)
  .map(info => ({
    value: info.value,
    label: info.label,
    shortLabel: info.shortLabel,
    category: info.category,
    icon: getDocumentTypeIcon(info.value),
  }));

const QUICK_BADGE_DEFAULT_DOC_TYPES: DocumentTypeValue[] = [
  DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT,
  DOCUMENT_TYPE_VALUES.SWIFT_MESSAGE,
  DOCUMENT_TYPE_VALUES.LC_APPLICATION,
  DOCUMENT_TYPE_VALUES.COMMERCIAL_INVOICE,
  DOCUMENT_TYPE_VALUES.PROFORMA_INVOICE,
  DOCUMENT_TYPE_VALUES.BILL_OF_LADING,
  DOCUMENT_TYPE_VALUES.AIR_WAYBILL,
  DOCUMENT_TYPE_VALUES.PACKING_LIST,
  DOCUMENT_TYPE_VALUES.CERTIFICATE_OF_ORIGIN,
  DOCUMENT_TYPE_VALUES.INSURANCE_CERTIFICATE,
  DOCUMENT_TYPE_VALUES.INSPECTION_CERTIFICATE,
  DOCUMENT_TYPE_VALUES.WEIGHT_CERTIFICATE,
  DOCUMENT_TYPE_VALUES.BENEFICIARY_CERTIFICATE,
  DOCUMENT_TYPE_VALUES.SHIPMENT_ADVICE,
  DOCUMENT_TYPE_VALUES.DELIVERY_NOTE,
];

const MAX_QUICK_BADGE_COUNT = 18;

type UploadDocumentTypeOption = (typeof exportDocumentTypes)[number];

type FilenameDetectionResult = {
  type: DocumentTypeValue;
  confidence: number;
  isTradeDoc: boolean;
  warning?: string;
};

export function detectDocumentTypeFromFilename(filename: string): FilenameDetectionResult {
  const name = filename.toLowerCase();

  const patterns: Array<{ pattern: RegExp; type: DocumentTypeValue; confidence: number }> = [
    { pattern: /(^|[_\s])(lc|letter[_\s]?of[_\s]?credit|mt700|mt760|swift|documentary[_\s]?credit)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT, confidence: 0.9 },
    { pattern: /(^|[_\s])(invoice|inv|commercial[_\s]?invoice)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.COMMERCIAL_INVOICE, confidence: 0.85 },
    { pattern: /(^|[_\s])(proforma)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.PROFORMA_INVOICE, confidence: 0.85 },
    { pattern: /(^|[_\s])(b[\/.]?l|bill[_\s]?of[_\s]?lading|bol|lading)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.BILL_OF_LADING, confidence: 0.85 },
    { pattern: /(^|[_\s])(ocean[_\s]?bill|ocean[_\s]?bl)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.OCEAN_BILL_OF_LADING, confidence: 0.85 },
    { pattern: /(^|[_\s])(sea[_\s]?waybill|swb)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.SEA_WAYBILL, confidence: 0.85 },
    { pattern: /(^|[_\s])(packing[_\s]?list|pack[_\s]?list|plist)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.PACKING_LIST, confidence: 0.85 },
    { pattern: /(^|[_\s])(coo|certificate[_\s]?of[_\s]?origin|origin[_\s]?cert)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.CERTIFICATE_OF_ORIGIN, confidence: 0.85 },
    { pattern: /(^|[_\s])(form[_\s]?a|gsp)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.GSP_FORM_A, confidence: 0.85 },
    { pattern: /(^|[_\s])(insurance[_\s]?cert|insurance|ins[_\s]?cert|marine[_\s]?insurance|cargo[_\s]?insurance)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.INSURANCE_CERTIFICATE, confidence: 0.85 },
    { pattern: /(^|[_\s])(insurance[_\s]?policy|policy)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.INSURANCE_POLICY, confidence: 0.85 },
    { pattern: /(^|[_\s])(inspection|insp[_\s]?cert|survey)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.INSPECTION_CERTIFICATE, confidence: 0.8 },
    { pattern: /(^|[_\s])(sgs)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.SGS_CERTIFICATE, confidence: 0.85 },
    { pattern: /(^|[_\s])(bureau[_\s]?veritas|bv)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.BUREAU_VERITAS_CERTIFICATE, confidence: 0.85 },
    { pattern: /(^|[_\s])(intertek)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.INTERTEK_CERTIFICATE, confidence: 0.85 },
    { pattern: /(^|[_\s])(psi|pre[_\s]?shipment)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.PRE_SHIPMENT_INSPECTION, confidence: 0.8 },
    { pattern: /(^|[_\s])(weight[_\s]?(?:cert|certificate|list)|weighment)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.WEIGHT_CERTIFICATE, confidence: 0.75 },
    { pattern: /(^|[_\s])(measurement|dimension)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.MEASUREMENT_CERTIFICATE, confidence: 0.75 },
    { pattern: /(^|[_\s])(quality[_\s]?cert|quality)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.QUALITY_CERTIFICATE, confidence: 0.75 },
    { pattern: /(^|[_\s])(analysis|chemical[_\s]?analysis)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.ANALYSIS_CERTIFICATE, confidence: 0.75 },
    { pattern: /(^|[_\s])(lab[_\s]?test|lab[_\s]?report|test[_\s]?report)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.LAB_TEST_REPORT, confidence: 0.75 },
    { pattern: /(^|[_\s])(fumigat|pest[_\s]?control)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.FUMIGATION_CERTIFICATE, confidence: 0.8 },
    { pattern: /(^|[_\s])(phyto|phytosanitary|plant[_\s]?health)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.PHYTOSANITARY_CERTIFICATE, confidence: 0.8 },
    { pattern: /(^|[_\s])(health[_\s]?cert|health)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.HEALTH_CERTIFICATE, confidence: 0.75 },
    { pattern: /(^|[_\s])(sanitary|sanit)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.SANITARY_CERTIFICATE, confidence: 0.75 },
    { pattern: /(^|[_\s])(vet|veterinary)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.VETERINARY_CERTIFICATE, confidence: 0.75 },
    { pattern: /(^|[_\s])(halal)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.HALAL_CERTIFICATE, confidence: 0.8 },
    { pattern: /(^|[_\s])(kosher)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.KOSHER_CERTIFICATE, confidence: 0.8 },
    { pattern: /(^|[_\s])(organic)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.ORGANIC_CERTIFICATE, confidence: 0.8 },
    { pattern: /(^|[_\s])(draft|bill[_\s]?of[_\s]?exchange|boe)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.DRAFT_BILL_OF_EXCHANGE, confidence: 0.8 },
    { pattern: /(^|[_\s])(beneficiary(?:[_\s]?(?:certificate|cert|statement))|benef(?:[_\s]?cert)?)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.BENEFICIARY_CERTIFICATE, confidence: 0.85 },
    { pattern: /(^|[_\s])(awb|air[_\s]?waybill|airway)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.AIR_WAYBILL, confidence: 0.85 },
    { pattern: /(^|[_\s])(fcr|forwarder|freight[_\s]?receipt)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.FORWARDER_CERTIFICATE_OF_RECEIPT, confidence: 0.75 },
    { pattern: /(^|[_\s])(shipping[_\s]?cert|carrier[_\s]?cert)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.SHIPPING_COMPANY_CERTIFICATE, confidence: 0.75 },
    { pattern: /(^|[_\s])(cmr|road[_\s]?transport)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.ROAD_TRANSPORT_DOCUMENT, confidence: 0.8 },
    { pattern: /(^|[_\s])(rail|railway)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.RAILWAY_CONSIGNMENT_NOTE, confidence: 0.8 },
    { pattern: /(^|[_\s])(customs|declaration)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.CUSTOMS_DECLARATION, confidence: 0.75 },
    { pattern: /(^|[_\s])(export[_\s]?license)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.EXPORT_LICENSE, confidence: 0.8 },
    { pattern: /(^|[_\s])(import[_\s]?license)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.IMPORT_LICENSE, confidence: 0.8 },
    { pattern: /(^|[_\s])(eur[_\s]?1|eur\.1)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.EUR1_MOVEMENT_CERTIFICATE, confidence: 0.85 },
    { pattern: /(^|[_\s])(warehouse[_\s]?receipt)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.WAREHOUSE_RECEIPT, confidence: 0.8 },
    { pattern: /(^|[_\s])(manifest|cargo[_\s]?manifest)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.CARGO_MANIFEST, confidence: 0.75 },
  ];

  const nonTradePatterns = [
    /\b(brochure|catalog|presentation|company.?profile|resume|cv)\b/i,
    /\b(contract|agreement|mou|nda)\b/i,
    /\b(photo|image|picture|selfie)\b/i,
    /\b(screenshot|screen.?shot)\b/i,
  ];

  for (const pattern of nonTradePatterns) {
    if (pattern.test(name)) {
      return {
        type: DOCUMENT_TYPE_VALUES.OTHER,
        confidence: 0.3,
        isTradeDoc: false,
        warning: "This file doesn't appear to be a trade document. Please verify.",
      };
    }
  }

  for (const { pattern, type, confidence } of patterns) {
    if (pattern.test(name)) {
      return { type, confidence, isTradeDoc: true };
    }
  }

  return { type: DOCUMENT_TYPE_VALUES.OTHER, confidence: 0.5, isTradeDoc: true };
}

export function formatWorkflowBadgeLabel(workflowType?: string): string {
  const normalized = String(workflowType || "").trim().toLowerCase();
  const humanized = normalized ? normalized.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase()) : 'Unknown';
  return `${humanized} Workflow`;
}

export { formatWorkflowConfidenceBadgeLabel };

export function buildValidationProgressCopy(fileCount: number): {
  heading: string;
  subheading: string;
  detail: string;
  statusLabel: string;
  estimateLabel: string;
} {
  const docCountLabel =
    fileCount > 0
      ? `${fileCount} supporting document${fileCount === 1 ? "" : "s"}`
      : "your supporting documents";
  const detail =
    "We're extracting document text, checking LC terms, and preparing your review for " +
    docCountLabel +
    ". Multi-document packs often take 1-2 minutes.";
  return {
    heading: "Processing documents...",
    subheading: "Estimated progress",
    detail,
    statusLabel: `Processing ${docCountLabel}`,
    estimateLabel: "Estimated client-side progress, not live backend telemetry.",
  };
}

function buildLcResolveProgressCopy(): {
  heading: string;
  subheading: string;
  detail: string;
  statusLabel: string;
  estimateLabel: string;
} {
  return {
    heading: "Resolving Letter of Credit...",
    subheading: "Estimated progress",
    detail:
      "We're reading the LC, identifying workflow, and preparing the required supporting-document checklist.",
    statusLabel: "Resolving your LC",
    estimateLabel: "Estimated client-side progress, not live backend telemetry.",
  };
}

export function getQuickBadgeDocumentTypes(
  allTypes: UploadDocumentTypeOption[],
  requiredDocumentTypes: string[],
): UploadDocumentTypeOption[] {
  const byValue = new Map(allTypes.map((item) => [item.value, item]));
  const selected: UploadDocumentTypeOption[] = [];
  const seen = new Set<string>();

  const push = (value: string | undefined): void => {
    if (!value) return;
    const normalized = normalizeDocumentType(value);
    if (normalized === DOCUMENT_TYPE_VALUES.UNKNOWN || seen.has(normalized)) return;
    const info = byValue.get(normalized);
    if (!info) return;
    seen.add(normalized);
    selected.push(info);
  };

  requiredDocumentTypes.forEach((value) => push(value));
  QUICK_BADGE_DEFAULT_DOC_TYPES.forEach((value) => push(value));

  if (selected.length === 0) {
    allTypes.forEach((item) => push(item.value));
  }

  return selected.slice(0, MAX_QUICK_BADGE_COUNT);
}

type ProgressMode = "lc" | "validation";

type ProcessingPhase = {
  id: string;
  label: string;
  duration: number;
  icon: typeof Upload;
};

const buildProgressPhases = (fileCount: number, mode: ProgressMode): ProcessingPhase[] => {
  if (mode === "lc") {
    return [
      { id: "upload", label: "Uploading LC file", duration: 3, icon: Upload },
      { id: "text", label: "Reading LC text", duration: 12, icon: FileText },
      { id: "classify", label: "Detecting workflow and instrument", duration: 8, icon: Sparkles },
      { id: "requirements", label: "Preparing required-document checklist", duration: 7, icon: FileCheck },
    ];
  }

  const normalizedCount = Math.max(1, fileCount);
  return [
    { id: "queue", label: "Preparing supporting documents", duration: 4, icon: Upload },
    { id: "text", label: "Extracting document text", duration: Math.max(20, normalizedCount * 6), icon: FileText },
    { id: "review", label: "Checking LC terms and document coverage", duration: Math.max(14, normalizedCount * 3.5), icon: FileCheck },
    { id: "finalize", label: "Preparing results workspace", duration: 10, icon: Sparkles },
  ];
};

const formatEstimatedDuration = (seconds: number): string => {
  const safeSeconds = Math.max(0, Math.ceil(seconds));
  if (safeSeconds < 60) {
    return `~${safeSeconds}s remaining`;
  }
  const minutes = Math.floor(safeSeconds / 60);
  const remainder = safeSeconds % 60;
  return remainder === 0 ? `~${minutes}m remaining` : `~${minutes}m ${remainder}s remaining`;
};

function ValidationProgressIndicator({
  fileCount,
  mode = "validation",
  realProgress,
}: {
  fileCount: number;
  mode?: ProgressMode;
  /** When provided and connected, real backend progress overrides the fake timer */
  realProgress?: UseValidationProgressState | null;
}) {
  const copy =
    mode === "lc" ? buildLcResolveProgressCopy() : buildValidationProgressCopy(fileCount);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [startTime] = useState(() => Date.now());

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    }, 500);
    return () => clearInterval(interval);
  }, [startTime]);

  const phases = useMemo(() => buildProgressPhases(fileCount, mode), [fileCount, mode]);
  const totalEstimated = useMemo(
    () => phases.reduce((sum, phase) => sum + phase.duration, 0),
    [phases],
  );

  let accumulatedTime = 0;
  let currentPhaseIndex = phases.length - 1;
  for (let i = 0; i < phases.length; i += 1) {
    const phase = phases[i];
    if (elapsedSeconds < accumulatedTime + phase.duration) {
      currentPhaseIndex = i;
      break;
    }
    accumulatedTime += phase.duration;
  }

  const currentPhase = phases[currentPhaseIndex];
  const CurrentIcon = currentPhase.icon;
  const fakeProgress = Math.min(95, (elapsedSeconds / totalEstimated) * 100);
  const remainingSeconds = Math.max(0, totalEstimated - elapsedSeconds);

  // Prefer real backend progress when the SSE stream is connected and has
  // delivered at least one stage event. Falls back to fake timer otherwise.
  const useReal = Boolean(
    realProgress?.isConnected && realProgress.progress != null && realProgress.progress > 0,
  );
  const overallProgress = useReal ? Math.max(5, realProgress!.progress!) : fakeProgress;
  const stageMessage = useReal && realProgress?.message ? realProgress.message : currentPhase.label;
  const badgeLabel = useReal ? "Live progress" : "Estimated progress";

  return (
    <div className="bg-exporter/5 border border-exporter/20 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="animate-spin w-5 h-5 border-2 border-exporter border-t-transparent rounded-full"></div>
            <CurrentIcon className="absolute inset-0 m-auto h-3 w-3 text-exporter/60" />
          </div>
          <div className="flex-1">
            <span className="font-medium text-exporter">{copy.heading}</span>
            <p className="text-xs text-muted-foreground">{copy.subheading}</p>
          </div>
        </div>
        <Badge variant="outline">{badgeLabel}</Badge>
      </div>
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
          <span>{stageMessage}</span>
          {!useReal && <span>{formatEstimatedDuration(remainingSeconds)}</span>}
        </div>
        <Progress value={overallProgress} className="h-2" />
        <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
          <span>{copy.statusLabel}</span>
          <span>{Math.max(5, Math.round(overallProgress))}%</span>
        </div>
      </div>
      <div className="flex gap-1">
        {phases.map((phase, idx) => {
          const isComplete = idx < currentPhaseIndex;
          const isCurrent = idx === currentPhaseIndex;
          return (
            <div
              key={phase.id}
              className={cn(
                "flex-1 h-1 rounded-full transition-colors",
                isComplete
                  ? "bg-exporter"
                  : isCurrent
                  ? "bg-exporter/50"
                  : "bg-border/70",
              )}
              title={phase.label}
            />
          );
        })}
      </div>
      <p className="text-sm text-muted-foreground">{copy.detail}</p>
      <p className="text-xs text-muted-foreground">{copy.estimateLabel}</p>
    </div>
  );
}

type ExportLCUploadProps = {
  embedded?: boolean;
  draftId?: string;
  templateId?: string;
  /**
   * Called after the user clicks "Start Validation" on the inline
   * extraction review and the resume-validate call completes. The parent
   * dashboard routes into the reviews section from here.
   */
  onComplete?: (payload: { jobId: string; lcNumber: string }) => void;
};

export default function ExportLCUpload({
  embedded = false,
  draftId,
  templateId,
  onComplete,
}: ExportLCUploadProps = {}) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [lcIntake, setLcIntake] = useState<LCIntakeState>({ status: "idle", file: null });
  const [lcNumber, setLcNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [showRateLimit, setShowRateLimit] = useState(false);
  const [quotaError, setQuotaError] = useState<ValidationError | null>(null);
  const [showQuotaModal, setShowQuotaModal] = useState(false);
  const [currentDraftId, setCurrentDraftId] = useState<string | null>(null);
  const [isLoadingDraft, setIsLoadingDraft] = useState(false);
  const [issueDate, setIssueDate] = useState("");
  const [stagedFilesMeta, setStagedFilesMeta] = useState<FileMeta[]>([]);
  const [hasSessionFiles, setHasSessionFiles] = useState(false);
  const [versionInfo, setVersionInfo] = useState<{ exists: boolean; nextVersion: string; currentVersions: number } | null>(null);
  const [isCheckingLC, setIsCheckingLC] = useState(false);
  const [showDocTypeErrors, setShowDocTypeErrors] = useState(false);
  const [templatePrefillInfo, setTemplatePrefillInfo] = useState<{
    templateName: string;
    appliedFields: string[];
  } | null>(null);
  
  // Blocked upload modal state
  const [blockedModal, setBlockedModal] = useState<{
    open: boolean;
    blockReason?: string;
    error?: {
      error_code: string;
      title: string;
      message: string;
      detail?: string;
      action?: string;
      redirect_url?: string;
      help_text?: string;
    };
    detectedDocuments?: Array<{ type: string; filename?: string }>;
    lcDetection?: {
      lc_type?: string;
      confidence?: number;
      reason?: string;
      is_draft?: boolean;
      source?: string;
      confidence_mode?: string;
      detection_basis?: string;
    };
  }>({ open: false });

  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const draftIdFromQuery = draftId ?? searchParams.get("draftId");
  const templateIdFromQuery = templateId ?? searchParams.get("templateId");
  const initialLcTypeParam = (searchParams.get('lcType') || '').toLowerCase();
  const initialLcTypeOverride: 'auto' | 'export' | 'import' =
    initialLcTypeParam === 'export' || initialLcTypeParam === 'import'
      ? (initialLcTypeParam as 'export' | 'import')
      : 'auto';
  const [lcTypeOverride, setLcTypeOverride] = useState<'auto' | 'export' | 'import'>(initialLcTypeOverride);
  
  // Validation hook
  const { validate, isLoading: isValidating, clearError } = useValidate();
  const quotaState = useLcopilotQuota();
  const isLCResolved = lcIntake.status === "resolved" && !!lcIntake.continuationAllowed;
  const isLcResolving = lcIntake.status === "uploading";

  // Extraction payload — set after the extract_only POST returns. The
  // ExtractionReview component renders inline on this same page (instead
  // of navigating to a separate section) so the user never leaves the
  // upload flow until they explicitly hit "Start Validation".
  const [extractionPayload, setExtractionPayload] = useState<any>(null);
  // Client-generated request id for SSE progress streaming. Set when the user
  // clicks "Extract & Review", cleared when the extract call finishes. The
  // same id is sent in the X-Client-Request-ID header on the POST and used
  // as the SSE channel key.
  const [clientRequestId, setClientRequestId] = useState<string | null>(null);
  const validationProgress = useValidationProgress({
    clientRequestId,
    enabled: clientRequestId !== null,
  });

  const { saveDraft, loadDraft, removeDraft } = useDrafts();
  const { checkLCExists } = useVersions();

  // Loading state
  const isProcessing = isValidating;
  const isValidationProcessing = isValidating && !isLcResolving;

  // Load draft if draftId is provided in URL params
  useEffect(() => {
    if (draftIdFromQuery) {
      setIsLoadingDraft(true);
      setCurrentDraftId(draftIdFromQuery);

      try {
        const result = loadDraft(draftIdFromQuery);
        if (result) {
          const { draft, filesData } = result;

          // Populate form with draft data
          setLcNumber(draft.lcNumber || '');
          setIssueDate(draft.issueDate || '');
          setNotes(draft.notes || '');

          if (filesData.length > 0) {
            const restoredLcFileData = filesData.find((fileData) => fileData.documentType === DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT);
            const restoredSupportingFilesData = filesData.filter((fileData) => fileData.documentType !== DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT);

            if (draft.lcIntakeSnapshot) {
              const lcFile = restoredLcFileData?.dataUrl
                ? dataUrlToFile(
                    restoredLcFileData.dataUrl,
                    draft.lcIntakeSnapshot.fileName || restoredLcFileData.name,
                    draft.lcIntakeSnapshot.type || restoredLcFileData.type || 'application/pdf',
                  )
                : draft.lcIntakeSnapshot.fileName
                ? new File([], draft.lcIntakeSnapshot.fileName, {
                    type: draft.lcIntakeSnapshot.type || 'application/pdf',
                  })
                : null;

              setLcIntake({
                status: draft.lcIntakeSnapshot.status,
                file: lcFile,
                message: draft.lcIntakeSnapshot.message,
                continuationAllowed: draft.lcIntakeSnapshot.continuationAllowed,
                isLc: draft.lcIntakeSnapshot.isLc,
                jobId: draft.lcIntakeSnapshot.jobId,
                lcSummary: draft.lcIntakeSnapshot.lcSummary,
                lcDetection: draft.lcIntakeSnapshot.lcDetection as any,
                requiredDocumentTypes: draft.lcIntakeSnapshot.requiredDocumentTypes || [],
                documentsRequired: draft.lcIntakeSnapshot.documentsRequired || [],
                requiredDocumentsDetailed: draft.lcIntakeSnapshot.requiredDocumentsDetailed || [],
                requirementConditions: draft.lcIntakeSnapshot.requirementConditions || [],
                unmappedRequirements: draft.lcIntakeSnapshot.unmappedRequirements || [],
                specialConditions: draft.lcIntakeSnapshot.specialConditions || [],
                detectedDocuments: draft.lcIntakeSnapshot.detectedDocuments || [],
              });
            }

            // Files available from session storage - restore them
            const restoredFiles: UploadedFile[] = restoredSupportingFilesData.map((fileData) => {
              const restoredFileData = fileData as RestoredFileData;
              const detection = detectDocumentTypeFromFilename(restoredFileData.name);
              const restoredDocumentType =
                restoredFileData.documentType || restoredFileData.tag || detection.type;
              return {
                id: restoredFileData.id,
                file: restoredFileData.dataUrl
                  ? dataUrlToFile(restoredFileData.dataUrl, restoredFileData.name, restoredFileData.type)
                  : new File([], restoredFileData.name, { type: restoredFileData.type }),
                name: restoredFileData.name,
                size: restoredFileData.size,
                type: restoredFileData.type,
                status: restoredFileData.status,
                progress: restoredFileData.progress,
                documentType: restoredDocumentType,
                manualDocumentType: !!restoredFileData.manualDocumentType,
                detectedType: restoredFileData.detectedType || detection.type,
                detectedConfidence: restoredFileData.detectedConfidence ?? detection.confidence,
                isTradeDocument: restoredFileData.isTradeDocument ?? detection.isTradeDoc,
                relevanceWarning: restoredFileData.relevanceWarning ?? detection.warning,
              };
            });

            setUploadedFiles(restoredFiles);
            setHasSessionFiles(true);
          } else if (draft.lcIntakeSnapshot) {
            setLcIntake({
              status: draft.lcIntakeSnapshot.status,
              file: draft.lcIntakeSnapshot.fileName
                ? new File([], draft.lcIntakeSnapshot.fileName, {
                    type: draft.lcIntakeSnapshot.type || 'application/pdf',
                  })
                : null,
              message: draft.lcIntakeSnapshot.message,
              continuationAllowed: draft.lcIntakeSnapshot.continuationAllowed,
              isLc: draft.lcIntakeSnapshot.isLc,
              jobId: draft.lcIntakeSnapshot.jobId,
              lcSummary: draft.lcIntakeSnapshot.lcSummary,
              lcDetection: draft.lcIntakeSnapshot.lcDetection as any,
              requiredDocumentTypes: draft.lcIntakeSnapshot.requiredDocumentTypes || [],
              documentsRequired: draft.lcIntakeSnapshot.documentsRequired || [],
              requiredDocumentsDetailed: draft.lcIntakeSnapshot.requiredDocumentsDetailed || [],
              requirementConditions: draft.lcIntakeSnapshot.requirementConditions || [],
              unmappedRequirements: draft.lcIntakeSnapshot.unmappedRequirements || [],
              specialConditions: draft.lcIntakeSnapshot.specialConditions || [],
              detectedDocuments: draft.lcIntakeSnapshot.detectedDocuments || [],
            });
          }

          if (filesData.length > 0) {

            toast({
              title: "Draft Loaded",
              description: `Resumed working on draft with ${filesData.length} files restored.`,
            });
          } else {
            // No files in session - show re-attach banner
            setStagedFilesMeta(draft.filesMeta || []);
            setHasSessionFiles(false);

            toast({
              title: "Draft Loaded",
              description: `Resumed working on draft. ${draft.filesMeta?.length || 0} files need to be re-attached.`,
            });
          }
        } else {
          toast({
            title: "Draft Not Found",
            description: "The requested draft could not be found.",
            variant: "destructive",
          });
        }
      } catch (error) {
        console.error('Failed to load draft:', error);
        toast({
          title: "Failed to Load Draft",
          description: "Could not load the saved draft. Please try again.",
          variant: "destructive",
        });
      } finally {
        setIsLoadingDraft(false);
      }
    }
  }, [draftIdFromQuery, loadDraft, toast]);

  useEffect(() => {
    if (draftIdFromQuery) {
      return;
    }

    const lcNumberParam = searchParams.get("lcNumber");
    const issueDateParam = searchParams.get("issueDate");
    const notesParam = searchParams.get("notes");

    if (lcNumberParam && !lcNumber.trim()) {
      setLcNumber(lcNumberParam);
    }

    if (issueDateParam && !issueDate.trim()) {
      setIssueDate(issueDateParam);
    }

    if (notesParam && !notes.trim()) {
      setNotes(notesParam);
    }
  }, [draftIdFromQuery, searchParams, lcNumber, issueDate, notes]);

  useEffect(() => {
    if (draftIdFromQuery || !templateIdFromQuery) {
      return;
    }

    let active = true;

    const loadTemplatePrefill = async () => {
      try {
        const response = await smeTemplatesApi.prefill({ template_id: templateIdFromQuery });
        if (!active) {
          return;
        }

        const prefill = buildTemplateUploadPrefill(response.fields || {}, response.template_name);

        setLcNumber((current) => (prefill.lcNumber && !current.trim() ? prefill.lcNumber : current));
        setIssueDate((current) => (prefill.issueDate && !current.trim() ? prefill.issueDate : current));
        setNotes((current) => (prefill.notes && !current.trim() ? prefill.notes : current));

        setTemplatePrefillInfo({
          templateName: response.template_name,
          appliedFields: prefill.appliedFields,
        });

        toast({
          title: "Template applied",
          description:
            prefill.appliedFields.length > 0
              ? `${response.template_name} filled ${prefill.appliedFields.join(", ")}. Review the values before validating.`
              : `${response.template_name} opened without any supported upload fields to prefill.`,
        });
      } catch (error: any) {
        if (!active) {
          return;
        }

        toast({
          title: "Template prefill unavailable",
          description:
            error.response?.data?.detail ||
            "The upload workflow opened, but this template could not be applied automatically.",
          variant: "destructive",
        });
      }
    };

    void loadTemplatePrefill();

    return () => {
      active = false;
    };
  }, [draftIdFromQuery, templateIdFromQuery, toast]);

  // Check if LC number exists when user enters it
  const handleLCNumberChange = async (value: string) => {
    setLcNumber(value);

    if (value.trim().length > 0) {
      setIsCheckingLC(true);
      try {
        const info = await checkLCExists(value.trim());
        setVersionInfo(info);
      } catch (error) {
        console.error('Failed to check LC:', error);
        setVersionInfo(null);
      } finally {
        setIsCheckingLC(false);
      }
    } else {
      setVersionInfo(null);
    }
  };

  const fileToDataUrl = (file: File) =>
    new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(reader.error || new Error('Failed to read file'));
      reader.readAsDataURL(file);
    });

  const handleSaveDraft = async () => {
    const completedFiles = uploadedFiles.filter(f => f.status === "completed");
    const hasResolvedOrAttachedLc = !!lcIntake.file || lcIntake.status === "resolved" || lcIntake.status === "ambiguous" || lcIntake.status === "invalid";

    if (completedFiles.length === 0 && !hasResolvedOrAttachedLc && !lcNumber.trim() && !notes.trim()) {
      toast({
        title: "Nothing to Save",
        description: "Upload the LC, add supporting files, or enter form data before saving a draft.",
        variant: "destructive",
      });
      return;
    }

    try {
      const filesMeta: FileMeta[] = completedFiles.map(file => ({
        name: file.name,
        size: file.size,
        type: file.type,
        tag: file.documentType,
      }));

      const lcFileData = lcIntake.file
        ? {
            id: `lc-${lcIntake.file.name}`,
            name: lcIntake.file.name,
            size: lcIntake.file.size,
            type: lcIntake.file.type,
            documentType: DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT,
            status: 'completed' as const,
            progress: 100,
            dataUrl: await fileToDataUrl(lcIntake.file),
          }
        : null;

      const completedFilesData = await Promise.all(
        completedFiles.map(async (file) => ({
          id: file.id,
          name: file.name,
          size: file.size,
          type: file.type,
          documentType: file.documentType,
          manualDocumentType: file.manualDocumentType,
          detectedType: file.detectedType,
          detectedConfidence: file.detectedConfidence,
          isTradeDocument: file.isTradeDocument,
          relevanceWarning: file.relevanceWarning,
          status: file.status,
          progress: file.progress,
          dataUrl: await fileToDataUrl(file.file),
        })),
      );

      const filesData: FileData[] = lcFileData ? [lcFileData, ...completedFilesData] : completedFilesData;

      const savedDraft = saveDraft({
        id: currentDraftId || undefined,
        lcNumber: lcNumber.trim() || undefined,
        issueDate: issueDate.trim() || undefined,
        notes: notes.trim() || undefined,
        filesMeta,
        filesData, // Save to session storage
        lcIntakeSnapshot: {
          status: lcIntake.status,
          fileName: lcIntake.file?.name,
          fileSize: lcIntake.file?.size,
          type: lcIntake.file?.type,
          message: lcIntake.message,
          continuationAllowed: lcIntake.continuationAllowed,
          isLc: lcIntake.isLc,
          jobId: lcIntake.jobId,
          lcSummary: lcIntake.lcSummary,
          lcDetection: lcIntake.lcDetection,
          requiredDocumentTypes: lcIntake.requiredDocumentTypes,
          documentsRequired: lcIntake.documentsRequired,
          requiredDocumentsDetailed: lcIntake.requiredDocumentsDetailed,
          requirementConditions: lcIntake.requirementConditions,
          unmappedRequirements: lcIntake.unmappedRequirements,
          specialConditions: lcIntake.specialConditions,
          detectedDocuments: lcIntake.detectedDocuments,
        },
      });

      setCurrentDraftId(savedDraft.id);

      toast({
        title: "Draft Saved",
        description: "Your progress has been saved. You can resume later from your dashboard.",
      });

      // Navigate back to dashboard only when in standalone mode
      if (!embedded) {
        navigate('/lcopilot/exporter-dashboard');
      }
    } catch (error: any) {
      console.error('Failed to save draft:', error);
      toast({
        title: "Failed to Save Draft",
        description: error.message || "Could not save the draft. Please try again.",
        variant: "destructive",
      });
    }
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadedFile[] = acceptedFiles.map(file => {
      // Auto-detect document type from filename
      const detection = detectDocumentTypeFromFilename(file.name);
      
      return {
        id: Math.random().toString(36).substring(2, 11),
        file,
        name: file.name,
        size: file.size,
        type: file.type,
        status: "pending" as const,
        progress: 0,
        documentType: detection.type, // Auto-set from detection
        manualDocumentType: false,
        detectedType: detection.type,
        detectedConfidence: detection.confidence,
        isTradeDocument: detection.isTradeDoc,
        relevanceWarning: detection.warning,
      };
    });

    setUploadedFiles(prev => [...prev, ...newFiles]);

    // Simulate file upload
    newFiles.forEach(file => {
      simulateUpload(file.id);
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxFiles: 10,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const simulateUpload = (fileId: string) => {
    setUploadedFiles(prev => 
      prev.map(file => 
        file.id === fileId ? { ...file, status: "uploading" as const } : file
      )
    );

    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 30;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        setUploadedFiles(prev => 
          prev.map(file => 
            file.id === fileId 
              ? { ...file, status: "completed" as const, progress: 100 }
              : file
          )
        );
      } else {
        setUploadedFiles(prev => 
          prev.map(file => 
            file.id === fileId ? { ...file, progress } : file
          )
        );
      }
    }, 200);
  };

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== fileId));
  };

  const updateFileDocumentType = (fileId: string, documentType: string) => {
    setUploadedFiles((prev) => {
      const updated = prev.map((file) =>
        file.id === fileId ? { ...file, documentType, manualDocumentType: true } : file
      );
      if (showDocTypeErrors) {
        const completed = updated.filter((file) => file.status === "completed");
        if (completed.length > 0 && completed.every((file) => !!file.documentType)) {
          setShowDocTypeErrors(false);
        }
      }
      return updated;
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const dataUrlToFile = (dataUrl: string, fileName: string, mimeType?: string) => {
    const [header, body] = dataUrl.split(',');
    const detectedMime = header?.match(/data:(.*?);base64/)?.[1] || mimeType || 'application/octet-stream';
    const binary = atob(body || '');
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return new File([bytes], fileName, { type: detectedMime });
  };

  const handlePreviewFile = (file: UploadedFile) => {
    if (file.file && file.file.size > 0) {
      // Create a blob URL for the file
      const fileUrl = URL.createObjectURL(file.file);

      // Open in new tab for preview
      window.open(fileUrl, '_blank');

      // Clean up the object URL after a short delay
      setTimeout(() => {
        URL.revokeObjectURL(fileUrl);
      }, 1000);
    } else {
      toast({
        title: "Preview Unavailable",
        description: "This file cannot be previewed.",
        variant: "destructive",
      });
    }
  };

  const handleLCIntakeFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] || null;
    if (!nextFile) return;

    setLcIntake({ status: "uploading", file: nextFile });

    // Generate a client request id so the LC intake phase also streams real
    // backend progress over SSE instead of relying on the fake timer.
    const intakeRequestId =
      typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : `intake-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setClientRequestId(intakeRequestId);

    try {
      const response = await validate({
        files: [nextFile],
        userType: "exporter",
        workflowType: "export-lc-intake",
        lcTypeOverride,
        intakeOnly: true,
        mode: "lc_intake",
        clientRequestId: intakeRequestId,
      });

      if (response.status === "blocked" || response.status === "invalid") {
        setLcIntake({
          status: response.status === "blocked" ? "invalid" : response.status,
          file: nextFile,
          message: response.message,
          continuationAllowed: response.continuation_allowed,
          isLc: response.is_lc,
          lcSummary: response.lc_summary,
          lcDetection: response.lc_detection,
          requiredDocumentTypes: response.required_document_types || [],
          documentsRequired: response.documents_required || [],
          requiredDocumentsDetailed: response.required_documents_detailed || [],
          requirementConditions: response.requirement_conditions || [],
          unmappedRequirements: response.unmapped_requirements || [],
          specialConditions: response.special_conditions || [],
          detectedDocuments: response.detected_documents || [],
          error: response.error,
        });
        return;
      }

      setLcIntake({
        status: response.status === "resolved" ? "resolved" : "ambiguous",
        file: nextFile,
        message: response.message,
        continuationAllowed: response.continuation_allowed,
        isLc: response.is_lc,
        jobId: response.jobId || response.job_id,
        lcSummary: response.lc_summary,
        lcDetection: response.lc_detection,
        requiredDocumentTypes: response.required_document_types || [],
        documentsRequired: response.documents_required || [],
        requiredDocumentsDetailed: response.required_documents_detailed || [],
        requirementConditions: response.requirement_conditions || [],
        unmappedRequirements: response.unmapped_requirements || [],
        specialConditions: response.special_conditions || [],
        detectedDocuments: response.detected_documents || [],
      });

      if (response.lc_summary?.lc_number && !lcNumber.trim()) {
        setLcNumber(String(response.lc_summary.lc_number));
      }

      toast({
        title: response.continuation_allowed ? "LC Resolved" : "LC Needs Review",
        description: response.message || "LC intake completed.",
      });
    } catch (error: any) {
      console.error('LC intake failed:', error);
      setLcIntake({
        status: "invalid",
        file: nextFile,
        message: error?.message || "Could not process the LC file.",
      });
    } finally {
      event.target.value = '';
      // Close the SSE progress stream for this intake run
      setClientRequestId(null);
    }
  };

  const handleClearLCIntake = () => {
    setLcIntake({ status: "idle", file: null });
    setUploadedFiles([]);
  };

  const handleProcessLC = async () => {
    if (!isLCResolved) {
      toast({
        title: "Upload LC First",
        description: "Resolve the Letter of Credit before validating supporting documents.",
        variant: "destructive",
      });
      return;
    }

    if (uploadedFiles.length === 0) {
      toast({
        title: "No Files Selected",
        description: "Please upload at least one supporting document to proceed.",
        variant: "destructive",
      });
      return;
    }

    if (!lcNumber.trim()) {
      toast({
        title: "LC Number Required",
        description: "Please enter the LC number before processing.",
        variant: "destructive",
      });
      return;
    }

    if (!quotaState.canValidate) {
      setQuotaError({
        type: 'quota',
        message: quotaState.detail,
        quota: quotaState.quota ?? undefined,
        nextActionUrl: quotaState.ctaUrl,
      });
      setShowQuotaModal(true);
      return;
    }

    const completedFiles = uploadedFiles.filter(f => f.status === "completed");
    if (completedFiles.some(file => !file.documentType)) {
      setShowDocTypeErrors(true);
      toast({
        title: "Assign document types",
        description: "Please categorize each uploaded document (LC, Invoice, B/L, etc.) before processing.",
        variant: "destructive",
      });
      return;
    } else {
      setShowDocTypeErrors(false);
    }

    const files = lcIntake.file ? [lcIntake.file, ...completedFiles.map(f => f.file)] : completedFiles.map(f => f.file);

    const resolveFinalDocumentType = (file: UploadedFile): string => {
      const normalizedManual = normalizeDocumentType(file.documentType);
      const normalizedDetected = normalizeDocumentType(file.detectedType);

      if (file.manualDocumentType && normalizedManual && normalizedManual !== DOCUMENT_TYPE_VALUES.UNKNOWN) {
        return normalizedManual;
      }
      if (normalizedDetected && normalizedDetected !== DOCUMENT_TYPE_VALUES.UNKNOWN && normalizedDetected !== DOCUMENT_TYPE_VALUES.OTHER) {
        return normalizedDetected;
      }
      if (normalizedManual && normalizedManual !== DOCUMENT_TYPE_VALUES.UNKNOWN) {
        return normalizedManual;
      }
      return DOCUMENT_TYPE_VALUES.OTHER;
    };

    // Create document tags mapping
    const documentTags: Record<string, string> = {};
    if (lcIntake.file) {
      documentTags[lcIntake.file.name] = DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT;
    }
    completedFiles.forEach(file => {
      const finalDocumentType = resolveFinalDocumentType(file);
      documentTags[file.name] = finalDocumentType;
    });

    try {
      clearError();
      setShowRateLimit(false);
      setQuotaError(null);

      toast({
        title: "Starting Document Validation",
        description: "Uploading documents and checking compliance...",
      });

      // Generate a client request id for SSE progress streaming. The
      // useValidationProgress hook (already initialized above) will pick this
      // up and open the EventSource connection BEFORE the POST is sent.
      // The same id flows to the backend as X-Client-Request-ID so the
      // pipeline publishes checkpoint events to the matching channel.
      const requestId =
        typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
          ? crypto.randomUUID()
          : `req-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setClientRequestId(requestId);

      // Log validation params
      console.log('📁 Files to validate:', files.map(f => f.name));
      console.log('🏷️  LC Number:', lcNumber.trim());
      console.log('📋 Document Tags:', documentTags);
      console.log('🧭 Final Tag Resolution:', completedFiles.map(file => ({
        name: file.name,
        detectedType: file.detectedType,
        selectedType: file.documentType,
        manualDocumentType: file.manualDocumentType,
        finalTag: documentTags[file.name],
      })));
      console.log('⚙️  LC Type Override:', lcTypeOverride);
      console.log('🔗 Client Request ID:', requestId);

      // Run extraction only — validation happens on the extraction review
      // screen after the user confirms / corrects fields. This is the new
      // LC → supporting docs → extract → user review → validate flow.
      const response = await validate({
        files,
        lcNumber: lcNumber.trim(),
        notes: notes.trim() || undefined,
        documentTags: documentTags,
        userType: "exporter",
        workflowType: "export-lc-upload",
        lcTypeOverride,
        extractOnly: true,
        clientRequestId: requestId,
      });

      // Check for blocked response (wrong LC type, no LC found, etc.)
      if (response.status === "blocked") {
        console.log('⚠️ Extraction blocked:', response.block_reason);
        setBlockedModal({
          open: true,
          blockReason: response.block_reason,
          error: response.error,
          detectedDocuments: response.detected_documents,
          lcDetection: response.lc_detection,
        });
        return;
      }

      const jobId = response.jobId || response.job_id;

      console.log('✅ Extraction complete, jobId:', jobId, 'status:', response.status);

      toast({
        title: "Extraction Complete",
        description: "Review the extracted fields before running validation.",
      });

      // Remove draft from storage if we're working with a draft
      if (currentDraftId) {
        try {
          removeDraft(currentDraftId);
          console.log('✅ Draft removed after extraction:', currentDraftId);
        } catch (error) {
          console.error('Failed to remove draft:', error);
        }
      }

      // Show the extraction review INLINE on this same page. The old flow
      // navigated to a separate ?section=extract-review section, which
      // fragmented the upload UX. Now the user stays on the upload page
      // and sees the review appear below their uploads; validation still
      // navigates away when they hit "Start Validation".
      if (jobId) {
        setExtractionPayload(response);
        console.log('✅ Extraction complete, showing inline review. jobId:', jobId);
        // Scroll the review into view once React renders it.
        setTimeout(() => {
          const reviewEl = document.getElementById('extraction-review-inline');
          if (reviewEl) {
            reviewEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }, 200);
      }

    } catch (error: any) {
      const errorCode = error?.errorCode || error?.error_code || 'unknown';
      const errorLog = {
        type: error?.type,
        message: error?.message,
        statusCode: error?.statusCode,
        errorCode,
        quota: error?.quota,
        nextActionUrl: error?.nextActionUrl,
      };
      console.error('❌ [COMPONENT] Validation error caught:', JSON.stringify(errorLog, null, 2));
      console.error('❌ [COMPONENT] Full error object:', error);
      
      if (error.type === 'quota') {
        setQuotaError(error);
        setShowQuotaModal(true);
        return;
      }
      if (error.type === 'rate_limit') {
        setShowRateLimit(true);
      } else {
        // Include error code in the message if available for debugging
        const description = errorCode !== 'unknown'
          ? `${error.message || 'Validation failed'} (${errorCode})`
          : error.message || "Something went wrong. Please try again.";
        toast({
          title: "Validation Failed",
          description,
          variant: "destructive",
        });
      }
    } finally {
      // Close the SSE progress stream once validation is done (success or fail)
      setClientRequestId(null);
    }
  };

  const completedFiles = uploadedFiles.filter(f => f.status === "completed");
  const isReadyToProcess = isLCResolved && completedFiles.length > 0 && !!lcNumber.trim() && !isProcessing;
  const quickBadgeTypes = useMemo(
    () => getQuickBadgeDocumentTypes(exportDocumentTypes, lcIntake.requiredDocumentTypes || []),
    [lcIntake.requiredDocumentTypes],
  );
  const specialConditionSummary = useMemo(
    () => summarizeSpecialConditions(lcIntake.specialConditions || []),
    [lcIntake.specialConditions],
  );
  const uploadRequirements = useMemo(
    () =>
      getUploadRequirementsModel({
        requiredDocumentTypes: lcIntake.requiredDocumentTypes || [],
        documentsRequired: lcIntake.documentsRequired || [],
        requiredDocumentsDetailed: lcIntake.requiredDocumentsDetailed || [],
        requirementConditions: lcIntake.requirementConditions || [],
        unmappedRequirements: lcIntake.unmappedRequirements || [],
        specialConditions: lcIntake.specialConditions || [],
        resolveLabel: (docType) => exportDocumentTypes.find((t) => t.value === docType)?.label || docType,
      }),
    [
      lcIntake.requiredDocumentTypes,
      lcIntake.documentsRequired,
      lcIntake.requiredDocumentsDetailed,
      lcIntake.requirementConditions,
      lcIntake.unmappedRequirements,
      lcIntake.specialConditions,
    ],
  );
  const requirementUploadStatus = useMemo(() => {
    const found: typeof uploadRequirements.documentRequirements = [];
    const missing: typeof uploadRequirements.documentRequirements = [];

    uploadRequirements.documentRequirements.forEach((requirement) => {
      const normalizedType = normalizeDocumentType(requirement.type);
      const isFound = completedFiles.some(
        (file) =>
          normalizeDocumentType(file.documentType) === normalizedType ||
          normalizeDocumentType(file.detectedType) === normalizedType,
      );
      (isFound ? found : missing).push(requirement);
    });

    return { found, missing };
  }, [completedFiles, uploadRequirements.documentRequirements]);
  const hiddenQuickBadgeCount = Math.max(0, exportDocumentTypes.length - quickBadgeTypes.length);

  const wrapperClass = embedded
    ? "mx-auto w-full max-w-4xl py-4"
    : "container mx-auto px-4 py-8 max-w-4xl";

  return (
    <div className={embedded ? "bg-transparent" : "bg-background"}>
      {/* Header */}
      {!embedded && (
        <header className="bg-card border-b border-gray-200">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center gap-4">
              <Link to="/lcopilot/exporter-dashboard">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Dashboard
                </Button>
              </Link>
              <div className="flex items-center gap-3">
                <div className="bg-gradient-exporter p-2 rounded-lg">
                  <Upload className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold text-foreground">Export LC & Trade Documents</h1>
                    {currentDraftId && (
                      <Badge variant="outline" className="text-xs">
                        Draft Mode
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {currentDraftId
                      ? "Continue working on your saved draft"
                      : "Upload LC and trade documents to generate customs-ready pack"
                    }
                  </p>
                </div>
              </div>
            </div>
          </div>
        </header>
      )}

      {isLoadingDraft && (
        <div className={embedded ? "mx-auto w-full max-w-4xl px-0 py-6" : "container mx-auto px-4 py-8 max-w-4xl"}>
          <Card>
            <CardContent className="p-8 text-center">
              <div className="animate-spin w-8 h-8 border-2 border-exporter border-t-transparent rounded-full mx-auto mb-4"></div>
              <h3 className="text-lg font-semibold mb-2">Loading Draft...</h3>
              <p className="text-muted-foreground">Retrieving your saved progress.</p>
            </CardContent>
          </Card>
        </div>
      )}

      {!isLoadingDraft && (
        <div className={wrapperClass}>
        {templatePrefillInfo && (
          <Card className="mb-6 border-blue-200 bg-blue-50">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="bg-blue-100 p-2 rounded-lg">
                  <Sparkles className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-blue-900 mb-1">
                    Template applied: {templatePrefillInfo.templateName}
                  </h4>
                  <p className="text-sm text-blue-700">
                    {templatePrefillInfo.appliedFields.length > 0
                      ? `Applied ${templatePrefillInfo.appliedFields.join(", ")} to this upload form. Review and adjust before validating.`
                      : "This template did not include any supported upload fields. You can still use it as a manual reference during this beta."}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Re-attach Files Banner - only show if no session files available */}
        {stagedFilesMeta.length > 0 && !hasSessionFiles && (
          <Card className="mb-6 border-blue-200 bg-blue-50">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="bg-blue-100 p-2 rounded-lg">
                  <FileText className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-blue-900 mb-2">Re-attach your files to continue</h4>
                  <p className="text-sm text-blue-700 mb-3">
                    Your files were saved in a previous session. Please re-attach the files listed below:
                  </p>
                  <div className="space-y-1">
                    {stagedFilesMeta.map((file, index) => (
                      <div key={index} className="text-sm text-blue-800 bg-blue-100 px-2 py-1 rounded inline-block mr-2 mb-1">
                        {file.name} ({(file.size / 1024 / 1024).toFixed(1)}MB)
                        {file.tag && <span className="ml-1 text-blue-600">• {exportDocumentTypes.find(t => t.value === file.tag)?.label || file.tag}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Session Files Restored Banner */}
        {hasSessionFiles && uploadedFiles.length > 0 && (
          <Card className="mb-6 border-green-200 bg-green-50">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="bg-green-100 p-2 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-green-900 mb-2">Files restored from draft</h4>
                  <p className="text-sm text-green-700">
                    Your uploaded files have been restored from your previous session. You can continue working or add more files.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Preparation Guide - Static checklist before upload */}
        <div className="mb-6">
          <PreparationGuide />
        </div>

        {/* Step 1: LC Intake */}
        <Card className="mb-6 shadow-soft border-0">
          <CardHeader>
            <CardTitle>Step 1 — Upload Letter of Credit</CardTitle>
            <CardDescription>
              Start with the LC first. We’ll detect required supporting documents automatically and unlock the bulk uploader below.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
                isLcResolving || !!lcIntake.file
                  ? "border-exporter bg-exporter/5 cursor-default"
                  : "border-gray-200 hover:border-exporter/50 hover:bg-secondary/20 cursor-pointer"
              )}
              onClick={() => {
                if (isLcResolving || isProcessing || !!lcIntake.file) return;
                const input = document.getElementById("lc-intake-upload") as HTMLInputElement | null;
                input?.click();
              }}
              role="button"
              tabIndex={isLcResolving || isProcessing || !!lcIntake.file ? -1 : 0}
              onKeyDown={(e) => {
                if (isLcResolving || isProcessing || !!lcIntake.file) return;
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  const input = document.getElementById("lc-intake-upload") as HTMLInputElement | null;
                  input?.click();
                }
              }}
            >
              <input
                id="lc-intake-upload"
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                className="hidden"
                onChange={handleLCIntakeFileChange}
              />
              <div className="flex flex-col items-center gap-4">
                <div className="p-4 rounded-full bg-exporter/10">
                  <Sparkles className="w-8 h-8 text-exporter" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {isLcResolving
                      ? "Resolving Letter of Credit..."
                      : lcIntake.file
                      ? "Letter of Credit Uploaded"
                      : "Upload Letter of Credit"}
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    {isLcResolving
                      ? "We’re checking the LC, detecting workflow, and extracting required supporting documents."
                      : lcIntake.file
                      ? "The LC file is already attached. Clear it first if you want to upload a different one."
                      : "Click anywhere in this box or use the button below to choose the LC file first."}
                  </p>
                </div>
                <div className="flex gap-3" onClick={(e) => e.stopPropagation()}>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={isLcResolving || isProcessing || !!lcIntake.file}
                    onClick={() => {
                      const input = document.getElementById("lc-intake-upload") as HTMLInputElement | null;
                      input?.click();
                    }}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Choose LC File
                  </Button>
                  {lcIntake.file && (
                    <Button variant="ghost" onClick={handleClearLCIntake} disabled={isLcResolving || isProcessing}>
                      Clear
                    </Button>
                  )}
                </div>
              </div>
            </div>

            {lcIntake.file && (
              <div className="rounded-lg border border-gray-200 p-4 bg-secondary/10 space-y-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-medium text-foreground">{lcIntake.file.name}</p>
                    <p className="text-xs text-muted-foreground">{formatFileSize(lcIntake.file.size)}</p>
                  </div>
                  <Badge variant={isLCResolved ? "default" : lcIntake.status === "uploading" ? "outline" : "secondary"}>
                    {lcIntake.status === "uploading" ? "Checking LC..." : isLCResolved ? "LC Resolved" : lcIntake.status}
                  </Badge>
                </div>

                {(lcIntake.message || lcIntake.error?.message) && (
                  <div className={cn(
                    "rounded-md p-3 text-sm border",
                    isLCResolved ? "bg-green-50 border-green-200 text-green-800" : "bg-amber-50 border-amber-200 text-amber-800"
                  )}>
                    {lcIntake.error?.message || lcIntake.message}
                  </div>
                )}

                {lcIntake.lcDetection && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    <Badge variant="default" className="font-semibold">
                      {getWorkflowPrimaryLabel(lcIntake.lcDetection as WorkflowDetectionSummary)}
                    </Badge>
                    {(() => {
                      const primary = getWorkflowPrimaryLabel(lcIntake.lcDetection as WorkflowDetectionSummary);
                      const fallback = formatWorkflowBadgeLabel(lcIntake.lcDetection.lc_type);
                      // Only show the generic "Export Workflow" badge if the
                      // subtype classifier couldn't produce a more specific label.
                      if (primary === "LC" || primary === "Export LC" || primary === "Import LC") {
                        return <Badge variant="outline">{fallback}</Badge>;
                      }
                      return null;
                    })()}
                    {getWorkflowDetectionStatusBadge(lcIntake.lcDetection as WorkflowDetectionSummary) && (
                      <Badge variant="outline">
                        {getWorkflowDetectionStatusBadge(lcIntake.lcDetection as WorkflowDetectionSummary)}
                      </Badge>
                    )}
                    {typeof lcIntake.lcDetection.confidence === 'number' && (
                      <Badge variant="outline">
                        {formatWorkflowConfidenceBadgeLabel(
                          lcIntake.lcDetection.confidence,
                          lcIntake.lcDetection as WorkflowDetectionSummary,
                        )}
                      </Badge>
                    )}
                    {lcIntake.lcDetection.is_draft && <Badge variant="outline">Draft LC</Badge>}
                  </div>
                )}

                {Object.keys(lcIntake.lcSummary || {}).length > 0 && (
                  <div className="grid md:grid-cols-3 gap-3 text-sm">
                    {Object.entries(lcIntake.lcSummary || {}).slice(0, 6).map(([key, value]) => (
                      <div key={key} className="rounded bg-background p-3 border border-gray-200/60">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">{key.replace(/_/g, ' ')}</p>
                        <p className="font-medium text-foreground break-words">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {lcIntake.status === "uploading" && (
          <Card className="mb-6 shadow-soft border-0">
            <CardContent className="pt-6">
              <ValidationProgressIndicator fileCount={1} mode="lc" realProgress={validationProgress} />
            </CardContent>
          </Card>
        )}

        {/* Step 1.5: Requirement summary / live checklist */}
        <Card className="mb-6 shadow-soft border-0">
          <CardHeader>
            <CardTitle>Required Documents</CardTitle>
            <CardDescription>
              {isLCResolved
                ? "These requirements were detected from the LC. Upload the remaining documents below in any order, any filename."
                : "Required documents will appear here after the LC is resolved."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!isLCResolved ? (
              <div className="flex items-center gap-3 rounded-lg border border-dashed border-gray-300 p-4 text-sm text-muted-foreground">
                <Lock className="w-4 h-4" />
                Upload and resolve the LC first to unlock the supporting-document checklist.
              </div>
            ) : (
              <div className="space-y-4">
                {requirementUploadStatus.missing.length > 0 && (
                  <div className="rounded-lg border border-amber-400/40 bg-amber-50/50 p-4">
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                      <div>
                        <p className="text-sm font-semibold text-foreground">
                          Still missing LC-required uploads ({requirementUploadStatus.missing.length})
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          You can validate a partial set, but these missing uploads will keep the case in review until they are provided.
                        </p>
                      </div>
                      <Badge variant="outline">Missing uploads</Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {requirementUploadStatus.missing.map((requirement) => (
                        <Badge
                          key={`missing-upload-${requirement.key}`}
                          variant="outline"
                          className="border-amber-500/40 text-amber-700 bg-amber-500/5"
                        >
                          {requirement.label}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {requirementUploadStatus.missing.length === 0 && uploadRequirements.documentRequirements.length > 0 && (
                  <div className="rounded-lg border border-success/30 bg-success/5 p-4">
                    <p className="text-sm font-semibold text-foreground">All LC-required document types are uploaded</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Continue with validation to confirm field coverage, review requirements, and presentation readiness.
                    </p>
                  </div>
                )}
                <div className="space-y-2">
                  {uploadRequirements.documentRequirements.length > 0 || uploadRequirements.additionalRequirements.length > 0 ? (
                    <>
                      {uploadRequirements.documentRequirements.map((requirement) => {
                        const normalizedType = normalizeDocumentType(requirement.type);
                        const isFound = completedFiles.some((file) => normalizeDocumentType(file.documentType) === normalizedType || normalizeDocumentType(file.detectedType) === normalizedType);
                        return (
                          <div key={requirement.key} className="rounded-lg border border-gray-200/70 bg-background p-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge variant={isFound ? "default" : "outline"}>
                                {requirement.label} - {isFound ? "Found" : "Missing"}
                              </Badge>
                            </div>
                            {requirement.exactRequirement && requirement.exactRequirement.toLowerCase() !== requirement.label.toLowerCase() && (
                              <p className="mt-2 text-xs text-muted-foreground">{requirement.exactRequirement}</p>
                            )}
                          </div>
                        );
                      })}
                      {uploadRequirements.additionalRequirements.map((requirement) => (
                        <div key={requirement.key} className="rounded-lg border border-amber-300/60 bg-amber-50/40 p-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="outline">{requirement.label} - Required</Badge>
                            <Badge variant="secondary">
                              {requirement.category === "identifier"
                                ? "LC condition"
                                : requirement.category === "unmapped_requirement"
                                ? "Manual review"
                                : "LC condition"}
                            </Badge>
                          </div>
                          <p className="mt-2 text-xs text-muted-foreground">{requirement.detail}</p>
                        </div>
                      ))}
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">No explicit supporting-document requirements were extracted yet.</p>
                  )}
                </div>
                {(specialConditionSummary.items.length > 0 || specialConditionSummary.placeholderOnly) && (
                  <div className="rounded-lg border border-gray-200 p-4 bg-secondary/10">
                    <p className="text-sm font-medium text-foreground mb-2">Special Conditions</p>
                    {specialConditionSummary.items.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-1 text-sm text-muted-foreground">
                        {specialConditionSummary.items.slice(0, 4).map((item, index) => (
                          <li key={`${item}-${index}`}>{item}</li>
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
            )}
          </CardContent>
        </Card>

        {/* Step 2: Supporting document bulk uploader */}
        <Card className="mb-8 shadow-soft border-0">
          <CardHeader>
            <CardTitle>Step 2 - Upload Supporting Documents</CardTitle>
            <CardDescription>
              Upload remaining documents in any order, any filename. We'll match them against LC requirements.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              {...(isLCResolved ? getRootProps() : {})}
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
                isLCResolved
                  ? isDragActive
                    ? "border-exporter bg-exporter/5 cursor-pointer"
                    : "border-gray-200 hover:border-exporter/50 hover:bg-secondary/20 cursor-pointer"
                  : "border-gray-200 bg-muted/30 opacity-70 cursor-not-allowed"
              )}
            >
              {isLCResolved && <input {...getInputProps()} />}
              <div className="flex flex-col items-center gap-4">
                <div className={cn("p-4 rounded-full", isLCResolved ? "bg-exporter/10" : "bg-muted") }>
                  {isLCResolved ? <Upload className="w-8 h-8 text-exporter" /> : <Lock className="w-8 h-8 text-muted-foreground" />}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {isLCResolved ? (isDragActive ? "Drop supporting documents here..." : "Upload Supporting Documents") : "Supporting uploader locked"}
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    {isLCResolved
                      ? "Drag and drop your supporting files here, or click to browse"
                      : "Resolve the LC above to unlock supporting document upload."}
                  </p>
                  <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
                    {quickBadgeTypes.map(type => (
                      <Badge key={type.value} variant="outline">{type.label}</Badge>
                    ))}
                    {hiddenQuickBadgeCount > 0 && (
                      <Badge variant="secondary">+{hiddenQuickBadgeCount} more in type picker</Badge>
                    )}
                  </div>
                </div>
                <Button variant="outline" disabled={!isLCResolved}>
                  <Plus className="w-4 h-4 mr-2" />
                  Choose Files
                </Button>
              </div>
            </div>

            {/* Uploaded Files List */}
            {uploadedFiles.length > 0 && (
              <div className="mt-6 space-y-3">
                <h4 className="font-semibold text-foreground">Uploaded Supporting Files ({uploadedFiles.length})</h4>
                {uploadedFiles.map((file) => (
                  <div key={file.id} className="flex items-center gap-4 p-4 bg-secondary/20 rounded-lg border border-gray-200/50">
                    <div className="flex-shrink-0">
                      {file.status === "completed" ? (
                        <div className="bg-success/10 p-2 rounded-lg">
                          <FileCheck className="w-5 h-5 text-success" />
                        </div>
                      ) : file.status === "error" ? (
                        <div className="bg-destructive/10 p-2 rounded-lg">
                          <AlertTriangle className="w-5 h-5 text-destructive" />
                        </div>
                      ) : (
                        <div className="bg-exporter/10 p-2 rounded-lg">
                          <FileText className="w-5 h-5 text-exporter" />
                        </div>
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <h5 className="font-medium text-foreground truncate">{file.name}</h5>
                        <span className="text-sm text-muted-foreground">{formatFileSize(file.size)}</span>
                      </div>
                      
                      {file.status === "uploading" && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
                            <div className="flex items-center gap-2">
                              <div className="animate-spin w-3.5 h-3.5 border-2 border-exporter border-t-transparent rounded-full"></div>
                              <p>Preparing file locally before validation...</p>
                            </div>
                            <span>{Math.max(5, Math.round(file.progress))}%</span>
                          </div>
                          <Progress value={file.progress} className="h-1.5" />
                          <p className="text-[11px] text-muted-foreground">
                            Estimated local upload progress before validation starts.
                          </p>
                        </div>
                      )}
                      
                      {file.status === "completed" && (
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <CheckCircle className="w-4 h-4 text-success" />
                            <span className="text-xs text-success">Upload complete</span>
                            {file.detectedType && file.detectedConfidence && file.detectedConfidence > 0.6 && (
                              <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                                Auto-detected: {exportDocumentTypes.find(d => d.value === file.detectedType)?.label || file.detectedType}
                                {file.detectedConfidence >= 0.8 && " ✓"}
                              </Badge>
                            )}
                          </div>

                          {file.relevanceWarning && (
                            <div className="flex items-start gap-2 p-2 rounded bg-amber-50 border border-amber-200">
                              <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                              <span className="text-xs text-amber-700">{file.relevanceWarning}</span>
                            </div>
                          )}

                          <div className="flex items-center gap-2 flex-wrap">
                            <Label className="text-xs text-muted-foreground whitespace-nowrap">
                              Document Type:
                            </Label>
                            <Select
                              value={file.documentType ?? "other"}
                              onValueChange={(value) => updateFileDocumentType(file.id, value)}
                            >
                              <SelectTrigger className={cn("h-7 text-xs w-48", showDocTypeErrors && !file.documentType && "border-destructive focus-visible:ring-destructive", file.relevanceWarning && "border-amber-300")}>
                                <SelectValue placeholder="Select type" />
                              </SelectTrigger>
                              <SelectContent className="max-h-80 overflow-y-auto">
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground bg-muted/50">Core Documents</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.CORE).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.icon} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Transport Documents</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.TRANSPORT).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.icon} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Inspection & Quality</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.INSPECTION).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.icon} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Health & Agricultural</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.HEALTH).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.icon} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Financial Documents</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.FINANCIAL).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.icon} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Customs & Trade</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.CUSTOMS).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.icon} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Other</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.OTHER).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.icon} {t.label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            {showDocTypeErrors && !file.documentType && <p className="text-xs text-destructive">Select the correct document category.</p>}
                          </div>
                        </div>
                      )}
                      
                      {file.status === "error" && <p className="text-xs text-destructive">Upload failed</p>}
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={() => handlePreviewFile(file)} disabled={file.status === "uploading"} title="Preview file">
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => removeFile(file.id)} disabled={file.status === "uploading"}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Validation Section */}
        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle>Document Validation</CardTitle>
            <CardDescription>
              Validate your LC and trade documents for compliance and completeness
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Summary */}
              <div className="bg-secondary/20 rounded-lg p-4 border border-gray-200/50">
                <h4 className="font-semibold text-foreground mb-3">Upload Summary</h4>
                <div className="grid md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">LC Number:</span>
                    <p className="font-medium">{lcNumber || "Not provided"}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Supporting Documents:</span>
                    <p className="font-medium">{completedFiles.length} files uploaded</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Total Size:</span>
                    <p className="font-medium">
                      {formatFileSize(completedFiles.reduce((acc, file) => acc + file.size, 0))}
                    </p>
                  </div>
                </div>
              </div>

              {/* Process Button */}
              <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  {isLCResolved && requirementUploadStatus.missing.length > 0 && completedFiles.length > 0 ? (
                    <span>
                      Missing LC-required uploads: {requirementUploadStatus.missing.map((item) => item.label).join(', ')}.
                      You can still validate the current set, but readiness will stay open until they are uploaded.
                    </span>
                  ) : isReadyToProcess ? (
                    <span className="text-success">✓ Ready to validate your export documents</span>
                  ) : isLCResolved && completedFiles.length === 0 ? (
                    <span>LC resolved. Upload at least one supporting document to start validation.</span>
                  ) : isLCResolved ? (
                    <span>Supporting documents are uploaded. Complete any remaining uploads or review your set before validation.</span>
                  ) : (
                    <span>Upload and resolve the LC first to unlock supporting-document validation.</span>
                  )}
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex gap-3">
                    <Button
                      variant="outline"
                      onClick={handleSaveDraft}
                      disabled={isLoadingDraft}
                    >
                      {currentDraftId ? "Update Draft" : "Save Draft"}
                    </Button>
                    <Button
                      onClick={handleProcessLC}
                      disabled={!isReadyToProcess || !quotaState.canValidate}
                      className="hover:opacity-90 bg-gradient-exporter"
                    >
                      {isValidationProcessing ? (
                        <>
                          <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                          Extracting...
                        </>
                      ) : (
                        "Extract & Review"
                      )}
                    </Button>
                  </div>
                </div>
              </div>

              {isValidationProcessing && (
                <ValidationProgressIndicator
                  fileCount={completedFiles.length}
                  realProgress={validationProgress}
                />
              )}

              <LcopilotQuotaBanner quotaState={quotaState} variant="exporter" />

              {showRateLimit && (
                <div className="mt-6">
                  <RateLimitNotice
                    onRetry={() => {
                      setShowRateLimit(false);
                      handleProcessLC();
                    }}
                    onCancel={() => setShowRateLimit(false)}
                  />
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Inline extraction review — appears below the upload card once
            the extract_only call has returned. User stays on this page;
            clicking Start Validation inside ExtractionReview navigates to
            the results section via onStartValidation. */}
        {extractionPayload && (
          <div id="extraction-review-inline" className="mt-8">
            <ExtractionReview
              extractionPayload={extractionPayload}
              jobId={extractionPayload?.jobId || extractionPayload?.job_id}
              lcNumber={lcNumber.trim()}
              onStartValidation={({ jobId }) => {
                // After Start Validation completes the resume call, route
                // the user into the reviews section of the dashboard.
                if (embedded && onComplete) {
                  onComplete({ jobId, lcNumber: lcNumber.trim() });
                } else {
                  const params = new URLSearchParams({
                    section: 'reviews',
                    jobId,
                    lc: lcNumber.trim(),
                  });
                  navigate(`/lcopilot/exporter-dashboard?${params.toString()}`);
                }
              }}
              onBackToUpload={() => {
                setExtractionPayload(null);
                const uploadEl = document.querySelector('h3');
                if (uploadEl) uploadEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }}
            />
          </div>
        )}
        </div>
      )}

      {/* Blocked Upload Modal - Shows when LC type mismatch or no LC found */}
      <BlockedUploadModal
        open={blockedModal.open}
        onClose={() => setBlockedModal({ open: false })}
        blockReason={blockedModal.blockReason}
        error={blockedModal.error}
        detectedDocuments={blockedModal.detectedDocuments}
        lcDetection={blockedModal.lcDetection}
      />
      <QuotaLimitModal
        open={showQuotaModal}
        onClose={() => setShowQuotaModal(false)}
        message={quotaError?.message ?? 'Your validation quota has been reached.'}
        quota={quotaError?.quota}
        nextActionUrl={quotaError?.nextActionUrl}
      />
    </div>
  );
}

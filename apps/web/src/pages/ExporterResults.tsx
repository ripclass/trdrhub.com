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
  BarChart3,
  TrendingUp,
  PieChart,
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
import { useJob, useResults } from "@/hooks/use-lcopilot";
import type { ValidationResults, IssueCard, AIEnrichmentPayload, ReferenceIssue } from "@/types/lcopilot";
import { isExporterFeatureEnabled } from "@/config/exporterFeatureFlags";
import { ExporterIssueCard } from "@/components/exporter/ExporterIssueCard";
// LcHeader removed - LC info now shown inline in SummaryStrip
// RiskPanel removed - action items now only in Issues tab
import SummaryStrip from "@/components/lcopilot/SummaryStrip";
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
import { DEFAULT_TAB, isResultsTab, type ResultsTab } from "@/components/lcopilot/dashboardTabs";
import { cn } from "@/lib/utils";
import { BlockedValidationCard } from "@/components/validation/ValidationStatusBanner";
import { deriveValidationState } from "@/lib/validation/validationState";

type ExporterResultsProps = {
  embedded?: boolean;
  jobId?: string;
  lcNumber?: string;
  initialTab?: ResultsTab;
  onTabChange?: (tab: ResultsTab) => void;
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
  
  const { jobStatus, isPolling: isPollingJob, error: jobError } = useJob(validationSessionId);
  const { getResults, isLoading: resultsLoading, error: resultsError, results: cachedResults } = useResults();
  const fetchedOnceRef = useRef(false);
  const lastFetchedJobIdRef = useRef<string | null>(null);
  const [liveResults, setLiveResults] = useState<ValidationResults | null>(null);
  const [resultsErrorState, setResultsErrorState] = useState<string | null>(null);
  
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
  
  useEffect(() => {
    setLiveResults(null);
    setResultsErrorState(null);
    fetchedOnceRef.current = false;
    lastFetchedJobIdRef.current = null;
    if (validationSessionId) {
      resultsLogger.debug('Reset results state for session change', { validationSessionId });
    }
  }, [validationSessionId]);

  const fetchResults = useCallback(
    async (source: 'auto' | 'manual', sessionOverride?: string) => {
      const targetId = sessionOverride ?? validationSessionId;
      if (!targetId) {
        resultsLogger.debug('Skip results fetch: missing session id');
        return;
      }

      fetchedOnceRef.current = true;
      lastFetchedJobIdRef.current = targetId;
      resultsLogger.debug('Fetching results', { validationSessionId: targetId, source });

      try {
        const data = await getResults(targetId);
        resultsLogger.debug('Results received', { validationSessionId: targetId });
        setLiveResults(data);
        setResultsErrorState(null);
      } catch (e: any) {
        resultsLogger.warn('Results fetch failed', { validationSessionId: targetId, error: e?.message });
        fetchedOnceRef.current = false; // allow manual retry
        lastFetchedJobIdRef.current = null;
        setResultsErrorState(e?.message || 'Failed to load validation results.');
        throw e;
      }
    },
    [getResults, validationSessionId],
  );

  // Auto-fetch results when job reaches terminal state
  useEffect(() => {
    const normalizedStatus = (jobStatus?.status || '').toString().toLowerCase();
    const isTerminal =
      normalizedStatus === 'completed' || normalizedStatus === 'failed' || normalizedStatus === 'error';
    const alreadyFetched = fetchedOnceRef.current && lastFetchedJobIdRef.current === validationSessionId;

    if (!validationSessionId) return;

    // If job status is not available yet, wait for it (but don't block forever)
    if (!normalizedStatus && !jobStatus) {
      resultsLogger.debug('Waiting for job status', { validationSessionId });
      return;
    }

    // If we have a status but it's not terminal, wait
    if (normalizedStatus && !isTerminal) {
      resultsLogger.debug('Job not terminal', { validationSessionId, status: normalizedStatus });
      return;
    }

    // If job is terminal, fetch results
    if (isTerminal) {
      if (resultsLoading || alreadyFetched) return;

      resultsLogger.debug('Fetching results triggered', { validationSessionId, status: normalizedStatus });
      
      fetchResults('auto', validationSessionId)
        .then(() => resultsLogger.debug('Results fetch success'))
        .catch((err) => resultsLogger.error('Results fetch error', err));
    }
  }, [validationSessionId, jobStatus?.status, resultsLoading, fetchResults, jobStatus]);

  // Fallback: If we have a jobId but no jobStatus after 3 seconds, try fetching results anyway
  // (This handles the case where the job is already completed when component mounts)
  useEffect(() => {
    if (!validationSessionId) return;
    if (fetchedOnceRef.current) return;
    if (resultsLoading) return;
    if (jobStatus?.status) return; // If we have status, the main effect handles it

    const timeoutId = setTimeout(() => {
      resultsLogger.debug('Fallback fetch triggered', { validationSessionId });
      fetchResults('auto', validationSessionId)
        .then(() => resultsLogger.debug('Fallback fetch success'))
        .catch((err) => resultsLogger.warn('Fallback fetch error', err));
    }, 3000);

    return () => clearTimeout(timeoutId);
  }, [validationSessionId, fetchResults, jobStatus, resultsLoading]);

  // Minimal terminal guard to force network call in case any guard above is bypassed
  useEffect(() => {
    const st = (jobStatus?.status || '').toLowerCase();
    const terminal = ['completed', 'failed', 'error'];
    const jobId = validationSessionId;

    if (!jobId || !terminal.includes(st)) return;

    resultsLogger.debug('Terminal guard fetch', { jobId, status: st });
    fetchResults('auto', jobId)
      .then(() => resultsLogger.debug('Terminal guard fetch success'))
      .catch((err) => resultsLogger.error('Terminal guard fetch error', err));
  }, [jobStatus?.status, validationSessionId, fetchResults]);

  const [activeTab, setActiveTab] = useState<ResultsTab>(initialTab ?? tabParam ?? DEFAULT_TAB);
  const [showBankSelector, setShowBankSelector] = useState(false);
  const [showManifestPreview, setShowManifestPreview] = useState(false);
  const [selectedBankId, setSelectedBankId] = useState<string>("");
  const [selectedBankName, setSelectedBankName] = useState<string>("");
  const [submissionNote, setSubmissionNote] = useState<string>("");
  const [manifestConfirmed, setManifestConfirmed] = useState(false);
  const [manifestData, setManifestData] = useState<CustomsPackManifest | null>(null);
  const [issueFilter, setIssueFilter] = useState<"all" | "critical" | "major" | "minor">("all");
  const [showRawLcJson, setShowRawLcJson] = useState(false);
  
  const resultData = liveResults ?? cachedResults;

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
  
  const { data: guardrails, isLoading: guardrailsLoading } = useQuery({
    queryKey: ['exporter-guardrails', validationSessionId, resolvedLcNumber],
    queryFn: () => exporterApi.checkGuardrails({ validation_session_id: validationSessionId, lc_number: resolvedLcNumber }),
    enabled: !!validationSessionId && !!resolvedLcNumber && enableBankSubmission,
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
  const summary = structuredResult?.processing_summary;
  const lcStructured = structuredResult?.lc_structured ?? null;
  const extractionStatus = useMemo(() => {
    // Check document-level extraction statuses first
    const docStatuses = structuredDocumentsPayload.map(
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
  }, [summary, structuredDocumentsPayload, lcStructured]);
  const documents = useMemo(() => {
    return structuredDocumentsPayload.map((doc, index) => {
      const docAny = doc as Record<string, any>;
      const documentId = String(doc.document_id ?? docAny.id ?? index);
      const filename = doc.filename ?? docAny.name ?? `Document ${index + 1}`;
      const typeKeyRaw = doc.document_type ?? docAny.type ?? "supporting_document";
      const typeKey = (typeKeyRaw || "supporting_document").toString();
      // Check multiple keys - backend sends discrepancyCount (camelCase)
      const issuesCount = Number(doc.discrepancyCount ?? doc.issues_count ?? docAny.discrepancyCount ?? docAny.issues ?? docAny.discrepancy_count ?? 0);
      const extractionStatus = (doc.extraction_status ?? docAny.extractionStatus ?? "unknown").toString().toLowerCase();
      const status: "success" | "warning" | "error" = (() => {
        if (extractionStatus === "error") return "error";
        if (extractionStatus === "partial" || extractionStatus === "pending") return "warning";
        const exempt = ["letter_of_credit", "insurance_certificate"];
        if (issuesCount > 0 && !exempt.includes(typeKey)) return "warning";
        return "success";
      })();
      // Ensure type is always a string to prevent React Error #31
      const typeLabel = DOCUMENT_LABELS[typeKey] ?? humanizeLabel(typeKey);
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
        extractedFields: doc.extracted_fields ?? docAny.extractedFields ?? {},
      };
    });
  }, [structuredDocumentsPayload]);
  resultsLogger.debug('Documents loaded', { count: documents.length });
  const issueCards = resultData?.issues ?? [];
  const analyticsData = resultData?.analytics ?? null;
  const timelineEvents = resultData?.timeline ?? [];
  const totalDocuments = summary?.total_documents ?? documents.length ?? 0;
  // Use the higher of summary.total_issues or actual issueCards.length
  // This ensures we show the correct count even if backend summary is stale
  const totalDiscrepancies = Math.max(summary?.total_issues ?? 0, issueCards.length);
  const severityBreakdown = summary?.severity_breakdown ?? {
    critical: 0,
    major: 0,
    medium: 0,
    minor: 0,
  };
  const extractedDocumentsMap = useMemo(() => {
    const map: Record<string, any> = {};
    structuredDocumentsPayload.forEach((doc, idx) => {
      const docAny = doc as Record<string, any>;
      const key = doc.document_type || doc.filename || `doc_${idx}`;
      map[key] = doc.extracted_fields ?? docAny.extractedFields ?? {};
    });
    return map;
  }, [structuredDocumentsPayload]);
  const extractedDocuments = useMemo(
    () =>
      structuredDocumentsPayload.map((doc) => ({
        filename: doc.filename,
        name: doc.filename,
        document_type: doc.document_type,
        extraction_status: doc.extraction_status,
        extractionStatus: doc.extraction_status,
        extracted_fields: doc.extracted_fields ?? {},
        extractedFields: doc.extracted_fields ?? {},
      })),
    [structuredDocumentsPayload],
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
  const lcGoodsItems = lcData && Array.isArray(lcData.goods_items) ? lcData.goods_items : [];
  const lcApplicantCard = lcData ? renderPartyCard("Applicant", lcData.applicant, "lc-applicant") : null;
  const lcBeneficiaryCard = lcData ? renderPartyCard("Beneficiary", lcData.beneficiary, "lc-beneficiary") : null;
  const lcPortsCard = lcData ? renderPortsCard(lcData.ports) : null;
  const lcGoodsItemsList = lcData ? renderGoodsItemsList(lcGoodsItems) : null;
  const lcAdditionalConditions = lcData?.additional_conditions;
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
  // LC Type can be: export, import, sight, usance, deferred, or unknown
  // Check both top-level and lc_structured for these values (backend stores in lc_structured)
  const lcStructuredData = structuredResult?.lc_structured as Record<string, any> | null;
  const rawLcType = structuredResult?.lc_type ?? lcStructuredData?.lc_type ?? "unknown";
  const lcType = rawLcType.toLowerCase() as string;
  const lcTypeReason = structuredResult?.lc_type_reason ?? lcStructuredData?.lc_type_reason ?? "LC type detection details unavailable.";
  // Get confidence from lc_structured (where backend actually stores it)
  const rawConfidence = structuredResult?.lc_type_confidence ?? lcStructuredData?.lc_type_confidence;
  const lcTypeConfidenceValue =
    typeof rawConfidence === "number"
      ? Math.round(rawConfidence * 100)
      : null;
  const lcTypeSource = structuredResult?.lc_type_source ?? lcStructuredData?.lc_type_source ?? "auto";
  const lcTypeLabelMap: Record<string, string> = {
    export: "Export LC",
    import: "Import LC",
    sight: "Sight LC",
    usance: "Usance LC",
    deferred: "Deferred Payment LC",
    transferable: "Transferable LC",
    standby: "Standby LC",
    irrevocable: "Irrevocable LC",
    unknown: "Unknown",
  };
  const lcTypeLabel = lcTypeLabelMap[lcType] ?? lcType.charAt(0).toUpperCase() + lcType.slice(1) + " LC";

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
          const severity = normalizeDiscrepancySeverity(card.severity);
          acc[severity] = (acc[severity] || 0) + 1;
          return acc;
        },
        { critical: 0, major: 0, minor: 0 } as Record<"critical" | "major" | "minor", number>
      ),
    [issueCards]
  );
  const filteredIssueCards = useMemo(() => {
    if (issueFilter === "all") return issueCards;
    return issueCards.filter(
      (card) => normalizeDiscrepancySeverity(card.severity) === issueFilter
    );
  }, [issueCards, issueFilter]);
  const showSkeletonLayout = Boolean(
    validationSessionId && !resultData && resultsLoading && !(jobError || resultsError || resultsErrorState),
  );
  const { successCount, errorCount, warningCount, successRate } = useMemo(() => {
    const derivedSuccessCount = documents.filter((doc) => doc.status === "success").length;
    const summarySuccessCount =
      typeof summary?.successful_extractions === "number" ? summary.successful_extractions : undefined;
    const resolvedSuccessCount =
      derivedSuccessCount > 0 ? derivedSuccessCount : summarySuccessCount ?? derivedSuccessCount;

    const resolvedErrorCount =
      typeof summary?.failed_extractions === "number"
        ? summary.failed_extractions
        : documents.filter((doc) => (doc.status ?? "").toLowerCase() === "error").length;

    const resolvedWarningCount =
      typeof documentStatusCounts.warning === "number"
        ? documentStatusCounts.warning
        : documents.filter((doc) => doc.status === "warning").length;

    const resolvedSuccessRate =
      totalDocuments > 0 ? Math.round((resolvedSuccessCount / totalDocuments) * 100) : 0;

    return {
      successCount: resolvedSuccessCount,
      errorCount: resolvedErrorCount,
      warningCount: resolvedWarningCount,
      successRate: resolvedSuccessRate,
    };
  }, [
    documents,
    summary?.successful_extractions,
    summary?.failed_extractions,
    documentStatusCounts.warning,
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
  const extractionAccuracy = useMemo(() => successRate, [successRate]);
  const customsReadyScore = useMemo(
    () => Math.max(0, complianceScore - warningCount * 5),
    [complianceScore, warningCount],
  );
  const performanceInsights = useMemo(
    () => [
      successCount + "/" + (totalDocuments || 0) + " documents extracted successfully",
      totalDiscrepancies + " issue" + (totalDiscrepancies === 1 ? "" : "s") + " detected",
      "Compliance score " + complianceScore + "%",
    ],
    [successCount, totalDocuments, totalDiscrepancies, complianceScore],
  );
  const overallStatus = errorCount > 0 ? "error" : warningCount > 0 || totalDiscrepancies > 0 ? "warning" : "success";
  const customsPack = structuredResult?.customs_pack;
  const packGenerated = customsPack?.ready ?? false;
  const processingSummaryExtras = structuredResult?.processing_summary as Record<string, any> | undefined;
  const analyticsExtras = structuredResult?.analytics as Record<string, any> | undefined;
  const processingTime =
    processingSummaryExtras?.processing_time_display ||
    analyticsExtras?.processing_time_display ||
    "-";
  const isReadyToSubmit = useMemo(() => {
    if (!enableBankSubmission) return false;
    if (guardrailsLoading) return false;
    if (!guardrails) {
      return totalDiscrepancies === 0;
    }
    return guardrails.can_submit && guardrails.high_severity_discrepancies === 0;
  }, [enableBankSubmission, guardrails, guardrailsLoading, totalDiscrepancies]);

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

    if (jobError || resultsError || resultsErrorState) {
      const errorMessage =
        jobError?.message ||
        resultsErrorState ||
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
    
    // Show placeholder when issues exist but no AI insights (feature not enabled)
    if (hasIssueCards && !aiInsights) {
      return (
        <Card className="shadow-soft border border-dashed border-muted-foreground/30 bg-muted/20">
          <CardContent className="py-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-muted">
                <Lightbulb className="w-6 h-6 text-muted-foreground" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-sm text-muted-foreground">AI Risk Insights Available</p>
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  Enable AI enrichment to get context-aware explanations, fix suggestions, and UCP600/ISBP745 references for your {issueCards.length} issue{issueCards.length !== 1 ? 's' : ''}.
                </p>
              </div>
              <Badge variant="outline" className="text-xs">
                Enterprise Feature
              </Badge>
            </div>
          </CardContent>
        </Card>
      );
    }
    
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
      // First generate if not already generated
      if (!manifestData) {
        await generateCustomsPackMutation.mutateAsync();
      }
      // Then download
      await downloadCustomsPackMutation.mutateAsync();
    } catch (error) {
      // Error handling is done in mutations
    }
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
                  onClick={() => fetchResults('manual')}
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
            lcTypeConfidence={lcTypeConfidenceValue}
            packGenerated={packGenerated}
            overallStatus={overallStatus}
            actualIssuesCount={issueCards.length}
            complianceScore={complianceScore}
          />
          
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
          {structuredResult?.bank_verdict && (
            <BankVerdictCard verdict={structuredResult.bank_verdict as BankVerdict} />
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
          <TabsList className="grid w-full grid-cols-7 md:grid-cols-7">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="documents">Documents ({totalDocuments})</TabsTrigger>
            <TabsTrigger value="discrepancies" className="relative">
              Issues ({totalDiscrepancies})
              {totalDiscrepancies > 0 && (
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-warning rounded-full"></div>
              )}
            </TabsTrigger>
            <TabsTrigger value="extracted-data">Extracted Data</TabsTrigger>
            <TabsTrigger value="history">Submission History</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
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
            <div className={cn("grid gap-6", hasTimeline ? "md:grid-cols-2" : "md:grid-cols-1")}>
              {hasTimeline && (
                <Card className="shadow-soft border border-border/60">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg font-semibold flex items-center gap-2">
                      <Clock className="w-5 h-5" />
                      Export Processing Timeline
                    </CardTitle>
                    <CardDescription className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      Real-time processing journey
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
              {/* Export Statistics */}
              <Card className="shadow-soft border border-border/60">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-semibold">Export Document Statistics</CardTitle>
                  <CardDescription className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    Validation health
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-success/5 border border-success/20 rounded-lg">
                      <div className="text-2xl font-bold text-success">{successCount}</div>
                      <div className="text-sm text-muted-foreground">Verified</div>
                    </div>
                    <div className="text-center p-3 bg-warning/5 border border-warning/20 rounded-lg">
                      <div className="text-2xl font-bold text-warning">{totalDiscrepancies}</div>
                      <div className="text-sm text-muted-foreground">Warnings</div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>LC Compliance:</span>
                      <span className={`font-medium ${successRate >= 90 ? 'text-success' : 'text-warning'}`}>
                        {successRate}%
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Customs Ready:</span>
                      <span className={`font-medium ${customsReadyScore >= 90 ? 'text-success' : 'text-warning'}`}>
                        {customsReadyScore >= 90 ? 'Yes' : 'Review'}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Bank Ready:</span>
                      <span className={`font-medium ${overallStatus === 'success' ? 'text-success' : 'text-warning'}`}>
                        {overallStatus === 'success' ? 'Ready' : 'Review needed'}
                      </span>
                    </div>
                  </div>
                  {packGenerated && (
                    <div className="p-3 bg-primary/5 border border-primary/20 rounded-lg">
                      <p className="text-sm font-medium text-primary">Customs-Ready Pack Generated</p>
                      <p className="text-xs text-muted-foreground mt-1">All documents bundled for smooth customs clearance</p>
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
                        : "Generate your customs pack after resolving issues."}
                    </p>
                  </div>
                  <div className="p-4 rounded-lg border border-border/60 space-y-2">
                    <p className="text-xs uppercase text-muted-foreground tracking-wide">Readiness</p>
                    <div className="flex items-center gap-3">
                      <div className="text-2xl font-semibold">{customsReadyScore}%</div>
                      <Badge variant="outline">Customs Ready Score</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Derived from structured_result.analytics.customs_ready_score
                    </p>
                  </div>
                  <div className="p-4 rounded-lg border border-border/60 space-y-2">
                    <p className="text-xs uppercase text-muted-foreground tracking-wide">Actions</p>
                    <div className="flex flex-col gap-2">
                      {/* Always show Generate button */}
                      <Button
                        size="sm"
                        className="w-full"
                        onClick={() => generateCustomsPackMutation.mutate()}
                        disabled={generateCustomsPackMutation.isPending}
                      >
                        {generateCustomsPackMutation.isPending ? "Generating..." : packGenerated ? "Re-generate Pack" : "Generate Customs Pack"}
                      </Button>
                      {/* Show Download when pack exists */}
                      {packGenerated && (
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

                <div className="space-y-3">
                  <p className="text-sm font-semibold">Manifest</p>
                  {manifestData ? (
                    <div className="rounded-lg border border-border/60 p-4 space-y-2">
                      <div className="flex items-center justify-between text-sm text-muted-foreground">
                        <span>LC Number</span>
                        <span className="font-medium text-foreground">{manifestData.lc_number}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm text-muted-foreground">
                        <span>Generated</span>
                        <span className="font-medium text-foreground">
                          {format(new Date(manifestData.generated_at), "MMM d, yyyy HH:mm")}
                        </span>
                      </div>
                      <div className="space-y-2">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Documents</p>
                        <ul className="divide-y divide-border/60 rounded-lg border border-border/60">
                          {manifestData.documents.map((doc, idx) => (
                            <li key={`${doc.name}-${idx}`} className="flex items-center justify-between px-3 py-2 text-sm">
                              <span className="font-medium">{doc.name}</span>
                              <Badge variant="outline">{safeString(doc.type)}</Badge>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ) : (
                    <Card className="border-dashed">
                      <CardContent className="py-6 text-sm text-muted-foreground">
                        Generate a customs pack to view the manifest.
                      </CardContent>
                    </Card>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="documents" className="space-y-4">
            {documents.map((document) => {
              const fieldEntries = Object.entries(document.extractedFields || {});
              const hasFieldEntries = fieldEntries.length > 0;
              const discrepancyCount = document.issuesCount ?? 0;
              
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
                        {discrepancyCount === 0 ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
                            <CheckCircle className="w-3.5 h-3.5" />
                            Verified
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            {discrepancyCount === 1 ? 'Minor Issues' : `${discrepancyCount} Issues`}
                          </span>
                        )}
                        <Button variant="outline" size="sm">
                          <Eye className="w-4 h-4 mr-2" />
                          View
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
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
                            {lcAdditionalConditions && (
                              <div>
                                <p className="text-sm font-semibold mb-2">Additional Conditions (47A)</p>
                                <ul className="text-sm space-y-1.5 list-disc list-inside">
                                  {formatConditions(lcAdditionalConditions).map((condition, idx) => (
                                    <li key={idx} className="text-muted-foreground">{condition}</li>
                                  ))}
                                </ul>
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
                        This document could not be fully parsed. Preview text is available for manual review.
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
              severityCounts={severityCounts}
              issueFilter={issueFilter}
              setIssueFilter={setIssueFilter}
              documentStatusMap={documentStatusMap}
              renderAIInsightsCard={renderAIInsightsCard}
              renderReferenceIssuesCard={renderReferenceIssuesCard}
            />
          </TabsContent>
          <TabsContent value="extracted-data" className="space-y-4">
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle>Extracted Document Data</CardTitle>
                <CardDescription>
                  Structured data extracted from your uploaded documents using OCR and text extraction.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Two-Stage Validation Summary */}
                {(() => {
                  // Get two-stage validation data from any document
                  const twoStageData = structuredResult?._two_stage_validation as { 
                    total_fields?: number; 
                    trusted?: number; 
                    review?: number; 
                    untrusted?: number;
                  } | undefined;
                  
                  if (twoStageData && typeof twoStageData.total_fields === 'number') {
                    const total = twoStageData.total_fields || 0;
                    const trusted = twoStageData.trusted || 0;
                    const review = twoStageData.review || 0;
                    const untrusted = twoStageData.untrusted || 0;
                    
                    return (
                      <div className="p-4 bg-gradient-to-r from-primary/5 to-primary/10 border border-primary/20 rounded-lg">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <ShieldCheck className="w-5 h-5 text-primary" />
                            <span className="font-semibold">Two-Stage Validation</span>
                          </div>
                          <Badge variant="outline" className="text-xs bg-primary/10 text-primary border-primary/30">
                            AI + Deterministic
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mb-3">
                          Fields are extracted by AI and then validated against reference data (ports, currencies, dates, etc.)
                        </p>
                        <div className="grid grid-cols-3 gap-3">
                          <div className="text-center p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                            <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{trusted}</div>
                            <div className="text-xs text-muted-foreground">Trusted</div>
                          </div>
                          <div className="text-center p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                            <div className="text-lg font-bold text-amber-600 dark:text-amber-400">{review}</div>
                            <div className="text-xs text-muted-foreground">Review</div>
                          </div>
                          <div className="text-center p-2 bg-red-500/10 rounded-lg border border-red-500/20">
                            <div className="text-lg font-bold text-red-600 dark:text-red-400">{untrusted}</div>
                            <div className="text-xs text-muted-foreground">Low Confidence</div>
                          </div>
                        </div>
                        {review > 0 || untrusted > 0 ? (
                          <p className="text-xs text-amber-600 dark:text-amber-400 mt-2 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            {review + untrusted} field(s) may need manual verification
                          </p>
                        ) : total > 0 ? (
                          <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            All extracted fields verified against reference data
                          </p>
                        ) : null}
                      </div>
                    );
                  }
                  return null;
                })()}
                
                {/* Extraction Status */}
                <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
                  <div className="font-semibold">Extraction Status:</div>
                  <Badge
                    variant={
                      extractionStatus === "success"
                        ? "default"
                        : extractionStatus === "partial"
                        ? "outline"
                        : extractionStatus === "pending"
                        ? "destructive"
                        : "secondary"
                    }
                  >
                    {extractionStatus || "unknown"}
                  </Badge>
                  {extractionStatus === "pending" && (
                    <p className="text-sm text-muted-foreground ml-2">
                      No text could be extracted from the documents. This may indicate scanned images that require OCR.
                    </p>
                  )}
                  {extractionStatus === "partial" && (
                    <p className="text-sm text-muted-foreground ml-2">
                      Some text was extracted, but structured fields could not be fully parsed.
                    </p>
                  )}
                  {extractionStatus === "error" && (
                    <p className="text-sm text-muted-foreground ml-2">
                      An error occurred during extraction. Please try uploading the documents again.
                    </p>
                  )}
                </div>

                {/* Extracted Data Display */}
                {lcData || Object.keys(extractedDocumentsMap).length > 0 ? (
                  <div className="space-y-4">
                    {lcData && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between gap-3 flex-wrap">
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold text-lg">Letter of Credit Data</h3>
                            {/* Source Format Badge */}
                            {(lcData as any)?._source_format && (
                              <Badge 
                                variant="outline" 
                                className={cn(
                                  "text-xs font-medium",
                                  (lcData as any)._source_format === "ISO20022" 
                                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                                    : (lcData as any)._source_format === "MT700"
                                    ? "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30"
                                    : "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/30"
                                )}
                              >
                                {(lcData as any)._source_format === "ISO20022" ? "📄 ISO 20022" 
                                  : (lcData as any)._source_format === "MT700" ? "📨 SWIFT MT700" 
                                  : "📷 PDF/OCR"}
                              </Badge>
                            )}
                            {(lcData as any)?._source_message_type && (
                              <span className="text-xs text-muted-foreground">
                                ({(lcData as any)._source_message_type})
                              </span>
                            )}
                          </div>
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
                          {lcAdditionalConditions && (
                            <div>
                              <p className="text-sm font-semibold mb-2">Additional Conditions (47A)</p>
                              <ul className="text-sm space-y-1.5 list-disc list-inside">
                                {formatConditions(lcAdditionalConditions).map((condition, idx) => (
                                  <li key={idx} className="text-muted-foreground">{condition}</li>
                                ))}
                              </ul>
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
                    )}

                    {Object.entries(extractedDocumentsMap)
                      .filter(([key]) => key !== "letter_of_credit" && key !== "lc")
                      .map(([key, value]) => renderGenericExtractedSection(key, value))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground mb-2">No extracted data available</p>
                    <p className="text-sm text-muted-foreground">
                      {extractionStatus === "pending"
                        ? "The documents may be scanned images that require OCR processing. Please ensure OCR is enabled in the system settings."
                        : "Data extraction may still be in progress or failed. Please check the extraction status above."}
                    </p>
                  </div>
                )}

                {/* Per-document OCR summary */}
                {extractedDocuments.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="font-semibold text-lg">Document OCR Overview</h3>
                    <div className="grid gap-4 md:grid-cols-2">
                      {extractedDocuments.map((doc, index) => {
                        const cardTitle = doc.filename || doc.name || `Document ${index + 1}`;
                        const docType = (doc.document_type || "supporting_document").toString().replace(/_/g, " ");
                        const extractionStatus = doc.extraction_status || "unknown";
                        const fieldEntries = Object.entries(doc.extracted_fields || {});

                        // Check for eBL or source format
                        const sourceFormat = (doc.extracted_fields as any)?._source_format;
                        const isElectronicBL = (doc.extracted_fields as any)?._is_electronic_bl;
                        
                        return (
                          <div key={`${cardTitle}-${index}`} className="border rounded-lg p-4 space-y-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <div>
                                  <p className="font-semibold">{cardTitle}</p>
                                  <p className="text-xs text-muted-foreground capitalize">{docType}</p>
                                </div>
                                {/* Source Format Badge (eBL indicator) */}
                                {sourceFormat && (
                                  <Badge 
                                    variant="outline" 
                                    className={cn(
                                      "text-xs font-medium ml-2",
                                      isElectronicBL
                                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                                        : sourceFormat.includes("ISO20022")
                                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                                        : sourceFormat.includes("MT")
                                        ? "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30"
                                        : "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/30"
                                    )}
                                    title={isElectronicBL ? "Electronic Bill of Lading - 100% accuracy" : ""}
                                  >
                                    {isElectronicBL ? "🔗 " : ""}{sourceFormat}
                                  </Badge>
                                )}
                              </div>
                              <Badge
                                variant={
                                  extractionStatus === "success"
                                    ? "default"
                                    : extractionStatus === "empty"
                                    ? "destructive"
                                    : "secondary"
                                }
                              >
                                {extractionStatus}
                              </Badge>
                            </div>

                            {fieldEntries.length > 0 ? (
                              <div className="space-y-2 text-sm">
                                {fieldEntries
                                  // Filter out internal/technical fields that aren't user-friendly
                                  .filter(([key]) => !['mt700', 'mt700_raw', 'source', 'timeline', 'blocks', 'raw', 
                                    '_extraction_confidence', '_extraction_method', '_ai_provider', '_ai_confidence',
                                    'lc_type_source', 'lc_classification'].includes(key))
                                  .map(([key, value]) => (
                                  <div key={key} className="flex flex-col">
                                    <span className="text-xs text-muted-foreground uppercase tracking-wide">
                                      {key.replace(/([A-Z_])/g, " $1").replace(/_/g, " ").trim()}
                                    </span>
                                    <span className="font-medium whitespace-pre-wrap break-words">
                                      {formatExtractedValue(value)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-xs text-muted-foreground">
                                No structured fields extracted for this document. OCR text is still available for
                                AI-assisted explanations.
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="history" className="space-y-6">
            <HistoryTab
              submissionsLoading={submissionsLoading}
              submissionsData={submissionsData}
              validationSessionId={validationSessionId || ''}
            />
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <AnalyticsTab
              analyticsAvailable={analyticsAvailable}
              extractionAccuracy={extractionAccuracy}
              lcComplianceScore={lcComplianceScore}
              customsReadyScore={customsReadyScore}
              processingTime={processingTime}
              totalDocuments={totalDocuments}
              successCount={successCount}
              warningCount={warningCount}
              errorCount={errorCount}
              performanceInsights={performanceInsights}
              documentProcessingList={documentProcessingList}
              documents={documents}
            />
          </TabsContent>
        </Tabs>

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
      </div>
    </div>
  );
}

// SubmissionHistoryCard is now imported from ./exporter/results

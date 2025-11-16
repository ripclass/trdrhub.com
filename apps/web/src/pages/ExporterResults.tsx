import { useState, useEffect, useMemo, useRef } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/ui/status-badge";
import { DiscrepancyGuidance } from "@/components/discrepancy/DiscrepancyGuidance";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
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
  Lightbulb
} from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { format } from "date-fns";
import { exporterApi, type BankSubmissionRead, type SubmissionEventRead, type GuardrailCheckResponse, type CustomsPackManifest } from "@/api/exporter";
import { useJob, useResults, type ValidationResults } from "@/hooks/use-lcopilot";
import { isExporterFeatureEnabled } from "@/config/exporterFeatureFlags";

// Mock exporter results
const mockExporterResults = {
  lcNumber: "EXP-BD-2024-001",
  status: "completed",
  processedAt: "2024-01-15T14:30:00Z",
  processingTime: "1.8 minutes",
  totalDocuments: 6,
  totalDiscrepancies: 1,
  overallStatus: "warning" as "success" | "error" | "warning",
  packGenerated: true,
  documents: [
    {
      id: "1",
      name: "Letter_of_Credit.pdf",
      type: "Letter of Credit",
      status: "success" as const,
      discrepancies: 0,
      extractedFields: {
        lcNumber: "LC-2024-BD-001",
        beneficiary: "Bangladesh Exports Ltd",
        amount: "USD 50,000",
        expiryDate: "2024-02-15"
      }
    },
    {
      id: "2", 
      name: "Commercial_Invoice.pdf",
      type: "Commercial Invoice",
      status: "warning" as const,
      discrepancies: 1,
      extractedFields: {
        invoiceNumber: "INV-2024-001",
        invoiceDate: "2024-01-08",
        totalAmount: "USD 50,000",
        buyer: "German Import GmbH"
      }
    },
    {
      id: "3",
      name: "Packing_List.pdf", 
      type: "Packing List",
      status: "success" as const,
      discrepancies: 0,
      extractedFields: {
        totalPackages: "100 cartons",
        grossWeight: "2500 KG",
        netWeight: "2300 KG",
        dimensions: "120x80x60 cm"
      }
    },
    {
      id: "4",
      name: "Bill_of_Lading.pdf",
      type: "Bill of Lading", 
      status: "success" as const,
      discrepancies: 0,
      extractedFields: {
        blNumber: "BL-2024-001",
        vessel: "MV Bangladesh Express",
        portOfLoading: "Chittagong",
        portOfDischarge: "Hamburg"
      }
    },
    {
      id: "5",
      name: "Certificate_of_Origin.pdf",
      type: "Certificate of Origin",
      status: "success" as const, 
      discrepancies: 0,
      extractedFields: {
        originCountry: "Bangladesh",
        issuingAuthority: "BGMEA",
        certificateNumber: "COO-2024-001",
        exporterName: "Bangladesh Exports Ltd"
      }
    },
    {
      id: "6",
      name: "GSP_Certificate.pdf",
      type: "GSP Certificate",
      status: "success" as const, 
      discrepancies: 0,
      extractedFields: {
        gspNumber: "GSP-BD-001",
        issuingCountry: "Bangladesh",
        beneficiaryCountry: "Germany",
        productDescription: "Cotton T-shirts"
      }
    }
  ],
  discrepancies: [
    {
      id: "1",
      documentId: "2",
      documentName: "Commercial_Invoice.pdf",
      severity: "medium" as const,
      rule: "LC Terms Compliance",
      title: "Product Description Variation",
      description: "Product description in invoice slightly differs from LC terms. May cause bank discrepancy.",
      suggestion: "Ensure product description exactly matches LC terms or request LC amendment.",
      field: "productDescription",
      expected: "100% Cotton T-shirts, Size M-XL",
      actual: "Cotton T-shirts, Mixed sizes"
    }
  ]
};

type ExporterResultsProps = {
  embedded?: boolean;
};

const normalizeDiscrepancySeverity = (
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

export default function ExporterResults({ embedded = false }: ExporterResultsProps = {}) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const jobIdParam = searchParams.get('jobId');
  const sessionParam = searchParams.get('session');
  const validationSessionId = jobIdParam || sessionParam || null;
  const isDemoMode = searchParams.get('demo') === 'true';
  
  const { jobStatus, isPolling: isPollingJob, error: jobError } = useJob(validationSessionId);
  const { getResults, isLoading: resultsLoading, error: resultsError } = useResults();
  const [liveResults, setLiveResults] = useState<ValidationResults | null>(null);
  const [resultsErrorState, setResultsErrorState] = useState<string | null>(null);
  
  const lcNumberParam = searchParams.get('lc') || undefined;

  const formatExtractedValue = (value: any): string => {
    if (value === null || value === undefined) {
      return "N/A";
    }
    if (Array.isArray(value)) {
      return value.map((item) => formatExtractedValue(item)).join(", ");
    }
    if (typeof value === "object") {
      try {
        return JSON.stringify(value, null, 2);
      } catch {
        return String(value);
      }
    }
    return String(value);
  };
  
  useEffect(() => {
    setLiveResults(null);
    setResultsErrorState(null);
  }, [validationSessionId]);

  useEffect(() => {
    if (!validationSessionId) return;
    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const pollResults = async (attempt = 0) => {
      try {
        const data = await getResults(validationSessionId);
        if (cancelled) {
          return;
        }
        setLiveResults(data);
        setResultsErrorState(null);
      } catch (err: any) {
        if (cancelled) {
          return;
        }
        const statusCode = err?.statusCode;
        const retriable = statusCode === 404 || statusCode === 409;
        if (retriable && attempt < 15) {
          const delay = Math.min(2000 + attempt * 500, 8000);
          retryTimer = setTimeout(() => pollResults(attempt + 1), delay);
        } else {
          setResultsErrorState(err?.message || "Failed to load validation results.");
        }
      }
    };

    pollResults();

    return () => {
      cancelled = true;
      if (retryTimer) {
        clearTimeout(retryTimer);
      }
    };
  }, [validationSessionId, getResults]);

  const [activeTab, setActiveTab] = useState("overview");
  const [showBankSelector, setShowBankSelector] = useState(false);
  const [showManifestPreview, setShowManifestPreview] = useState(false);
  const [selectedBankId, setSelectedBankId] = useState<string>("");
  const [selectedBankName, setSelectedBankName] = useState<string>("");
  const [submissionNote, setSubmissionNote] = useState<string>("");
  const [manifestConfirmed, setManifestConfirmed] = useState(false);
  const [manifestData, setManifestData] = useState<CustomsPackManifest | null>(null);
  
  const effectiveResults = liveResults ?? (isDemoMode ? mockExporterResults : null);
  const resultData = effectiveResults;

  // Feature flags
  const enableBankSubmission = isExporterFeatureEnabled("exporter_bank_submission");
  const enableCustomsPackPDF = isExporterFeatureEnabled("exporter_customs_pack_pdf");
  
  // Guardrails check
  const fallbackResults = isDemoMode ? mockExporterResults : null;
  const resolvedResults = resultData ?? fallbackResults;
  const resolvedLcNumber =
    lcNumberParam ??
    resultData?.lcNumber ??
    liveResults?.lcNumber ??
    jobStatus?.lcNumber ??
    fallbackResults?.lcNumber ??
    null;
  const lcNumber = resolvedLcNumber ?? mockExporterResults.lcNumber;
  
  // Compute totalDiscrepancies early for use in isReadyToSubmit
  const totalDiscrepancies = resolvedResults?.discrepancies?.length ?? 0;
  const documents = resolvedResults?.documents ?? [];
  const extractedDocuments =
    Array.isArray(resolvedResults?.extracted_data?.documents)
      ? (resolvedResults?.extracted_data?.documents as Array<Record<string, any>>)
      : [];
  const issueCards = resolvedResults?.issue_cards ?? [];
  const referenceIssues = resolvedResults?.reference_issues ?? [];
  const aiInsights = resolvedResults?.ai_enrichment ?? resolvedResults?.aiEnrichment;
  const hasIssueCards = issueCards.length > 0;
  const [issueFilter, setIssueFilter] = useState<"all" | "critical" | "major" | "minor">("all");
  const documentStatusMap = useMemo(() => {
    const map = new Map<string, { status?: string; type?: string }>();
    documents.forEach((doc) => {
      if (doc.name) {
        map.set(doc.name, { status: doc.status, type: doc.type });
      }
    });
    return map;
  }, [documents]);
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
  const invoiceId = (resolvedResults as any)?.invoiceId;
  
  // Check if ready to submit (Phase 5: Guardrails)
  const isReadyToSubmit = useMemo(() => {
    if (!enableBankSubmission) return false;
    if (guardrailsLoading) return false;
    if (!guardrails) return totalDiscrepancies === 0;
    return guardrails.can_submit && guardrails.high_severity_discrepancies === 0;
  }, [guardrails, guardrailsLoading, enableBankSubmission, totalDiscrepancies]);
  
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
      console.log("Telemetry: customs_pack_generated", {
        validation_session_id: validationSessionId,
        lc_number: lcNumber,
        sha256: data.sha256,
      });
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
      console.log("Telemetry: bank_submit_requested", {
        validation_session_id: validationSessionId,
        lc_number: lcNumber,
        submission_id: submission.id,
        bank_name: submission.bank_name,
      });
    },
    onError: (error: any) => {
      toast({
        title: "Submission Failed",
        description: error?.response?.data?.detail || "Failed to submit to bank. Please try again.",
        variant: "destructive",
      });
    },
  });

  if (!resultData && !isDemoMode) {
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
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto" />
          <div>
            <p className="text-lg font-semibold">Validation in progress</p>
            <p className="text-sm text-muted-foreground">
              Current status: {statusLabel}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!resolvedResults) {
    return null;
  }

  const getDocumentNamesForCard = (card: IssueCard): string[] => {
    const names = new Set<string>();
    const anyCard = card as any;
    if (card.documentName) {
      names.add(card.documentName);
    }
    if (Array.isArray(anyCard.documentNames)) {
      anyCard.documentNames.forEach((name: string) => {
        if (name) names.add(name);
      });
    }
    if (Array.isArray(anyCard.documents)) {
      anyCard.documents.forEach((name: string) => {
        if (name) names.add(name);
      });
    }
    return Array.from(names);
  };

  const renderDocumentChips = (card: IssueCard) => {
    const names = getDocumentNamesForCard(card);
    if (names.length === 0) {
      return null;
    }

    return (
      <div className="flex flex-wrap gap-2">
        {names.map((name) => {
          const meta = documentStatusMap.get(name);
          const status = meta?.status ?? "warning";
          const statusClass =
            status === "success"
              ? "bg-success/10 text-success border-success/20"
              : status === "error"
              ? "bg-destructive/10 text-destructive border-destructive/20"
              : "bg-warning/10 text-warning border-warning/20";
          return (
            <Badge key={name} variant="outline" className={statusClass}>
              {meta?.type ? `${meta.type}: ` : ""}
              {name}
            </Badge>
          );
        })}
      </div>
    );
  };

  const renderAIInsightsCard = () => {
    if (!aiInsights?.summary) {
      return null;
    }

    return (
      <Card className="shadow-soft border-0">
        <CardHeader>
          <div className="flex items-center gap-3">
            <Lightbulb className="w-5 h-5 text-primary" />
            <div>
              <CardTitle>AI Risk Insights</CardTitle>
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
              <p className="text-sm font-medium text-muted-foreground">Next Suggestions</p>
              <ul className="list-disc list-inside text-sm text-foreground space-y-1">
                {aiInsights.suggestions.map((suggestion, idx) => (
                  <li key={idx}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    );
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
                Severity: {issue.severity || "reference"} · {issue.ruleset_domain || "rulebook"}
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
  const totalDocuments = documents.length || 0;
  // totalDiscrepancies already computed above for use in isReadyToSubmit
  const successCount = documents?.filter((d) => d.status === "success").length ?? 0;
  const warningCount = documents?.filter((d) => d.status === "warning").length ?? 0;
  const errorCount = documents?.filter((d) => d.status === "error").length ?? 0;
  const successRate = totalDocuments ? Math.round((successCount / totalDocuments) * 100) : 0;
  const overallStatus =
    resolvedResults.overallStatus ||
    resolvedResults.status ||
    (totalDiscrepancies > 0 ? "warning" : "success");
  const packGenerated = resolvedResults.packGenerated ?? false;
  const processingTime =
    resolvedResults.processingTime ||
    resolvedResults.processing_time ||
    resolvedResults.processingTimeMinutes ||
    "—";
  const processedAt =
    resolvedResults.processedAt ||
    resolvedResults.completedAt ||
    resolvedResults.processingCompletedAt ||
    resolvedResults.processedAt ||
    resolvedResults.processed_at ||
    mockExporterResults.processedAt;
  
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
            </div>
          </div>
        </header>
      )}

      <div className={containerClass}>
        {/* Status Overview */}
        <Card className="mb-8 shadow-soft border-0">
          <CardContent className="p-6">
            <div className="grid md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className={`w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center ${
                  overallStatus === "success" ? "bg-success/10" :
                  overallStatus === "error" ? "bg-destructive/10" : "bg-warning/10"
                }`}>
                  {overallStatus === "success" ? (
                    <CheckCircle className="w-8 h-8 text-success" />
                  ) : overallStatus === "error" ? (
                    <XCircle className="w-8 h-8 text-destructive" />
                  ) : (
                    <AlertTriangle className="w-8 h-8 text-warning" />
                  )}
                </div>
                <StatusBadge status={overallStatus} className="text-sm font-medium">
                  {packGenerated ? "Customs Pack Ready" : "Processing Required"}
                </StatusBadge>
                {/* Ready to Submit Badge */}
                {isReadyToSubmit && (
                  <Badge className="mt-2 bg-green-600 text-white">
                    <Send className="w-3 h-3 mr-1" />
                    Ready to Submit to Bank
                  </Badge>
                )}
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Processing Summary</h3>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Documents:</span>
                    <span className="font-medium">{totalDocuments}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Compliance Rate:</span>
                    <span className="font-medium text-success">
                      {totalDocuments ? Math.round(((totalDocuments - totalDiscrepancies) / totalDocuments) * 100) : 0}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Processing Time:</span>
                    <span className="font-medium">{processingTime}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Document Status</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <span className="text-sm">{successCount} documents verified</span>
                  </div>
                  {warningCount > 0 && (
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-warning rounded-full"></div>
                      <span className="text-sm">{warningCount} with warnings</span>
                    </div>
                  )}
                  {errorCount > 0 && (
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-destructive rounded-full"></div>
                      <span className="text-sm">{errorCount} with errors</span>
                    </div>
                  )}
                  <Progress value={successRate} className="h-2 mt-2" />
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Next Steps</h3>
                <div className="space-y-2">
                  {totalDiscrepancies > 0 ? (
                    <>
                      <Link to="/lcopilot/exporter-dashboard?section=upload">
                        <Button variant="outline" size="sm" className="w-full">
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Fix & Re-process
                        </Button>
                      </Link>
                      <p className="text-xs text-muted-foreground text-center">
                        Review warnings before bank submission
                      </p>
                    </>
                  ) : (
                    <>
                      <Button 
                        className="w-full bg-gradient-primary hover:opacity-90" 
                        size="sm"
                        onClick={handleDownloadCustomsPack}
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download Customs Pack
                      </Button>
                      {isReadyToSubmit && enableBankSubmission && (
                        <Button 
                          className="w-full bg-green-600 hover:bg-green-700 text-white" 
                          size="sm"
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
                      {!isReadyToSubmit && guardrails && guardrails.blocking_issues.length > 0 && (
                        <div className="text-xs text-muted-foreground space-y-1">
                          <p className="font-medium text-destructive">Cannot submit:</p>
                          {guardrails.blocking_issues.map((issue, idx) => (
                            <p key={idx}>• {issue}</p>
                          ))}
                        </div>
                      )}
                      <p className="text-xs text-success text-center">
                        {isReadyToSubmit ? "Ready for bank submission" : "Ready for customs clearance"}
                      </p>
                    </>
                  )}
                  {invoiceId && (
                    <Link to={`/lcopilot/exporter-dashboard?tab=billing&invoice=${invoiceId}`}>
                      <Button variant="outline" size="sm" className="w-full">
                        <Receipt className="w-4 h-4 mr-2" />
                        View Invoice
                      </Button>
                    </Link>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Detailed Results */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-6">
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
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Processing Timeline */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    Export Processing Timeline
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Documents Uploaded</p>
                      <p className="text-xs text-muted-foreground">14:28 - LC + 5 trade documents</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">LC Terms Extracted</p>
                      <p className="text-xs text-muted-foreground">14:29 - Requirements identified</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Document Cross-Check</p>
                      <p className="text-xs text-muted-foreground">14:30 - Against LC terms</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-warning rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Customs Pack Generated</p>
                      <p className="text-xs text-muted-foreground">14:30 - 1 minor issue noted</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Export Statistics */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle>Export Document Statistics</CardTitle>
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
                      <span className="font-medium text-success">95%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Customs Ready:</span>
                      <span className="font-medium text-success">Yes</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Bank Ready:</span>
                      <span className="font-medium text-warning">Review needed</span>
                    </div>
                  </div>
                  {packGenerated && (
                    <div className="p-3 bg-primary/5 border border-primary/20 rounded-lg">
                      <p className="text-sm font-medium text-primary">✓ Customs-Ready Pack Generated</p>
                      <p className="text-xs text-muted-foreground mt-1">All documents bundled for smooth customs clearance</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="documents" className="space-y-4">
            {documents.map((document) => (
              <Card key={document.id} className="shadow-soft border-0">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        document.status === "success" ? "bg-success/10" : 
                        document.status === "warning" ? "bg-warning/10" : "bg-destructive/10"
                      }`}>
                        <FileText className={`w-5 h-5 ${
                          document.status === "success" ? "text-success" : 
                          document.status === "warning" ? "text-warning" : "text-destructive"
                        }`} />
                      </div>
                      <div>
                        <CardTitle className="text-base">{document.name}</CardTitle>
                        <CardDescription>{document.type}</CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge status={document.status}>
                        {document.discrepancies === 0 ? "Verified" : 
                         document.status === "warning" ? "Minor Issues" : `${document.discrepancies} Issues`}
                      </StatusBadge>
                      <Button variant="outline" size="sm">
                        <Eye className="w-4 h-4 mr-2" />
                        View
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {Object.entries(document.extractedFields || {}).map(([key, value]) => {
                      const displayValue = formatExtractedValue(value);
                      return (
                        <div key={key} className="space-y-1">
                          <p className="text-xs text-muted-foreground font-medium capitalize">
                            {key.replace(/([A-Z])/g, ' $1').trim()}
                          </p>
                          <p className="text-sm font-medium text-foreground whitespace-pre-wrap break-words">
                            {displayValue}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="discrepancies" className="space-y-4">
            {hasIssueCards ? (
              <>
                <Card className="shadow-soft border-0">
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-4">
                      <div className="p-3 rounded-lg bg-destructive/5 border border-destructive/20">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Critical</p>
                        <p className="text-2xl font-bold text-destructive">{severityCounts.critical}</p>
                      </div>
                      <div className="p-3 rounded-lg bg-warning/5 border border-warning/20">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Major</p>
                        <p className="text-2xl font-bold text-warning">{severityCounts.major}</p>
                      </div>
                      <div className="p-3 rounded-lg bg-muted/30 border border-muted">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Minor</p>
                        <p className="text-2xl font-bold text-foreground">{severityCounts.minor}</p>
                      </div>
                      <div className="p-3 rounded-lg bg-secondary/30 border border-secondary/60">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Total Issues</p>
                        <p className="text-2xl font-bold text-foreground">{issueCards.length}</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {[
                        { value: "all", label: `All (${issueCards.length})` },
                        { value: "critical", label: `Critical (${severityCounts.critical})` },
                        { value: "major", label: `Major (${severityCounts.major})` },
                        { value: "minor", label: `Minor (${severityCounts.minor})` },
                      ].map((option) => (
                        <Button
                          key={option.value}
                          size="sm"
                          variant={issueFilter === option.value ? "default" : "outline"}
                          onClick={() => setIssueFilter(option.value as typeof issueFilter)}
                        >
                          {option.label}
                        </Button>
                      ))}
                    </div>
                  </CardContent>
                </Card>
                {filteredIssueCards.length === 0 ? (
                  <Card className="shadow-soft border border-dashed">
                    <CardContent className="py-6 text-center text-sm text-muted-foreground">
                      No issues match this severity filter.
                    </CardContent>
                  </Card>
                ) : (
                  filteredIssueCards.map((card, index) => {
                    const normalizedSeverity = normalizeDiscrepancySeverity(card.severity);
                    const fallbackId = card.id || `${card.rule ?? "rule"}-${card.title ?? index}`;
                    const documentLabel = card.documentName || (card as any).document || "Supporting Document";

                    return (
                      <div key={fallbackId} className="space-y-3">
                        {renderDocumentChips(card)}
                        <DiscrepancyGuidance
                          discrepancy={{
                            id: fallbackId,
                            title: card.title ?? "Review Required",
                            description: card.description ?? "",
                            severity: normalizedSeverity,
                            documentName: documentLabel,
                            documentType: card.documentType ?? documentLabel,
                            rule: card.rule ?? fallbackId,
                            expected: card.expected ?? card.title ?? card.rule ?? "",
                            actual: card.actual ?? "",
                            suggestion: card.suggestion ?? "Align the document with the LC clause.",
                            field: card.field,
                          }}
                          onRevalidate={async (id) => {
                            console.log("Re-validating discrepancy:", id);
                          }}
                          onUploadFixed={async (id, file) => {
                            console.log("Uploading fixed document for discrepancy:", id, file.name);
                          }}
                        />
                      </div>
                    );
                  })
                )}
                {renderAIInsightsCard()}
                {renderReferenceIssuesCard()}
              </>
            ) : (
              <>
                <Card className="shadow-soft border-0">
                  <CardContent className="p-8 text-center">
                    <div className="bg-success/10 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <CheckCircle className="w-8 h-8 text-success" />
                    </div>
                    <h3 className="text-lg font-semibold text-foreground mb-2">Perfect Compliance</h3>
                    <p className="text-muted-foreground">
                      All export documents align with the LC. Review the AI insights and technical references below for deeper context.
                    </p>
                  </CardContent>
                </Card>
                {renderAIInsightsCard()}
                {renderReferenceIssuesCard()}
              </>
            )}
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
                {/* Extraction Status */}
                <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
                  <div className="font-semibold">Extraction Status:</div>
                  <Badge
                    variant={
                      resolvedResults.extraction_status === "success"
                        ? "default"
                        : resolvedResults.extraction_status === "partial"
                        ? "outline"
                        : resolvedResults.extraction_status === "empty"
                        ? "destructive"
                        : "secondary"
                    }
                  >
                    {resolvedResults.extraction_status || "unknown"}
                  </Badge>
                  {resolvedResults.extraction_status === "empty" && (
                    <p className="text-sm text-muted-foreground ml-2">
                      No text could be extracted from the documents. This may indicate scanned images that require OCR.
                    </p>
                  )}
                  {resolvedResults.extraction_status === "partial" && (
                    <p className="text-sm text-muted-foreground ml-2">
                      Some text was extracted, but structured fields could not be fully parsed.
                    </p>
                  )}
                  {resolvedResults.extraction_status === "error" && (
                    <p className="text-sm text-muted-foreground ml-2">
                      An error occurred during extraction. Please try uploading the documents again.
                    </p>
                  )}
                </div>

                {/* Extracted Data Display */}
                {resolvedResults.extracted_data ? (
                  <div className="space-y-4">
                    {/* LC Data */}
                    {resolvedResults.extracted_data.lc && (
                      <div className="space-y-2">
                        <h3 className="font-semibold text-lg">Letter of Credit Data</h3>
                        <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-md">
                          <pre className="text-sm overflow-auto max-h-[400px] whitespace-pre-wrap">
                            {JSON.stringify(resolvedResults.extracted_data.lc, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* Invoice Data */}
                    {resolvedResults.extracted_data.invoice && (
                      <div className="space-y-2">
                        <h3 className="font-semibold text-lg">Commercial Invoice Data</h3>
                        <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-md">
                          <pre className="text-sm overflow-auto max-h-[400px] whitespace-pre-wrap">
                            {JSON.stringify(resolvedResults.extracted_data.invoice, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* Bill of Lading Data */}
                    {resolvedResults.extracted_data.bill_of_lading && (
                      <div className="space-y-2">
                        <h3 className="font-semibold text-lg">Bill of Lading Data</h3>
                        <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-md">
                          <pre className="text-sm overflow-auto max-h-[400px] whitespace-pre-wrap">
                            {JSON.stringify(resolvedResults.extracted_data.bill_of_lading, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* Raw Extracted Data (if no structured sections) */}
                    {!resolvedResults.extracted_data.lc &&
                      !resolvedResults.extracted_data.invoice &&
                      !resolvedResults.extracted_data.bill_of_lading && (
                        <div className="space-y-2">
                          <h3 className="font-semibold text-lg">Raw Extracted Data</h3>
                          <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-md">
                            <pre className="text-sm overflow-auto max-h-[400px] whitespace-pre-wrap">
                              {JSON.stringify(resolvedResults.extracted_data, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}

                    {/* Per-document OCR summary */}
                    {extractedDocuments.length > 0 && (
                      <div className="space-y-3">
                        <h3 className="font-semibold text-lg">Document OCR Overview</h3>
                        <div className="grid gap-4 md:grid-cols-2">
                          {extractedDocuments.map((doc, index) => {
                            const cardTitle = doc.filename || doc.name || `Document ${index + 1}`;
                            const docType = (doc.document_type || doc.type || "supporting_document")
                              .toString()
                              .replace(/_/g, " ");
                            const extractionStatus = doc.extraction_status || doc.extractionStatus || "unknown";
                            const fieldEntries = Object.entries(doc.extracted_fields || doc.extractedFields || {});

                            return (
                              <div key={`${cardTitle}-${index}`} className="border rounded-lg p-4 space-y-3">
                                <div className="flex items-center justify-between">
                                  <div>
                                    <p className="font-semibold">{cardTitle}</p>
                                    <p className="text-xs text-muted-foreground capitalize">{docType}</p>
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
                                    {fieldEntries.map(([key, value]) => (
                                      <div key={key} className="flex flex-col">
                                        <span className="text-xs text-muted-foreground uppercase tracking-wide">
                                          {key.replace(/([A-Z])/g, " $1").trim()}
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
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground mb-2">No extracted data available</p>
                    <p className="text-sm text-muted-foreground">
                      {resolvedResults.extraction_status === "empty"
                        ? "The documents may be scanned images that require OCR processing. Please ensure OCR is enabled in the system settings."
                        : "Data extraction may still be in progress or failed. Please check the extraction status above."}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="history" className="space-y-6">
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <History className="w-5 h-5" />
                  Submission History
                </CardTitle>
                <CardDescription>
                  Track all submissions of this LC to banks
                </CardDescription>
              </CardHeader>
              <CardContent>
                {submissionsLoading ? (
                  <div className="text-center py-12">
                    <Loader2 className="w-8 h-8 mx-auto text-muted-foreground mb-4 animate-spin" />
                    <p className="text-muted-foreground">Loading submission history...</p>
                  </div>
                ) : !submissionsData || submissionsData.items.length === 0 ? (
                  <div className="text-center py-12">
                    <Building2 className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground mb-2">No submissions yet</p>
                    <p className="text-sm text-muted-foreground">
                      Submit this LC to a bank to track its submission history
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {submissionsData.items.map((submission) => (
                      <SubmissionHistoryCard 
                        key={submission.id} 
                        submission={submission}
                        validationSessionId={validationSessionId}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Processing Performance */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Processing Performance
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Document Extraction Speed</span>
                      <span className="text-sm font-medium">98% accuracy</span>
                    </div>
                    <Progress value={98} className="h-2" />
                    
                    <div className="flex items-center justify-between">
                      <span className="text-sm">LC Compliance Check</span>
                      <span className="text-sm font-medium">95% compliance</span>
                    </div>
                    <Progress value={95} className="h-2" />
                    
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Customs Readiness</span>
                      <span className="text-sm font-medium">92% ready</span>
                    </div>
                    <Progress value={92} className="h-2" />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mt-4">
                    <div className="text-center p-3 bg-success/5 border border-success/20 rounded-lg">
                      <div className="text-lg font-bold text-success">1.8m</div>
                      <div className="text-xs text-muted-foreground">Processing Time</div>
                    </div>
                    <div className="text-center p-3 bg-primary/5 border border-primary/20 rounded-lg">
                      <div className="text-lg font-bold text-primary">6/6</div>
                      <div className="text-xs text-muted-foreground">Documents Processed</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Document Status Breakdown */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="w-5 h-5" />
                    Document Status Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-success rounded-full"></div>
                        <span className="text-sm">Verified Documents</span>
                      </div>
                      <span className="text-sm font-medium">{successCount} ({totalDocuments ? Math.round((successCount/totalDocuments)*100) : 0}%)</span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-warning rounded-full"></div>
                        <span className="text-sm">Minor Issues</span>
                      </div>
                      <span className="text-sm font-medium">{warningCount} ({totalDocuments ? Math.round((warningCount/totalDocuments)*100) : 0}%)</span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-destructive rounded-full"></div>
                        <span className="text-sm">Critical Issues</span>
                      </div>
                      <span className="text-sm font-medium">{errorCount} (0%)</span>
                    </div>
                  </div>
                  
                  <div className="mt-4 p-3 bg-gradient-primary/5 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="w-4 h-4 text-primary" />
                      <span className="text-sm font-medium text-primary">Performance Insights</span>
                    </div>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li>• Processing 15% faster than average</li>
                      <li>• Above average compliance rate</li>
                      <li>• Ready for expedited customs clearance</li>
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Detailed Analytics Table */}
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle>Document Processing Analytics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2">Document Type</th>
                        <th className="text-left py-2">Processing Time</th>
                        <th className="text-left py-2">Accuracy Score</th>
                        <th className="text-left py-2">Compliance Level</th>
                        <th className="text-left py-2">Risk Assessment</th>
                      </tr>
                    </thead>
                    <tbody className="space-y-2">
                      {documents.map((doc, index) => (
                        <tr key={doc.id} className="border-b border-gray-200/50">
                          <td className="py-3 font-medium">{doc.type}</td>
                          <td className="py-3 text-muted-foreground">{(0.2 + index * 0.1).toFixed(1)}s</td>
                          <td className="py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-16 bg-muted rounded-full h-2">
                                <div 
                                  className="h-2 rounded-full bg-success" 
                                  style={{ width: `${95 + Math.random() * 5}%` }}
                                ></div>
                              </div>
                              <span className="text-xs">{(95 + Math.random() * 5).toFixed(0)}%</span>
                            </div>
                          </td>
                          <td className="py-3">
                            <StatusBadge status={doc.status}>
                              {doc.status === "success" ? "High" : doc.status === "warning" ? "Medium" : "Low"}
                            </StatusBadge>
                          </td>
                          <td className="py-3 text-muted-foreground">
                            {doc.status === "success" ? "Low Risk" : doc.status === "warning" ? "Medium Risk" : "High Risk"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
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
                          <Badge variant="outline">{doc.type}</Badge>
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

// Submission History Card Component (Phase 4)
function SubmissionHistoryCard({ 
  submission, 
  validationSessionId 
}: { 
  submission: BankSubmissionRead; 
  validationSessionId: string;
}) {
  const { data: eventsData } = useQuery({
    queryKey: ['exporter-submission-events', submission.id],
    queryFn: () => exporterApi.getSubmissionEvents(submission.id),
    enabled: !!submission.id,
  });
  
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'accepted':
        return 'default';
      case 'rejected':
      case 'failed':
        return 'destructive';
      case 'cancelled':
        return 'secondary';
      default:
        return 'secondary';
    }
  };
  
  return (
    <Card className="border-l-4 border-l-primary">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-muted-foreground" />
            <span className="font-medium">{submission.bank_name || 'Unknown Bank'}</span>
            <Badge variant={getStatusVariant(submission.status)}>
              {submission.status}
            </Badge>
          </div>
          {submission.receipt_url && (
            <Button variant="outline" size="sm" asChild>
              <a href={submission.receipt_url} target="_blank" rel="noopener noreferrer">
                <Receipt className="w-4 h-4 mr-2" />
                View Receipt
              </a>
            </Button>
          )}
        </div>
        <div className="text-sm text-muted-foreground space-y-1">
          <div>Submitted: {submission.submitted_at ? format(new Date(submission.submitted_at), "MMM d, yyyy 'at' HH:mm") : 'N/A'}</div>
          {submission.note && (
            <div className="mt-2 p-2 bg-muted rounded text-xs">
              <strong>Note:</strong> {submission.note}
            </div>
          )}
        </div>
        {eventsData && eventsData.items.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <Label className="text-xs text-muted-foreground mb-2 block">Event Timeline</Label>
            <div className="space-y-2">
              {eventsData.items.map((event) => (
                <div key={event.id} className="flex items-center gap-2 text-xs">
                  <div className="w-2 h-2 bg-primary rounded-full"></div>
                  <span className="text-muted-foreground">
                    {format(new Date(event.created_at), "MMM d, HH:mm")} - {event.event_type}
                    {event.actor_name && ` by ${event.actor_name}`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
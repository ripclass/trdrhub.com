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
  Loader2
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
  const [resultsFetched, setResultsFetched] = useState(false);
  const [resultsErrorState, setResultsErrorState] = useState<string | null>(null);
  
  const lcNumberParam = searchParams.get('lc') || undefined;
  
  useEffect(() => {
    setLiveResults(null);
    setResultsFetched(false);
  }, [validationSessionId]);

  useEffect(() => {
    if (!validationSessionId) return;
    if (resultsFetched) return;
    if (jobStatus?.status === "completed") {
      getResults(validationSessionId)
        .then((data) => {
          setLiveResults(data);
          setResultsErrorState(null);
          setResultsFetched(true);
        })
        .catch((err: any) => {
          setResultsErrorState(err?.message || "Failed to load validation results.");
          setResultsFetched(true);
        });
    }
  }, [validationSessionId, jobStatus?.status, getResults, resultsFetched]);

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

  const documents = resolvedResults.documents ?? [];
  const discrepanciesList = resolvedResults.discrepancies ?? [];
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
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="documents">Documents ({totalDocuments})</TabsTrigger>
            <TabsTrigger value="discrepancies" className="relative">
              Issues ({totalDiscrepancies})
              {totalDiscrepancies > 0 && (
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-warning rounded-full"></div>
              )}
            </TabsTrigger>
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
                    {Object.entries(document.extractedFields).map(([key, value]) => (
                      <div key={key} className="space-y-1">
                        <p className="text-xs text-muted-foreground font-medium capitalize">
                          {key.replace(/([A-Z])/g, ' $1').trim()}
                        </p>
                        <p className="text-sm font-medium text-foreground">{value}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="discrepancies" className="space-y-4">
            {discrepanciesList.length === 0 ? (
              <Card className="shadow-soft border-0">
                <CardContent className="p-8 text-center">
                  <div className="bg-success/10 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-success" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">Perfect Compliance!</h3>
                  <p className="text-muted-foreground">All export documents are ready for bank submission and customs clearance.</p>
                </CardContent>
              </Card>
            ) : (
              discrepanciesList.map((discrepancy) => (
                <DiscrepancyGuidance
                  key={discrepancy.id}
                  discrepancy={{
                    ...discrepancy,
                    documentType: discrepancy.documentName,
                    severity: discrepancy.severity === "medium" ? "major" : discrepancy.severity as "critical" | "major" | "minor",
                  }}
                  onRevalidate={async (id) => {
                    // In a real app, call API to re-validate
                    console.log("Re-validating discrepancy:", id);
                  }}
                  onUploadFixed={async (id, file) => {
                    // In a real app, upload fixed document
                    console.log("Uploading fixed document for discrepancy:", id, file.name);
                  }}
                />
              ))
            )}
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
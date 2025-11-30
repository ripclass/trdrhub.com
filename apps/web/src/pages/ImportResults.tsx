import { useState, useEffect } from "react";
import { Link, useParams, useSearchParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/ui/status-badge";
import { DiscrepancyGuidance } from "@/components/discrepancy/DiscrepancyGuidance";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { useJob, useResults, usePackage } from "@/hooks/use-lcopilot";
import { format } from "date-fns";
import { isImporterFeatureEnabled } from "@/config/importerFeatureFlags";
import { importerApi } from "@/api/importer";
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
  ShieldCheck,
  AlertCircle,
  BarChart3,
  TrendingUp,
  PieChart,
  Receipt,
  Send,
  History,
  Building2,
  Mail,
  Package
} from "lucide-react";

// Mock data for demonstration - in real app this would come from API
const mockDraftLCResults = {
  lcNumber: "DRAFT-LC-BD-2024-001",
  status: "completed",
  processedAt: "2024-01-15T14:30:00Z",
  processingTime: "1.5 minutes",
  totalClauses: 12,
  totalRisks: 4,
  overallRiskScore: 65,
  overallStatus: "warning" as "success" | "error" | "warning",
  riskLevel: "medium" as "low" | "medium" | "high",

  lcClauses: [
    {
      id: "1",
      type: "Payment Terms",
      text: "Payment at sight against presentation of compliant documents",
      riskLevel: "low" as const,
      analysis: "Standard sight payment terms - low risk for importer",
      recommendation: "Acceptable - standard industry practice"
    },
    {
      id: "2",
      type: "Shipment Terms",
      text: "Latest shipment date: 15 days from LC opening date",
      riskLevel: "high" as const,
      analysis: "Very tight shipment timeline. Supplier may struggle to meet this deadline, causing delays and potential penalties.",
      recommendation: "Request extension to 30-45 days to reduce supplier rejection risk"
    },
    {
      id: "3",
      type: "Documentation Requirements",
      text: "Certificate of Origin must be issued by Bangladesh Export Promotion Council only",
      riskLevel: "high" as const,
      analysis: "Specific authority requirement may be difficult for foreign suppliers to fulfill. Could cause document discrepancies.",
      recommendation: "Accept certificates from equivalent recognized authorities or specify alternative bodies"
    }
  ],

  risks: [
    {
      id: "1",
      severity: "high" as const,
      category: "Timeline Risk",
      title: "Unrealistic Shipment Deadline",
      description: "15-day shipment window is extremely tight for international trade. Most suppliers need 30-45 days minimum.",
      businessImpact: "High probability of supplier rejection or non-compliance, leading to shipment delays and potential contract penalties.",
      financialImpact: "Potential demurrage charges, storage costs, and production delays if goods arrive late.",
      recommendation: "Extend shipment deadline to 30-45 days from LC opening date."
    },
    {
      id: "2",
      severity: "high" as const,
      category: "Documentation Risk",
      title: "Restrictive Certificate Authority",
      description: "Requiring certificates from only Bangladesh Export Promotion Council limits supplier options.",
      businessImpact: "May cause document discrepancies and LC rejections by banks.",
      financialImpact: "Document amendment fees ($150-500 per amendment) and delayed payments.",
      recommendation: "Allow certificates from equivalent recognized authorities in supplier's country."
    }
  ]
};

const mockSupplierResults = {
  lcNumber: "IMP-BD-2024-001",
  status: "completed",
  processedAt: "2024-01-15T14:30:00Z",
  processingTime: "2.1 minutes",
  totalDocuments: 4,
  totalIssues: 3,
  complianceRate: 75,
  overallStatus: "warning" as "success" | "error" | "warning",
  customsReady: false,

  documents: [
    {
      id: "1",
      name: "Suppliers_Commercial_Invoice.pdf",
      type: "Commercial Invoice",
      status: "error" as const,
      issues: 2,
      complianceScore: 60,
      extractedFields: {
        invoiceNumber: "SUP-INV-001",
        invoiceDate: "2024-01-12",
        totalAmount: "USD 51,500",
        supplier: "Indian Cotton Mills Ltd",
        consignee: "Bangladesh Textiles Ltd"
      }
    },
    {
      id: "2",
      name: "Suppliers_Packing_List.pdf",
      type: "Packing List",
      status: "warning" as const,
      issues: 1,
      complianceScore: 85,
      extractedFields: {
        totalPackages: "95 bales",
        grossWeight: "2600 KG",
        netWeight: "2350 KG",
        description: "Raw Cotton Bales"
      }
    },
    {
      id: "3",
      name: "Bill_of_Lading.pdf",
      type: "Bill of Lading",
      status: "success" as const,
      issues: 0,
      complianceScore: 100,
      extractedFields: {
        blNumber: "BL-CTG-001",
        vessel: "MV Dhaka Express",
        portOfLoading: "Mumbai",
        portOfDischarge: "Chittagong"
      }
    }
  ],

  issues: [
    {
      id: "1",
      documentId: "1",
      severity: "high" as const,
      category: "Amount Discrepancy",
      title: "Invoice Amount Exceeds LC Value",
      description: "Commercial invoice amount ($51,500) exceeds LC maximum value ($50,000).",
      recommendation: "Request supplier to adjust invoice amount or consider LC amendment to increase value."
    },
    {
      id: "2",
      documentId: "1",
      severity: "medium" as const,
      category: "Date Discrepancy",
      title: "Late Invoice Date",
      description: "Invoice date (Jan 12) is after shipment date per BL (Jan 10).",
      recommendation: "Request corrected invoice with date before or on shipment date."
    },
    {
      id: "3",
      documentId: "2",
      severity: "low" as const,
      category: "Description Mismatch",
      title: "Minor Description Variance",
      description: "Packing list shows 'Raw Cotton Bales' vs LC requirement 'Cotton Raw Materials'.",
      recommendation: "Acceptable variance - no action required."
    }
  ]
};

const mockLCValidationTrends = [
  { month: "Jul", riskScore: 78, supplierIssues: 6 },
  { month: "Aug", riskScore: 74, supplierIssues: 5 },
  { month: "Sep", riskScore: 70, supplierIssues: 4 },
  { month: "Oct", riskScore: 67, supplierIssues: 4 },
  { month: "Nov", riskScore: 63, supplierIssues: 3 },
  { month: "Dec", riskScore: 59, supplierIssues: 2 }
];

type ImportResultsProps = {
  embedded?: boolean;
  jobId?: string;
  lcNumber?: string;
  mode?: "draft" | "supplier";
};

// Transform API results to display format for supplier mode
const transformApiToSupplierFormat = (apiResults: any) => {
  if (!apiResults) return null;
  
  const summary = apiResults.summary || apiResults.structured_result?.processing_summary || {};
  const docs = apiResults.documents || [];
  const issues = apiResults.issues || [];
  const analytics = apiResults.analytics || apiResults.structured_result?.analytics || {};
  
  // Calculate compliance rate from summary or analytics
  const complianceRate = summary.compliance_rate ?? analytics.compliance_score ?? 
    (issues.length === 0 ? 100 : Math.max(0, 100 - issues.length * 15));
  
  // Transform documents to expected format
  const transformedDocs = docs.map((doc: any, idx: number) => ({
    id: doc.id || doc.documentId || String(idx + 1),
    name: doc.name || doc.filename || `Document ${idx + 1}`,
    type: doc.type || doc.typeKey || 'Supporting Document',
    status: doc.status || (doc.issuesCount > 0 ? 'warning' : 'success'),
    issues: doc.issuesCount ?? doc.discrepancyCount ?? 0,
    complianceScore: doc.issuesCount > 0 ? Math.max(60, 100 - doc.issuesCount * 15) : 100,
    extractedFields: doc.extractedFields || {}
  }));
  
  // Transform issues to expected format
  const transformedIssues = issues.map((issue: any, idx: number) => ({
    id: issue.id || String(idx + 1),
    severity: issue.severity || 'warning',
    category: issue.documentType || issue.documentName || 'Document Issue',
    title: issue.title || 'Review Required',
    description: issue.description || '',
    recommendation: issue.suggestion || 'Review and correct this issue before bank submission.',
    document: issue.documentName || issue.documents?.[0] || 'Document'
  }));
  
  // Determine overall status
  const criticalIssues = issues.filter((i: any) => i.severity === 'critical' || i.severity === 'error').length;
  const overallStatus = criticalIssues > 0 ? 'error' : issues.length > 0 ? 'warning' : 'success';
  
  return {
    lcNumber: apiResults.lc_structured?.lc_number || summary.lc_number || 'LC-VALIDATION',
    status: 'completed',
    processedAt: new Date().toISOString(),
    processingTime: summary.processing_time_display || `${(summary.processing_time_seconds || 30).toFixed(1)} seconds`,
    totalDocuments: transformedDocs.length || summary.total_documents || 0,
    totalIssues: issues.length,
    complianceRate: Math.round(complianceRate),
    overallStatus: overallStatus as 'success' | 'error' | 'warning',
    customsReady: issues.length === 0,
    documents: transformedDocs,
    issues: transformedIssues
  };
};

// Transform API results to display format for draft LC mode
const transformApiToDraftFormat = (apiResults: any) => {
  if (!apiResults) return null;
  
  const summary = apiResults.summary || apiResults.structured_result?.processing_summary || {};
  const issues = apiResults.issues || [];
  const lcData = apiResults.lc_structured || apiResults.structured_result?.lc_structured || {};
  
  // Calculate risk score (inverse of compliance)
  const complianceRate = summary.compliance_rate ?? 100;
  const riskScore = Math.round(100 - complianceRate * 0.65); // Scale to risk perspective
  
  // Transform issues to risks
  const risks = issues.map((issue: any, idx: number) => ({
    id: String(idx + 1),
    severity: issue.severity || 'warning',
    category: issue.documentType || 'LC Terms',
    title: issue.title || 'Review Required',
    description: issue.description || '',
    businessImpact: issue.description || 'May cause document discrepancies.',
    financialImpact: 'Potential amendment fees and delays.',
    recommendation: issue.suggestion || 'Review and address before LC issuance.'
  }));
  
  // Create LC clauses from extracted data
  const lcClauses = [];
  if (lcData.payment_terms) {
    lcClauses.push({
      id: '1',
      type: 'Payment Terms',
      text: lcData.payment_terms,
      riskLevel: 'low' as const,
      analysis: 'Payment terms extracted from LC.',
      recommendation: 'Review payment terms for alignment with contract.'
    });
  }
  if (lcData.latest_shipment_date) {
    const hasTimelineRisk = risks.some((r: any) => r.category?.includes('Timeline') || r.title?.includes('date'));
    lcClauses.push({
      id: '2',
      type: 'Shipment Terms',
      text: `Latest shipment date: ${lcData.latest_shipment_date}`,
      riskLevel: hasTimelineRisk ? 'high' as const : 'low' as const,
      analysis: hasTimelineRisk ? 'Timeline may be tight for fulfillment.' : 'Shipment timeline appears reasonable.',
      recommendation: hasTimelineRisk ? 'Consider requesting timeline extension.' : 'Acceptable timeline.'
    });
  }
  if (lcData.documents_required) {
    lcClauses.push({
      id: '3',
      type: 'Documentation Requirements',
      text: lcData.documents_required,
      riskLevel: risks.length > 0 ? 'medium' as const : 'low' as const,
      analysis: 'Document requirements extracted from LC.',
      recommendation: 'Ensure supplier can provide all required documents.'
    });
  }
  
  // Add default clauses if none extracted
  if (lcClauses.length === 0) {
    lcClauses.push({
      id: '1',
      type: 'General Terms',
      text: 'LC terms analyzed for compliance',
      riskLevel: risks.length > 0 ? 'medium' as const : 'low' as const,
      analysis: `${issues.length} issues identified during analysis.`,
      recommendation: issues.length > 0 ? 'Review identified issues before proceeding.' : 'LC terms appear acceptable.'
    });
  }
  
  const overallStatus = risks.filter((r: any) => r.severity === 'critical' || r.severity === 'high').length > 0 
    ? 'error' : risks.length > 0 ? 'warning' : 'success';
  const riskLevel = riskScore > 70 ? 'high' : riskScore > 40 ? 'medium' : 'low';
  
  return {
    lcNumber: lcData.lc_number || summary.lc_number || 'DRAFT-LC-ANALYSIS',
    status: 'completed',
    processedAt: new Date().toISOString(),
    processingTime: summary.processing_time_display || `${(summary.processing_time_seconds || 30).toFixed(1)} seconds`,
    totalClauses: lcClauses.length,
    totalRisks: risks.length,
    overallRiskScore: riskScore,
    overallStatus: overallStatus as 'success' | 'error' | 'warning',
    riskLevel: riskLevel as 'low' | 'medium' | 'high',
    lcClauses,
    risks
  };
};

export default function ImportResults({
  embedded = false,
  jobId: jobIdOverride,
  lcNumber: lcNumberOverride,
  mode: modeOverride,
}: ImportResultsProps = {}) {
  const params = useParams<{ jobId: string }>();
  const [searchParams] = useSearchParams();
  const { toast } = useToast();

  const mode = (modeOverride ?? searchParams.get('mode') ?? 'draft') as 'draft' | 'supplier';
  const rawJobId = jobIdOverride ?? params.jobId ?? searchParams.get('jobId') ?? undefined;
  const jobId = rawJobId ?? `demo-${mode}`;
  const lcNumber = lcNumberOverride ?? searchParams.get('lc') ?? (
    mode === 'draft' ? mockDraftLCResults.lcNumber : mockSupplierResults.lcNumber
  );

  const isDemoJob = !rawJobId || jobId.startsWith('demo-');
  const shouldUseAPI = !isDemoJob;

  const { jobStatus, isPolling, startPolling } = useJob(shouldUseAPI ? jobId : null);
  const { results, getResults, isLoading: isLoadingResults } = useResults();
  const { generatePackage, downloadPackage, isLoading: isGeneratingPackage } = usePackage();
  const [activeTab, setActiveTab] = useState("overview");
  const [useMockData, setUseMockData] = useState(false);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [showSupplierDialog, setShowSupplierDialog] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSendingToSupplier, setIsSendingToSupplier] = useState(false);
  const [isGeneratingFixPack, setIsGeneratingFixPack] = useState(false);
  const [submissionHistory, setSubmissionHistory] = useState<any[]>([]);
  const [supplierEmail, setSupplierEmail] = useState("");
  const [supplierMessage, setSupplierMessage] = useState("");
  const navigate = useNavigate();

  // Feature flags
  const enableBankPrecheck = isImporterFeatureEnabled("importer_bank_precheck");
  const enableSupplierFixPack = isImporterFeatureEnabled("supplier_fix_pack");

  // Transform API results or use mock data
  const hasRealResults = results && !isDemoJob;
  const transformedSupplierData = hasRealResults ? transformApiToSupplierFormat(results) : null;
  const transformedDraftData = hasRealResults ? transformApiToDraftFormat(results) : null;
  
  // Use real data if available, otherwise fall back to mock
  const supplierData = transformedSupplierData || mockSupplierResults;
  const draftData = transformedDraftData || mockDraftLCResults;
  const displayData = mode === 'draft' ? draftData : supplierData;
  
  // Legacy alias for backward compatibility
  const mockData = displayData;
  
  // Determine if ready to submit (only for supplier mode with no issues and feature flag enabled)
  const isReadyToSubmit = mode === 'supplier' && supplierData.totalIssues === 0 && enableBankPrecheck;
  
  // Determine if supplier has issues (for supplier mode)
  const hasSupplierIssues = mode === 'supplier' && supplierData.totalIssues > 0;

  useEffect(() => {
    // For demo job IDs, immediately use mock data
    if (isDemoJob) {
      console.log('Demo job detected, using mock data immediately');
      setUseMockData(true);
      return;
    }

    // For real jobs, if no jobId or API fails, use mock data after 2 seconds
    const timer = setTimeout(() => {
      if (!jobStatus && jobId) {
        console.log('Using mock data for demo purposes');
        setUseMockData(true);
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [jobId, jobStatus, isDemoJob]);

  useEffect(() => {
    if (!isDemoJob && jobId && jobStatus?.status === 'active' && !isPolling) {
      console.log('Starting polling for job:', jobId);
      startPolling(jobId);
    }

    if (!isDemoJob && jobId && jobStatus?.status === 'completed') {
      console.log('Job completed, fetching results');
      getResults(jobId);
    }
  }, [jobId, jobStatus, getResults, isDemoJob, isPolling, startPolling]);

  const handleDownloadReport = async () => {
    console.log("Download button clicked, jobId:", jobId);

    // Demo mode: simulate download for demo job IDs
    if (isDemoJob) {
      console.log("Demo mode detected, creating mock download");

      const reportType = mode === 'draft' ? 'Risk Analysis' : 'Compliance Check';
      const fileName = `${mode === 'draft' ? 'LC_Risk_Analysis' : 'Supplier_Compliance'}_Report_${jobId.split('-').pop()}.txt`;

      const mockReportContent = `${reportType} Report
=====================================

Job ID: ${jobId}
LC Number: ${mockData.lcNumber}
Generated: ${new Date().toLocaleString()}
Processing Time: ${mockData.processingTime}

${mode === 'draft' ? `
RISK ANALYSIS SUMMARY
=====================
Overall Risk Score: ${mockData.overallRiskScore}/100
Risk Level: ${mockData.riskLevel?.toUpperCase()}
Total Clauses Analyzed: ${mockData.totalClauses}
Risks Identified: ${mockData.totalRisks}

HIGH PRIORITY RISKS:
${mockData.risks?.filter(r => r.severity === 'high').map(risk => `
- ${risk.title}
  Category: ${risk.category}
  Description: ${risk.description}
  Recommendation: ${risk.recommendation}
`).join('\n') || 'No high priority risks identified.'}

LC CLAUSES ANALYSIS:
${mockData.lcClauses?.map(clause => `
- ${clause.type} (${clause.riskLevel?.toUpperCase()} RISK)
  Text: ${clause.text}
  Analysis: ${clause.analysis}
  Recommendation: ${clause.recommendation}
`).join('\n') || 'No clauses analyzed.'}
` : `
COMPLIANCE CHECK SUMMARY
========================
Compliance Rate: ${supplierData.complianceRate}%
Total Documents: ${supplierData.totalDocuments}
Issues Found: ${supplierData.totalIssues}
Customs Ready: ${supplierData.customsReady ? 'YES' : 'NO'}

DOCUMENT STATUS:
${supplierData.documents.map(doc => `
- ${doc.name} (${doc.type})
  Status: ${doc.status.toUpperCase()}
  Compliance Score: ${doc.complianceScore}%
  Issues: ${doc.issues}
`).join('\n')}

COMPLIANCE ISSUES:
${supplierData.issues.map(issue => `
- ${issue.title} (${issue.severity?.toUpperCase()})
  Category: ${issue.category}
  Description: ${issue.description}
  Recommendation: ${issue.recommendation}
`).join('\n')}
`}

This is a demo report generated by LCopilot.
In production, this would be a comprehensive PDF report with detailed analysis, charts, and actionable recommendations.

© 2024 LCopilot - AI-Powered Trade Document Analysis
`;

      // Create blob and trigger download
      const blob = new Blob([mockReportContent], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);

      toast({
        title: "Report Downloaded",
        description: `${reportType} report has been downloaded successfully.`,
      });
      return;
    }

    console.log("Attempting real API download for jobId:", jobId);

    try {
      const packageInfo = await generatePackage(jobId);
      await downloadPackage(packageInfo.downloadUrl, packageInfo.fileName);

      toast({
        title: "Report Downloaded",
        description: `${mode === 'draft' ? 'Risk analysis' : 'Compliance'} report has been downloaded successfully.`,
      });
    } catch (error: any) {
      console.error("Download failed:", error);
      toast({
        title: "Download Failed",
        description: error.message || "Failed to download report. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleReAnalyze = () => {
    toast({
      title: "Re-analysis Started",
      description: `Starting fresh ${mode === 'draft' ? 'risk analysis' : 'compliance check'} with updated algorithms.`,
    });

    // Simulate re-analysis by refreshing the page after a short delay
    setTimeout(() => {
      window.location.reload();
    }, 1500);
  };

  const handleSubmitToBank = async () => {
    setIsSubmitting(true);
    try {
      // Get validation session ID from jobId or results
      const validationSessionId = results?.validation_session_id || jobId;
      
      if (!validationSessionId) {
        throw new Error("Validation session ID not found");
      }

      const response = await importerApi.requestBankPrecheck({
        validation_session_id: validationSessionId,
        lc_number: lcNumber,
        bank_name: "Bank One", // TODO: Get from user settings
      });

      toast({
        title: "Bank Review Requested",
        description: response.message || `LC ${lcNumber} has been sent to the bank for pre-check review.`,
      });

      setShowSubmitDialog(false);
      // Refresh submission history
      setSubmissionHistory([
        {
          id: response.request_id,
          lc_number: lcNumber,
          submitted_at: response.submitted_at,
          status: "pending",
          bank_name: response.bank_name || "Bank One",
          submitted_by: "Current User",
        },
        ...submissionHistory,
      ]);

      // Track telemetry (Phase 6)
      console.log("Telemetry: bank_precheck_requested", { lcNumber, validationSessionId, requestId: response.request_id });
    } catch (error: any) {
      console.error("Bank precheck request failed:", error);
      toast({
        title: "Request Failed",
        description: error.response?.data?.detail || error.message || "Failed to request bank review. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownloadSupplierFixPack = async () => {
    setIsGeneratingFixPack(true);
    try {
      // Get validation session ID from jobId or results
      const validationSessionId = results?.validation_session_id || jobId;
      
      if (!validationSessionId) {
        throw new Error("Validation session ID not found");
      }

      // Download fix pack from API
      const blob = await importerApi.downloadSupplierFixPack(validationSessionId);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Supplier_Fix_Pack_${lcNumber}_${Date.now()}.zip`;
      document.body.appendChild(link);
      link.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);

      toast({
        title: "Fix Pack Downloaded",
        description: "Supplier fix pack has been downloaded successfully.",
      });

      // Track event (Phase 6)
      console.log("Telemetry: supplier_fix_pack_downloaded", { 
        lcNumber, 
        validationSessionId, 
        issueCount: supplierData.totalIssues 
      });
    } catch (error: any) {
      console.error("Fix pack download failed:", error);
      toast({
        title: "Download Failed",
        description: error.response?.data?.detail || error.message || "Failed to generate supplier fix pack. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGeneratingFixPack(false);
    }
  };

  const handleSendToSupplier = async () => {
    if (!supplierEmail.trim()) {
      toast({
        title: "Email Required",
        description: "Please enter supplier email address.",
        variant: "destructive",
      });
      return;
    }

    setIsSendingToSupplier(true);
    try {
      // Get validation session ID from jobId or results
      const validationSessionId = results?.validation_session_id || jobId;
      
      if (!validationSessionId) {
        throw new Error("Validation session ID not found");
      }

      const response = await importerApi.notifySupplier({
        validation_session_id: validationSessionId,
        supplier_email: supplierEmail,
        message: supplierMessage || undefined,
        lc_number: lcNumber,
      });

      toast({
        title: "Sent to Supplier",
        description: response.message || `Supplier fix pack has been sent to ${supplierEmail}.`,
      });

      setShowSupplierDialog(false);
      setSupplierEmail("");
      setSupplierMessage("");

      // Track event (Phase 6)
      console.log("Telemetry: supplier_notify_sent", { 
        lcNumber, 
        validationSessionId, 
        supplierEmail, 
        notificationId: response.notification_id,
        issueCount: supplierData.totalIssues 
      });
    } catch (error: any) {
      console.error("Supplier notification failed:", error);
      toast({
        title: "Send Failed",
        description: error.response?.data?.detail || error.message || "Failed to send fix pack to supplier. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSendingToSupplier(false);
    }
  };

  const renderHeader = () => {
    const title = mode === 'draft' ? "Draft LC Risk Analysis" : "Supplier Document Compliance";
    const description = mode === 'draft'
      ? "Analysis of potential risks and unfavorable terms in your draft LC"
      : "Compliance check of supplier documents against LC requirements";

    return (
      <header className="bg-card border-b border-gray-200">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link to="/lcopilot/import-upload">
              <Button variant="outline" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Upload
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="bg-gradient-importer p-2 rounded-lg">
                {mode === 'draft' ? (
                  <ShieldCheck className="w-6 h-6 text-primary-foreground" />
                ) : (
                  <FileText className="w-6 h-6 text-primary-foreground" />
                )}
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">{title}</h1>
                <p className="text-sm text-muted-foreground">{description}</p>
              </div>
            </div>
          </div>
        </div>
      </header>
    );
  };

  const renderProcessingState = () => {
    if ((isPolling || jobStatus?.status === 'processing') && !useMockData) {
      return (
        <div className="container mx-auto px-4 py-8 max-w-4xl">
          <Card>
            <CardContent className="p-8 text-center">
              <div className="animate-spin w-8 h-8 border-2 border-importer border-t-transparent rounded-full mx-auto mb-4"></div>
              <h3 className="text-lg font-semibold mb-2">
                {mode === 'draft' ? 'Analyzing LC Terms for Risks...' : 'Checking Document Compliance...'}
              </h3>
              <p className="text-muted-foreground mb-4">
                {mode === 'draft'
                  ? 'Reviewing LC clauses for potential risks, timeline issues, and unfavorable terms.'
                  : 'Validating supplier documents against LC requirements and checking for discrepancies.'
                }
              </p>
              <Progress value={75} className="w-64 mx-auto" />
            </CardContent>
          </Card>
        </div>
      );
    }

    if (jobStatus?.status === 'failed' && !useMockData) {
      return (
        <div className="container mx-auto px-4 py-8 max-w-4xl">
          <Card>
            <CardContent className="p-8 text-center">
              <XCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Processing Failed</h3>
              <p className="text-muted-foreground mb-4">
                Something went wrong while processing your documents. Please try again.
              </p>
              <Button onClick={() => window.location.href = '/lcopilot/import-upload'}>
                Back to Upload
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    return null;
  };

  const renderOverviewTab = () => {
    if (mode === 'draft') {
      return (
        <div className="space-y-6">
          {/* Risk Summary Cards */}
          <div className="grid md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="bg-importer/10 p-2 rounded-lg">
                    <BarChart3 className="w-5 h-5 text-importer" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Risk Score</p>
                    <p className="text-2xl font-bold">{mockData.overallRiskScore}/100</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="bg-destructive/10 p-2 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-destructive" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Risks</p>
                    <p className="text-2xl font-bold">{mockData.totalRisks}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="bg-warning/10 p-2 rounded-lg">
                    <FileText className="w-5 h-5 text-warning" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">LC Clauses</p>
                    <p className="text-2xl font-bold">{mockData.totalClauses}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="bg-success/10 p-2 rounded-lg">
                    <Clock className="w-5 h-5 text-success" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Processed In</p>
                    <p className="text-2xl font-bold">{mockData.processingTime}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Top Risks */}
          <Card>
            <CardHeader>
              <CardTitle>High Priority Risks</CardTitle>
              <CardDescription>Critical issues that require immediate attention</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockData.risks.filter(r => r.severity === 'high').map((risk) => (
                  <div key={risk.id} className="border border-destructive/20 rounded-lg p-4 bg-destructive/5">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="destructive">{risk.severity.toUpperCase()}</Badge>
                        <span className="font-medium">{risk.category}</span>
                      </div>
                    </div>
                    <h4 className="font-semibold mb-2">{risk.title}</h4>
                    <p className="text-sm text-muted-foreground mb-3">{risk.description}</p>
                    <div className="bg-card p-3 rounded border">
                      <p className="text-sm">
                        <strong>Recommendation:</strong> {risk.recommendation}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      );
    } else {
      // Supplier document mode
      return (
        <div className="space-y-6">
          {/* Compliance Summary Cards */}
          <div className="grid md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="bg-importer/10 p-2 rounded-lg">
                    <TrendingUp className="w-5 h-5 text-importer" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Compliance Rate</p>
                    <p className="text-2xl font-bold">{supplierData.complianceRate}%</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="bg-warning/10 p-2 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-warning" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Issues</p>
                    <p className="text-2xl font-bold">{supplierData.totalIssues}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="bg-info/10 p-2 rounded-lg">
                    <FileText className="w-5 h-5 text-info" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Documents</p>
                    <p className="text-2xl font-bold">{supplierData.totalDocuments}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="bg-success/10 p-2 rounded-lg">
                    <Clock className="w-5 h-5 text-success" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Processed In</p>
                    <p className="text-2xl font-bold">{supplierData.processingTime}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Document Status */}
          <Card>
            <CardHeader>
              <CardTitle>Document Summary</CardTitle>
              <CardDescription>Status and compliance score for each document</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {supplierData.documents.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="flex-shrink-0">
                        {doc.status === "success" ? (
                          <div className="bg-success/10 p-2 rounded-lg">
                            <CheckCircle className="w-4 h-4 text-success" />
                          </div>
                        ) : doc.status === "error" ? (
                          <div className="bg-destructive/10 p-2 rounded-lg">
                            <XCircle className="w-4 h-4 text-destructive" />
                          </div>
                        ) : (
                          <div className="bg-warning/10 p-2 rounded-lg">
                            <AlertTriangle className="w-4 h-4 text-warning" />
                          </div>
                        )}
                      </div>
                      <div>
                        <h4 className="font-medium">{doc.name}</h4>
                        <p className="text-sm text-muted-foreground">{doc.type}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{doc.complianceScore}%</p>
                      <p className="text-sm text-muted-foreground">
                        {doc.issues} issue{doc.issues !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }
  };

  const renderAnalyticsTab = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Processing Analytics</CardTitle>
          <CardDescription>Detailed metrics from the analysis</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold mb-3">Processing Details</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Job ID:</span>
                  <span className="font-mono">{jobId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">LC Number:</span>
                  <span>{mockData.lcNumber}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Processed At:</span>
                  <span>{new Date(mockData.processedAt).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Processing Time:</span>
                  <span>{mockData.processingTime}</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-3">Analysis Summary</h4>
              <div className="space-y-2 text-sm">
                {mode === 'draft' ? (
                  <>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Risk Level:</span>
                      <Badge variant={mockData.riskLevel === 'high' ? 'destructive' : mockData.riskLevel === 'medium' ? 'secondary' : 'default'}>
                        {mockData.riskLevel?.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Clauses Analyzed:</span>
                      <span>{mockData.totalClauses}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Risks Identified:</span>
                      <span>{mockData.totalRisks}</span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Customs Ready:</span>
                      <Badge variant={supplierData.customsReady ? 'default' : 'destructive'}>
                        {supplierData.customsReady ? 'YES' : 'NO'}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Documents Processed:</span>
                      <span>{supplierData.totalDocuments}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Issues Found:</span>
                      <span>{supplierData.totalIssues}</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  // Show processing state if job is still running
  const processingState = renderProcessingState();
  if (processingState) {
    return (
      <div className="min-h-screen bg-background">
        {renderHeader()}
        {processingState}
      </div>
    );
  }

  // Main results view
  return (
    <div className={embedded ? "bg-transparent" : "bg-background min-h-screen"}>
      {/* Header */}
      {!embedded && (
        <header className="bg-card border-b border-gray-200">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Link to="/lcopilot/importer-dashboard">
                  <Button variant="outline" size="sm">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Dashboard
                  </Button>
                </Link>
                <div className="flex items-center gap-3">
                  <div className="bg-gradient-importer p-2 rounded-lg">
                    <FileText className="w-6 h-6 text-primary-foreground" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-foreground">Import Validation Results</h1>
                    <p className="text-sm text-muted-foreground">Review the results of your latest LC or supplier document validation</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </header>
      )}

      <div className={embedded ? "mx-auto w-full max-w-6xl py-4" : "container mx-auto px-4 py-8 max-w-6xl"}>
        {/* Status and Action Bar */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <StatusBadge status={mockData.overallStatus}>
                  {mockData.overallStatus === "success" ? "Success" : mockData.overallStatus === "error" ? "Error" : "Warning"}
                </StatusBadge>
                <div>
                  <h2 className="text-lg font-semibold">{mockData.lcNumber}</h2>
                  <p className="text-sm text-muted-foreground">
                    Completed on {new Date(mockData.processedAt).toLocaleDateString()}
                  </p>
                  {mode === 'supplier' && supplierData.totalIssues === 0 && (
                    <Badge className="mt-2 bg-green-600 text-white">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Bank Ready
                    </Badge>
                  )}
                  {mode === 'supplier' && supplierData.totalIssues > 0 && (
                    <Badge className="mt-2 bg-warning text-white">
                      <AlertTriangle className="w-3 h-3 mr-1" />
                      {supplierData.totalIssues} Issue{supplierData.totalIssues !== 1 ? 's' : ''} Require Correction
                    </Badge>
                  )}
                  {mode === 'draft' && (
                    <Badge className="mt-2 bg-blue-600 text-white">
                      <ShieldCheck className="w-3 h-3 mr-1" />
                      Risk Analysis Complete
                    </Badge>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3 flex-wrap">
                {/* Common actions */}
                <Button variant="outline" size="sm" onClick={handleReAnalyze}>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Re-analyze
                </Button>
                <Button variant="outline" size="sm">
                  <Share2 className="w-4 h-4 mr-2" />
                  Share
                </Button>

                {/* Draft mode actions */}
                {mode === 'draft' && (
                  <Button
                    onClick={handleDownloadReport}
                    disabled={isGeneratingPackage}
                    className="bg-gradient-importer hover:opacity-90"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    {isGeneratingPackage ? 'Generating...' : 'Download Risk Report'}
                  </Button>
                )}

                {/* Supplier mode actions */}
                {mode === 'supplier' && (
                  <>
                    {/* Supplier fix pack actions (when issues exist) */}
                    {hasSupplierIssues && enableSupplierFixPack && (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowSupplierDialog(true)}
                        >
                          <Mail className="w-4 h-4 mr-2" />
                          Send to Supplier
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleDownloadSupplierFixPack}
                          disabled={isGeneratingFixPack}
                        >
                          <Package className="w-4 h-4 mr-2" />
                          {isGeneratingFixPack ? 'Generating...' : 'Download Fix Pack'}
                        </Button>
                      </>
                    )}

                    {/* Bank precheck (when no issues and feature flag enabled) */}
                    {isReadyToSubmit && enableBankPrecheck && (
                      <Button
                        className="bg-green-600 hover:bg-green-700 text-white"
                        size="sm"
                        onClick={() => setShowSubmitDialog(true)}
                      >
                        <Send className="w-4 h-4 mr-2" />
                        Request Bank Review
                      </Button>
                    )}

                    {/* Compliance report download */}
                    <Button
                      onClick={handleDownloadReport}
                      disabled={isGeneratingPackage}
                      className="bg-gradient-importer hover:opacity-90"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      {isGeneratingPackage ? 'Generating...' : 'Download Compliance Report'}
                    </Button>
                  </>
                )}

                {/* Invoice link (if available) */}
                {(mockData as any).invoiceId && (
                  <Link to={`/lcopilot/importer-dashboard?section=billing&invoice=${(mockData as any).invoiceId}`}>
                    <Button variant="outline" size="sm">
                      <Receipt className="w-4 h-4 mr-2" />
                      Invoice
                    </Button>
                  </Link>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className={`grid w-full ${mode === 'supplier' ? 'grid-cols-5' : 'grid-cols-4'}`}>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="details">
              {mode === 'draft' ? 'LC Clauses' : 'Documents'}
            </TabsTrigger>
            <TabsTrigger value="issues">
              {mode === 'draft' ? 'Risk Analysis' : 'Issues'}
            </TabsTrigger>
            {mode === 'supplier' && (
              <TabsTrigger value="history">Submission History</TabsTrigger>
            )}
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            {renderOverviewTab()}
          </TabsContent>

          <TabsContent value="details" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>
                  {mode === 'draft' ? 'LC Clauses Analysis' : 'Document Details'}
                </CardTitle>
                <CardDescription>
                  {mode === 'draft'
                    ? 'Detailed analysis of each LC clause and associated risks'
                    : 'Extracted data and compliance status for each document'
                  }
                </CardDescription>
              </CardHeader>
              <CardContent>
                {mode === 'draft' ? (
                  <div className="space-y-4">
                    {mockData.lcClauses.map((clause) => (
                      <div key={clause.id} className="border rounded-lg p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h4 className="font-semibold">{clause.type}</h4>
                            <Badge
                              variant={clause.riskLevel === 'high' ? 'destructive' :
                                     clause.riskLevel === 'medium' ? 'secondary' : 'default'}
                              className="mt-1"
                            >
                              {clause.riskLevel.toUpperCase()} RISK
                            </Badge>
                          </div>
                        </div>
                        <div className="bg-muted p-3 rounded text-sm mb-3">
                          <strong>Clause Text:</strong> {clause.text}
                        </div>
                        <div className="space-y-2 text-sm">
                          <div>
                            <strong>Analysis:</strong> {clause.analysis}
                          </div>
                          <div>
                            <strong>Recommendation:</strong> {clause.recommendation}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {supplierData.documents.map((doc) => (
                      <div key={doc.id} className="border rounded-lg p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h4 className="font-semibold">{doc.name}</h4>
                            <p className="text-sm text-muted-foreground">{doc.type}</p>
                          </div>
                          <div className="text-right">
                            <StatusBadge status={doc.status}>
                              {doc.status === "success" ? "Success" : doc.status === "error" ? "Error" : "Warning"}
                            </StatusBadge>
                            <p className="text-sm text-muted-foreground mt-1">
                              Score: {doc.complianceScore}%
                            </p>
                          </div>
                        </div>
                        <div className="bg-muted p-3 rounded">
                          <h5 className="font-medium mb-2">Extracted Data:</h5>
                          <div className="grid md:grid-cols-2 gap-2 text-sm">
                            {Object.entries(doc.extractedFields || {}).map(([key, value]) => {
                              // Handle objects, arrays, and null/undefined values
                              let displayValue: string;
                              if (value === null || value === undefined) {
                                displayValue = "N/A";
                              } else if (typeof value === "object" && !Array.isArray(value)) {
                                displayValue = JSON.stringify(value, null, 2);
                              } else if (Array.isArray(value)) {
                                displayValue = value.join(", ");
                              } else {
                                displayValue = String(value);
                              }
                              
                              return (
                                <div key={key} className="flex justify-between">
                                  <span className="text-muted-foreground capitalize">
                                    {key.replace(/([A-Z])/g, ' $1').trim()}:
                                  </span>
                                  <span>{displayValue}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="issues" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>
                  {mode === 'draft' ? 'Risk Analysis' : 'Compliance Issues'}
                </CardTitle>
                <CardDescription>
                  {mode === 'draft'
                    ? 'Detailed risk assessment and mitigation strategies'
                    : 'Issues found during document compliance checking'
                  }
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {mode === 'draft' ? (
                    // Draft mode: Show risk analysis (keep existing format)
                    mockData.risks.map((issue) => (
                      <div key={issue.id} className={`border rounded-lg p-4 ${
                        issue.severity === 'high' ? 'border-destructive/20 bg-destructive/5' :
                        issue.severity === 'medium' ? 'border-warning/20 bg-warning/5' :
                        'border-success/20 bg-success/5'
                      }`}>
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Badge
                              variant={issue.severity === 'high' ? 'destructive' :
                                     issue.severity === 'medium' ? 'secondary' : 'default'}
                            >
                              {issue.severity.toUpperCase()}
                            </Badge>
                            <span className="font-medium">{issue.category}</span>
                          </div>
                        </div>
                        <h4 className="font-semibold mb-2">{issue.title}</h4>
                        <p className="text-sm text-muted-foreground mb-3">{issue.description}</p>
                        {('businessImpact' in issue) && (
                          <div className="space-y-2 mb-3 text-sm">
                            <div>
                              <strong>Business Impact:</strong> {issue.businessImpact}
                            </div>
                            {'financialImpact' in issue && (
                              <div>
                                <strong>Financial Impact:</strong> {issue.financialImpact}
                              </div>
                            )}
                          </div>
                        )}
                        <div className="bg-card p-3 rounded border">
                          <p className="text-sm">
                            <strong>Recommendation:</strong> {issue.recommendation}
                          </p>
                        </div>
                      </div>
                    ))
                  ) : (
                    // Supplier document mode: Use DiscrepancyGuidance component
                    supplierData.issues.map((issue) => {
                      // Map issue structure to DiscrepancyGuidance format
                      const document = supplierData.documents.find(d => d.id === issue.documentId);
                      return (
                        <DiscrepancyGuidance
                          key={issue.id}
                          discrepancy={{
                            id: issue.id,
                            title: issue.title,
                            description: issue.description,
                            severity: issue.severity === 'high' ? 'critical' : issue.severity === 'medium' ? 'major' : 'minor',
                            documentName: document?.name || 'Unknown Document',
                            documentType: document?.type,
                            rule: issue.category,
                            expected: 'expected' in issue ? (issue as any).expected : '',
                            actual: 'actual' in issue ? (issue as any).actual : '',
                            suggestion: issue.recommendation,
                            field: 'field' in issue ? (issue as any).field : undefined,
                          }}
                          onRevalidate={async (id) => {
                            // In a real app, call API to re-validate
                            console.log("Re-validating discrepancy:", id);
                            toast({
                              title: "Re-validation Started",
                              description: "Your documents are being re-validated. Results will appear shortly.",
                            });
                          }}
                          onUploadFixed={async (id, file) => {
                            // In a real app, upload fixed document
                            console.log("Uploading fixed document for discrepancy:", id, file.name);
                            toast({
                              title: "File Uploaded",
                              description: "Your corrected document has been uploaded. Click 'Re-validate' to check again.",
                            });
                          }}
                          validationSessionId={supplierData.lcNumber}
                        />
                      );
                    })
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {mode === 'supplier' && (
            <TabsContent value="history" className="mt-6">
              <Card>
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
                  {submissionHistory.length === 0 ? (
                    <div className="text-center py-12">
                      <Building2 className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                      <p className="text-muted-foreground mb-2">No submissions yet</p>
                      <p className="text-sm text-muted-foreground">
                        Submit this LC to a bank to track its submission history
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {submissionHistory.map((submission) => (
                        <Card key={submission.id} className="border-l-4 border-l-primary">
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <Building2 className="w-4 h-4 text-muted-foreground" />
                                  <span className="font-medium">{submission.bank_name}</span>
                                  <Badge
                                    variant={
                                      submission.status === "approved"
                                        ? "default"
                                        : submission.status === "rejected"
                                        ? "destructive"
                                        : "secondary"
                                    }
                                  >
                                    {submission.status}
                                  </Badge>
                                </div>
                                <div className="text-sm text-muted-foreground space-y-1">
                                  <div>Submitted: {format(new Date(submission.submitted_at), "MMM d, yyyy 'at' HH:mm")}</div>
                                  <div>By: {submission.submitted_by}</div>
                                  {submission.bank_response && (
                                    <div className="mt-2 p-2 bg-muted rounded text-xs">
                                      <strong>Bank Response:</strong> {submission.bank_response}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          )}

          <TabsContent value="analytics" className="mt-6">
            {renderAnalyticsTab()}
          </TabsContent>
        </Tabs>

        {/* Request Bank Review Dialog (Supplier mode, no issues, feature flag enabled) */}
        {mode === 'supplier' && enableBankPrecheck && (
          <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Send className="w-5 h-5" />
                  Request Bank Pre-Check Review
                </DialogTitle>
                <DialogDescription>
                  Request the bank to review LC {lcNumber} before final submission
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-medium mb-2">Review Request Details</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">LC Number:</span>
                      <span className="font-medium">{lcNumber}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Documents:</span>
                      <span className="font-medium">{supplierData.totalDocuments}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Compliance Rate:</span>
                      <span className="font-medium text-green-600">
                        {supplierData.complianceRate}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Status:</span>
                      <Badge className="bg-green-600">Bank Ready</Badge>
                    </div>
                  </div>
                </div>
                <div className="p-4 border rounded-lg">
                  <p className="text-sm text-muted-foreground">
                    This will request the bank to perform a pre-check review of your LC and documents.
                    The bank will provide feedback before final submission.
                  </p>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowSubmitDialog(false)} disabled={isSubmitting}>
                  Cancel
                </Button>
                <Button onClick={handleSubmitToBank} disabled={isSubmitting} className="bg-green-600 hover:bg-green-700">
                  {isSubmitting ? (
                    <>
                      <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                      Requesting...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Request Bank Review
                    </>
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}

        {/* Send to Supplier Dialog (Supplier mode, issues exist) */}
        {mode === 'supplier' && enableSupplierFixPack && (
          <Dialog open={showSupplierDialog} onOpenChange={setShowSupplierDialog}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Mail className="w-5 h-5" />
                  Send Fix Pack to Supplier
                </DialogTitle>
                <DialogDescription>
                  Send the supplier fix pack with all issues and corrections needed
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="supplier-email">Supplier Email Address *</Label>
                  <Input
                    id="supplier-email"
                    type="email"
                    placeholder="supplier@example.com"
                    value={supplierEmail}
                    onChange={(e) => setSupplierEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="supplier-message">Message (Optional)</Label>
                  <Textarea
                    id="supplier-message"
                    placeholder="Add a custom message to include with the fix pack..."
                    value={supplierMessage}
                    onChange={(e) => setSupplierMessage(e.target.value)}
                    rows={4}
                  />
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-medium mb-2 text-sm">What will be sent:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>LC Number: {lcNumber}</li>
                    <li>{supplierData.totalIssues} issue(s) requiring correction</li>
                    <li>Detailed recommendations for each issue</li>
                    <li>Document status summary</li>
                    <li>Next steps and action items</li>
                  </ul>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowSupplierDialog(false)} disabled={isSendingToSupplier}>
                  Cancel
                </Button>
                <Button onClick={handleSendToSupplier} disabled={isSendingToSupplier || !supplierEmail.trim()}>
                  {isSendingToSupplier ? (
                    <>
                      <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                      Sending...
                    </>
                  ) : (
                    <>
                      <Mail className="w-4 h-4 mr-2" />
                      Send to Supplier
                    </>
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  );
}
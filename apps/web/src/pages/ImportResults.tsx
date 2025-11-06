import { useState, useEffect } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/ui/status-badge";
import { useToast } from "@/hooks/use-toast";
import { useJob, useResults, usePackage } from "@/hooks/use-lcopilot";
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
  PieChart
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

export default function ImportResults() {
  const { jobId } = useParams<{ jobId: string }>();
  const [searchParams] = useSearchParams();
  const mode = searchParams.get('mode') as 'draft' | 'supplier' || 'draft';
  const { toast } = useToast();

  // Hooks for API calls - only use for non-demo jobs
  const shouldUseAPI = jobId && !jobId.startsWith('demo-');
  const { jobStatus, isPolling, startPolling } = useJob(shouldUseAPI ? jobId : null);
  const { results, getResults, isLoading: isLoadingResults } = useResults();
  const { generatePackage, downloadPackage, isLoading: isGeneratingPackage } = usePackage();

  const [activeTab, setActiveTab] = useState("overview");
  const [useMockData, setUseMockData] = useState(false);

  // Get appropriate mock data based on mode
  const mockData = mode === 'draft' ? mockDraftLCResults : mockSupplierResults;

  useEffect(() => {
    // For demo job IDs, immediately use mock data
    if (jobId && jobId.startsWith('demo-')) {
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
  }, [jobId, jobStatus]);

  useEffect(() => {
    if (jobId && jobStatus?.status === 'completed') {
      getResults(jobId);
    }
  }, [jobId, jobStatus, getResults]);

  const handleDownloadReport = async () => {
    console.log("Download button clicked, jobId:", jobId);

    if (!jobId) {
      console.log("No jobId, returning early");
      toast({
        title: "Error",
        description: "No job ID found. Please try re-analyzing.",
        variant: "destructive",
      });
      return;
    }

    // Demo mode: simulate download for demo job IDs
    if (jobId.startsWith('demo-')) {
      console.log("Demo mode detected, creating mock download");

      // Create mock file content
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
Compliance Rate: ${mockSupplierResults.complianceRate}%
Total Documents: ${mockSupplierResults.totalDocuments}
Issues Found: ${mockSupplierResults.totalIssues}
Customs Ready: ${mockSupplierResults.customsReady ? 'YES' : 'NO'}

DOCUMENT STATUS:
${mockSupplierResults.documents.map(doc => `
- ${doc.name} (${doc.type})
  Status: ${doc.status.toUpperCase()}
  Compliance Score: ${doc.complianceScore}%
  Issues: ${doc.issues}
`).join('\n')}

COMPLIANCE ISSUES:
${mockSupplierResults.issues.map(issue => `
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
                    <p className="text-2xl font-bold">{mockSupplierResults.complianceRate}%</p>
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
                    <p className="text-2xl font-bold">{mockSupplierResults.totalIssues}</p>
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
                    <p className="text-2xl font-bold">{mockSupplierResults.totalDocuments}</p>
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
                    <p className="text-2xl font-bold">{mockSupplierResults.processingTime}</p>
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
                {mockSupplierResults.documents.map((doc) => (
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
                      <Badge variant={mockSupplierResults.customsReady ? 'default' : 'destructive'}>
                        {mockSupplierResults.customsReady ? 'YES' : 'NO'}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Documents Processed:</span>
                      <span>{mockSupplierResults.totalDocuments}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Issues Found:</span>
                      <span>{mockSupplierResults.totalIssues}</span>
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
                <StatusBadge status={mockData.overallStatus} />
                <div>
                  <h2 className="text-lg font-semibold">{mockData.lcNumber}</h2>
                  <p className="text-sm text-muted-foreground">
                    Completed on {new Date(mockData.processedAt).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Button variant="outline" size="sm" onClick={handleReAnalyze}>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Re-analyze
                </Button>
                <Button variant="outline" size="sm">
                  <Share2 className="w-4 h-4 mr-2" />
                  Share
                </Button>
                <Button
                  onClick={handleDownloadReport}
                  disabled={isGeneratingPackage}
                  className="bg-gradient-importer hover:opacity-90"
                >
                  <Download className="w-4 h-4 mr-2" />
                  {isGeneratingPackage ? 'Generating...' : `Download ${mode === 'draft' ? 'Risk Report' : 'Compliance Report'}`}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="details">
              {mode === 'draft' ? 'LC Clauses' : 'Documents'}
            </TabsTrigger>
            <TabsTrigger value="issues">
              {mode === 'draft' ? 'Risk Analysis' : 'Issues'}
            </TabsTrigger>
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
                    {mockSupplierResults.documents.map((doc) => (
                      <div key={doc.id} className="border rounded-lg p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h4 className="font-semibold">{doc.name}</h4>
                            <p className="text-sm text-muted-foreground">{doc.type}</p>
                          </div>
                          <div className="text-right">
                            <StatusBadge status={doc.status} />
                            <p className="text-sm text-muted-foreground mt-1">
                              Score: {doc.complianceScore}%
                            </p>
                          </div>
                        </div>
                        <div className="bg-muted p-3 rounded">
                          <h5 className="font-medium mb-2">Extracted Data:</h5>
                          <div className="grid md:grid-cols-2 gap-2 text-sm">
                            {Object.entries(doc.extractedFields).map(([key, value]) => (
                              <div key={key} className="flex justify-between">
                                <span className="text-muted-foreground capitalize">
                                  {key.replace(/([A-Z])/g, ' $1').trim()}:
                                </span>
                                <span>{value}</span>
                              </div>
                            ))}
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
                  {(mode === 'draft' ? mockData.risks : mockSupplierResults.issues).map((issue) => (
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

                      {mode === 'draft' && 'businessImpact' in issue && (
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
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analytics" className="mt-6">
            {renderAnalyticsTab()}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
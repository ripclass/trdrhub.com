import { useState, useEffect } from "react";
import { Link, useSearchParams, useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/ui/status-badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useJob, useResults, usePackage } from "@/hooks/use-lcopilot";
import { useVersions, type LCVersion } from "@/hooks/use-versions";
import { RateLimitNotice } from "@/components/RateLimitNotice";
import { VersionComparisonDialog } from "@/components/VersionComparison";
import { useToast } from "@/hooks/use-toast";
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
  GitBranch
} from "lucide-react";

// Mock validation results - replace with real API data
//
// 🟢 CURRENT: PASSING VALIDATION (All documents compliant, ready for customs)
// 🔴 TO TEST FAILING: Change totalDiscrepancies to 2, overallStatus to "warning", add discrepancies array
//
const mockResults = {
  lcNumber: "BD-2024-001",
  status: "completed",
  processedAt: "2024-01-15T14:30:00Z",
  processingTime: "1.8 minutes",
  totalDocuments: 5,
  totalDiscrepancies: 0, // ✅ PASSING - No discrepancies found
  overallStatus: "success" as "success" | "error" | "warning",
  documents: [
    {
      id: "1",
      name: "Bill_of_Lading.pdf",
      type: "Bill of Lading",
      status: "success" as const,
      discrepancies: 0,
      extractedFields: {
        vesselName: "MV Bangladesh Express",
        portOfLoading: "Chittagong",
        portOfDischarge: "Hamburg",
        dateOfShipment: "2024-01-10"
      }
    },
    {
      id: "2",
      name: "Commercial_Invoice.pdf",
      type: "Commercial Invoice",
      status: "success" as const,
      discrepancies: 0,
      extractedFields: {
        invoiceNumber: "INV-2024-001",
        invoiceDate: "2024-01-12",
        totalAmount: "USD 50,000",
        currency: "USD"
      }
    },
    {
      id: "3",
      name: "Packing_List.pdf", 
      type: "Packing List",
      status: "success" as const,
      discrepancies: 0,
      extractedFields: {
        totalPackages: "100",
        grossWeight: "2500 KG",
        netWeight: "2300 KG"
      }
    },
    {
      id: "4",
      name: "Insurance_Certificate.pdf",
      type: "Insurance Certificate", 
      status: "success" as const,
      discrepancies: 0,
      extractedFields: {
        policyNumber: "INS-2024-001",
        insuredAmount: "USD 55,000",
        validUntil: "2024-03-15"
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
        certificateNumber: "COO-2024-001"
      }
    }
  ],
  discrepancies: [] // ✅ No discrepancies - all documents are compliant
};

/*
// 🔴 FAILING VALIDATION MOCK DATA (Uncomment to test failing scenario)
const mockResults = {
  lcNumber: "BD-2024-001",
  status: "completed",
  processedAt: "2024-01-15T14:30:00Z",
  processingTime: "2.3 minutes",
  totalDocuments: 5,
  totalDiscrepancies: 2, // ❌ FAILING - Has discrepancies
  overallStatus: "warning" as "success" | "error" | "warning",
  documents: [
    {
      id: "1",
      name: "Bill_of_Lading.pdf",
      type: "Bill of Lading",
      status: "success" as const,
      discrepancies: 0,
      extractedFields: {
        vesselName: "MV Bangladesh Express",
        portOfLoading: "Chittagong",
        portOfDischarge: "Hamburg",
        dateOfShipment: "2024-01-10"
      }
    },
    {
      id: "2",
      name: "Commercial_Invoice.pdf",
      type: "Commercial Invoice",
      status: "error" as const, // ❌ This document has issues
      discrepancies: 2,
      extractedFields: {
        invoiceNumber: "INV-2024-001",
        invoiceDate: "2024-01-08", // ❌ Date issue
        totalAmount: "USD 50,000",
        currency: "USD"
      }
    },
    {
      id: "3",
      name: "Packing_List.pdf",
      type: "Packing List",
      status: "success" as const,
      discrepancies: 0,
      extractedFields: {
        totalPackages: "100",
        grossWeight: "2500 KG",
        netWeight: "2300 KG"
      }
    },
    {
      id: "4",
      name: "Insurance_Certificate.pdf",
      type: "Insurance Certificate",
      status: "success" as const,
      discrepancies: 0,
      extractedFields: {
        policyNumber: "INS-2024-001",
        insuredAmount: "USD 55,000",
        validUntil: "2024-03-15"
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
        certificateNumber: "COO-2024-001"
      }
    }
  ],
  discrepancies: [
    {
      id: "1",
      documentId: "2",
      documentName: "Commercial_Invoice.pdf",
      severity: "high" as const,
      rule: "UCP 600 Article 18",
      title: "Invoice Date Discrepancy",
      description: "Invoice date (2024-01-08) is earlier than LC issue date (2024-01-10). This violates UCP 600 requirements.",
      suggestion: "Ensure invoice date is on or after the LC issue date. Consider reissuing the invoice with correct date.",
      field: "invoiceDate",
      expected: "On or after 2024-01-10",
      actual: "2024-01-08"
    },
    {
      id: "2",
      documentId: "2",
      documentName: "Commercial_Invoice.pdf",
      severity: "medium" as const,
      rule: "UCP 600 Article 14",
      title: "Amount Tolerance Issue",
      description: "Invoice amount may exceed LC amount tolerance. Please verify against LC terms.",
      suggestion: "Check if the invoice amount falls within the acceptable tolerance range as specified in the LC.",
      field: "totalAmount",
      expected: "Within LC tolerance",
      actual: "USD 50,000"
    }
  ]
};
*/

export default function Results() {
  const { jobId } = useParams<{ jobId?: string }>();
  const [searchParams] = useSearchParams();
  const lcNumber = searchParams.get('lc') || mockResults.lcNumber;
  const [activeTab, setActiveTab] = useState("overview");
  const [showRateLimit, setShowRateLimit] = useState(false);
  const [actualResults, setActualResults] = useState<any>(null);
  const [versions, setVersions] = useState<LCVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string>('');
  const [currentVersion, setCurrentVersion] = useState<LCVersion | null>(null);

  const { toast } = useToast();
  const navigate = useNavigate();
  const { jobStatus, isPolling } = useJob(jobId || null);
  const { results, getResults, isLoading: isLoadingResults } = useResults();
  const { generatePackage, downloadPackage, isLoading: isPackaging, error: packageError, clearError } = usePackage();
  const { getVersions } = useVersions();
  const [isManualPackaging, setIsManualPackaging] = useState(false);

  // Use actual results if available, otherwise fall back to mock
  const currentResults = actualResults || mockResults;

  const successCount = currentResults.documents.filter(d => d.status === "success").length;
  const errorCount = currentResults.documents.filter(d => d.status === "error").length;
  const successRate = Math.round((successCount / currentResults.totalDocuments) * 100);

  // Fetch results when jobId is available and job is completed
  useEffect(() => {
    console.log('🔍 Results page loaded with jobId:', jobId);
    console.log('📊 Job status:', jobStatus);

    if (jobId && jobStatus?.status === 'completed') {
      console.log('✅ Job completed, fetching results...');
      getResults(jobId).then(setActualResults).catch(console.error);
    } else if (jobId && !jobStatus) {
      console.log('⏳ Job ID provided but no status yet, will poll...');
    }
  }, [jobId, jobStatus?.status, getResults]);

  // Fetch versions for this LC
  useEffect(() => {
    if (lcNumber) {
      getVersions(lcNumber)
        .then(versions => {
          setVersions(versions);
          // If we have a current jobId, find the corresponding version
          if (jobId) {
            const currentVer = versions.find(v => v.job_id === jobId);
            if (currentVer) {
              setCurrentVersion(currentVer);
              setSelectedVersion(currentVer.version);
            }
          } else if (versions.length > 0) {
            // Default to latest version
            const latest = versions[versions.length - 1];
            setCurrentVersion(latest);
            setSelectedVersion(latest.version);
          }
        })
        .catch(console.error);
    }
  }, [lcNumber, jobId, getVersions]);

  // Handle package generation
  const handleGeneratePackage = async () => {
    console.log('🚀 Generate Package button clicked!');
    console.log('🔍 Current jobId:', jobId);
    console.log('🔍 Current discrepancies:', currentResults.totalDiscrepancies);
    console.log('🔍 Toast function available:', typeof toast);

    if (!jobId) {
      console.log('❌ No jobId found');
      toast({
        title: "Error",
        description: "No job ID available for package generation.",
        variant: "destructive",
      });
      return;
    }

    try {
      clearError();
      setShowRateLimit(false);

      console.log('📢 Showing initial toast...');
      toast({
        title: "Generating Package",
        description: "Creating your customs-ready document pack...",
      });

      // Development mode - simulate package generation
      if (jobId.startsWith('job_')) {
        console.log('🔧 DEV MODE: Simulating package generation for jobId:', jobId);

        setIsManualPackaging(true);

        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Mock successful package generation
        const mockPackageInfo = {
          downloadUrl: `blob:mock-download-${jobId}`,
          fileName: `LC_CustomsPack_${jobId.slice(-8)}.zip`,
          fileSize: 1024 * 1024 * 2.5, // 2.5MB
          expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
        };

        toast({
          title: "Package Ready! 📦",
          description: "Your customs-ready pack has been generated successfully. In production, this would download automatically.",
        });

        console.log('📦 Mock package info:', mockPackageInfo);
        console.log('💾 In production, file would download automatically');

        // Create a mock downloadable file for demo
        const mockFileContent = `LC Customs-Ready Package - ${lcNumber}

Generated: ${new Date().toLocaleString()}
Job ID: ${jobId}

This is a mock file for development purposes.
In production, this would contain:
- Validated commercial invoice
- Packing list
- Bill of lading
- Certificate of origin
- Insurance certificate
- All required customs documentation

Status: Ready for customs clearance
Total documents: ${currentResults.totalDocuments}
Compliance check: PASSED
        `;

        // Create and download the mock file
        const blob = new Blob([mockFileContent], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = mockPackageInfo.fileName.replace('.zip', '.txt'); // Use .txt for demo
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        // Show success feedback
        toast({
          title: "Download Started! 📥",
          description: `${mockPackageInfo.fileName.replace('.zip', '.txt')} (${(mockPackageInfo.fileSize / (1024 * 1024)).toFixed(1)}MB mock file)`,
        });

        console.log('✅ Mock file download triggered');
        setIsManualPackaging(false);
        return;
      }

      // Real API call for production
      const packageInfo = await generatePackage(jobId);

      toast({
        title: "Package Ready",
        description: "Your customs-ready pack is ready for download.",
      });

      // Auto-download the package
      await downloadPackage(packageInfo.downloadUrl, packageInfo.fileName);

    } catch (error: any) {
      console.error('❌ Package generation error:', error);
      setIsManualPackaging(false); // Reset loading state on error
      if (error.type === 'rate_limit') {
        setShowRateLimit(true);
      } else {
        toast({
          title: "Package Generation Failed",
          description: error.message || "Failed to generate package. Please try again.",
          variant: "destructive",
        });
      }
    }
  };

  // Handle re-upload navigation
  const handleReUpload = () => {
    console.log('🔄 Navigating back to upload page to fix discrepancies');
    navigate('/export-lc-upload');
  };

  // Handle version selection
  const handleVersionChange = (version: string) => {
    setSelectedVersion(version);
    const versionData = versions.find(v => v.version === version);
    if (versionData) {
      setCurrentVersion(versionData);
      // Navigate to the new version's results
      navigate(`/lcopilot/results/${versionData.job_id}?lc=${lcNumber}`);
    }
  };


  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-gray-200">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/dashboard">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Dashboard
                </Button>
              </Link>
              <div className="flex items-center gap-3">
                <div className="bg-gradient-primary p-2 rounded-lg">
                  <FileText className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <div className="flex items-center gap-3">
                    <h1 className="text-xl font-bold text-foreground">Validation Results</h1>
                    {versions.length > 1 && (
                      <Badge variant="outline" className="flex items-center gap-1">
                        <GitBranch className="w-3 h-3" />
                        Amended
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-4">
                    <p className="text-sm text-muted-foreground">LC Number: {lcNumber}</p>
                    {currentVersion && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Version:</span>
                        <Select value={selectedVersion} onValueChange={handleVersionChange}>
                          <SelectTrigger className="w-24 h-6 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {versions.map((version) => (
                              <SelectItem key={version.version} value={version.version}>
                                {version.version}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {versions.length > 1 && (
                <VersionComparisonDialog
                  lcNumber={lcNumber}
                  versions={versions}
                  currentVersion={selectedVersion}
                />
              )}
              <Button variant="outline" size="sm">
                <Share2 className="w-4 h-4 mr-2" />
                Share
              </Button>
              <Button variant="outline" size="sm">
                <PrinterIcon className="w-4 h-4 mr-2" />
                Print
              </Button>
              <Button className="bg-gradient-primary hover:opacity-90">
                <Download className="w-4 h-4 mr-2" />
                Download Report
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Development Mode Banner */}
        {jobId && jobId.startsWith('job_') && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
              <h4 className="font-semibold text-blue-800">Development Mode</h4>
            </div>
            <p className="text-sm text-blue-700 mt-1">
              Using mock data for demo. Job ID: <code className="bg-blue-100 px-1 rounded">{jobId}</code>
            </p>
          </div>
        )}

        {/* Status Overview */}
        <Card className="mb-8 shadow-soft border-0">
          <CardContent className="p-6">
            <div className="grid md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className={`w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center ${
                  currentResults.overallStatus === "success" ? "bg-success/10" :
                  currentResults.overallStatus === "error" ? "bg-destructive/10" : "bg-warning/10"
                }`}>
                  {currentResults.overallStatus === "success" ? (
                    <CheckCircle className="w-8 h-8 text-success" />
                  ) : currentResults.overallStatus === "error" ? (
                    <XCircle className="w-8 h-8 text-destructive" />
                  ) : (
                    <AlertTriangle className="w-8 h-8 text-warning" />
                  )}
                </div>
                <StatusBadge status={currentResults.overallStatus} className="text-sm font-medium">
                  {currentResults.totalDiscrepancies === 0 ? "No Issues Found" : 
                   `${currentResults.totalDiscrepancies} Issues Found`}
                </StatusBadge>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Processing Summary</h3>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Documents:</span>
                    <span className="font-medium">{currentResults.totalDocuments}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Success Rate:</span>
                    <span className="font-medium text-success">{successRate}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Processing Time:</span>
                    <span className="font-medium">{currentResults.processingTime}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Validation Results</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <span className="text-sm">{successCount} documents passed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-destructive rounded-full"></div>
                    <span className="text-sm">{errorCount} documents with issues</span>
                  </div>
                  <Progress value={successRate} className="h-2 mt-2" />
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Next Steps</h3>
                <div className="space-y-2">
                  {/* Show loading state while polling */}
                  {isPolling && (
                    <div className="text-center py-2">
                      <div className="animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full mx-auto mb-2"></div>
                      <p className="text-xs text-muted-foreground">Processing documents...</p>
                    </div>
                  )}

                  {/* Show actions when processing is complete */}
                  {!isPolling && (
                    <div className="space-y-2">
                      {/* Re-upload button - shown when there are discrepancies */}
                      {currentResults.totalDiscrepancies > 0 && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full border-warning text-warning hover:bg-warning hover:text-warning-foreground"
                            onClick={handleReUpload}
                          >
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Re-upload Fixed Documents
                          </Button>
                          <p className="text-xs text-muted-foreground text-center">
                            ⚠️ LC will be rejected by bank - fix discrepancies first
                          </p>
                        </>
                      )}

                      {/* Generate Pack button - always shown but conditionally disabled */}
                      <Button
                        className={`w-full ${currentResults.totalDiscrepancies > 0
                          ? 'opacity-50 cursor-not-allowed bg-gray-400'
                          : 'bg-gradient-exporter hover:opacity-90'
                        }`}
                        size="sm"
                        onClick={handleGeneratePackage}
                        disabled={currentResults.totalDiscrepancies > 0 || isPackaging || isManualPackaging}
                      >
                        {(isPackaging || isManualPackaging) ? (
                          <>
                            <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                            Generating Pack...
                          </>
                        ) : (
                          <>
                            <Download className="w-4 h-4 mr-2" />
                            Generate Customs-Ready Pack
                          </>
                        )}
                      </Button>

                      {/* Status message */}
                      <p className={`text-xs text-center ${
                        currentResults.totalDiscrepancies > 0
                          ? 'text-muted-foreground'
                          : 'text-success'
                      }`}>
                        {currentResults.totalDiscrepancies > 0
                          ? '🚫 Cannot generate pack until all issues are resolved'
                          : '✅ Ready for customs clearance'
                        }
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Detailed Results */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="documents">Documents ({currentResults.totalDocuments})</TabsTrigger>
            <TabsTrigger value="discrepancies" className="relative">
              Discrepancies ({currentResults.totalDiscrepancies})
              {currentResults.totalDiscrepancies > 0 && (
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-destructive rounded-full"></div>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Processing Timeline */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    Processing Timeline
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Documents Uploaded</p>
                      <p className="text-xs text-muted-foreground">14:28 - 5 files received</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">OCR Processing Complete</p>
                      <p className="text-xs text-muted-foreground">14:29 - Text extracted</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">AI Data Extraction</p>
                      <p className="text-xs text-muted-foreground">14:30 - Fields identified</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-warning rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Compliance Check Complete</p>
                      <p className="text-xs text-muted-foreground">14:30 - 2 issues found</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Quick Stats */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle>Validation Statistics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-success/5 border border-success/20 rounded-lg">
                      <div className="text-2xl font-bold text-success">{successCount}</div>
                      <div className="text-sm text-muted-foreground">Passed</div>
                    </div>
                    <div className="text-center p-3 bg-destructive/5 border border-destructive/20 rounded-lg">
                      <div className="text-2xl font-bold text-destructive">{errorCount}</div>
                      <div className="text-sm text-muted-foreground">Issues</div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>High Priority Issues:</span>
                      <span className="font-medium text-destructive">
                        {currentResults.discrepancies.filter(d => d.severity === "high").length}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Medium Priority Issues:</span>
                      <span className="font-medium text-warning">
                        {currentResults.discrepancies.filter(d => d.severity === "medium").length}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Fields Extracted:</span>
                      <span className="font-medium">23</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="documents" className="space-y-4">
            {currentResults.documents.map((document) => (
              <Card key={document.id} className="shadow-soft border-0">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        document.status === "success" ? "bg-success/10" : "bg-destructive/10"
                      }`}>
                        <FileText className={`w-5 h-5 ${
                          document.status === "success" ? "text-success" : "text-destructive"
                        }`} />
                      </div>
                      <div>
                        <CardTitle className="text-base">{document.name}</CardTitle>
                        <CardDescription>{document.type}</CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge status={document.status}>
                        {document.discrepancies === 0 ? "Valid" : `${document.discrepancies} Issues`}
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
            {currentResults.discrepancies.length === 0 ? (
              <Card className="shadow-soft border-0">
                <CardContent className="p-8 text-center">
                  <div className="bg-success/10 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-success" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">No Discrepancies Found!</h3>
                  <p className="text-muted-foreground">All your LC documents passed validation successfully.</p>
                </CardContent>
              </Card>
            ) : (
              currentResults.discrepancies.map((discrepancy) => (
                <Card key={discrepancy.id} className={`shadow-soft border-0 ${
                  discrepancy.severity === "high" ? "border-l-4 border-l-destructive" : "border-l-4 border-l-warning"
                }`}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant={discrepancy.severity === "high" ? "destructive" : "secondary"}>
                            {discrepancy.severity.toUpperCase()} PRIORITY
                          </Badge>
                          <span className="text-sm text-muted-foreground">{discrepancy.rule}</span>
                        </div>
                        <CardTitle className="text-lg text-foreground">{discrepancy.title}</CardTitle>
                        <CardDescription className="mt-2">
                          Document: {discrepancy.documentName}
                        </CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="bg-secondary/20 p-4 rounded-lg border border-gray-200/50">
                      <h4 className="font-semibold text-foreground mb-2">Issue Description</h4>
                      <p className="text-sm text-muted-foreground">{discrepancy.description}</p>
                    </div>
                    
                    <div className="grid md:grid-cols-2 gap-4">
                      <div>
                        <h5 className="font-semibold text-sm text-foreground mb-2">Expected</h5>
                        <div className="bg-success/5 border border-success/20 p-3 rounded-lg">
                          <p className="text-sm text-success font-mono">{discrepancy.expected}</p>
                        </div>
                      </div>
                      <div>
                        <h5 className="font-semibold text-sm text-foreground mb-2">Found</h5>
                        <div className="bg-destructive/5 border border-destructive/20 p-3 rounded-lg">
                          <p className="text-sm text-destructive font-mono">{discrepancy.actual}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-info/5 border border-info/20 p-4 rounded-lg">
                      <h4 className="font-semibold text-info mb-2">💡 Suggested Solution</h4>
                      <p className="text-sm text-muted-foreground">{discrepancy.suggestion}</p>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>
        </Tabs>

        {/* Rate Limit Notice */}
        {showRateLimit && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="max-w-md">
              <RateLimitNotice
                onRetry={() => {
                  setShowRateLimit(false);
                  handleGeneratePackage();
                }}
                onCancel={() => setShowRateLimit(false)}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/ui/status-badge";
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
  TrendingUp,
  BarChart3,
  PieChart
} from "lucide-react";

// Mock supplier document compliance results
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
        description: "Raw Cotton Bales",
        packingDetails: "Compressed cotton bales"
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
        portOfDischarge: "Chittagong",
        notifyParty: "Bangladesh Textiles Ltd"
      }
    },
    {
      id: "4",
      name: "Certificate_of_Origin.pdf",
      type: "Certificate of Origin",
      status: "success" as const, 
      issues: 0,
      complianceScore: 100,
      extractedFields: {
        originCountry: "India",
        issuingAuthority: "Indian Export Authority",
        certificateNumber: "COO-IND-001",
        productOrigin: "Maharashtra, India",
        exporterDetails: "Indian Cotton Mills Ltd"
      }
    }
  ],
  
  complianceIssues: [
    {
      id: "1",
      documentId: "1",
      documentName: "Suppliers_Commercial_Invoice.pdf",
      severity: "high" as const,
      category: "Amount Discrepancy",
      rule: "LC Value Compliance",
      title: "Invoice Amount Exceeds LC Limit",
      description: "Supplier's invoice amount (USD 51,500) exceeds the LC maximum value (USD 50,000). This creates a discrepancy that banks will reject.",
      impact: "Bank will refuse documents, causing delays and potential demurrage charges. Shipment may be held at port.",
      suggestion: "Contact supplier immediately to issue corrected invoice within LC amount or apply for LC amendment to increase value limit.",
      field: "totalAmount",
      lcValue: "≤ USD 50,000",
      actualValue: "USD 51,500",
      action: "critical"
    },
    {
      id: "2", 
      documentId: "1",
      documentName: "Suppliers_Commercial_Invoice.pdf",
      severity: "medium" as const,
      category: "Date Compliance",
      rule: "LC Timeline Requirements",
      title: "Invoice Date vs Shipment Timeline",
      description: "Invoice date (2024-01-12) is after the latest shipment date specified in LC (2024-01-10).",
      impact: "May cause presentation timeline issues and additional bank processing fees.",
      suggestion: "Verify with bank if this falls within acceptable tolerance period or request supplier clarification on shipment timing.",
      field: "invoiceDate",
      lcValue: "On or before 2024-01-10",
      actualValue: "2024-01-12",
      action: "review"
    },
    {
      id: "3",
      documentId: "2",
      documentName: "Suppliers_Packing_List.pdf",
      severity: "low" as const,
      category: "Quantity Variance",
      rule: "LC Quantity Terms",
      title: "Package Count Minor Discrepancy",
      description: "Packing list shows 95 bales while LC specifies approximately 100 bales. Within acceptable tolerance range.",
      impact: "Minor variance - within industry standard tolerance. Should not cause bank rejection.",
      suggestion: "Document the variance for customs records. No immediate action required.",
      field: "totalPackages",
      lcValue: "Approximately 100 bales",
      actualValue: "95 bales",
      action: "monitor"
    }
  ]
};

export default function SupplierDocumentResults() {
  const [searchParams] = useSearchParams();
  const lcNumber = searchParams.get('lc') || mockSupplierResults.lcNumber;
  const [activeTab, setActiveTab] = useState("overview");

  const successCount = mockSupplierResults.documents.filter(d => d.status === "success").length;
  const warningCount = mockSupplierResults.documents.filter(d => d.status === "warning").length;
  const errorCount = mockSupplierResults.documents.filter(d => d.status === "error").length;

  const highIssueCount = mockSupplierResults.complianceIssues.filter(i => i.severity === "high").length;
  const mediumIssueCount = mockSupplierResults.complianceIssues.filter(i => i.severity === "medium").length;
  const lowIssueCount = mockSupplierResults.complianceIssues.filter(i => i.severity === "low").length;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-gray-200">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/importer-dashboard">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Dashboard
                </Button>
              </Link>
              <div className="flex items-center gap-3">
                <div className="bg-gradient-primary p-2 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-foreground">Supplier Document Compliance</h1>
                  <p className="text-sm text-muted-foreground">LC Number: {lcNumber}</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
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
                {mockSupplierResults.customsReady ? "Download Customs Pack" : "Download Compliance Report"}
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Compliance Overview */}
        <Card className="mb-8 shadow-soft border-0">
          <CardContent className="p-6">
            <div className="grid md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className={`w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-between ${
                  mockSupplierResults.overallStatus === "success" ? "bg-success/10" :
                  mockSupplierResults.overallStatus === "error" ? "bg-destructive/10" : "bg-warning/10"
                }`}>
                  {mockSupplierResults.overallStatus === "success" ? (
                    <CheckCircle className="w-8 h-8 text-success" />
                  ) : mockSupplierResults.overallStatus === "error" ? (
                    <XCircle className="w-8 h-8 text-destructive" />
                  ) : (
                    <AlertTriangle className="w-8 h-8 text-warning" />
                  )}
                </div>
                <StatusBadge status={mockSupplierResults.overallStatus} className="text-sm font-medium">
                  {mockSupplierResults.totalIssues === 0 ? "Fully Compliant" : `${mockSupplierResults.totalIssues} Issues Found`}
                </StatusBadge>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Document Summary</h3>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Documents:</span>
                    <span className="font-medium">{mockSupplierResults.totalDocuments}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Compliance Rate:</span>
                    <span className={`font-medium ${mockSupplierResults.complianceRate >= 80 ? "text-success" : "text-warning"}`}>
                      {mockSupplierResults.complianceRate}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Processing Time:</span>
                    <span className="font-medium">{mockSupplierResults.processingTime}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Document Status</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <span className="text-sm">{successCount} documents compliant</span>
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
                      <span className="text-sm">{errorCount} with critical issues</span>
                    </div>
                  )}
                  <Progress value={mockSupplierResults.complianceRate} className="h-2 mt-2" />
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Recommended Actions</h3>
                <div className="space-y-2">
                  {mockSupplierResults.totalIssues > 0 ? (
                    <>
                      <Link to="/supplier-document-corrections">
                        <Button variant="outline" size="sm" className="w-full">
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Request Document Corrections
                        </Button>
                      </Link>
                      <p className="text-xs text-muted-foreground text-center">
                        Fix critical issues before bank presentation
                      </p>
                    </>
                  ) : (
                    <>
                      <Button className="w-full bg-gradient-primary hover:opacity-90" size="sm">
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Proceed to Customs
                      </Button>
                      <p className="text-xs text-success text-center">
                        Ready for customs clearance
                      </p>
                    </>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Detailed Results */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="documents">Documents ({mockSupplierResults.totalDocuments})</TabsTrigger>
            <TabsTrigger value="issues" className="relative">
              Issues ({mockSupplierResults.totalIssues})
              {mockSupplierResults.totalIssues > 0 && (
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-warning rounded-full"></div>
              )}
            </TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Processing Timeline */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    Document Check Timeline
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Supplier Documents Uploaded</p>
                      <p className="text-xs text-muted-foreground">14:28 - {mockSupplierResults.totalDocuments} documents received</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">LC Terms Retrieved</p>
                      <p className="text-xs text-muted-foreground">14:29 - Original LC requirements loaded</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-warning rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Compliance Cross-Check</p>
                      <p className="text-xs text-muted-foreground">14:30 - Against LC terms and regulations</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-warning rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Analysis Complete</p>
                      <p className="text-xs text-muted-foreground">14:30 - {mockSupplierResults.totalIssues} compliance issues found</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Compliance Statistics */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle>Compliance Statistics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-success/5 border border-success/20 rounded-lg">
                      <div className="text-2xl font-bold text-success">{mockSupplierResults.complianceRate}%</div>
                      <div className="text-sm text-muted-foreground">Compliance</div>
                    </div>
                    <div className="text-center p-3 bg-warning/5 border border-warning/20 rounded-lg">
                      <div className="text-2xl font-bold text-warning">{mockSupplierResults.totalIssues}</div>
                      <div className="text-sm text-muted-foreground">Issues</div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Critical Issues:</span>
                      <span className="font-medium text-destructive">{highIssueCount}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Medium Issues:</span>
                      <span className="font-medium text-warning">{mediumIssueCount}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Minor Issues:</span>
                      <span className="font-medium text-info">{lowIssueCount}</span>
                    </div>
                  </div>
                  
                  {mockSupplierResults.customsReady ? (
                    <div className="p-3 bg-success/5 border border-success/20 rounded-lg">
                      <p className="text-sm font-medium text-success">✓ Customs-Ready Status</p>
                      <p className="text-xs text-muted-foreground mt-1">Documents meet customs requirements</p>
                    </div>
                  ) : (
                    <div className="p-3 bg-warning/5 border border-warning/20 rounded-lg">
                      <p className="text-sm font-medium text-warning">⚠️ Action Required</p>
                      <p className="text-xs text-muted-foreground mt-1">Resolve {highIssueCount} critical issues before customs clearance</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="documents" className="space-y-4">
            {mockSupplierResults.documents.map((document) => (
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
                      <div className="text-right">
                        <StatusBadge status={document.status}>
                          {document.issues === 0 ? "Compliant" : `${document.issues} Issues`}
                        </StatusBadge>
                        <p className="text-xs text-muted-foreground mt-1">
                          Score: {document.complianceScore}%
                        </p>
                      </div>
                      <Button variant="outline" size="sm">
                        <Eye className="w-4 h-4 mr-2" />
                        View
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
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

          <TabsContent value="issues" className="space-y-4">
            {mockSupplierResults.complianceIssues.length === 0 ? (
              <Card className="shadow-soft border-0">
                <CardContent className="p-8 text-center">
                  <div className="bg-success/10 w-16 h-16 rounded-full flex items-center justify-between mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-success" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">Perfect Compliance!</h3>
                  <p className="text-muted-foreground">All supplier documents comply with LC requirements and are ready for customs clearance.</p>
                </CardContent>
              </Card>
            ) : (
              mockSupplierResults.complianceIssues.map((issue) => (
                <Card key={issue.id} className="shadow-soft border-0">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg mt-1 ${
                          issue.severity === "high" ? "bg-destructive/10" : 
                          issue.severity === "medium" ? "bg-warning/10" : "bg-info/10"
                        }`}>
                          {issue.severity === "high" ? (
                            <XCircle className="w-5 h-5 text-destructive" />
                          ) : issue.severity === "medium" ? (
                            <AlertTriangle className="w-5 h-5 text-warning" />
                          ) : (
                            <AlertTriangle className="w-5 h-5 text-info" />
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <CardTitle className="text-base">{issue.title}</CardTitle>
                            <Badge variant={issue.severity === "high" ? "destructive" : "secondary"} className="text-xs">
                              {issue.severity} priority
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {issue.action}
                            </Badge>
                          </div>
                          <CardDescription className="text-sm mb-2">
                            {issue.documentName} • {issue.category}
                          </CardDescription>
                          <p className="text-sm text-muted-foreground mb-3">{issue.description}</p>
                          
                          <div className="bg-warning/5 border border-warning/20 rounded-lg p-3 mb-3">
                            <p className="text-xs font-medium text-warning mb-1">⚠️ Business Impact</p>
                            <p className="text-xs text-muted-foreground">{issue.impact}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="grid md:grid-cols-2 gap-4 mb-4">
                      <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">LC Requirement</p>
                        <p className="text-sm font-mono bg-muted/50 p-2 rounded border">{issue.lcValue}</p>
                      </div>
                      <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Supplier Document</p>
                        <p className="text-sm font-mono bg-muted/50 p-2 rounded border">{issue.actualValue}</p>
                      </div>
                    </div>
                    <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
                      <p className="text-xs font-medium text-primary mb-1">💡 Recommended Action</p>
                      <p className="text-sm text-muted-foreground">{issue.suggestion}</p>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Compliance Analytics */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Compliance Performance
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Overall Compliance Rate</span>
                      <span className="text-sm font-medium">{mockSupplierResults.complianceRate}%</span>
                    </div>
                    <Progress value={mockSupplierResults.complianceRate} className="h-2" />
                    
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Document Quality Score</span>
                      <span className="text-sm font-medium">82%</span>
                    </div>
                    <Progress value={82} className="h-2" />
                    
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Customs Readiness</span>
                      <span className="text-sm font-medium">{mockSupplierResults.customsReady ? "100%" : "65%"}</span>
                    </div>
                    <Progress value={mockSupplierResults.customsReady ? 100 : 65} className="h-2" />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mt-4">
                    <div className="text-center p-3 bg-success/5 border border-success/20 rounded-lg">
                      <div className="text-lg font-bold text-success">{successCount}</div>
                      <div className="text-xs text-muted-foreground">Compliant Docs</div>
                    </div>
                    <div className="text-center p-3 bg-warning/5 border border-warning/20 rounded-lg">
                      <div className="text-lg font-bold text-warning">{mockSupplierResults.totalIssues}</div>
                      <div className="text-xs text-muted-foreground">Issues Found</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Issue Severity Breakdown */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="w-5 h-5" />
                    Issue Severity Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-destructive rounded-full"></div>
                        <span className="text-sm">Critical Issues</span>
                      </div>
                      <span className="text-sm font-medium">{highIssueCount} ({Math.round((highIssueCount/mockSupplierResults.totalIssues)*100)}%)</span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-warning rounded-full"></div>
                        <span className="text-sm">Medium Issues</span>
                      </div>
                      <span className="text-sm font-medium">{mediumIssueCount} ({Math.round((mediumIssueCount/mockSupplierResults.totalIssues)*100)}%)</span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-info rounded-full"></div>
                        <span className="text-sm">Minor Issues</span>
                      </div>
                      <span className="text-sm font-medium">{lowIssueCount} ({Math.round((lowIssueCount/mockSupplierResults.totalIssues)*100)}%)</span>
                    </div>
                  </div>
                  
                  <div className="mt-4 p-3 bg-gradient-primary/5 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="w-4 h-4 text-primary" />
                      <span className="text-sm font-medium text-primary">Supplier Performance</span>
                    </div>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li>• Document accuracy improving by 12%</li>
                      <li>• Faster submission times compared to average</li>
                      <li>• Strong compliance in core requirements</li>
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Document Compliance Matrix */}
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle>Document Compliance Analytics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2">Document Type</th>
                        <th className="text-left py-2">Compliance Score</th>
                        <th className="text-left py-2">Processing Time</th>
                        <th className="text-left py-2">Quality Grade</th>
                        <th className="text-left py-2">Risk Level</th>
                      </tr>
                    </thead>
                    <tbody className="space-y-2">
                      {mockSupplierResults.documents.map((doc, index) => (
                        <tr key={doc.id} className="border-b border-gray-200/50">
                          <td className="py-3 font-medium">{doc.type}</td>
                          <td className="py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-16 bg-muted rounded-full h-2">
                                <div 
                                  className={`h-2 rounded-full ${
                                    doc.complianceScore >= 90 ? 'bg-success' : 
                                    doc.complianceScore >= 70 ? 'bg-warning' : 'bg-destructive'
                                  }`}
                                  style={{ width: `${doc.complianceScore}%` }}
                                ></div>
                              </div>
                              <span className="text-xs">{doc.complianceScore}%</span>
                            </div>
                          </td>
                          <td className="py-3 text-muted-foreground">{(0.3 + index * 0.15).toFixed(1)}s</td>
                          <td className="py-3">
                            <StatusBadge status={doc.status}>
                              {doc.complianceScore >= 90 ? "A" : doc.complianceScore >= 80 ? "B" : doc.complianceScore >= 70 ? "C" : "D"}
                            </StatusBadge>
                          </td>
                          <td className="py-3 text-muted-foreground">
                            {doc.status === "success" ? "Low" : doc.status === "warning" ? "Medium" : "High"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                
                <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-3 bg-success/5 border border-success/20 rounded-lg text-center">
                    <div className="text-lg font-bold text-success">{mockSupplierResults.processingTime}</div>
                    <div className="text-xs text-muted-foreground">Total Processing Time</div>
                  </div>
                  <div className="p-3 bg-primary/5 border border-primary/20 rounded-lg text-center">
                    <div className="text-lg font-bold text-primary">4/4</div>
                    <div className="text-xs text-muted-foreground">Documents Analyzed</div>
                  </div>
                  <div className="p-3 bg-info/5 border border-info/20 rounded-lg text-center">
                    <div className="text-lg font-bold text-info">98.5%</div>
                    <div className="text-xs text-muted-foreground">Data Extraction Accuracy</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
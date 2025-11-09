import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/ui/status-badge";
import { DiscrepancyGuidance } from "@/components/discrepancy/DiscrepancyGuidance";
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
  Receipt
} from "lucide-react";
import { useNavigate } from "react-router-dom";

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
  const lcNumber = searchParams.get('lc') || mockExporterResults.lcNumber;
  const [activeTab, setActiveTab] = useState("overview");
  
  // Check if result has invoiceId (future enhancement)
  const invoiceId = (mockExporterResults as any).invoiceId;

  const successCount = mockExporterResults.documents.filter(d => d.status === "success").length;
  const warningCount = mockExporterResults.documents.filter(d => d.status === "warning").length;
  const errorCount = 0; // No error status in current mock data
  const successRate = Math.round((successCount / mockExporterResults.totalDocuments) * 100);

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
                  mockExporterResults.overallStatus === "success" ? "bg-success/10" :
                  mockExporterResults.overallStatus === "error" ? "bg-destructive/10" : "bg-warning/10"
                }`}>
                  {mockExporterResults.overallStatus === "success" ? (
                    <CheckCircle className="w-8 h-8 text-success" />
                  ) : mockExporterResults.overallStatus === "error" ? (
                    <XCircle className="w-8 h-8 text-destructive" />
                  ) : (
                    <AlertTriangle className="w-8 h-8 text-warning" />
                  )}
                </div>
                <StatusBadge status={mockExporterResults.overallStatus} className="text-sm font-medium">
                  {mockExporterResults.packGenerated ? "Customs Pack Ready" : "Processing Required"}
                </StatusBadge>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Processing Summary</h3>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Documents:</span>
                    <span className="font-medium">{mockExporterResults.totalDocuments}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Compliance Rate:</span>
                    <span className="font-medium text-success">{Math.round(((mockExporterResults.totalDocuments - mockExporterResults.totalDiscrepancies) / mockExporterResults.totalDocuments) * 100)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Processing Time:</span>
                    <span className="font-medium">{mockExporterResults.processingTime}</span>
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
                  {mockExporterResults.totalDiscrepancies > 0 ? (
                    <>
                      <Link to="/export-lc-upload">
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
                      <Button className="w-full bg-gradient-primary hover:opacity-90" size="sm">
                        <Download className="w-4 h-4 mr-2" />
                        Download Customs Pack
                      </Button>
                      <p className="text-xs text-success text-center">
                        Ready for customs clearance
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
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="documents">Documents ({mockExporterResults.totalDocuments})</TabsTrigger>
            <TabsTrigger value="discrepancies" className="relative">
              Issues ({mockExporterResults.totalDiscrepancies})
              {mockExporterResults.totalDiscrepancies > 0 && (
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
                      <div className="text-2xl font-bold text-warning">{mockExporterResults.totalDiscrepancies}</div>
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
                  {mockExporterResults.packGenerated && (
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
            {mockExporterResults.documents.map((document) => (
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
            {mockExporterResults.discrepancies.length === 0 ? (
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
              mockExporterResults.discrepancies.map((discrepancy) => (
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
                      <span className="text-sm font-medium">{successCount} ({Math.round((successCount/mockExporterResults.totalDocuments)*100)}%)</span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-warning rounded-full"></div>
                        <span className="text-sm">Minor Issues</span>
                      </div>
                      <span className="text-sm font-medium">{warningCount} ({Math.round((warningCount/mockExporterResults.totalDocuments)*100)}%)</span>
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
                      {mockExporterResults.documents.map((doc, index) => (
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
      </div>
    </div>
  );
}
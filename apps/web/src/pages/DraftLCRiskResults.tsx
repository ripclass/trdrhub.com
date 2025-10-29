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
  ShieldCheck,
  AlertCircle,
  BarChart3,
  TrendingUp,
  PieChart
} from "lucide-react";

// Mock LC Risk Analysis results
const mockLCRiskResults = {
  lcNumber: "DRAFT-LC-BD-2024-001",
  status: "completed",
  processedAt: "2024-01-15T14:30:00Z",
  processingTime: "1.5 minutes",
  totalClauses: 12,
  totalRisks: 4,
  overallRiskScore: 65, // out of 100, higher is better
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
    },
    {
      id: "4",
      type: "Goods Description", 
      text: "100% Cotton Raw Materials, Grade A, moisture content max 8%",
      riskLevel: "medium" as const,
      analysis: "Specific quality parameters are good but may limit supplier flexibility",
      recommendation: "Consider allowing slight tolerance (±0.5%) for moisture content"
    },
    {
      id: "5",
      type: "Insurance Terms",
      text: "Insurance coverage 110% of invoice value",
      riskLevel: "low" as const,
      analysis: "Standard insurance coverage - adequate protection",
      recommendation: "Acceptable coverage level"
    },
    {
      id: "6",
      type: "Partial Shipments",
      text: "Partial shipments and transshipments prohibited",
      riskLevel: "medium" as const,
      analysis: "Strict shipping terms may limit supplier logistics options",
      recommendation: "Consider allowing partial shipments to provide supplier flexibility"
    }
  ],
  
  risks: [
    {
      id: "1",
      clauseId: "2",
      severity: "high" as const,
      category: "Timeline Risk",
      title: "Unrealistic Shipment Deadline",
      description: "15-day shipment window is extremely tight for international trade. Most suppliers need 30-45 days minimum.",
      businessImpact: "High probability of supplier rejection or non-compliance, leading to shipment delays and potential contract penalties.",
      financialImpact: "Potential demurrage charges, storage costs, and production delays if goods arrive late.",
      recommendation: "Negotiate with supplier for realistic timeline or request LC amendment to extend shipment period to 30-45 days.",
      urgency: "immediate"
    },
    {
      id: "2",
      clauseId: "3", 
      severity: "high" as const,
      category: "Documentation Risk",
      title: "Restrictive Certificate Authority",
      description: "Requiring certificates only from Bangladesh Export Promotion Council limits supplier options unnecessarily.",
      businessImpact: "Foreign suppliers may not have access to this specific authority, causing document rejection at bank.",
      financialImpact: "Document discrepancy fees, amendment charges, and potential shipment delays.",
      recommendation: "Accept certificates from internationally recognized authorities like Chamber of Commerce or equivalent export bodies.",
      urgency: "high"
    },
    {
      id: "3",
      clauseId: "4",
      severity: "medium" as const,
      category: "Quality Risk", 
      title: "Strict Quality Parameters",
      description: "8% moisture content requirement with no tolerance may be difficult to maintain during shipping.",
      businessImpact: "Goods may naturally exceed moisture limits during transport, causing quality disputes.",
      financialImpact: "Potential goods rejection, re-testing costs, and quality claims.",
      recommendation: "Allow ±0.5% tolerance for moisture content to account for natural variations during transport.",
      urgency: "medium"
    },
    {
      id: "4",
      clauseId: "6",
      severity: "low" as const,
      category: "Logistics Risk",
      title: "No Partial Shipments Allowed", 
      description: "Prohibition of partial shipments may limit supplier's logistics flexibility.",
      businessImpact: "Supplier may struggle with large single shipments, potentially causing delays.",
      financialImpact: "Minor impact - may increase logistics costs for supplier.",
      recommendation: "Consider allowing partial shipments to provide supplier flexibility, especially for large orders.",
      urgency: "low"
    }
  ]
};

export default function DraftLCRiskResults() {
  const [searchParams] = useSearchParams();
  const lcNumber = searchParams.get('lc') || mockLCRiskResults.lcNumber;
  const [activeTab, setActiveTab] = useState("overview");

  const highRiskCount = mockLCRiskResults.risks.filter(r => r.severity === "high").length;
  const mediumRiskCount = mockLCRiskResults.risks.filter(r => r.severity === "medium").length;
  const lowRiskCount = mockLCRiskResults.risks.filter(r => r.severity === "low").length;

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
                  <ShieldCheck className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-foreground">Draft LC Risk Analysis</h1>
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
                Download Risk Report
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Risk Overview */}
        <Card className="mb-8 shadow-soft border-0">
          <CardContent className="p-6">
            <div className="grid md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className={`w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center ${
                  mockLCRiskResults.riskLevel === "low" ? "bg-success/10" :
                  mockLCRiskResults.riskLevel === "high" ? "bg-destructive/10" : "bg-warning/10"
                }`}>
                  {mockLCRiskResults.riskLevel === "low" ? (
                    <CheckCircle className="w-8 h-8 text-success" />
                  ) : mockLCRiskResults.riskLevel === "high" ? (
                    <XCircle className="w-8 h-8 text-destructive" />
                  ) : (
                    <AlertTriangle className="w-8 h-8 text-warning" />
                  )}
                </div>
                <StatusBadge status={mockLCRiskResults.overallStatus} className="text-sm font-medium">
                  Risk Score: {mockLCRiskResults.overallRiskScore}/100
                </StatusBadge>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">LC Analysis</h3>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Clauses:</span>
                    <span className="font-medium">{mockLCRiskResults.totalClauses}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Risk Level:</span>
                    <span className={`font-medium ${
                      mockLCRiskResults.riskLevel === "low" ? "text-success" :
                      mockLCRiskResults.riskLevel === "high" ? "text-destructive" : "text-warning"
                    }`}>
                      {mockLCRiskResults.riskLevel.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Analysis Time:</span>
                    <span className="font-medium">{mockLCRiskResults.processingTime}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Risk Breakdown</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-destructive rounded-full"></div>
                    <span className="text-sm">{highRiskCount} high risk items</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-warning rounded-full"></div>
                    <span className="text-sm">{mediumRiskCount} medium risk items</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <span className="text-sm">{lowRiskCount} low risk items</span>
                  </div>
                  <Progress value={mockLCRiskResults.overallRiskScore} className="h-2 mt-2" />
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-foreground">Recommendation</h3>
                <div className="space-y-2">
                  {mockLCRiskResults.totalRisks > 2 ? (
                    <>
                      <Link to="/draft-lc-corrections">
                        <Button variant="outline" size="sm" className="w-full">
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Request LC Amendments
                        </Button>
                      </Link>
                      <p className="text-xs text-muted-foreground text-center">
                        Address high-risk clauses before accepting
                      </p>
                    </>
                  ) : (
                    <>
                      <Button className="w-full bg-gradient-primary hover:opacity-90" size="sm">
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Accept LC Terms
                      </Button>
                      <p className="text-xs text-success text-center">
                        Acceptable risk level
                      </p>
                    </>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Detailed Analysis */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="clauses">LC Clauses ({mockLCRiskResults.lcClauses.length})</TabsTrigger>
            <TabsTrigger value="risks" className="relative">
              Risk Analysis ({mockLCRiskResults.totalRisks})
              {mockLCRiskResults.totalRisks > 0 && (
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-warning rounded-full"></div>
              )}
            </TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Analysis Timeline */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    LC Risk Analysis Timeline
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Draft LC Uploaded</p>
                      <p className="text-xs text-muted-foreground">14:28 - LC terms received from bank</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-success rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Clause Extraction</p>
                      <p className="text-xs text-muted-foreground">14:29 - {mockLCRiskResults.totalClauses} clauses identified</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-warning rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Risk Assessment</p>
                      <p className="text-xs text-muted-foreground">14:30 - Industry standards comparison</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-warning rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Analysis Complete</p>
                      <p className="text-xs text-muted-foreground">14:30 - {mockLCRiskResults.totalRisks} risks identified</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Risk Summary */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle>Risk Assessment Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-warning/5 border border-warning/20 rounded-lg">
                      <div className="text-2xl font-bold text-warning">{mockLCRiskResults.overallRiskScore}</div>
                      <div className="text-sm text-muted-foreground">Risk Score</div>
                    </div>
                    <div className="text-center p-3 bg-destructive/5 border border-destructive/20 rounded-lg">
                      <div className="text-2xl font-bold text-destructive">{highRiskCount}</div>
                      <div className="text-sm text-muted-foreground">High Risk</div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Business Impact:</span>
                      <span className="font-medium text-warning">Medium</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Financial Risk:</span>
                      <span className="font-medium text-warning">Moderate</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Supplier Acceptance:</span>
                      <span className="font-medium text-destructive">Low</span>
                    </div>
                  </div>
                  
                  <div className="p-3 bg-destructive/5 border border-destructive/20 rounded-lg">
                    <p className="text-sm font-medium text-destructive mb-1">⚠️ Action Required</p>
                    <p className="text-xs text-muted-foreground">Request amendments for {highRiskCount} high-risk clauses before LC acceptance</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="clauses" className="space-y-4">
            {mockLCRiskResults.lcClauses.map((clause) => (
              <Card key={clause.id} className="shadow-soft border-0">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        clause.riskLevel === "high" ? "bg-destructive/10" : 
                        clause.riskLevel === "medium" ? "bg-warning/10" : "bg-success/10"
                      }`}>
                        <FileText className={`w-5 h-5 ${
                          clause.riskLevel === "high" ? "text-destructive" : 
                          clause.riskLevel === "medium" ? "text-warning" : "text-success"
                        }`} />
                      </div>
                      <div>
                        <CardTitle className="text-base">{clause.type}</CardTitle>
                        <CardDescription>LC Clause</CardDescription>
                      </div>
                    </div>
                    <Badge variant={
                      clause.riskLevel === "high" ? "destructive" : 
                      clause.riskLevel === "medium" ? "secondary" : "default"
                    }>
                      {clause.riskLevel} risk
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Clause Text</p>
                      <p className="text-sm font-mono bg-muted/50 p-3 rounded border">{clause.text}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Risk Analysis</p>
                      <p className="text-sm text-muted-foreground">{clause.analysis}</p>
                    </div>
                    <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
                      <p className="text-xs font-medium text-primary mb-1">💡 Recommendation</p>
                      <p className="text-sm text-muted-foreground">{clause.recommendation}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="risks" className="space-y-4">
            {mockLCRiskResults.risks.map((risk) => (
              <Card key={risk.id} className="shadow-soft border-0">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg mt-1 ${
                        risk.severity === "high" ? "bg-destructive/10" : 
                        risk.severity === "medium" ? "bg-warning/10" : "bg-info/10"
                      }`}>
                        {risk.severity === "high" ? (
                          <XCircle className="w-5 h-5 text-destructive" />
                        ) : risk.severity === "medium" ? (
                          <AlertTriangle className="w-5 h-5 text-warning" />
                        ) : (
                          <AlertCircle className="w-5 h-5 text-info" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <CardTitle className="text-base">{risk.title}</CardTitle>
                          <Badge variant={risk.severity === "high" ? "destructive" : "secondary"} className="text-xs">
                            {risk.severity} priority
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {risk.urgency}
                          </Badge>
                        </div>
                        <CardDescription className="text-sm mb-2">
                          {risk.category}
                        </CardDescription>
                        <p className="text-sm text-muted-foreground mb-3">{risk.description}</p>
                        
                        <div className="grid md:grid-cols-2 gap-3 mb-3">
                          <div className="bg-warning/5 border border-warning/20 rounded-lg p-2">
                            <p className="text-xs font-medium text-warning mb-1">📈 Business Impact</p>
                            <p className="text-xs text-muted-foreground">{risk.businessImpact}</p>
                          </div>
                          <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-2">
                            <p className="text-xs font-medium text-destructive mb-1">💰 Financial Impact</p>
                            <p className="text-xs text-muted-foreground">{risk.financialImpact}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
                    <p className="text-xs font-medium text-primary mb-1">💡 Recommended Action</p>
                    <p className="text-sm text-muted-foreground">{risk.recommendation}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Risk Assessment Analytics */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Risk Assessment Metrics
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Overall Risk Score</span>
                      <span className="text-sm font-medium">{mockLCRiskResults.overallRiskScore}/100</span>
                    </div>
                    <Progress value={mockLCRiskResults.overallRiskScore} className="h-2" />
                    
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Supplier Acceptance Probability</span>
                      <span className="text-sm font-medium">35%</span>
                    </div>
                    <Progress value={35} className="h-2" />
                    
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Timeline Feasibility</span>
                      <span className="text-sm font-medium">25%</span>
                    </div>
                    <Progress value={25} className="h-2" />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mt-4">
                    <div className="text-center p-3 bg-warning/5 border border-warning/20 rounded-lg">
                      <div className="text-lg font-bold text-warning">{mockLCRiskResults.totalRisks}</div>
                      <div className="text-xs text-muted-foreground">Total Risks</div>
                    </div>
                    <div className="text-center p-3 bg-destructive/5 border border-destructive/20 rounded-lg">
                      <div className="text-lg font-bold text-destructive">{highRiskCount}</div>
                      <div className="text-xs text-muted-foreground">High Priority</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Risk Category Breakdown */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="w-5 h-5" />
                    Risk Category Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-destructive rounded-full"></div>
                        <span className="text-sm">High Risk</span>
                      </div>
                      <span className="text-sm font-medium">{highRiskCount} ({Math.round((highRiskCount/mockLCRiskResults.totalRisks)*100)}%)</span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-warning rounded-full"></div>
                        <span className="text-sm">Medium Risk</span>
                      </div>
                      <span className="text-sm font-medium">{mediumRiskCount} ({Math.round((mediumRiskCount/mockLCRiskResults.totalRisks)*100)}%)</span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-success rounded-full"></div>
                        <span className="text-sm">Low Risk</span>
                      </div>
                      <span className="text-sm font-medium">{lowRiskCount} ({Math.round((lowRiskCount/mockLCRiskResults.totalRisks)*100)}%)</span>
                    </div>
                  </div>
                  
                  <div className="mt-4 p-3 bg-gradient-primary/5 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="w-4 h-4 text-primary" />
                      <span className="text-sm font-medium text-primary">Strategic Recommendations</span>
                    </div>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li>• Negotiate shipment timeline extension</li>
                      <li>• Expand certificate authority options</li>
                      <li>• Consider partial shipment allowance</li>
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Detailed Risk Analytics */}
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle>Risk Analysis Matrix</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2">Risk Category</th>
                        <th className="text-left py-2">Business Impact</th>
                        <th className="text-left py-2">Financial Impact</th>
                        <th className="text-left py-2">Urgency Level</th>
                        <th className="text-left py-2">Mitigation Effort</th>
                      </tr>
                    </thead>
                    <tbody className="space-y-2">
                      {mockLCRiskResults.risks.map((risk) => (
                        <tr key={risk.id} className="border-b border-gray-200/50">
                          <td className="py-3 font-medium">{risk.category}</td>
                          <td className="py-3">
                            <StatusBadge status={risk.severity === "high" ? "error" : risk.severity === "medium" ? "warning" : "success"}>
                              {risk.severity === "high" ? "High" : risk.severity === "medium" ? "Medium" : "Low"}
                            </StatusBadge>
                          </td>
                          <td className="py-3 text-muted-foreground">
                            {risk.severity === "high" ? "$$$ Significant" : risk.severity === "medium" ? "$$ Moderate" : "$ Minimal"}
                          </td>
                          <td className="py-3">
                            <Badge variant={risk.urgency === "immediate" ? "destructive" : risk.urgency === "high" ? "secondary" : "outline"}>
                              {risk.urgency}
                            </Badge>
                          </td>
                          <td className="py-3 text-muted-foreground">
                            {risk.severity === "high" ? "High effort" : risk.severity === "medium" ? "Medium effort" : "Low effort"}
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
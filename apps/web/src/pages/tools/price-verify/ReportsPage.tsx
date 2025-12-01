import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { 
  FileText, 
  Download, 
  Calendar, 
  FileSpreadsheet,
  File,
  Clock,
  Plus,
  AlertTriangle,
  CheckCircle,
  Shield,
  Loader2,
  BarChart3,
  TrendingUp,
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface ReportStats {
  total_verifications_30d: number;
  high_risk_count: number;
  failed_count: number;
  reports_available: boolean;
}

export default function ReportsPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<ReportStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  
  // Report generation form
  const [reportType, setReportType] = useState("compliance");
  const [dateRange, setDateRange] = useState("30d");
  const [format, setFormat] = useState("pdf");
  const [companyName, setCompanyName] = useState("");
  const [includePassed, setIncludePassed] = useState(true);
  
  // SAR specific fields
  const [verificationId, setVerificationId] = useState("");
  const [sarReportType, setSarReportType] = useState("SAR");
  const [reporterName, setReporterName] = useState("");
  const [reporterEmail, setReporterEmail] = useState("");

  // Fetch stats on mount
  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/price-verify/reports/stats`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setStats(data.stats);
        }
      }
    } catch (err) {
      console.error("Failed to fetch report stats:", err);
    } finally {
      setStatsLoading(false);
    }
  };

  const generateReport = async () => {
    setLoading(true);
    
    try {
      let url = "";
      let options: RequestInit = {};
      let filename = "";
      
      if (reportType === "compliance") {
        // General compliance report
        url = `${API_BASE}/price-verify/reports/compliance`;
        options = {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            date_range: dateRange,
            format: format,
            company_name: companyName || undefined,
            include_passed: includePassed,
          }),
        };
        filename = `compliance_report.${format}`;
        
      } else if (reportType === "tbml") {
        // TBML summary report (always PDF)
        const params = new URLSearchParams({
          days: dateRange === "7d" ? "7" : dateRange === "90d" ? "90" : "30",
        });
        if (companyName) params.append("company_name", companyName);
        
        url = `${API_BASE}/price-verify/reports/tbml-summary?${params}`;
        options = { method: "GET" };
        filename = "tbml_summary.pdf";
        
      } else if (reportType === "sar") {
        // SAR/STR report (requires verification ID)
        if (!verificationId) {
          toast({
            title: "Verification ID Required",
            description: "Please enter the verification ID for the flagged transaction.",
            variant: "destructive",
          });
          setLoading(false);
          return;
        }
        
        url = `${API_BASE}/price-verify/reports/sar`;
        options = {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            verification_id: verificationId,
            report_type: sarReportType,
            company_name: companyName || undefined,
            reporter_name: reporterName || undefined,
            reporter_email: reporterEmail || undefined,
          }),
        };
        filename = `${sarReportType}_report.pdf`;
      }
      
      const response = await fetch(url, options);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Report generation failed" }));
        throw new Error(errorData.detail || "Failed to generate report");
      }
      
      // Download the file
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      toast({
        title: "Report Generated",
        description: `Your ${reportType} report has been downloaded.`,
      });
      
    } catch (err: any) {
      console.error("Report generation error:", err);
      toast({
        title: "Generation Failed",
        description: err.message || "Failed to generate report. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const quickGenerate = async (type: string, fmt: string) => {
    setReportType(type);
    setFormat(fmt);
    setDateRange("30d");
    setIncludePassed(type !== "tbml");
    
    // Wait for state update then generate
    setTimeout(() => {
      generateReport();
    }, 100);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
          {stats && (
            <Badge variant="outline" className="text-xs bg-green-500/10 text-green-500 border-green-500/20">
              <CheckCircle className="w-3 h-3 mr-1" />
              Live Data
            </Badge>
          )}
        </div>
        <p className="text-muted-foreground">
          Generate and download compliance reports for price verifications.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-blue-500/10 rounded-lg">
              <BarChart3 className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Verifications (30d)</p>
              <p className="text-2xl font-bold">
                {statsLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : (stats?.total_verifications_30d || 0)}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-red-500/10 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">High Risk</p>
              <p className="text-2xl font-bold text-red-600">
                {statsLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : (stats?.high_risk_count || 0)}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-yellow-500/10 rounded-lg">
              <TrendingUp className="w-6 h-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Failed Verifications</p>
              <p className="text-2xl font-bold text-yellow-600">
                {statsLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : (stats?.failed_count || 0)}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Generate Report */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Generate New Report
          </CardTitle>
          <CardDescription>
            Create a compliance or summary report for your verification history.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>Report Type</Label>
              <Select value={reportType} onValueChange={setReportType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="compliance">Compliance Report</SelectItem>
                  <SelectItem value="tbml">TBML Summary</SelectItem>
                  <SelectItem value="sar">SAR/STR Report</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {reportType !== "sar" && (
              <>
                <div className="space-y-2">
                  <Label>Date Range</Label>
                  <Select value={dateRange} onValueChange={setDateRange}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="7d">Last 7 days</SelectItem>
                      <SelectItem value="30d">Last 30 days</SelectItem>
                      <SelectItem value="90d">Last 90 days</SelectItem>
                      <SelectItem value="ytd">Year to Date</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {reportType === "compliance" && (
                  <div className="space-y-2">
                    <Label>Format</Label>
                    <Select value={format} onValueChange={setFormat}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pdf">PDF Report</SelectItem>
                        <SelectItem value="xlsx">Excel (.xlsx)</SelectItem>
                        <SelectItem value="csv">CSV Export</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </>
            )}
            
            <div className="space-y-2">
              <Label>Company Name (Optional)</Label>
              <Input
                placeholder="Enter company name"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
              />
            </div>
          </div>
          
          {/* SAR specific fields */}
          {reportType === "sar" && (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2 border-t">
              <div className="space-y-2">
                <Label>Verification ID *</Label>
                <Input
                  placeholder="Enter verification ID"
                  value={verificationId}
                  onChange={(e) => setVerificationId(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Report Type</Label>
                <Select value={sarReportType} onValueChange={setSarReportType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SAR">SAR (Suspicious Activity Report)</SelectItem>
                    <SelectItem value="STR">STR (Suspicious Transaction Report)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Reporter Name</Label>
                <Input
                  placeholder="Your name"
                  value={reporterName}
                  onChange={(e) => setReporterName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Reporter Email</Label>
                <Input
                  type="email"
                  placeholder="your@email.com"
                  value={reporterEmail}
                  onChange={(e) => setReporterEmail(e.target.value)}
                />
              </div>
            </div>
          )}
          
          {/* Include passed checkbox for compliance reports */}
          {reportType === "compliance" && (
            <div className="flex items-center gap-2">
              <Checkbox 
                id="include-passed" 
                checked={includePassed}
                onCheckedChange={(checked) => setIncludePassed(checked === true)}
              />
              <Label htmlFor="include-passed" className="text-sm font-normal cursor-pointer">
                Include passed verifications (uncheck for flagged-only report)
              </Label>
            </div>
          )}
          
          <Button onClick={generateReport} disabled={loading} className="w-full sm:w-auto">
            {loading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <FileText className="w-4 h-4 mr-2" />
            )}
            {loading ? "Generating..." : "Generate Report"}
          </Button>
        </CardContent>
      </Card>

      {/* Report Templates */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Templates</CardTitle>
          <CardDescription>Pre-configured report templates for common use cases</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid sm:grid-cols-3 gap-4">
            <div 
              onClick={() => quickGenerate("compliance", "pdf")}
              className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <File className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium">Monthly Compliance</p>
                  <p className="text-xs text-muted-foreground">PDF • All verifications</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                Complete compliance report with all verifications, risk analysis, and recommendations.
              </p>
            </div>
            <div 
              onClick={() => quickGenerate("tbml", "pdf")}
              className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-red-500/10 rounded-lg">
                  <Shield className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="font-medium">TBML Alert Report</p>
                  <p className="text-xs text-muted-foreground">PDF • High risk only</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                Detailed analysis of all TBML-flagged transactions with risk narratives.
              </p>
            </div>
            <div 
              onClick={() => quickGenerate("compliance", "xlsx")}
              className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-green-500/10 rounded-lg">
                  <FileSpreadsheet className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="font-medium">Data Export</p>
                  <p className="text-xs text-muted-foreground">Excel • Raw data</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                Full data export for integration with your existing systems.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Report Types Info */}
      <Card>
        <CardHeader>
          <CardTitle>Report Types Guide</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-4 p-4 bg-muted/50 rounded-lg">
              <div className="p-2 bg-blue-500/10 rounded-lg h-fit">
                <FileText className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h4 className="font-semibold">Compliance Report</h4>
                <p className="text-sm text-muted-foreground mt-1">
                  Comprehensive report of all price verifications. Includes document details, 
                  market prices, variance analysis, and risk assessments. Available in PDF, 
                  Excel, or CSV formats for flexible integration.
                </p>
              </div>
            </div>
            
            <div className="flex gap-4 p-4 bg-muted/50 rounded-lg">
              <div className="p-2 bg-red-500/10 rounded-lg h-fit">
                <Shield className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h4 className="font-semibold">TBML Summary Report</h4>
                <p className="text-sm text-muted-foreground mt-1">
                  Trade-Based Money Laundering summary focusing on high-risk and critical 
                  flagged transactions. Designed for compliance officers and regulatory review. 
                  Includes risk patterns, commodity analysis, and recommended actions.
                </p>
              </div>
            </div>
            
            <div className="flex gap-4 p-4 bg-muted/50 rounded-lg">
              <div className="p-2 bg-yellow-500/10 rounded-lg h-fit">
                <AlertTriangle className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <h4 className="font-semibold">SAR/STR Report</h4>
                <p className="text-sm text-muted-foreground mt-1">
                  Suspicious Activity Report (SAR) or Suspicious Transaction Report (STR) 
                  for individual flagged transactions. Formatted for regulatory filing with 
                  FinCEN or local Financial Intelligence Units. Requires specific verification ID.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

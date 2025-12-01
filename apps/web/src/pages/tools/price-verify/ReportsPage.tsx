import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  FileText, 
  Download, 
  Calendar, 
  FileSpreadsheet,
  File,
  Clock,
  Plus,
  Trash2,
  Info
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Report {
  id: string;
  name: string;
  type: "compliance" | "tbml" | "summary";
  format: "pdf" | "csv" | "xlsx";
  dateRange: string;
  createdAt: string;
  size: string;
}

const sampleReports: Report[] = [
  { id: "1", name: "November 2024 Compliance Report", type: "compliance", format: "pdf", dateRange: "Nov 1-30, 2024", createdAt: "2024-11-30T10:00:00Z", size: "2.4 MB" },
  { id: "2", name: "TBML Flagged Transactions Q4", type: "tbml", format: "pdf", dateRange: "Oct-Dec 2024", createdAt: "2024-11-28T14:30:00Z", size: "1.8 MB" },
  { id: "3", name: "Weekly Summary Export", type: "summary", format: "xlsx", dateRange: "Nov 23-29, 2024", createdAt: "2024-11-29T09:00:00Z", size: "456 KB" },
  { id: "4", name: "Commodities Analysis", type: "summary", format: "csv", dateRange: "Nov 2024", createdAt: "2024-11-25T16:00:00Z", size: "128 KB" },
];

export default function ReportsPage() {
  const [reports] = useState<Report[]>(sampleReports);
  const [reportType, setReportType] = useState("compliance");
  const [dateRange, setDateRange] = useState("30d");
  const [format, setFormat] = useState("pdf");

  const generateReport = () => {
    // TODO: Generate report via API
    alert(`Generating ${reportType} report for ${dateRange} in ${format.toUpperCase()} format...`);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
          <Badge variant="outline" className="text-xs text-muted-foreground">
            <Info className="w-3 h-3 mr-1" />
            Sample Data
          </Badge>
        </div>
        <p className="text-muted-foreground">
          Generate and download compliance reports.
        </p>
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
        <CardContent>
          <div className="grid sm:grid-cols-4 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Report Type</label>
              <Select value={reportType} onValueChange={setReportType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="compliance">Compliance Report</SelectItem>
                  <SelectItem value="tbml">TBML Summary</SelectItem>
                  <SelectItem value="summary">Verification Summary</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Date Range</label>
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
            <div>
              <label className="text-sm font-medium mb-2 block">Format</label>
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
            <div className="flex items-end">
              <Button onClick={generateReport} className="w-full">
                <FileText className="w-4 h-4 mr-2" />
                Generate
              </Button>
            </div>
          </div>
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
            <div className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors">
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
            <div className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-red-500/10 rounded-lg">
                  <File className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="font-medium">TBML Alert Report</p>
                  <p className="text-xs text-muted-foreground">PDF • Flagged only</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                Detailed analysis of all TBML-flagged transactions with risk narratives.
              </p>
            </div>
            <div className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors">
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

      {/* Recent Reports */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Reports</CardTitle>
          <CardDescription>Previously generated reports available for download</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {reports.map(report => (
              <div
                key={report.id}
                className="flex items-center justify-between p-4 rounded-lg bg-muted/50"
              >
                <div className="flex items-center gap-4">
                  {report.format === "pdf" ? (
                    <File className="w-8 h-8 text-red-600" />
                  ) : report.format === "xlsx" ? (
                    <FileSpreadsheet className="w-8 h-8 text-green-600" />
                  ) : (
                    <FileText className="w-8 h-8 text-blue-600" />
                  )}
                  <div>
                    <p className="font-medium">{report.name}</p>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="w-3 h-3" />
                      {report.dateRange}
                      <span>•</span>
                      <Clock className="w-3 h-3" />
                      {new Date(report.createdAt).toLocaleDateString()}
                      <span>•</span>
                      {report.size}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="uppercase">
                    {report.format}
                  </Badge>
                  <Button variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </Button>
                  <Button variant="ghost" size="icon">
                    <Trash2 className="w-4 h-4 text-muted-foreground" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


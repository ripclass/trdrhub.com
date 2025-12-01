import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Search, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle,
  Download,
  Calendar,
  FileText,
  Eye,
  Trash2,
  Filter,
  Info,
  Loader2,
  X,
  FileSpreadsheet,
  Printer
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface VerificationRecord {
  id: string;
  date: string;
  commodity: string;
  commodityCode: string;
  documentPrice: number;
  marketPrice: number;
  variance: number;
  verdict: "pass" | "warning" | "fail";
  documentType: string;
  documentRef?: string;
  tbmlFlag: boolean;
  riskLevel?: string;
}

export default function HistoryPage() {
  const [history, setHistory] = useState<VerificationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [search, setSearch] = useState("");
  const [verdictFilter, setVerdictFilter] = useState<string>("all");
  const [dateRange, setDateRange] = useState<string>("7d");
  const [selectedRecord, setSelectedRecord] = useState<VerificationRecord | null>(null);

  // Export to CSV
  const exportToCSV = useCallback(() => {
    const headers = [
      "Date",
      "Commodity",
      "Commodity Code",
      "Document Price (USD)",
      "Market Price (USD)",
      "Variance (%)",
      "Verdict",
      "Risk Level",
      "TBML Flag",
      "Document Type",
      "Document Ref",
      "Verification ID"
    ];
    
    const rows = history.map(record => [
      record.date,
      record.commodity,
      record.commodityCode,
      (record.documentPrice ?? 0).toFixed(2),
      (record.marketPrice ?? 0).toFixed(2),
      (record.variance ?? 0).toFixed(2),
      (record.verdict || 'unknown').toUpperCase(),
      record.riskLevel || "N/A",
      record.tbmlFlag ? "YES" : "NO",
      record.documentType || "N/A",
      record.documentRef || "N/A",
      record.id
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(","))
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `price-verifications-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [history]);

  // Export to Excel (XLSX format via CSV)
  const exportToExcel = useCallback(() => {
    // For now, use CSV with .xlsx extension - proper XLSX would need a library like xlsx
    const headers = [
      "Date",
      "Commodity",
      "Commodity Code",
      "Document Price (USD)",
      "Market Price (USD)",
      "Variance (%)",
      "Verdict",
      "Risk Level",
      "TBML Flag",
      "Document Type",
      "Document Ref",
      "Verification ID"
    ];
    
    const rows = history.map(record => [
      record.date,
      record.commodity,
      record.commodityCode,
      (record.documentPrice ?? 0).toFixed(2),
      (record.marketPrice ?? 0).toFixed(2),
      (record.variance ?? 0).toFixed(2),
      (record.verdict || 'unknown').toUpperCase(),
      record.riskLevel || "N/A",
      record.tbmlFlag ? "YES" : "NO",
      record.documentType || "N/A",
      record.documentRef || "N/A",
      record.id
    ]);

    // Tab-separated for better Excel compatibility
    const tsvContent = [
      headers.join("\t"),
      ...rows.map(row => row.join("\t"))
    ].join("\n");

    const blob = new Blob([tsvContent], { type: "application/vnd.ms-excel;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `price-verifications-${new Date().toISOString().split('T')[0]}.xls`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [history]);

  // Print function
  const handlePrint = useCallback(() => {
    window.print();
  }, []);
  
  // Fetch real history data from API
  useEffect(() => {
    fetchHistory();
  }, [verdictFilter, dateRange]);
  
  const fetchHistory = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (verdictFilter && verdictFilter !== "all") {
        params.append("verdict", verdictFilter);
      }
      
      // Calculate date range
      const now = new Date();
      if (dateRange === "7d") {
        const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        params.append("start_date", start.toISOString().split("T")[0]);
      } else if (dateRange === "30d") {
        const start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        params.append("start_date", start.toISOString().split("T")[0]);
      } else if (dateRange === "90d") {
        const start = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
        params.append("start_date", start.toISOString().split("T")[0]);
      }
      
      const response = await fetch(`${API_BASE}/price-verify/history?${params.toString()}`);
      if (response.ok) {
        const data = await response.json();
        
        // Transform API response to frontend format
        const records: VerificationRecord[] = (data.records || []).map((r: any) => ({
          id: r.id,
          date: r.created_at,
          commodity: r.commodity || r.commodity_name,
          commodityCode: r.commodity_code,
          documentPrice: r.document_price,
          marketPrice: r.market_price,
          variance: r.variance_percent,
          verdict: r.verdict as "pass" | "warning" | "fail",
          documentType: r.document_type || "Document",
          documentRef: r.document_reference,
          tbmlFlag: r.risk_level === "critical" || (r.risk_flags || []).includes("tbml_risk"),
          riskLevel: r.risk_level,
        }));
        
        setHistory(records);
        setTotalCount(data.total || records.length);
      }
    } catch (err) {
      console.error("Failed to fetch history:", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredHistory = history.filter(record => {
    const matchesSearch = search === "" ||
      record.commodity.toLowerCase().includes(search.toLowerCase()) ||
      record.documentRef?.toLowerCase().includes(search.toLowerCase());
    const matchesVerdict = verdictFilter === "all" || record.verdict === verdictFilter;
    return matchesSearch && matchesVerdict;
  });

  const stats = {
    total: history.length,
    passed: history.filter(r => r.verdict === "pass").length,
    warnings: history.filter(r => r.verdict === "warning").length,
    failed: history.filter(r => r.verdict === "fail").length,
    tbmlFlags: history.filter(r => r.tbmlFlag).length,
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">Verification History</h1>
            {loading ? (
              <Badge variant="outline" className="text-xs text-muted-foreground">
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                Loading...
              </Badge>
            ) : history.length === 0 ? (
              <Badge variant="outline" className="text-xs text-muted-foreground">
                <Info className="w-3 h-3 mr-1" />
                No Data Yet
              </Badge>
            ) : (
              <Badge variant="outline" className="text-xs bg-green-500/10 text-green-500 border-green-500/20">
                {totalCount} Records
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground">
            View and export your past price verifications.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={handlePrint} title="Print">
            <Printer className="w-4 h-4" />
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" disabled={history.length === 0}>
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={exportToCSV}>
                <FileText className="w-4 h-4 mr-2" />
                Export as CSV
              </DropdownMenuItem>
              <DropdownMenuItem onClick={exportToExcel}>
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                Export as Excel
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold">{stats.total}</p>
            <p className="text-sm text-muted-foreground">Total</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-green-600">{stats.passed}</p>
            <p className="text-sm text-muted-foreground">Passed</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-yellow-600">{stats.warnings}</p>
            <p className="text-sm text-muted-foreground">Warnings</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-red-600">{stats.failed}</p>
            <p className="text-sm text-muted-foreground">Failed</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-purple-600">{stats.tbmlFlags}</p>
            <p className="text-sm text-muted-foreground">TBML Flags</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search by commodity or document reference..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={verdictFilter} onValueChange={setVerdictFilter}>
          <SelectTrigger className="w-[150px]">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="All Results" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Results</SelectItem>
            <SelectItem value="pass">Passed</SelectItem>
            <SelectItem value="warning">Warnings</SelectItem>
            <SelectItem value="fail">Failed</SelectItem>
          </SelectContent>
        </Select>
        <Select value={dateRange} onValueChange={setDateRange}>
          <SelectTrigger className="w-[150px]">
            <Calendar className="w-4 h-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7d">Last 7 days</SelectItem>
            <SelectItem value="30d">Last 30 days</SelectItem>
            <SelectItem value="90d">Last 90 days</SelectItem>
            <SelectItem value="all">All time</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* History Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Verifications</CardTitle>
          <CardDescription>{filteredHistory.length} records found</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {filteredHistory.map(record => (
              <div
                key={record.id}
                className="flex items-center justify-between p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-4">
                  {record.verdict === "pass" && (
                    <CheckCircle2 className="w-5 h-5 text-green-600" />
                  )}
                  {record.verdict === "warning" && (
                    <AlertTriangle className="w-5 h-5 text-yellow-600" />
                  )}
                  {record.verdict === "fail" && (
                    <XCircle className="w-5 h-5 text-red-600" />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{record.commodity}</span>
                      {record.tbmlFlag && (
                        <Badge variant="destructive" className="text-xs">TBML</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="w-3 h-3" />
                      {formatDate(record.date)}
                      {record.documentRef && (
                        <>
                          <span>•</span>
                          <FileText className="w-3 h-3" />
                          {record.documentRef}
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="font-mono text-sm">
                      ${record.documentPrice?.toLocaleString() ?? '?'} vs ${record.marketPrice?.toLocaleString() ?? '?'}
                    </p>
                    <p className={`text-sm ${
                      (record.variance ?? 0) > 15 ? "text-red-600" :
                      (record.variance ?? 0) > 5 ? "text-yellow-600" :
                      "text-green-600"
                    }`}>
                      {(record.variance ?? 0) > 0 ? "+" : ""}{(record.variance ?? 0).toFixed(1)}% variance
                    </p>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => setSelectedRecord(record)}>
                    <Eye className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}

            {filteredHistory.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                No verification records found.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Verification Detail Modal */}
      <Dialog open={!!selectedRecord} onOpenChange={() => setSelectedRecord(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedRecord?.verdict === "pass" && <CheckCircle2 className="w-5 h-5 text-green-600" />}
              {selectedRecord?.verdict === "warning" && <AlertTriangle className="w-5 h-5 text-yellow-600" />}
              {selectedRecord?.verdict === "fail" && <XCircle className="w-5 h-5 text-red-600" />}
              Verification Details
            </DialogTitle>
            <DialogDescription>
              {selectedRecord?.commodity} - {selectedRecord?.date ? formatDate(selectedRecord.date) : ""}
            </DialogDescription>
          </DialogHeader>
          
          {selectedRecord && (
            <div className="space-y-4">
              {/* Verdict Badge */}
              <div className="flex items-center gap-2">
                <Badge variant={
                  selectedRecord.verdict === "pass" ? "default" :
                  selectedRecord.verdict === "warning" ? "secondary" : "destructive"
                } className={
                  selectedRecord.verdict === "pass" ? "bg-green-600" :
                  selectedRecord.verdict === "warning" ? "bg-yellow-600" : ""
                }>
                  {selectedRecord.verdict.toUpperCase()}
                </Badge>
                {selectedRecord.tbmlFlag && (
                  <Badge variant="destructive">⚠️ TBML FLAG</Badge>
                )}
              </div>

              {/* Price Comparison */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                <div>
                  <p className="text-sm text-muted-foreground">Document Price</p>
                  <p className="text-xl font-bold">${selectedRecord.documentPrice?.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">per {selectedRecord.documentType || "unit"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Market Price</p>
                  <p className="text-xl font-bold">${selectedRecord.marketPrice?.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">reference</p>
                </div>
              </div>

              {/* Variance */}
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground mb-1">Variance</p>
                <p className={`text-2xl font-bold ${
                  Math.abs(selectedRecord.variance ?? 0) > 25 ? "text-red-600" :
                  Math.abs(selectedRecord.variance ?? 0) > 10 ? "text-yellow-600" :
                  "text-green-600"
                }`}>
                  {(selectedRecord.variance ?? 0) > 0 ? "+" : ""}{(selectedRecord.variance ?? 0).toFixed(2)}%
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {Math.abs(selectedRecord.variance ?? 0) > 50 ? "Critical - Potential TBML indicator" :
                   Math.abs(selectedRecord.variance ?? 0) > 25 ? "High - Requires investigation" :
                   Math.abs(selectedRecord.variance ?? 0) > 10 ? "Medium - Monitor closely" :
                   "Low - Within acceptable range"}
                </p>
              </div>

              {/* Details */}
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Commodity Code</span>
                  <span className="font-mono">{selectedRecord.commodityCode}</span>
                </div>
                {selectedRecord.documentRef && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Document Ref</span>
                    <span>{selectedRecord.documentRef}</span>
                  </div>
                )}
                {selectedRecord.documentType && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Document Type</span>
                    <span>{selectedRecord.documentType}</span>
                  </div>
                )}
                {selectedRecord.riskLevel && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Risk Level</span>
                    <Badge variant="outline" className={
                      selectedRecord.riskLevel === "critical" ? "border-red-500 text-red-500" :
                      selectedRecord.riskLevel === "high" ? "border-orange-500 text-orange-500" :
                      selectedRecord.riskLevel === "medium" ? "border-yellow-500 text-yellow-500" :
                      "border-green-500 text-green-500"
                    }>
                      {selectedRecord.riskLevel.toUpperCase()}
                    </Badge>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Verification ID</span>
                  <span className="font-mono text-xs">{selectedRecord.id}</span>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}


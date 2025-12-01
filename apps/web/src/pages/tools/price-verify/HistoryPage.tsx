import { useState, useEffect } from "react";
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
  Loader2
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

  const downloadHistory = () => {
    const headers = ["Date", "Commodity", "Doc Price", "Market Price", "Variance", "Verdict", "Document", "TBML"];
    const rows = filteredHistory.map(r => [
      new Date(r.date).toISOString(),
      r.commodity,
      r.documentPrice,
      r.marketPrice,
      `${r.variance}%`,
      r.verdict,
      r.documentRef || "-",
      r.tbmlFlag ? "YES" : "NO",
    ]);
    const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `verification_history_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
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
        <Button variant="outline" onClick={downloadHistory} disabled={history.length === 0}>
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </Button>
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
                      ${record.documentPrice.toLocaleString()} vs ${record.marketPrice.toLocaleString()}
                    </p>
                    <p className={`text-sm ${
                      record.variance > 15 ? "text-red-600" :
                      record.variance > 5 ? "text-yellow-600" :
                      "text-green-600"
                    }`}>
                      {record.variance > 0 ? "+" : ""}{record.variance.toFixed(1)}% variance
                    </p>
                  </div>
                  <Button variant="ghost" size="icon">
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
    </div>
  );
}


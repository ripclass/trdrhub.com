import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Download,
  FileText,
  Eye,
  Filter,
  Download as DownloadIcon,
} from "lucide-react";
import { format } from "date-fns";

interface ValidationResult {
  id: string;
  jobId: string;
  clientName: string;
  lcNumber?: string;
  submittedAt: Date;
  completedAt: Date;
  status: "compliant" | "discrepancies" | "failed";
  complianceScore: number;
  discrepancyCount: number;
  documentCount: number;
}

interface ResultsTableProps {}

export function ResultsTable({}: ResultsTableProps) {
  const [results, setResults] = useState<ValidationResult[]>([]);
  const [filteredResults, setFilteredResults] = useState<ValidationResult[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [clientFilter, setClientFilter] = useState("");
  const [dateRange, setDateRange] = useState("90"); // days

  // Load results from localStorage (temporary until backend is ready)
  useEffect(() => {
    const loadResults = () => {
      const stored = localStorage.getItem("bank_validation_results");
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          const loaded = parsed.map((r: any) => ({
            ...r,
            submittedAt: new Date(r.submittedAt),
            completedAt: new Date(r.completedAt),
          }));

          // Filter by date range (default: last 90 days)
          const cutoffDate = new Date();
          cutoffDate.setDate(cutoffDate.getDate() - parseInt(dateRange));
          const filtered = loaded.filter(
            (r: ValidationResult) => r.completedAt >= cutoffDate
          );

          setResults(filtered);
        } catch (e) {
          console.error("Failed to load results:", e);
        }
      }
    };

    loadResults();
  }, [dateRange]);

  // Apply filters
  useEffect(() => {
    let filtered = [...results];

    // Status filter
    if (statusFilter !== "all") {
      filtered = filtered.filter((r) => r.status === statusFilter);
    }

    // Client name filter
    if (clientFilter.trim()) {
      filtered = filtered.filter((r) =>
        r.clientName.toLowerCase().includes(clientFilter.toLowerCase())
      );
    }

    // Sort by completed date (newest first)
    filtered.sort((a, b) => b.completedAt.getTime() - a.completedAt.getTime());

    setFilteredResults(filtered);
  }, [results, statusFilter, clientFilter]);

  const getStatusBadge = (status: ValidationResult["status"]) => {
    switch (status) {
      case "compliant":
        return <Badge variant="default" className="bg-green-500">Compliant</Badge>;
      case "discrepancies":
        return <Badge variant="default" className="bg-yellow-500">Discrepancies</Badge>;
      case "failed":
        return <Badge variant="destructive">Failed</Badge>;
    }
  };

  const handleExportCSV = () => {
    const csvContent = [
      ["LC Number", "Client Name", "Date", "Status", "Score", "Discrepancies", "Documents"].join(","),
      ...filteredResults.map((r) =>
        [
          r.lcNumber || "N/A",
          r.clientName,
          format(r.completedAt, "yyyy-MM-dd HH:mm:ss"),
          r.status,
          r.complianceScore,
          r.discrepancyCount,
          r.documentCount,
        ].join(",")
      ),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `bank-lc-results-${format(new Date(), "yyyy-MM-dd")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = () => {
    // TODO: Implement PDF export
    alert("PDF export coming soon!");
  };

  const handleViewDetails = (result: ValidationResult) => {
    // TODO: Navigate to detail view or open modal
    window.location.href = `/lcopilot/results/${result.jobId}`;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Validation Results</CardTitle>
            <CardDescription>
              {filteredResults.length} result(s) from last {dateRange} days
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleExportCSV}>
              <DownloadIcon className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportPDF}>
              <FileText className="w-4 h-4 mr-2" />
              Export PDF
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="space-y-2">
            <Label>Date Range</Label>
            <Select value={dateRange} onValueChange={setDateRange}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
                <SelectItem value="180">Last 180 days</SelectItem>
                <SelectItem value="365">Last year</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Status</Label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="compliant">Compliant</SelectItem>
                <SelectItem value="discrepancies">With Discrepancies</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Client Name</Label>
            <Input
              placeholder="Search by client name..."
              value={clientFilter}
              onChange={(e) => setClientFilter(e.target.value)}
            />
          </div>
        </div>

        {/* Results Table */}
        {filteredResults.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No results found</p>
            <p className="text-sm text-muted-foreground mt-2">
              Try adjusting your filters or upload more LCs
            </p>
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>LC Number</TableHead>
                  <TableHead>Client Name</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead className="text-right">Discrepancies</TableHead>
                  <TableHead className="text-right">Documents</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredResults.map((result) => (
                  <TableRow key={result.id}>
                    <TableCell className="font-medium">
                      {result.lcNumber || "N/A"}
                    </TableCell>
                    <TableCell>{result.clientName}</TableCell>
                    <TableCell>
                      {format(result.completedAt, "MMM dd, yyyy HH:mm")}
                    </TableCell>
                    <TableCell>{getStatusBadge(result.status)}</TableCell>
                    <TableCell className="text-right">
                      {result.complianceScore}%
                    </TableCell>
                    <TableCell className="text-right">
                      {result.discrepancyCount}
                    </TableCell>
                    <TableCell className="text-right">
                      {result.documentCount}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewDetails(result)}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm">
                          <Download className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
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
  Download as DownloadIcon,
} from "lucide-react";
import { format } from "date-fns";
import { bankApi, BankResult } from "@/api/bank";
import { sanitizeDisplayText } from "@/lib/sanitize";
import { generateCSV } from "@/lib/csv";

interface ResultsTableProps {}

export function ResultsTable({}: ResultsTableProps) {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [clientFilter, setClientFilter] = useState("");
  const [dateRange, setDateRange] = useState("90"); // days

  // Calculate date range for API
  const getDateRange = () => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - parseInt(dateRange));
    return {
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
    };
  };

  // Fetch results from API
  const { data: resultsData, isLoading } = useQuery({
    queryKey: ['bank-results', dateRange],
    queryFn: () => bankApi.getResults({
      ...getDateRange(),
      limit: 500,
      offset: 0,
    }),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const allResults: BankResult[] = resultsData?.results || [];

  // Apply filters
  const filteredResults = allResults.filter((result) => {
    // Status filter
    if (statusFilter !== "all" && result.status !== statusFilter) {
      return false;
    }

    // Client name filter
    if (clientFilter.trim()) {
      const clientName = result.client_name || "";
      if (!clientName.toLowerCase().includes(clientFilter.toLowerCase())) {
        return false;
      }
    }

    return true;
  }).sort((a, b) => {
    // Sort by completed date (newest first)
    const dateA = a.completed_at ? new Date(a.completed_at).getTime() : 0;
    const dateB = b.completed_at ? new Date(b.completed_at).getTime() : 0;
    return dateB - dateA;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "compliant":
        return <Badge variant="default" className="bg-green-500">Compliant</Badge>;
      case "discrepancies":
        return <Badge variant="default" className="bg-yellow-500">Discrepancies</Badge>;
      case "failed":
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const handleExportCSV = () => {
    const csvRows = [
      ["LC Number", "Client Name", "Date", "Status", "Score", "Discrepancies", "Documents"],
      ...filteredResults.map((r) => {
        const completedAt = r.completed_at ? new Date(r.completed_at) : new Date();
        return [
          sanitizeDisplayText(r.lc_number, "N/A"),
          sanitizeDisplayText(r.client_name, ""),
          format(completedAt, "yyyy-MM-dd HH:mm:ss"),
          r.status,
          r.compliance_score.toString(),
          r.discrepancy_count.toString(),
          r.document_count.toString(),
        ];
      }),
    ];

    const csvContent = generateCSV(csvRows);

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

  const handleViewDetails = (result: BankResult) => {
    window.location.href = `/lcopilot/results/${result.jobId}`;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Validation Results</CardTitle>
            <CardDescription>
              {isLoading ? "Loading..." : `${filteredResults.length} result(s) from last ${dateRange} days`}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleExportCSV} disabled={filteredResults.length === 0}>
              <DownloadIcon className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportPDF} disabled={filteredResults.length === 0}>
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
        {isLoading ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4 animate-pulse" />
            <p className="text-muted-foreground">Loading results...</p>
          </div>
        ) : filteredResults.length === 0 ? (
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
                {filteredResults.map((result) => {
                  const completedAt = result.completed_at ? new Date(result.completed_at) : new Date();
                  const clientName = sanitizeDisplayText(result.client_name, "Unknown");
                  const lcNumber = sanitizeDisplayText(result.lc_number, "N/A");

                  return (
                    <TableRow key={result.id}>
                      <TableCell className="font-medium">
                        {lcNumber}
                      </TableCell>
                      <TableCell>{clientName}</TableCell>
                      <TableCell>
                        {format(completedAt, "MMM dd, yyyy HH:mm")}
                      </TableCell>
                      <TableCell>{getStatusBadge(result.status)}</TableCell>
                      <TableCell className="text-right">
                        {result.compliance_score}%
                      </TableCell>
                      <TableCell className="text-right">
                        {result.discrepancy_count}
                      </TableCell>
                      <TableCell className="text-right">
                        {result.document_count}
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
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

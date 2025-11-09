import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
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
  ChevronDown,
  ChevronUp,
  Copy,
  Receipt,
} from "lucide-react";
import { format } from "date-fns";
import { bankApi, BankResult, BankResultsFilters } from "@/api/bank";
import { sanitizeDisplayText } from "@/lib/sanitize";
import { generateCSV } from "@/lib/csv";
import { LCResultDetailModal } from "./LCResultDetailModal";
import { Checkbox } from "@/components/ui/checkbox";
import { AdvancedFilters } from "./AdvancedFilters";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { SavedViewsManager } from "@/components/shared/SavedViewsManager";
import { parseDeepLinkFilters } from "@/lib/savedViews";

interface ResultsTableProps {}

export function ResultsTable({}: ResultsTableProps) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const clientFromUrl = searchParams.get("client") || "";
  
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [clientFilter, setClientFilter] = useState(clientFromUrl);
  const [dateRange, setDateRange] = useState("90"); // days
  const [advancedFilters, setAdvancedFilters] = useState<BankResultsFilters>({});
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedClientName, setSelectedClientName] = useState<string | undefined>();
  const [selectedLcNumber, setSelectedLcNumber] = useState<string | undefined>();
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [isAdvancedFiltersOpen, setIsAdvancedFiltersOpen] = useState(false);

  // Handle deep link views
  useEffect(() => {
    const deepLink = parseDeepLinkFilters(searchParams);
    if (deepLink.viewId && deepLink.filters) {
      // Apply filters from deep link
      if (deepLink.filters.status) setStatusFilter(deepLink.filters.status);
      if (deepLink.filters.client_name) setClientFilter(deepLink.filters.client_name);
      if (deepLink.filters.dateRange) setDateRange(deepLink.filters.dateRange);
      if (deepLink.filters.advancedFilters) setAdvancedFilters(deepLink.filters.advancedFilters);
    }
  }, [searchParams]);

  // Update client filter when URL changes
  useEffect(() => {
    const clientFromUrl = searchParams.get("client") || "";
    if (clientFromUrl && clientFromUrl !== clientFilter) {
      setClientFilter(clientFromUrl);
    }
  }, [searchParams, clientFilter]);

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

  // Build API filters
  const apiFilters: BankResultsFilters = {
    ...getDateRange(),
    client_name: clientFilter || undefined,
    status: statusFilter !== "all" ? statusFilter as "compliant" | "discrepancies" : undefined,
    ...advancedFilters,
    limit: 500,
    offset: 0,
  };

  // Fetch results from API with all filters
  const { data: resultsData, isLoading } = useQuery({
    queryKey: ['bank-results', dateRange, statusFilter, clientFilter, advancedFilters],
    queryFn: () => bankApi.getResults(apiFilters),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const filteredResults: BankResult[] = resultsData?.results || [];

  // Get selected results (if any selected, use those; otherwise use filtered)
  const exportResults = selectedRows.size > 0
    ? filteredResults.filter(r => selectedRows.has(r.jobId))
    : filteredResults;

  // Selection handlers
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedRows(new Set(filteredResults.map(r => r.jobId)));
    } else {
      setSelectedRows(new Set());
    }
  };

  const handleSelectRow = (jobId: string, checked: boolean) => {
    const newSelected = new Set(selectedRows);
    if (checked) {
      newSelected.add(jobId);
    } else {
      newSelected.delete(jobId);
    }
    setSelectedRows(newSelected);
  };

  // Clear selection when filters change
  useEffect(() => {
    setSelectedRows(new Set());
  }, [statusFilter, clientFilter, dateRange, advancedFilters]);

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
    // Enhanced CSV with all available fields
    const csvRows = [
      [
        "Job ID",
        "LC Number",
        "Client Name",
        "Date Received",
        "Submitted At",
        "Processing Started At",
        "Completed At",
        "Processing Time (seconds)",
        "Status",
        "Compliance Score (%)",
        "Discrepancy Count",
        "Document Count",
      ],
      ...exportResults.map((r) => {
        const submittedAt = r.submitted_at ? new Date(r.submitted_at) : null;
        const processingStartedAt = r.processing_started_at ? new Date(r.processing_started_at) : null;
        const completedAt = r.completed_at ? new Date(r.completed_at) : null;
        const dateReceived = r.date_received || "";

        return [
          r.jobId || r.id,
          sanitizeDisplayText(r.lc_number, "N/A"),
          sanitizeDisplayText(r.client_name, ""),
          dateReceived,
          submittedAt ? format(submittedAt, "yyyy-MM-dd HH:mm:ss") : "",
          processingStartedAt ? format(processingStartedAt, "yyyy-MM-dd HH:mm:ss") : "",
          completedAt ? format(completedAt, "yyyy-MM-dd HH:mm:ss") : "",
          r.processing_time_seconds !== undefined && r.processing_time_seconds !== null
            ? r.processing_time_seconds.toString()
            : "",
          r.status,
          r.compliance_score.toString(),
          r.discrepancy_count.toString(),
          r.document_count.toString(),
        ];
      }),
    ];

    const csvContent = generateCSV(csvRows);

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const selectedCount = selectedRows.size > 0 ? `-selected-${selectedRows.size}` : "";
    a.download = `bank-lc-results${selectedCount}-${format(new Date(), "yyyy-MM-dd")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = async () => {
    try {
      const params: any = {
        ...getDateRange(),
        client_name: clientFilter || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        ...advancedFilters,
        limit: 500, // Export all filtered results
      };

      // If rows are selected, send job IDs instead of filters
      if (selectedRows.size > 0) {
        params.job_ids = Array.from(selectedRows).join(",");
        // Clear other filters when using job_ids
        delete params.start_date;
        delete params.end_date;
        delete params.client_name;
        delete params.status;
      }

      const pdfBlob = await bankApi.exportResultsPDF(params);

      // Create download link
      const url = URL.createObjectURL(pdfBlob);
      const a = document.createElement("a");
      a.href = url;
      const selectedCount = selectedRows.size > 0 ? `-selected-${selectedRows.size}` : "";
      a.download = `bank-lc-results${selectedCount}-${format(new Date(), "yyyy-MM-dd")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      console.error("Failed to export PDF:", error);
      alert("Failed to export PDF. Please try again.");
    }
  };

  const handleViewDetails = (result: BankResult) => {
    setSelectedJobId(result.jobId);
    setSelectedClientName(result.client_name);
    setSelectedLcNumber(result.lc_number);
  };

  const handleDownloadPDF = async (result: BankResult) => {
    try {
      const { getReportDownloadUrl } = await import("@/api/sessions");
      const reportData = await getReportDownloadUrl(result.jobId);
      window.open(reportData.download_url, "_blank");
    } catch (error: any) {
      console.error("Failed to download report:", error);
      alert("Failed to download report. Please try again.");
    }
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
            {selectedRows.size > 0 && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>{selectedRows.size} selected</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedRows(new Set())}
                >
                  Clear
                </Button>
              </div>
            )}
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleExportCSV} 
              disabled={exportResults.length === 0}
            >
              <DownloadIcon className="w-4 h-4 mr-2" />
              Export CSV {selectedRows.size > 0 ? `(${selectedRows.size})` : ""}
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleExportPDF} 
              disabled={exportResults.length === 0}
            >
              <FileText className="w-4 h-4 mr-2" />
              Export PDF {selectedRows.size > 0 ? `(${selectedRows.size})` : ""}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Basic Filters */}
        <div className="flex items-center justify-between mb-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1">
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
          
          {/* Saved Views Manager */}
          <div className="ml-4">
            <SavedViewsManager
              dashboard="bank"
              section="results"
              currentFilters={{
                status: statusFilter,
                client_name: clientFilter,
                dateRange,
                advancedFilters,
              }}
              onLoadView={(filters) => {
                if (filters.status) setStatusFilter(filters.status);
                if (filters.client_name) setClientFilter(filters.client_name);
                if (filters.dateRange) setDateRange(filters.dateRange);
                if (filters.advancedFilters) setAdvancedFilters(filters.advancedFilters);
              }}
            />
          </div>
        </div>

        {/* Advanced Filters */}
        <Collapsible open={isAdvancedFiltersOpen} onOpenChange={setIsAdvancedFiltersOpen} className="mb-6">
          <CollapsibleTrigger asChild>
            <Button variant="outline" className="w-full">
              {isAdvancedFiltersOpen ? (
                <>
                  <ChevronUp className="w-4 h-4 mr-2" />
                  Hide Advanced Filters
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4 mr-2" />
                  Show Advanced Filters
                </>
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-4">
            <AdvancedFilters
              filters={advancedFilters}
              onFiltersChange={setAdvancedFilters}
            />
          </CollapsibleContent>
        </Collapsible>

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
            <Table dense sticky>
              <TableHeader sticky>
                <TableRow dense>
                  <TableHead dense className="w-12">
                    <Checkbox
                      checked={filteredResults.length > 0 && selectedRows.size === filteredResults.length}
                      onCheckedChange={handleSelectAll}
                      aria-label="Select all"
                    />
                  </TableHead>
                  <TableHead dense>LC Number</TableHead>
                  <TableHead dense>Client Name</TableHead>
                  <TableHead dense>Date</TableHead>
                  <TableHead dense>Status</TableHead>
                  <TableHead dense numeric>Score</TableHead>
                  <TableHead dense numeric>Discrepancies</TableHead>
                  <TableHead dense numeric>Documents</TableHead>
                  <TableHead dense className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody zebra>
                {filteredResults.map((result) => {
                  const completedAt = result.completed_at ? new Date(result.completed_at) : new Date();
                  const clientName = sanitizeDisplayText(result.client_name, "Unknown");
                  const lcNumber = sanitizeDisplayText(result.lc_number, "N/A");
                  const isSelected = selectedRows.has(result.jobId);

                  return (
                    <TableRow dense key={result.id} className={isSelected ? "bg-muted/50" : ""}>
                      <TableCell dense>
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={(checked) => handleSelectRow(result.jobId, checked === true)}
                          aria-label={`Select ${lcNumber}`}
                        />
                      </TableCell>
                      <TableCell dense className="font-medium">
                        <div className="flex items-center gap-1.5">
                          {lcNumber}
                          {result.duplicate_count && result.duplicate_count > 0 && (
                            <Badge variant="outline" className="text-[10px] h-4 px-1" title={`This LC has been validated ${result.duplicate_count} time(s) before`}>
                              <Copy className="w-2.5 h-2.5 mr-0.5" />
                              {result.duplicate_count}x
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell dense>
                        <button
                          onClick={() => navigate(`/lcopilot/bank-dashboard/client/${encodeURIComponent(clientName)}`)}
                          className="text-primary hover:underline font-medium"
                        >
                          {clientName}
                        </button>
                      </TableCell>
                      <TableCell dense>
                        {format(completedAt, "MMM dd, HH:mm")}
                      </TableCell>
                      <TableCell dense>{getStatusBadge(result.status)}</TableCell>
                      <TableCell dense numeric>
                        {result.compliance_score}%
                      </TableCell>
                      <TableCell dense numeric>
                        {result.discrepancy_count}
                      </TableCell>
                      <TableCell dense numeric>
                        {result.document_count}
                      </TableCell>
                      <TableCell dense className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          {/* Invoice link - check if result has invoiceId (future enhancement) */}
                          {(result as any).invoiceId && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => navigate(`/lcopilot/bank-dashboard?tab=billing-invoices&invoice=${(result as any).invoiceId}`)}
                              title="View Invoice"
                            >
                              <Receipt className="w-4 h-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewDetails(result)}
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDownloadPDF(result)}
                            title="Download PDF Report"
                          >
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
    <LCResultDetailModal
      jobId={selectedJobId}
      open={!!selectedJobId}
      onOpenChange={(open) => {
        if (!open) {
          setSelectedJobId(null);
          setSelectedClientName(undefined);
          setSelectedLcNumber(undefined);
        }
      }}
      clientName={selectedClientName}
      lcNumber={selectedLcNumber}
    />
  );
}

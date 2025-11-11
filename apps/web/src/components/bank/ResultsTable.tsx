import React, { useState, useEffect, useMemo } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Download,
  FileText,
  Eye,
  Copy,
  Receipt,
} from "lucide-react";
import { format } from "date-fns";
import { bankApi, BankResult, BankResultsFilters } from "@/api/bank";
import { sanitizeDisplayText } from "@/lib/sanitize";
import { LCResultDetailModal } from "./LCResultDetailModal";
import { Checkbox } from "@/components/ui/checkbox";
import { FilterBar } from "@/components/shared/FilterBar";
import { ExportJobHandler } from "@/components/shared/ExportJobHandler";
import { DuplicateBadge } from "./DuplicateBadge";
import { DuplicateCandidatesPanel } from "./DuplicateCandidatesPanel";
import { MergeModal } from "./MergeModal";
import type { DuplicateCandidate } from "@/api/bank";

interface ResultsTableProps {}

export function ResultsTable({}: ResultsTableProps) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedClientName, setSelectedClientName] = useState<string | undefined>();
  const [selectedLcNumber, setSelectedLcNumber] = useState<string | undefined>();
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [duplicateCandidatesSessionId, setDuplicateCandidatesSessionId] = useState<string | null>(null);
  const [mergeCandidate, setMergeCandidate] = useState<DuplicateCandidate | null>(null);

  // Extract filters from URL
  const q = searchParams.get('q') || '';
  const assignee = searchParams.get('assignee') || '';
  const queue = searchParams.get('queue') || '';
  const status = searchParams.get('status') || 'all';
  const clientName = searchParams.get('client_name') || '';
  const dateRange = searchParams.get('date_range') || '90';
  const sortBy = searchParams.get('sort_by') || 'completed_at';
  const sortOrder = searchParams.get('sort_order') || 'desc';
  const advancedFiltersStr = searchParams.get('advanced_filters');
  const advancedFilters: BankResultsFilters = useMemo(() => {
    try {
      return advancedFiltersStr ? JSON.parse(advancedFiltersStr) : {};
    } catch {
      return {};
    }
  }, [advancedFiltersStr]);

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
    q: q || undefined,
    assignee: assignee || undefined,
    queue: queue || undefined,
    client_name: clientName || undefined,
    status: status !== "all" ? status as "compliant" | "discrepancies" : undefined,
    sort_by: sortBy as any,
    sort_order: sortOrder as any,
    ...advancedFilters,
    limit: 500,
    offset: 0,
  };

  // Fetch results from API with all filters
  const { data: resultsData, isLoading } = useQuery({
    queryKey: ['bank-results', apiFilters],
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
  }, [q, assignee, queue, status, clientName, dateRange, advancedFilters]);

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

  const handleExportCSV = async () => {
    try {
      setExportLoading(true);
      const params: BankResultsFilters = {
        ...apiFilters,
        limit: undefined, // Remove limit for export
        offset: undefined,
      };

      // If rows are selected, send job IDs instead of filters
      if (selectedRows.size > 0) {
        (params as any).job_ids = Array.from(selectedRows).join(",");
      }

      const result = await bankApi.exportResultsCSV(params);

      // Check if async job was created
      if (typeof result === 'object' && 'job_id' in result) {
        setExportJobId(result.job_id);
        toast({
          title: "Export Started",
          description: `Exporting ${result.total_rows.toLocaleString()} rows. This may take a moment...`,
        });
      } else {
        // Direct download
        const blob = result as Blob;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const selectedCount = selectedRows.size > 0 ? `-selected-${selectedRows.size}` : "";
        a.download = `bank-lc-results${selectedCount}-${format(new Date(), "yyyy-MM-dd")}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        toast({
          title: "Export Complete",
          description: "CSV file downloaded successfully.",
        });
      }
    } catch (error: any) {
      console.error("Failed to export CSV:", error);
      toast({
        title: "Export Failed",
        description: error.message || "Failed to export CSV. Please try again.",
        variant: "destructive",
      });
    } finally {
      setExportLoading(false);
    }
  };

  const handleExportPDF = async () => {
    try {
      setExportLoading(true);
      const params: BankResultsFilters = {
        ...apiFilters,
        limit: undefined, // Remove limit for export
        offset: undefined,
      };

      // If rows are selected, send job IDs instead of filters
      if (selectedRows.size > 0) {
        (params as any).job_ids = Array.from(selectedRows).join(",");
      }

      const result = await bankApi.exportResultsPDF(params);

      // Check if async job was created
      if (typeof result === 'object' && 'job_id' in result) {
        setExportJobId(result.job_id);
        toast({
          title: "Export Started",
          description: `Exporting ${result.total_rows.toLocaleString()} rows. This may take a moment...`,
        });
      } else {
        // Direct download
        const blob = result as Blob;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const selectedCount = selectedRows.size > 0 ? `-selected-${selectedRows.size}` : "";
        a.download = `bank-lc-results${selectedCount}-${format(new Date(), "yyyy-MM-dd")}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        toast({
          title: "Export Complete",
          description: "PDF file downloaded successfully.",
        });
      }
    } catch (error: any) {
      console.error("Failed to export PDF:", error);
      toast({
        title: "Export Failed",
        description: error.message || "Failed to export PDF. Please try again.",
        variant: "destructive",
      });
    } finally {
      setExportLoading(false);
    }
  };

  const handleViewDetails = (result: BankResult) => {
    if (!result) return;
    setSelectedJobId(result.jobId);
    setSelectedClientName(result.client_name);
    setSelectedLcNumber(result.lc_number || undefined);
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
    <div>
      <Card>
        <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Validation Results</CardTitle>
            <CardDescription>
              {isLoading ? "Loading..." : `${filteredResults.length} result(s)`}
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
              <Download className="w-4 h-4 mr-2" />
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
        {/* Filter Bar */}
        <div className="mb-6">
          <FilterBar
            resource="results"
            onFiltersChange={(filters) => {
              // Filters are managed via URL params, so this is mainly for side effects
            }}
            onExportCSV={handleExportCSV}
            onExportPDF={handleExportPDF}
            exportLoading={exportLoading}
          />
        </div>

        {/* Export Job Handler */}
        {exportJobId && (
          <div className="mb-4">
            <ExportJobHandler
              jobId={exportJobId}
              onComplete={(downloadUrl) => {
                window.open(downloadUrl, '_blank');
                setExportJobId(null);
              }}
              onError={() => {
                setExportJobId(null);
              }}
              onClear={() => {
                setExportJobId(null);
              }}
            />
          </div>
        )}

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
                  if (!result) return null;
                  const completedAt = result.completed_at ? new Date(result.completed_at) : new Date();
                  const clientName = sanitizeDisplayText(result.client_name, "Unknown");
                  const lcNumber = sanitizeDisplayText(result.lc_number || "", "N/A");
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
                            <DuplicateBadge
                              count={result.duplicate_count}
                              onClick={() => setDuplicateCandidatesSessionId(result.jobId)}
                            />
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
    <DuplicateCandidatesPanel
      sessionId={duplicateCandidatesSessionId || ''}
      open={!!duplicateCandidatesSessionId}
      onOpenChange={(open) => {
        if (!open) setDuplicateCandidatesSessionId(null);
      }}
      onMerge={(candidate) => {
        setDuplicateCandidatesSessionId(null);
        setMergeCandidate(candidate);
      }}
    />
    <MergeModal
      sourceSessionId={duplicateCandidatesSessionId || ''}
      candidate={mergeCandidate!}
      open={!!mergeCandidate}
      onOpenChange={(open) => {
        if (!open) {
          setMergeCandidate(null);
          setDuplicateCandidatesSessionId(null);
        }
      }}
      onSuccess={() => {
        // Refresh results after merge
        queryClient.invalidateQueries({ queryKey: ['bank-results'] });
      }}
    />
    </div>
  );
}

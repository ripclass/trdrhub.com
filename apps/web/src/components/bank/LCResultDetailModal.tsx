import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Download,
  Clock,
  Calendar,
  Building2,
  Hash,
} from "lucide-react";
import { MergeHistoryTimeline } from "./MergeHistoryTimeline";

interface LCResultDetailModalProps {
  jobId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  clientName?: string;
  lcNumber?: string;
}

export function LCResultDetailModal({
  jobId,
  open,
  onOpenChange,
  clientName: propClientName,
  lcNumber: propLcNumber,
}: LCResultDetailModalProps) {
  const [downloadingReport, setDownloadingReport] = useState(false);

  // Fetch full session details
  const { data: session, isLoading, error } = useQuery<ValidationSession>({
    queryKey: ["validation-session", jobId],
    queryFn: () => getValidationSession(jobId!),
    enabled: open && !!jobId,
  });

  // Extract bank metadata
  const bankMetadata = session?.extracted_data?.bank_metadata || {};
  const clientName = propClientName || bankMetadata.client_name || "Unknown";
  const lcNumber = propLcNumber || bankMetadata.lc_number || "N/A";

  const handleDownloadReport = async () => {
    if (!jobId) return;

    setDownloadingReport(true);
    try {
      const reportData = await getReportDownloadUrl(jobId);
      window.open(reportData.download_url, "_blank");
    } catch (error: any) {
      console.error("Failed to download report:", error);
      alert("Failed to download report. Please try again.");
    } finally {
      setDownloadingReport(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "critical":
        return <Badge variant="destructive">Critical</Badge>;
      case "major":
        return <Badge variant="default" className="bg-yellow-500">Major</Badge>;
      case "minor":
        return <Badge variant="secondary">Minor</Badge>;
      default:
        return <Badge variant="secondary">{severity}</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge variant="default" className="bg-green-500">Completed</Badge>;
      case "failed":
        return <Badge variant="destructive">Failed</Badge>;
      case "processing":
        return <Badge variant="default" className="bg-blue-500">Processing</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (error) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Error Loading Details</DialogTitle>
            <DialogDescription>
              Failed to load validation details. Please try again.
            </DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            LC Validation Details
          </DialogTitle>
          <DialogDescription>
            Complete validation results and document information
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Clock className="w-8 h-8 animate-spin text-muted-foreground" />
            <p className="ml-2 text-muted-foreground">Loading details...</p>
          </div>
        ) : session ? (
          <ScrollArea className="max-h-[calc(90vh-120px)] pr-4">
            <div className="space-y-6">
              {/* Summary Info */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <div className="text-sm text-muted-foreground flex items-center gap-2">
                        <Building2 className="w-4 h-4" />
                        Client Name
                      </div>
                      <p className="font-medium">{sanitizeDisplayText(clientName, "Unknown")}</p>
                    </div>
                    <div className="space-y-1">
                      <div className="text-sm text-muted-foreground flex items-center gap-2">
                        <Hash className="w-4 h-4" />
                        LC Number
                      </div>
                      <p className="font-medium">{sanitizeDisplayText(lcNumber, "N/A")}</p>
                    </div>
                    <div className="space-y-1">
                      <div className="text-sm text-muted-foreground flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        Submitted At
                      </div>
                      <p className="font-medium">
                        {session.created_at
                          ? format(new Date(session.created_at), "MMM dd, yyyy HH:mm:ss")
                          : "N/A"}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <div className="text-sm text-muted-foreground flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        Status
                      </div>
                      <div>{getStatusBadge(session.status)}</div>
                    </div>
                  </div>
                  {session.processing_completed_at && (
                    <div className="space-y-1">
                      <div className="text-sm text-muted-foreground">Completed At</div>
                      <p className="font-medium">
                        {format(
                          new Date(session.processing_completed_at),
                          "MMM dd, yyyy HH:mm:ss"
                        )}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Tabs for Documents, Discrepancies, and History */}
              <Tabs defaultValue="documents" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="documents">
                    Documents ({session.documents?.length || 0})
                  </TabsTrigger>
                  <TabsTrigger value="discrepancies">
                    Discrepancies ({session.discrepancies?.length || 0})
                  </TabsTrigger>
                  <TabsTrigger value="history">
                    History
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="documents" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>Uploaded Documents</CardTitle>
                      <CardDescription>
                        All documents processed for this validation
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {session.documents && session.documents.length > 0 ? (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Document Type</TableHead>
                              <TableHead>Filename</TableHead>
                              <TableHead>File Size</TableHead>
                              <TableHead>OCR Confidence</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {session.documents.map((doc) => (
                              <TableRow key={doc.id}>
                                <TableCell className="font-medium">
                                  {doc.document_type || "Unknown"}
                                </TableCell>
                                <TableCell>{sanitizeDisplayText(doc.original_filename, "N/A")}</TableCell>
                                <TableCell>
                                  {doc.file_size
                                    ? `${(doc.file_size / 1024 / 1024).toFixed(2)} MB`
                                    : "N/A"}
                                </TableCell>
                                <TableCell>
                                  {doc.ocr_confidence !== undefined
                                    ? `${(doc.ocr_confidence * 100).toFixed(1)}%`
                                    : "N/A"}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      ) : (
                        <p className="text-sm text-muted-foreground text-center py-8">
                          No documents found
                        </p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="discrepancies" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>Validation Discrepancies</CardTitle>
                      <CardDescription>
                        Issues found during validation process
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {session.discrepancies && session.discrepancies.length > 0 ? (
                        <div className="space-y-4">
                          {session.discrepancies.map((disc) => (
                            <div
                              key={disc.id}
                              className="border rounded-lg p-4 space-y-2"
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex items-center gap-2">
                                  {disc.severity === "critical" ? (
                                    <AlertTriangle className="w-5 h-5 text-destructive" />
                                  ) : (
                                    <AlertTriangle className="w-5 h-5 text-yellow-500" />
                                  )}
                                  <div>
                                    <div className="font-medium flex items-center gap-2">
                                      {disc.rule_name}
                                      {getSeverityBadge(disc.severity)}
                                    </div>
                                    <div className="text-sm text-muted-foreground">
                                      {disc.discrepancy_type}
                                    </div>
                                  </div>
                                </div>
                              </div>
                              <Separator />
                              <div className="space-y-2 text-sm">
                                <p className="font-medium">{disc.description}</p>
                                {disc.field_name && (
                                  <div className="grid grid-cols-2 gap-4 text-xs">
                                    <div>
                                      <span className="text-muted-foreground">Field: </span>
                                      <span className="font-medium">{disc.field_name}</span>
                                    </div>
                                    {disc.expected_value && (
                                      <div>
                                        <span className="text-muted-foreground">Expected: </span>
                                        <span className="font-medium">{disc.expected_value}</span>
                                      </div>
                                    )}
                                    {disc.actual_value && (
                                      <div>
                                        <span className="text-muted-foreground">Actual: </span>
                                        <span className="font-medium">{disc.actual_value}</span>
                                      </div>
                                    )}
                                  </div>
                                )}
                                {disc.source_document_types &&
                                  disc.source_document_types.length > 0 && (
                                    <div className="text-xs text-muted-foreground">
                                      Source documents: {disc.source_document_types.join(", ")}
                                    </div>
                                  )}
                                <div className="text-xs text-muted-foreground">
                                  Found:{" "}
                                  {format(new Date(disc.created_at), "MMM dd, yyyy HH:mm:ss")}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center py-12">
                          <CheckCircle className="w-12 h-12 mx-auto text-green-500 mb-4" />
                          <p className="text-sm font-medium">No Discrepancies Found</p>
                          <p className="text-xs text-muted-foreground mt-2">
                            All validation checks passed successfully
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="history" className="space-y-4">
                  {jobId && <MergeHistoryTimeline sessionId={jobId} />}
                </TabsContent>
              </Tabs>

              {/* Action Buttons */}
              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Close
                </Button>
                {session.status === "completed" && (
                  <Button onClick={handleDownloadReport} disabled={downloadingReport}>
                    {downloadingReport ? (
                      <>
                        <Clock className="w-4 h-4 mr-2 animate-spin" />
                        Downloading...
                      </>
                    ) : (
                      <>
                        <Download className="w-4 h-4 mr-2" />
                        Download PDF Report
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
          </ScrollArea>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}


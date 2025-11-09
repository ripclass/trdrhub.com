import * as React from "react";
import { useSearchParams } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  FileText,
  Download,
  Package,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  FileArchive,
  FileDown,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ValidationSession {
  id: string;
  lc_number: string;
  client_name: string;
  status: "completed" | "failed" | "processing";
  completed_at: string;
  discrepancy_count: number;
  document_count: number;
  compliance_score: number;
}

// Mock data - replace with API calls
const mockSessions: ValidationSession[] = [
  {
    id: "session-1",
    lc_number: "LC-BNK-2024-001",
    client_name: "Global Importers Ltd",
    status: "completed",
    completed_at: "2024-01-18T10:30:00Z",
    discrepancy_count: 2,
    document_count: 5,
    compliance_score: 85,
  },
  {
    id: "session-2",
    lc_number: "LC-BNK-2024-002",
    client_name: "Trade Partners Inc",
    status: "completed",
    completed_at: "2024-01-17T14:15:00Z",
    discrepancy_count: 0,
    document_count: 6,
    compliance_score: 100,
  },
  {
    id: "session-3",
    lc_number: "LC-BNK-2024-003",
    client_name: "Export Solutions Co",
    status: "completed",
    completed_at: "2024-01-16T09:20:00Z",
    discrepancy_count: 5,
    document_count: 4,
    compliance_score: 60,
  },
];

export function EvidencePacksView({ embedded = false }: { embedded?: boolean }) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = React.useState(false);
  const [sessions, setSessions] = React.useState<ValidationSession[]>(mockSessions);
  const [selectedSessions, setSelectedSessions] = React.useState<Set<string>>(new Set());
  const [packFormat, setPackFormat] = React.useState<"pdf" | "zip">("pdf");
  const [includeDocuments, setIncludeDocuments] = React.useState(true);
  const [includeFindings, setIncludeFindings] = React.useState(true);
  const [includeAuditTrail, setIncludeAuditTrail] = React.useState(true);
  const [generating, setGenerating] = React.useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = React.useState(false);

  React.useEffect(() => {
    // In a real app, fetch validation sessions: getBankService().listValidationSessions().then(setSessions);
  }, []);

  const handleSelectAll = () => {
    if (selectedSessions.size === sessions.length) {
      setSelectedSessions(new Set());
    } else {
      setSelectedSessions(new Set(sessions.map((s) => s.id)));
    }
  };

  const handleSelectSession = (sessionId: string) => {
    const newSelected = new Set(selectedSessions);
    if (newSelected.has(sessionId)) {
      newSelected.delete(sessionId);
    } else {
      newSelected.add(sessionId);
    }
    setSelectedSessions(newSelected);
  };

  const handleGeneratePack = async () => {
    if (selectedSessions.size === 0) {
      toast({
        title: "No Sessions Selected",
        description: "Please select at least one validation session to include in the evidence pack.",
        variant: "destructive",
      });
      return;
    }

    setGenerating(true);
    try {
      // In a real app, call API:
      // const response = await api.post('/bank/evidence-packs/generate', {
      //   session_ids: Array.from(selectedSessions),
      //   format: packFormat,
      //   include_documents: includeDocuments,
      //   include_findings: includeFindings,
      //   include_audit_trail: includeAuditTrail,
      // });
      // const downloadUrl = response.data.download_url;
      // window.open(downloadUrl, '_blank');

      // Simulate generation
      await new Promise((resolve) => setTimeout(resolve, 2000));

      toast({
        title: "Evidence Pack Generated",
        description: `Your ${packFormat.toUpperCase()} evidence pack with ${selectedSessions.size} session(s) is ready for download.`,
      });
      setGenerateDialogOpen(false);
      setSelectedSessions(new Set());
    } catch (error) {
      toast({
        title: "Generation Failed",
        description: "Failed to generate evidence pack. Please try again.",
        variant: "destructive",
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleQuickPack = async (sessionId: string) => {
    setSelectedSessions(new Set([sessionId]));
    setPackFormat("pdf");
    setIncludeDocuments(true);
    setIncludeFindings(true);
    setIncludeAuditTrail(true);
    setGenerateDialogOpen(true);
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Evidence Packs</h2>
          <p className="text-muted-foreground">
            Generate comprehensive evidence packs (PDF/ZIP) with validation findings, documents, and audit trails.
          </p>
        </div>
        <Dialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
          <DialogTrigger asChild>
            <Button disabled={selectedSessions.size === 0} className="gap-2">
              <Package className="h-4 w-4" />
              Generate Pack ({selectedSessions.size})
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Generate Evidence Pack</DialogTitle>
              <DialogDescription>
                Configure your evidence pack options for {selectedSessions.size} selected session(s).
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Pack Format</Label>
                <Select value={packFormat} onValueChange={(value) => setPackFormat(value as "pdf" | "zip")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pdf">PDF Report</SelectItem>
                    <SelectItem value="zip">ZIP Archive</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {packFormat === "pdf"
                    ? "Single PDF document with all findings and embedded attachments"
                    : "ZIP archive containing PDF report and separate document files"}
                </p>
              </div>

              <div className="space-y-3">
                <Label>Include</Label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="include-findings"
                      checked={includeFindings}
                      onCheckedChange={(checked) => setIncludeFindings(checked === true)}
                    />
                    <Label htmlFor="include-findings" className="font-normal cursor-pointer">
                      Validation Findings & Discrepancies
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="include-documents"
                      checked={includeDocuments}
                      onCheckedChange={(checked) => setIncludeDocuments(checked === true)}
                    />
                    <Label htmlFor="include-documents" className="font-normal cursor-pointer">
                      Original Documents
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="include-audit"
                      checked={includeAuditTrail}
                      onCheckedChange={(checked) => setIncludeAuditTrail(checked === true)}
                    />
                    <Label htmlFor="include-audit" className="font-normal cursor-pointer">
                      Audit Trail & Timestamps
                    </Label>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={() => setGenerateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleGeneratePack} disabled={generating}>
                  {generating ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4 mr-2" />
                      Generate & Download
                    </>
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <FileText className="h-4 w-4" />
            About Evidence Packs
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Evidence packs provide a complete audit trail for LC validations, including:
          </p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>Validation findings and discrepancy details</li>
            <li>Original uploaded documents</li>
            <li>Processing timestamps and audit logs</li>
            <li>Compliance scores and status</li>
          </ul>
          <p className="mt-2">
            <strong>PDF Format:</strong> Single document with embedded attachments (best for single LC or small batches)
          </p>
          <p>
            <strong>ZIP Format:</strong> Archive with separate PDF report and document files (best for multiple LCs or large batches)
          </p>
        </CardContent>
      </Card>

      {/* Sessions Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-sm font-medium">Validation Sessions</CardTitle>
              <CardDescription>Select sessions to include in your evidence pack</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleSelectAll}>
                {selectedSessions.size === sessions.length ? "Deselect All" : "Select All"}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <RefreshCw className="h-5 w-5 animate-spin mr-2" /> Loading sessions...
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No validation sessions found</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={selectedSessions.size === sessions.length}
                      onCheckedChange={handleSelectAll}
                    />
                  </TableHead>
                  <TableHead>LC Number</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Discrepancies</TableHead>
                  <TableHead>Documents</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.map((session) => (
                  <TableRow key={session.id}>
                    <TableCell>
                      <Checkbox
                        checked={selectedSessions.has(session.id)}
                        onCheckedChange={() => handleSelectSession(session.id)}
                      />
                    </TableCell>
                    <TableCell className="font-medium">{session.lc_number}</TableCell>
                    <TableCell>{session.client_name}</TableCell>
                    <TableCell>
                      <StatusBadge
                        status={
                          session.status === "completed"
                            ? "success"
                            : session.status === "failed"
                            ? "destructive"
                            : "info"
                        }
                      >
                        {session.status}
                      </StatusBadge>
                    </TableCell>
                    <TableCell>
                      {session.discrepancy_count > 0 ? (
                        <Badge variant="destructive">{session.discrepancy_count}</Badge>
                      ) : (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      )}
                    </TableCell>
                    <TableCell>{session.document_count}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={session.compliance_score} className="w-16 h-2" />
                        <span className="text-sm font-medium">{session.compliance_score}%</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(session.completed_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleQuickPack(session.id)}
                        className="gap-2"
                      >
                        <FileDown className="h-4 w-4" />
                        Quick Pack
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


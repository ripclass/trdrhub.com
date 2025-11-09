import * as React from "react";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
  Download,
  Trash2,
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface DataRequest {
  id: string;
  type: "download" | "deletion";
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  requestedAt: string;
  completedAt?: string;
  expiresAt?: string;
  downloadUrl?: string;
  reason?: string;
  dataScope: string[];
}

// Mock data - replace with API calls
const mockRequests: DataRequest[] = [
  {
    id: "req-1",
    type: "download",
    status: "completed",
    requestedAt: "2024-01-15T10:00:00Z",
    completedAt: "2024-01-15T11:30:00Z",
    expiresAt: "2024-01-22T11:30:00Z",
    downloadUrl: "https://example.com/download/req-1.zip",
    dataScope: ["profile", "validation_sessions", "documents"],
  },
  {
    id: "req-2",
    type: "deletion",
    status: "pending",
    requestedAt: "2024-01-18T14:00:00Z",
    reason: "Account closure request",
    dataScope: ["all"],
  },
];

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString();
};

const formatRelativeTime = (dateString: string) => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays < 1) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return formatDate(dateString);
};

export function DataRetentionView({ embedded = false }: { embedded?: boolean }) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [requests, setRequests] = React.useState<DataRequest[]>(mockRequests);
  const [loading, setLoading] = React.useState(false);
  const [downloadDialogOpen, setDownloadDialogOpen] = React.useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [downloadScope, setDownloadScope] = React.useState<string[]>([]);
  const [deleteReason, setDeleteReason] = React.useState("");
  const [deleteScope, setDeleteScope] = React.useState<string>("all");

  const dataScopeOptions = [
    { value: "profile", label: "Profile Information" },
    { value: "validation_sessions", label: "Validation Sessions" },
    { value: "documents", label: "Uploaded Documents" },
    { value: "analytics", label: "Analytics Data" },
    { value: "billing", label: "Billing & Payment History" },
    { value: "audit_logs", label: "Audit Logs" },
  ];

  React.useEffect(() => {
    // In a real app, fetch requests: getDataRetentionService().listRequests().then(setRequests);
  }, []);

  const handleRequestDownload = async () => {
    if (downloadScope.length === 0) {
      toast({
        title: "Selection Required",
        description: "Please select at least one data type to download.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      // In a real app, call API: await api.post('/data-retention/download', { scope: downloadScope })
      const newRequest: DataRequest = {
        id: `req-${Date.now()}`,
        type: "download",
        status: "pending",
        requestedAt: new Date().toISOString(),
        dataScope: downloadScope,
      };
      setRequests((prev) => [newRequest, ...prev]);
      setDownloadDialogOpen(false);
      setDownloadScope([]);
      toast({
        title: "Download Request Submitted",
        description: "Your data export will be prepared and you'll receive a notification when ready.",
      });
    } catch (error) {
      toast({
        title: "Request Failed",
        description: "Failed to submit download request. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRequestDeletion = async () => {
    if (!deleteReason.trim()) {
      toast({
        title: "Reason Required",
        description: "Please provide a reason for the deletion request.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      // In a real app, call API: await api.post('/data-retention/deletion', { reason: deleteReason, scope: deleteScope })
      const newRequest: DataRequest = {
        id: `req-${Date.now()}`,
        type: "deletion",
        status: "pending",
        requestedAt: new Date().toISOString(),
        reason: deleteReason,
        dataScope: deleteScope === "all" ? ["all"] : [deleteScope],
      };
      setRequests((prev) => [newRequest, ...prev]);
      setDeleteDialogOpen(false);
      setDeleteReason("");
      setDeleteScope("all");
      toast({
        title: "Deletion Request Submitted",
        description: "Your deletion request is being processed. You'll be notified once completed.",
        variant: "default",
      });
    } catch (error) {
      toast({
        title: "Request Failed",
        description: "Failed to submit deletion request. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (request: DataRequest) => {
    if (request.downloadUrl) {
      window.open(request.downloadUrl, "_blank");
    } else {
      toast({
        title: "Download Not Available",
        description: "The download link is not yet available. Please check back later.",
        variant: "default",
      });
    }
  };

  const handleCancelRequest = async (requestId: string) => {
    setLoading(true);
    try {
      // In a real app, call API: await api.post(`/data-retention/${requestId}/cancel`)
      setRequests((prev) =>
        prev.map((r) => (r.id === requestId ? { ...r, status: "cancelled" as const } : r))
      );
      toast({
        title: "Request Cancelled",
        description: "Your data request has been cancelled.",
      });
    } catch (error) {
      toast({
        title: "Cancellation Failed",
        description: "Failed to cancel request. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Data Retention & Privacy</h2>
          <p className="text-muted-foreground">
            Manage your data download and deletion requests in compliance with GDPR and privacy regulations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Dialog open={downloadDialogOpen} onOpenChange={setDownloadDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="gap-2">
                <Download className="h-4 w-4" />
                Request Data Download
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Request Data Download</DialogTitle>
                <DialogDescription>
                  Select the data types you want to download. Your export will be prepared and available for 7 days.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Select Data Types</Label>
                  <div className="space-y-2">
                    {dataScopeOptions.map((option) => (
                      <div key={option.value} className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id={option.value}
                          checked={downloadScope.includes(option.value)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setDownloadScope([...downloadScope, option.value]);
                            } else {
                              setDownloadScope(downloadScope.filter((s) => s !== option.value));
                            }
                          }}
                          className="rounded border-gray-300"
                        />
                        <Label htmlFor={option.value} className="font-normal cursor-pointer">
                          {option.label}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setDownloadDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleRequestDownload} disabled={loading || downloadScope.length === 0}>
                    {loading ? "Submitting..." : "Submit Request"}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="destructive" className="gap-2">
                <Trash2 className="h-4 w-4" />
                Request Data Deletion
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Request Data Deletion</DialogTitle>
                <DialogDescription>
                  This action cannot be undone. All selected data will be permanently deleted.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Warning</AlertTitle>
                  <AlertDescription>
                    Data deletion is permanent and irreversible. Please ensure you have backups of any important data.
                  </AlertDescription>
                </Alert>
                <div className="space-y-2">
                  <Label>Deletion Scope</Label>
                  <select
                    value={deleteScope}
                    onChange={(e) => setDeleteScope(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2"
                  >
                    <option value="all">All Data</option>
                    {dataScopeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label} Only
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Reason for Deletion</Label>
                  <Textarea
                    placeholder="Please provide a reason for the deletion request..."
                    value={deleteReason}
                    onChange={(e) => setDeleteReason(e.target.value)}
                    rows={4}
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleRequestDeletion}
                    disabled={loading || !deleteReason.trim()}
                  >
                    {loading ? "Submitting..." : "Confirm Deletion"}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Information Cards */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Your Rights
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>• Right to access your personal data</p>
            <p>• Right to data portability</p>
            <p>• Right to erasure ("right to be forgotten")</p>
            <p>• Right to rectification</p>
            <p>• Right to object to processing</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Processing Times
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>• Download requests: 1-3 business days</p>
            <p>• Deletion requests: 7-14 business days</p>
            <p>• Download links expire after 7 days</p>
            <p>• Some data may be retained for legal compliance</p>
          </CardContent>
        </Card>
      </div>

      {/* Requests Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Your Data Requests</CardTitle>
          <CardDescription>Track the status of your download and deletion requests</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <RefreshCw className="h-5 w-5 animate-spin mr-2" /> Loading requests...
            </div>
          ) : requests.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No data requests yet</p>
              <p className="text-sm">Submit a request above to get started</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Data Scope</TableHead>
                  <TableHead>Requested</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requests.map((request) => (
                  <TableRow key={request.id}>
                    <TableCell>
                      <Badge variant={request.type === "download" ? "default" : "destructive"}>
                        {request.type === "download" ? (
                          <Download className="h-3 w-3 mr-1" />
                        ) : (
                          <Trash2 className="h-3 w-3 mr-1" />
                        )}
                        {request.type === "download" ? "Download" : "Deletion"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <StatusBadge
                        status={
                          request.status === "completed"
                            ? "success"
                            : request.status === "failed"
                            ? "destructive"
                            : request.status === "cancelled"
                            ? "secondary"
                            : "info"
                        }
                      >
                        {request.status}
                      </StatusBadge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {request.dataScope.map((scope) => (
                          <Badge key={scope} variant="outline" className="text-xs">
                            {scope === "all" ? "All Data" : scope.replace(/_/g, " ")}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatRelativeTime(request.requestedAt)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {request.completedAt ? formatRelativeTime(request.completedAt) : "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {request.type === "download" &&
                          request.status === "completed" &&
                          request.downloadUrl && (
                            <Button variant="ghost" size="sm" onClick={() => handleDownload(request)}>
                              <Download className="h-4 w-4" />
                            </Button>
                          )}
                        {request.status === "pending" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleCancelRequest(request.id)}
                            className="text-destructive"
                          >
                            Cancel
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Logs Visibility */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Audit Logs</CardTitle>
          <CardDescription>View your account activity and data access logs</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="recent" className="w-full">
            <TabsList>
              <TabsTrigger value="recent">Recent Activity</TabsTrigger>
              <TabsTrigger value="access">Data Access</TabsTrigger>
              <TabsTrigger value="changes">Account Changes</TabsTrigger>
            </TabsList>
            <TabsContent value="recent" className="space-y-2">
              <div className="text-sm text-muted-foreground">
                <p>• Login from new device - {formatRelativeTime(new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString())}</p>
                <p>• Profile updated - {formatRelativeTime(new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString())}</p>
                <p>• Password changed - {formatRelativeTime(new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString())}</p>
              </div>
            </TabsContent>
            <TabsContent value="access" className="space-y-2">
              <div className="text-sm text-muted-foreground">
                <p>• Data download requested - {formatRelativeTime(new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString())}</p>
                <p>• Validation session accessed - {formatRelativeTime(new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString())}</p>
              </div>
            </TabsContent>
            <TabsContent value="changes" className="space-y-2">
              <div className="text-sm text-muted-foreground">
                <p>• Email address updated - {formatRelativeTime(new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString())}</p>
                <p>• Account created - {formatRelativeTime(new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString())}</p>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}


/**
 * LC Workspace Component - Comprehensive workspace for managing LC drafts, amendments, and document checklists
 */

import * as React from "react";
import { useState, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Upload,
  FileText,
  Edit3,
  Trash2,
  ArrowRight,
  GitBranch,
  Plus,
  RefreshCw,
  FolderKanban,
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { StatusBadge } from "@/components/ui/status-badge";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Types
interface DocumentChecklistItem {
  document_type: string;
  required: boolean;
  status: "missing" | "uploaded" | "valid" | "invalid" | "pending_review";
  document_id?: string;
  uploaded_at?: string;
  validation_status?: string;
}

interface LCWorkspace {
  id: string;
  lc_number: string;
  client_name?: string;
  description?: string;
  document_checklist: DocumentChecklistItem[];
  completion_percentage: number;
  latest_validation_session_id?: string;
  created_at: string;
  updated_at: string;
}

interface Draft {
  id: string;
  lc_number?: string;
  client_name?: string;
  draft_type: string;
  status: "draft" | "ready_for_submission" | "submitted" | "archived";
  uploaded_docs: Array<{
    file_id?: string;
    filename: string;
    document_type: string;
    uploaded_at: string;
  }>;
  notes?: string;
  created_at: string;
  updated_at: string;
}

interface Amendment {
  id: string;
  lc_number: string;
  version: number;
  status: "pending" | "approved" | "rejected" | "archived";
  changes_diff?: Record<string, any>;
  document_changes?: Array<{
    document_type: string;
    action: string;
  }>;
  notes?: string;
  created_at: string;
  updated_at: string;
}

type WorkspaceTab = "workspace" | "drafts" | "amendments";

export function LCWorkspaceView({ embedded = false }: { embedded?: boolean }) {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("workspace");
  const [workspaces, setWorkspaces] = useState<LCWorkspace[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [amendments, setAmendments] = useState<Amendment[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkspace, setSelectedWorkspace] = useState<LCWorkspace | null>(null);
  const [showCreateWorkspace, setShowCreateWorkspace] = useState(false);
  const [showCreateDraft, setShowCreateDraft] = useState(false);
  const [newLCNumber, setNewLCNumber] = useState("");
  const [newClientName, setNewClientName] = useState("");

  // Load data
  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      if (activeTab === "workspace") {
        const res = await fetch(`${API_BASE}/api/sme/lc-workspaces`, { headers });
        if (res.ok) {
          const data = await res.json();
          setWorkspaces(data.items || []);
        }
      } else if (activeTab === "drafts") {
        const res = await fetch(`${API_BASE}/api/sme/drafts`, { headers });
        if (res.ok) {
          const data = await res.json();
          setDrafts(data.items || []);
        }
      } else if (activeTab === "amendments") {
        const res = await fetch(`${API_BASE}/api/sme/amendments`, { headers });
        if (res.ok) {
          const data = await res.json();
          setAmendments(data.items || []);
        }
      }
    } catch (error) {
      console.error("Failed to load data:", error);
      toast({
        title: "Error",
        description: "Failed to load workspace data",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorkspace = async () => {
    if (!newLCNumber.trim()) {
      toast({
        title: "Validation Error",
        description: "LC Number is required",
        variant: "destructive",
      });
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE}/api/sme/lc-workspaces`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          lc_number: newLCNumber,
          client_name: newClientName || undefined,
          document_checklist: [
            { document_type: "letter_of_credit", required: true, status: "missing" },
            { document_type: "commercial_invoice", required: true, status: "missing" },
            { document_type: "bill_of_lading", required: true, status: "missing" },
          ],
        }),
      });

      if (res.ok) {
        toast({
          title: "Success",
          description: "LC Workspace created successfully",
        });
        setShowCreateWorkspace(false);
        setNewLCNumber("");
        setNewClientName("");
        loadData();
      } else {
        const error = await res.json();
        throw new Error(error.detail || "Failed to create workspace");
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to create workspace",
        variant: "destructive",
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "valid":
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case "invalid":
        return <XCircle className="h-4 w-4 text-destructive" />;
      case "uploaded":
        return <Clock className="h-4 w-4 text-info" />;
      case "pending_review":
        return <AlertCircle className="h-4 w-4 text-warning" />;
      default:
        return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "valid":
        return <Badge variant="default" className="bg-success/10 text-success">Valid</Badge>;
      case "invalid":
        return <Badge variant="destructive">Invalid</Badge>;
      case "uploaded":
        return <Badge variant="outline">Uploaded</Badge>;
      case "pending_review":
        return <Badge variant="outline" className="bg-warning/10 text-warning">Pending Review</Badge>;
      default:
        return <Badge variant="outline" className="bg-muted">Missing</Badge>;
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">LC Workspace</h2>
          <p className="text-muted-foreground">Manage your LC documents, drafts, and amendments</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
          {activeTab === "workspace" && (
            <Dialog open={showCreateWorkspace} onOpenChange={setShowCreateWorkspace}>
              <DialogTrigger asChild>
                <Button size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  New Workspace
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create LC Workspace</DialogTitle>
                  <DialogDescription>Create a new workspace for tracking LC documents</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="lc-number">LC Number *</Label>
                    <Input
                      id="lc-number"
                      value={newLCNumber}
                      onChange={(e) => setNewLCNumber(e.target.value)}
                      placeholder="LC-2024-001"
                    />
                  </div>
                  <div>
                    <Label htmlFor="client-name">Client Name</Label>
                    <Input
                      id="client-name"
                      value={newClientName}
                      onChange={(e) => setNewClientName(e.target.value)}
                      placeholder="Optional"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreateWorkspace(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateWorkspace}>Create</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as WorkspaceTab)}>
        <TabsList>
          <TabsTrigger value="workspace">LC Workspaces</TabsTrigger>
          <TabsTrigger value="drafts">Drafts</TabsTrigger>
          <TabsTrigger value="amendments">Amendments</TabsTrigger>
        </TabsList>

        <TabsContent value="workspace" className="mt-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : workspaces.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FolderKanban className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No LC workspaces yet</p>
                <p className="text-sm text-muted-foreground mt-2">Create a workspace to start tracking LC documents</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {workspaces.map((workspace) => (
                <Card key={workspace.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="flex items-center gap-2">
                          {workspace.lc_number}
                          {workspace.client_name && (
                            <span className="text-sm font-normal text-muted-foreground">
                              - {workspace.client_name}
                            </span>
                          )}
                        </CardTitle>
                        <CardDescription>
                          {workspace.description || "No description"}
                        </CardDescription>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{workspace.completion_percentage}% Complete</Badge>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setSelectedWorkspace(workspace);
                            setActiveTab("workspace");
                          }}
                        >
                          View Details
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">Document Checklist</span>
                          <Progress value={workspace.completion_percentage} className="w-32" />
                        </div>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Document Type</TableHead>
                              <TableHead>Status</TableHead>
                              <TableHead>Required</TableHead>
                              <TableHead>Actions</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {workspace.document_checklist.map((item, idx) => (
                              <TableRow key={idx}>
                                <TableCell className="font-medium">{item.document_type}</TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    {getStatusIcon(item.status)}
                                    {getStatusBadge(item.status)}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  {item.required ? (
                                    <Badge variant="outline">Required</Badge>
                                  ) : (
                                    <Badge variant="outline" className="bg-muted">Optional</Badge>
                                  )}
                                </TableCell>
                                <TableCell>
                                  {item.status === "missing" && (
                                    <Button variant="ghost" size="sm">
                                      <Upload className="h-4 w-4" />
                                    </Button>
                                  )}
                                  {item.status === "invalid" && (
                                    <Button variant="ghost" size="sm">
                                      <RefreshCw className="h-4 w-4" />
                                    </Button>
                                  )}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="drafts" className="mt-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : drafts.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Edit3 className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No drafts saved</p>
                <p className="text-sm text-muted-foreground mt-2">Save a draft while uploading to resume later</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {drafts.map((draft) => (
                <Card key={draft.id}>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="bg-primary/10 p-3 rounded-lg">
                          <Edit3 className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <h4 className="font-semibold">{draft.lc_number || "Untitled Draft"}</h4>
                          <p className="text-sm text-muted-foreground">
                            {draft.uploaded_docs.length} file{draft.uploaded_docs.length === 1 ? "" : "s"} •{" "}
                            {draft.draft_type}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <StatusBadge
                              status={
                                draft.status === "ready_for_submission"
                                  ? "success"
                                  : draft.status === "submitted"
                                  ? "info"
                                  : "warning"
                              }
                            >
                              {draft.status.replace("_", " ")}
                            </StatusBadge>
                            <span className="text-xs text-muted-foreground">
                              Updated {new Date(draft.updated_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {draft.status === "draft" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={async () => {
                              try {
                                const token = localStorage.getItem("token");
                                const res = await fetch(`${API_BASE}/api/sme/drafts/${draft.id}/promote`, {
                                  method: "POST",
                                  headers: {
                                    "Content-Type": "application/json",
                                    Authorization: `Bearer ${token}`,
                                  },
                                  body: JSON.stringify({ notes: "Promoted to ready for submission" }),
                                });
                                if (res.ok) {
                                  toast({
                                    title: "Success",
                                    description: "Draft promoted successfully",
                                  });
                                  loadData();
                                }
                              } catch (error) {
                                toast({
                                  title: "Error",
                                  description: "Failed to promote draft",
                                  variant: "destructive",
                                });
                              }
                            }}
                          >
                            Promote
                          </Button>
                        )}
                        <Button variant="outline" size="sm">
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="amendments" className="mt-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : amendments.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <GitBranch className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No amendments recorded</p>
                <p className="text-sm text-muted-foreground mt-2">LC amendments will appear here</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {amendments.map((amendment) => (
                <Card key={amendment.id}>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="bg-primary/10 p-3 rounded-lg">
                          <GitBranch className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <h4 className="font-semibold">
                            {amendment.lc_number} - Version {amendment.version}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {amendment.document_changes?.length || 0} document change
                            {(amendment.document_changes?.length || 0) === 1 ? "" : "s"}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <StatusBadge
                              status={
                                amendment.status === "approved"
                                  ? "success"
                                  : amendment.status === "rejected"
                                  ? "error"
                                  : "warning"
                              }
                            >
                              {amendment.status}
                            </StatusBadge>
                            <span className="text-xs text-muted-foreground">
                              Created {new Date(amendment.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={async () => {
                            try {
                              const token = localStorage.getItem("token");
                              const res = await fetch(`${API_BASE}/api/sme/amendments/${amendment.id}/diff`, {
                                headers: {
                                  Authorization: `Bearer ${token}`,
                                },
                              });
                              if (res.ok) {
                                const diff = await res.json();
                                // Show diff in a dialog or navigate to diff view
                                toast({
                                  title: "Diff Loaded",
                                  description: `Found ${diff.summary.added + diff.summary.modified + diff.summary.removed} changes`,
                                });
                              }
                            } catch (error) {
                              toast({
                                title: "Error",
                                description: "Failed to load diff",
                                variant: "destructive",
                              });
                            }
                          }}
                        >
                          View Diff
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}


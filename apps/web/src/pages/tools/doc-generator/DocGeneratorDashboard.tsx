/**
 * Doc Generator Dashboard
 * 
 * Lists all document sets with actions to create, view, and generate documents.
 */

import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  FileText,
  Plus,
  Download,
  Eye,
  Trash2,
  MoreHorizontal,
  Clock,
  CheckCircle,
  AlertCircle,
  FileSpreadsheet,
  Filter,
  Import,
  Copy,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { ImportFromLCopilot } from "./ImportFromLCopilot";
import { PDFPreview } from "./PDFPreview";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface DocumentSet {
  id: string;
  name: string | null;
  status: string;
  lc_number: string | null;
  beneficiary_name: string;
  applicant_name: string;
  total_amount: number;
  documents_generated: number;
  created_at: string;
}

const statusBadgeVariants: Record<string, "default" | "secondary" | "success" | "warning"> = {
  draft: "secondary",
  generated: "success",
  finalized: "default",
  archived: "warning",
};

const statusIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  draft: Clock,
  generated: CheckCircle,
  finalized: FileText,
  archived: AlertCircle,
};

export default function DocGeneratorDashboard() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user, session } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [documentSets, setDocumentSets] = useState<DocumentSet[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>(searchParams.get("status") || "all");
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [previewDocSetId, setPreviewDocSetId] = useState<string | null>(null);

  useEffect(() => {
    fetchDocumentSets();
  }, [statusFilter]);

  const fetchDocumentSets = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== "all") {
        params.append("status", statusFilter);
      }
      
      const token = session?.access_token || user?.access_token;
      if (!token) {
        console.warn("No auth token available for document sets fetch");
        setDocumentSets([]);
        return;
      }
      
      const response = await fetch(`${API_BASE}/doc-generator/document-sets?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Document sets API error: ${response.status} - ${errorText}`);
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      setDocumentSets(data);
    } catch (error) {
      console.error("Error fetching document sets:", error);
      toast({
        title: "Error",
        description: "Failed to load document sets. Please try again.",
        variant: "destructive",
      });
      setDocumentSets([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this document set?")) return;
    
    try {
      const token = session?.access_token || user?.id;
      const response = await fetch(`${API_BASE}/doc-generator/document-sets/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error("Failed to delete document set");
      }
      
      toast({
        title: "Deleted",
        description: "Document set has been deleted",
      });
      
      fetchDocumentSets();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete document set",
        variant: "destructive",
      });
    }
  };

  const handleDownload = async (id: string) => {
    try {
      const token = session?.access_token || user?.id;
      const response = await fetch(`${API_BASE}/doc-generator/document-sets/${id}/download`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error("Failed to download documents");
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `documents_${id}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast({
        title: "Downloaded",
        description: "Documents have been downloaded",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to download documents",
        variant: "destructive",
      });
    }
  };

  const handleDuplicate = async (id: string) => {
    try {
      const token = session?.access_token || user?.id;
      const response = await fetch(`${API_BASE}/api/doc-generator/document-sets/${id}/duplicate`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error("Failed to duplicate document set");
      }
      
      const data = await response.json();
      
      toast({
        title: "Duplicated",
        description: "Document set has been duplicated",
      });
      
      // Refresh list and navigate to edit
      fetchDocumentSets();
      navigate(`/doc-generator/dashboard/edit/${data.id}`);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to duplicate document set",
        variant: "destructive",
      });
    }
  };

  const filteredSets = documentSets.filter((set) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      (set.name?.toLowerCase().includes(query)) ||
      (set.lc_number?.toLowerCase().includes(query)) ||
      set.beneficiary_name.toLowerCase().includes(query) ||
      set.applicant_name.toLowerCase().includes(query)
    );
  });

  // Stats
  const totalSets = documentSets.length;
  const generatedSets = documentSets.filter((s) => s.status === "generated").length;
  const draftSets = documentSets.filter((s) => s.status === "draft").length;

  return (
    <div className="p-6 space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardDescription className="text-slate-400">Total Document Sets</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{totalSets}</div>
          </CardContent>
        </Card>
        
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardDescription className="text-slate-400">Generated</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-400">{generatedSets}</div>
          </CardContent>
        </Card>
        
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardDescription className="text-slate-400">Drafts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-400">{draftSets}</div>
          </CardContent>
        </Card>
        
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardDescription className="text-slate-400">This Month</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-400">
              {documentSets.filter((s) => {
                const created = new Date(s.created_at);
                const now = new Date();
                return created.getMonth() === now.getMonth() && created.getFullYear() === now.getFullYear();
              }).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Document Sets List */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="text-white">Document Sets</CardTitle>
            <CardDescription className="text-slate-400">
              Manage your shipping document sets
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              className="border-slate-700 hover:bg-slate-800"
              onClick={() => setShowImportDialog(true)}
            >
              <Import className="w-4 h-4 mr-2" />
              Import from LC
            </Button>
            <Button asChild className="bg-blue-600 hover:bg-blue-700">
              <Link to="/doc-generator/dashboard/new">
                <Plus className="w-4 h-4 mr-2" />
                Create New
              </Link>
            </Button>
          </div>
        </CardHeader>
        
        <CardContent>
          {/* Filters */}
          <div className="flex gap-4 mb-4">
            <div className="flex-1">
              <Input
                placeholder="Search by LC number, beneficiary, or applicant..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-slate-800 border-slate-700 text-white"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px] bg-slate-800 border-slate-700 text-white">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="generated">Generated</SelectItem>
                <SelectItem value="finalized">Finalized</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Table */}
          {isLoading ? (
            <div className="text-center py-12 text-slate-400">Loading...</div>
          ) : filteredSets.length === 0 ? (
            <div className="text-center py-12">
              <FileSpreadsheet className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No document sets found</h3>
              <p className="text-slate-400 mb-4">
                {searchQuery || statusFilter !== "all"
                  ? "Try adjusting your filters"
                  : "Create your first document set to get started"}
              </p>
              {!searchQuery && statusFilter === "all" && (
                <Button asChild className="bg-blue-600 hover:bg-blue-700">
                  <Link to="/doc-generator/dashboard/new">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Document Set
                  </Link>
                </Button>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-transparent">
                  <TableHead className="text-slate-400">Name / LC</TableHead>
                  <TableHead className="text-slate-400">Beneficiary</TableHead>
                  <TableHead className="text-slate-400">Applicant</TableHead>
                  <TableHead className="text-slate-400 text-right">Amount</TableHead>
                  <TableHead className="text-slate-400">Status</TableHead>
                  <TableHead className="text-slate-400">Created</TableHead>
                  <TableHead className="text-slate-400 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSets.map((set) => {
                  const StatusIcon = statusIcons[set.status] || Clock;
                  return (
                    <TableRow key={set.id} className="border-slate-800 hover:bg-slate-800/50">
                      <TableCell className="text-white font-medium">
                        <div>
                          {set.name || "Untitled"}
                          {set.lc_number && (
                            <div className="text-xs text-slate-400">LC: {set.lc_number}</div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-slate-300">{set.beneficiary_name}</TableCell>
                      <TableCell className="text-slate-300">{set.applicant_name}</TableCell>
                      <TableCell className="text-slate-300 text-right">
                        ${set.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusBadgeVariants[set.status] || "default"} className="gap-1">
                          <StatusIcon className="w-3 h-3" />
                          {set.status.charAt(0).toUpperCase() + set.status.slice(1)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-400 text-sm">
                        {new Date(set.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="text-slate-400 hover:text-white">
                              <MoreHorizontal className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => navigate(`/doc-generator/dashboard/edit/${set.id}`)}>
                              <Eye className="w-4 h-4 mr-2" />
                              View / Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setPreviewDocSetId(set.id)}>
                              <FileText className="w-4 h-4 mr-2" />
                              Preview PDF
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDownload(set.id)}>
                              <Download className="w-4 h-4 mr-2" />
                              Download All
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDuplicate(set.id)}>
                              <Copy className="w-4 h-4 mr-2" />
                              Duplicate
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => handleDelete(set.id)}
                              className="text-red-500 focus:text-red-500"
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Import from LCopilot Dialog */}
      <ImportFromLCopilot
        open={showImportDialog}
        onOpenChange={setShowImportDialog}
        onImportComplete={(id) => {
          fetchDocumentSets();
          navigate(`/doc-generator/dashboard/edit/${id}`);
        }}
      />

      {/* PDF Preview Dialog */}
      {previewDocSetId && (
        <PDFPreview
          docSetId={previewDocSetId}
          open={!!previewDocSetId}
          onOpenChange={(open) => !open && setPreviewDocSetId(null)}
          mode="modal"
        />
      )}
    </div>
  );
}


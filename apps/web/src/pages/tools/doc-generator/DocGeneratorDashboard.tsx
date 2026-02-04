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
  Search,
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
import { AppShellToolbar, AppShellToolbarSection } from "@/components/layout/AppShell";

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
      const response = await fetch(`${API_BASE}/doc-generator/document-sets/${id}/duplicate`, {
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
    <div className="p-6 space-y-6 bg-[#00261C] min-h-full">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-[#00382E]/50 border-[#EDF5F2]/10 backdrop-blur-sm" dense>
          <CardHeader className="pb-2" dense>
            <CardDescription className="text-[#EDF5F2]/60">Total Document Sets</CardDescription>
          </CardHeader>
          <CardContent dense>
            <div className="text-2xl font-bold text-white font-display">{totalSets}</div>
          </CardContent>
        </Card>
        
        <Card className="bg-[#00382E]/50 border-[#EDF5F2]/10 backdrop-blur-sm" dense>
          <CardHeader className="pb-2" dense>
            <CardDescription className="text-[#EDF5F2]/60">Generated</CardDescription>
          </CardHeader>
          <CardContent dense>
            <div className="text-2xl font-bold text-[#B2F273] font-display">{generatedSets}</div>
          </CardContent>
        </Card>
        
        <Card className="bg-[#00382E]/50 border-[#EDF5F2]/10 backdrop-blur-sm" dense>
          <CardHeader className="pb-2" dense>
            <CardDescription className="text-[#EDF5F2]/60">Drafts</CardDescription>
          </CardHeader>
          <CardContent dense>
            <div className="text-2xl font-bold text-amber-400 font-display">{draftSets}</div>
          </CardContent>
        </Card>
        
        <Card className="bg-[#00382E]/50 border-[#EDF5F2]/10 backdrop-blur-sm" dense>
          <CardHeader className="pb-2" dense>
            <CardDescription className="text-[#EDF5F2]/60">This Month</CardDescription>
          </CardHeader>
          <CardContent dense>
            <div className="text-2xl font-bold text-blue-400 font-display">
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
      <Card className="bg-[#00382E]/50 border-[#EDF5F2]/10 backdrop-blur-sm" dense>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4" dense>
          <div>
            <CardTitle className="text-white font-display" dense>Document Sets</CardTitle>
            <CardDescription className="text-[#EDF5F2]/60">
              Manage your shipping document sets
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              className="border-[#EDF5F2]/10 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 bg-transparent"
              onClick={() => setShowImportDialog(true)}
              size="sm"
            >
              <Import className="w-4 h-4 mr-2" />
              Import from LC
            </Button>
            <Button asChild className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold" size="sm">
              <Link to="/doc-generator/dashboard/new">
                <Plus className="w-4 h-4 mr-2" />
                Create New
              </Link>
            </Button>
          </div>
        </CardHeader>
        
        <CardContent dense>
          {/* Filters */}
          <AppShellToolbar className="mb-4">
            <AppShellToolbarSection className="flex-1">
              <div className="relative w-full max-w-sm">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-[#EDF5F2]/40" />
                <Input
                  placeholder="Search by LC number, beneficiary, or applicant..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 bg-[#00261C]/50 border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/40 h-9 text-sm"
                  dense
                />
              </div>
            </AppShellToolbarSection>
            <AppShellToolbarSection>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px] bg-[#00261C]/50 border-[#EDF5F2]/10 text-white h-9 text-sm">
                  <Filter className="w-4 h-4 mr-2 text-[#EDF5F2]/40" />
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent className="bg-[#00261C] border-[#EDF5F2]/10 text-white">
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="generated">Generated</SelectItem>
                  <SelectItem value="finalized">Finalized</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
            </AppShellToolbarSection>
          </AppShellToolbar>

          {/* Table */}
          {isLoading ? (
            <div className="text-center py-12 text-[#EDF5F2]/40">Loading...</div>
          ) : filteredSets.length === 0 ? (
            <div className="text-center py-12">
              <FileSpreadsheet className="w-12 h-12 text-[#EDF5F2]/20 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2 font-display">No document sets found</h3>
              <p className="text-[#EDF5F2]/40 mb-4">
                {searchQuery || statusFilter !== "all"
                  ? "Try adjusting your filters"
                  : "Create your first document set to get started"}
              </p>
              {!searchQuery && statusFilter === "all" && (
                <Button asChild className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold">
                  <Link to="/doc-generator/dashboard/new">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Document Set
                  </Link>
                </Button>
              )}
            </div>
          ) : (
            <Table dense sticky>
              <TableHeader sticky className="bg-[#00261C] hover:bg-[#00261C]">
                <TableRow className="border-[#EDF5F2]/10 hover:bg-transparent" dense>
                  <TableHead className="text-[#EDF5F2]/40 font-mono uppercase text-xs" dense>Name / LC</TableHead>
                  <TableHead className="text-[#EDF5F2]/40 font-mono uppercase text-xs" dense>Beneficiary</TableHead>
                  <TableHead className="text-[#EDF5F2]/40 font-mono uppercase text-xs" dense>Applicant</TableHead>
                  <TableHead className="text-[#EDF5F2]/40 font-mono uppercase text-xs text-right" dense>Amount</TableHead>
                  <TableHead className="text-[#EDF5F2]/40 font-mono uppercase text-xs" dense>Status</TableHead>
                  <TableHead className="text-[#EDF5F2]/40 font-mono uppercase text-xs" dense>Created</TableHead>
                  <TableHead className="text-[#EDF5F2]/40 font-mono uppercase text-xs text-right" dense>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSets.map((set) => {
                  const StatusIcon = statusIcons[set.status] || Clock;
                  return (
                    <TableRow key={set.id} className="border-[#EDF5F2]/5 hover:bg-[#B2F273]/5 transition-colors" dense>
                      <TableCell className="text-white font-medium" dense>
                        <div>
                          {set.name || "Untitled"}
                          {set.lc_number && (
                            <div className="text-xs text-[#EDF5F2]/40 font-mono mt-0.5">LC: {set.lc_number}</div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-[#EDF5F2]/80" dense>{set.beneficiary_name}</TableCell>
                      <TableCell className="text-[#EDF5F2]/80" dense>{set.applicant_name}</TableCell>
                      <TableCell className="text-[#EDF5F2]/80 text-right font-mono" dense>
                        ${set.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell dense>
                        <Badge variant={statusBadgeVariants[set.status] || "default"} className="gap-1 bg-[#00261C] border-[#EDF5F2]/10 text-[#EDF5F2]/80 hover:bg-[#00261C]">
                          <StatusIcon className="w-3 h-3" />
                          {set.status.charAt(0).toUpperCase() + set.status.slice(1)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-[#EDF5F2]/40 text-xs font-mono" dense>
                        {new Date(set.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right" dense>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-[#EDF5F2]/40 hover:text-white hover:bg-[#EDF5F2]/5">
                              <MoreHorizontal className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="bg-[#00261C] border-[#EDF5F2]/10 text-white">
                            <DropdownMenuItem onClick={() => navigate(`/doc-generator/dashboard/edit/${set.id}`)} className="hover:bg-[#EDF5F2]/5 hover:text-white focus:bg-[#EDF5F2]/5 focus:text-white">
                              <Eye className="w-4 h-4 mr-2" />
                              View / Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setPreviewDocSetId(set.id)} className="hover:bg-[#EDF5F2]/5 hover:text-white focus:bg-[#EDF5F2]/5 focus:text-white">
                              <FileText className="w-4 h-4 mr-2" />
                              Preview PDF
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDownload(set.id)} className="hover:bg-[#EDF5F2]/5 hover:text-white focus:bg-[#EDF5F2]/5 focus:text-white">
                              <Download className="w-4 h-4 mr-2" />
                              Download All
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDuplicate(set.id)} className="hover:bg-[#EDF5F2]/5 hover:text-white focus:bg-[#EDF5F2]/5 focus:text-white">
                              <Copy className="w-4 h-4 mr-2" />
                              Duplicate
                            </DropdownMenuItem>
                            <DropdownMenuSeparator className="bg-[#EDF5F2]/10" />
                            <DropdownMenuItem
                              onClick={() => handleDelete(set.id)}
                              className="text-red-400 focus:text-red-400 hover:bg-red-500/10 focus:bg-red-500/10"
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


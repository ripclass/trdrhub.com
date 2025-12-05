import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Plus,
  FileText,
  Clock,
  AlertTriangle,
  CheckCircle,
  MoreVertical,
  Trash2,
  Copy,
  Eye,
  Download,
  Search,
  Filter,
  ArrowLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
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

const API_BASE = import.meta.env.VITE_API_URL || "";

interface LCApplication {
  id: string;
  reference_number: string;
  name: string | null;
  status: string;
  lc_type: string;
  amount: number;
  currency: string;
  beneficiary_name: string;
  expiry_date: string | null;
  risk_score: number | null;
  created_at: string;
  updated_at: string;
}

const statusColors: Record<string, string> = {
  draft: "bg-slate-500",
  review: "bg-amber-500",
  submitted: "bg-blue-500",
  approved: "bg-emerald-500",
  rejected: "bg-red-500",
  amended: "bg-purple-500",
};

const riskColors = (score: number | null) => {
  if (score === null) return "text-slate-500";
  if (score <= 20) return "text-emerald-500";
  if (score <= 50) return "text-amber-500";
  return "text-red-500";
};

export default function LCBuilderDashboard() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { session, user, loading: authLoading } = useAuth();
  
  const [applications, setApplications] = useState<LCApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  
  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate("/login?redirect=/lc-builder/dashboard");
    }
  }, [authLoading, user, navigate]);
  
  useEffect(() => {
    if (session?.access_token) {
      fetchApplications();
    }
  }, [statusFilter, session?.access_token]);
  
  const fetchApplications = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (statusFilter !== "all") params.append("status", statusFilter);
      
      const response = await fetch(
        `${API_BASE}/lc-builder/applications?${params}`,
        {
          headers: { Authorization: `Bearer ${session?.access_token || ""}` },
        }
      );
      
      if (!response.ok) throw new Error("Failed to fetch applications");
      
      const data = await response.json();
      setApplications(data.applications || []);
    } catch (error) {
      console.error("Error fetching applications:", error);
      toast({
        title: "Error",
        description: "Failed to load LC applications",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };
  
  const handleDuplicate = async (id: string) => {
    try {
      const response = await fetch(
        `${API_BASE}/lc-builder/applications/${id}/duplicate`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${session?.access_token || ""}` },
        }
      );
      
      if (!response.ok) throw new Error("Failed to duplicate");
      
      const data = await response.json();
      toast({
        title: "Duplicated",
        description: `Created copy: ${data.reference_number}`,
      });
      fetchApplications();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to duplicate application",
        variant: "destructive",
      });
    }
  };
  
  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this LC application?")) return;
    
    try {
      const response = await fetch(
        `${API_BASE}/lc-builder/applications/${id}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${session?.access_token || ""}` },
        }
      );
      
      if (!response.ok) throw new Error("Failed to delete");
      
      toast({ title: "Deleted", description: "LC application deleted" });
      fetchApplications();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete application",
        variant: "destructive",
      });
    }
  };
  
  const filteredApplications = applications.filter((app) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      app.reference_number.toLowerCase().includes(query) ||
      app.name?.toLowerCase().includes(query) ||
      app.beneficiary_name?.toLowerCase().includes(query)
    );
  });
  
  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" asChild>
                <Link to="/hub">
                  <ArrowLeft className="h-5 w-5" />
                </Link>
              </Button>
              <div>
                <h1 className="text-xl font-bold text-white">LC Builder</h1>
                <p className="text-sm text-slate-400">
                  Create and manage LC applications
                </p>
              </div>
            </div>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700"
              onClick={() => navigate("/lc-builder/wizard")}
            >
              <Plus className="h-4 w-4 mr-2" />
              New LC Application
            </Button>
          </div>
        </div>
      </div>
      
      {/* Filters */}
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Search by reference, name, or beneficiary..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-slate-800 border-slate-700"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px] bg-slate-800 border-slate-700">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="review">In Review</SelectItem>
              <SelectItem value="submitted">Submitted</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-slate-800">
                  <FileText className="h-5 w-5 text-slate-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">
                    {applications.length}
                  </p>
                  <p className="text-xs text-slate-400">Total Applications</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-amber-500/10">
                  <Clock className="h-5 w-5 text-amber-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">
                    {applications.filter((a) => a.status === "draft").length}
                  </p>
                  <p className="text-xs text-slate-400">Drafts</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10">
                  <CheckCircle className="h-5 w-5 text-emerald-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">
                    {applications.filter((a) => a.status === "approved").length}
                  </p>
                  <p className="text-xs text-slate-400">Approved</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <AlertTriangle className="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">
                    {applications.filter((a) => (a.risk_score || 0) > 50).length}
                  </p>
                  <p className="text-xs text-slate-400">High Risk</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
        
        {/* Applications List */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
          </div>
        ) : filteredApplications.length === 0 ? (
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="py-16 text-center">
              <FileText className="h-12 w-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">
                No LC applications yet
              </h3>
              <p className="text-slate-400 mb-6">
                Create your first LC application to get started
              </p>
              <Button
                className="bg-emerald-600 hover:bg-emerald-700"
                onClick={() => navigate("/lc-builder/wizard")}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create LC Application
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {filteredApplications.map((app) => (
              <Card
                key={app.id}
                className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors"
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="p-2 rounded-lg bg-slate-800">
                        <FileText className="h-5 w-5 text-emerald-500" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm text-emerald-400">
                            {app.reference_number}
                          </span>
                          <Badge
                            className={`${statusColors[app.status]} text-white text-xs`}
                          >
                            {app.status}
                          </Badge>
                        </div>
                        <p className="text-white font-medium">
                          {app.name || app.beneficiary_name || "Untitled"}
                        </p>
                        <p className="text-sm text-slate-400">
                          {app.currency} {app.amount?.toLocaleString()} •{" "}
                          {app.lc_type}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4">
                      <div className="text-right hidden sm:block">
                        <p className={`font-medium ${riskColors(app.risk_score)}`}>
                          Risk: {app.risk_score ?? "N/A"}
                        </p>
                        <p className="text-xs text-slate-400">
                          {app.expiry_date
                            ? `Expires ${new Date(app.expiry_date).toLocaleDateString()}`
                            : "No expiry set"}
                        </p>
                      </div>
                      
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => navigate(`/lc-builder/wizard/${app.id}`)}
                          >
                            <Eye className="h-4 w-4 mr-2" />
                            View / Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleDuplicate(app.id)}>
                            <Copy className="h-4 w-4 mr-2" />
                            Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() =>
                              window.open(
                                `${API_BASE}/lc-builder/applications/${app.id}/export/pdf`,
                                "_blank"
                              )
                            }
                          >
                            <Download className="h-4 w-4 mr-2" />
                            Export PDF
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-red-400"
                            onClick={() => handleDelete(app.id)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Package, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  AlertTriangle,
  Shield,
  FileText,
  RefreshCw,
  BarChart3,
  Users,
  Activity,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface Commodity {
  id: string;
  code: string;
  name: string;
  category: string;
  unit: string;
  aliases: string[];
  hs_codes: string[];
  price_low: number | null;
  price_high: number | null;
  current_estimate: number | null;
  verified: boolean;
  is_active: boolean;
  created_at: string;
}

interface CommodityRequest {
  id: string;
  requested_name: string;
  suggested_category: string | null;
  suggested_unit: string | null;
  suggested_hs_code: string | null;
  status: string;
  admin_notes: string | null;
  created_at: string;
}

interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  resource: string;
  user_id: string | null;
  ip_address: string | null;
  details: {
    commodity: string;
    document_price: number | null;
    market_price: number | null;
    verdict: string;
    risk_level: string;
  };
}

interface AdminStats {
  commodities: { total: number; verified: number; unverified: number };
  requests: { pending: number };
  verifications: { last_24h: number; last_7d: number; high_risk_7d: number };
}

export default function AdminPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("commodities");
  
  // Commodities state
  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [commoditiesLoading, setCommoditiesLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  
  // Commodity edit/create modal
  const [showCommodityModal, setShowCommodityModal] = useState(false);
  const [editingCommodity, setEditingCommodity] = useState<Commodity | null>(null);
  const [commodityForm, setCommodityForm] = useState({
    code: "",
    name: "",
    category: "",
    unit: "kg",
    aliases: "",
    hs_codes: "",
    price_low: "",
    price_high: "",
    current_estimate: "",
    verified: false,
  });
  
  // Requests state
  const [requests, setRequests] = useState<CommodityRequest[]>([]);
  const [requestsLoading, setRequestsLoading] = useState(true);
  const [requestStatusFilter, setRequestStatusFilter] = useState<string | null>(null);
  const [statusCounts, setStatusCounts] = useState({ pending: 0, approved: 0, rejected: 0 });
  
  // Audit logs state
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(true);
  
  // Stats state
  const [stats, setStats] = useState<AdminStats | null>(null);
  
  // Saving state
  const [saving, setSaving] = useState(false);

  // Fetch data on mount and tab change
  useEffect(() => {
    fetchStats();
    if (activeTab === "commodities") fetchCommodities();
    if (activeTab === "requests") fetchRequests();
    if (activeTab === "audit") fetchAuditLogs();
  }, [activeTab]);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/admin/stats`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) setStats(data.stats);
      }
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  };

  const fetchCommodities = async () => {
    setCommoditiesLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append("search", searchTerm);
      if (categoryFilter) params.append("category", categoryFilter);
      
      const response = await fetch(`${API_BASE}/admin/commodities?${params}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setCommodities(data.commodities);
          setCategories(data.categories || []);
        }
      }
    } catch (err) {
      console.error("Failed to fetch commodities:", err);
    } finally {
      setCommoditiesLoading(false);
    }
  };

  const fetchRequests = async () => {
    setRequestsLoading(true);
    try {
      const params = new URLSearchParams();
      if (requestStatusFilter) params.append("status", requestStatusFilter);
      
      const response = await fetch(`${API_BASE}/admin/commodity-requests?${params}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setRequests(data.requests);
          setStatusCounts(data.status_counts);
        }
      }
    } catch (err) {
      console.error("Failed to fetch requests:", err);
    } finally {
      setRequestsLoading(false);
    }
  };

  const fetchAuditLogs = async () => {
    setLogsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/admin/audit-logs?days=7`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) setAuditLogs(data.logs);
      }
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
    } finally {
      setLogsLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingCommodity(null);
    setCommodityForm({
      code: "",
      name: "",
      category: "",
      unit: "kg",
      aliases: "",
      hs_codes: "",
      price_low: "",
      price_high: "",
      current_estimate: "",
      verified: false,
    });
    setShowCommodityModal(true);
  };

  const openEditModal = (commodity: Commodity) => {
    setEditingCommodity(commodity);
    setCommodityForm({
      code: commodity.code,
      name: commodity.name,
      category: commodity.category,
      unit: commodity.unit,
      aliases: commodity.aliases?.join(", ") || "",
      hs_codes: commodity.hs_codes?.join(", ") || "",
      price_low: commodity.price_low?.toString() || "",
      price_high: commodity.price_high?.toString() || "",
      current_estimate: commodity.current_estimate?.toString() || "",
      verified: commodity.verified,
    });
    setShowCommodityModal(true);
  };

  const saveCommodity = async () => {
    setSaving(true);
    try {
      const payload = {
        code: commodityForm.code.toUpperCase().replace(/\s+/g, "_"),
        name: commodityForm.name,
        category: commodityForm.category.toLowerCase(),
        unit: commodityForm.unit.toLowerCase(),
        aliases: commodityForm.aliases.split(",").map(a => a.trim()).filter(Boolean),
        hs_codes: commodityForm.hs_codes.split(",").map(h => h.trim()).filter(Boolean),
        price_low: commodityForm.price_low ? parseFloat(commodityForm.price_low) : null,
        price_high: commodityForm.price_high ? parseFloat(commodityForm.price_high) : null,
        current_estimate: commodityForm.current_estimate ? parseFloat(commodityForm.current_estimate) : null,
        verified: commodityForm.verified,
      };

      const url = editingCommodity 
        ? `${API_BASE}/admin/commodities/${editingCommodity.id}`
        : `${API_BASE}/admin/commodities`;
      
      const response = await fetch(url, {
        method: editingCommodity ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to save");
      }

      toast({
        title: editingCommodity ? "Commodity Updated" : "Commodity Created",
        description: `${commodityForm.name} has been ${editingCommodity ? "updated" : "created"}.`,
      });

      setShowCommodityModal(false);
      fetchCommodities();
      fetchStats();

    } catch (err: any) {
      toast({
        title: "Error",
        description: err.message || "Failed to save commodity",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const deleteCommodity = async (commodity: Commodity) => {
    if (!confirm(`Are you sure you want to deactivate "${commodity.name}"?`)) return;

    try {
      const response = await fetch(`${API_BASE}/admin/commodities/${commodity.id}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("Failed to delete");

      toast({
        title: "Commodity Deactivated",
        description: `${commodity.name} has been deactivated.`,
      });

      fetchCommodities();
      fetchStats();

    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to deactivate commodity",
        variant: "destructive",
      });
    }
  };

  const reviewRequest = async (requestId: string, action: "approve" | "reject", createCommodity = false) => {
    try {
      const response = await fetch(`${API_BASE}/admin/commodity-requests/${requestId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, create_commodity: createCommodity }),
      });

      if (!response.ok) throw new Error("Failed to review");

      toast({
        title: action === "approve" ? "Request Approved" : "Request Rejected",
        description: `The request has been ${action}d.`,
      });

      fetchRequests();
      fetchStats();

    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to review request",
        variant: "destructive",
      });
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Admin Panel</h1>
          <Badge variant="outline" className="text-xs bg-purple-500/10 text-purple-500 border-purple-500/20">
            <Shield className="w-3 h-3 mr-1" />
            Admin Only
          </Badge>
        </div>
        <p className="text-muted-foreground">
          Manage commodities, review requests, and view audit logs.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Package className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Commodities</p>
              <p className="text-xl font-bold">{stats?.commodities.total || 0}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-yellow-500/10 rounded-lg">
              <Clock className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Pending Requests</p>
              <p className="text-xl font-bold">{stats?.requests.pending || 0}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-green-500/10 rounded-lg">
              <Activity className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Verifications (24h)</p>
              <p className="text-xl font-bold">{stats?.verifications.last_24h || 0}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-red-500/10 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">High Risk (7d)</p>
              <p className="text-xl font-bold text-red-600">{stats?.verifications.high_risk_7d || 0}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="commodities" className="gap-2">
            <Package className="w-4 h-4" />
            Commodities
          </TabsTrigger>
          <TabsTrigger value="requests" className="gap-2">
            <FileText className="w-4 h-4" />
            Requests
            {statusCounts.pending > 0 && (
              <Badge variant="destructive" className="ml-1 h-5 px-1.5">
                {statusCounts.pending}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="audit" className="gap-2">
            <BarChart3 className="w-4 h-4" />
            Audit Logs
          </TabsTrigger>
        </TabsList>

        {/* Commodities Tab */}
        <TabsContent value="commodities" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Commodity Database</CardTitle>
                  <CardDescription>Manage commodity definitions and pricing data</CardDescription>
                </div>
                <Button onClick={openCreateModal}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Commodity
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {/* Filters */}
              <div className="flex gap-4 mb-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Search commodities..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && fetchCommodities()}
                    className="pl-10"
                  />
                </div>
                <Select value={categoryFilter || "all"} onValueChange={(v) => setCategoryFilter(v === "all" ? null : v)}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    {categories.map(cat => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="outline" onClick={fetchCommodities}>
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </div>

              {/* Table */}
              {commoditiesLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-3 font-medium">Commodity</th>
                        <th className="text-left p-3 font-medium">Category</th>
                        <th className="text-left p-3 font-medium">Unit</th>
                        <th className="text-right p-3 font-medium">Price Range</th>
                        <th className="text-center p-3 font-medium">Status</th>
                        <th className="text-right p-3 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {commodities.map(c => (
                        <tr key={c.id} className="border-b hover:bg-muted/50">
                          <td className="p-3">
                            <div>
                              <p className="font-medium">{c.name}</p>
                              <p className="text-xs text-muted-foreground font-mono">{c.code}</p>
                            </div>
                          </td>
                          <td className="p-3">
                            <Badge variant="outline">{c.category}</Badge>
                          </td>
                          <td className="p-3">{c.unit}</td>
                          <td className="p-3 text-right font-mono text-sm">
                            {c.price_low && c.price_high ? (
                              `$${c.price_low} - $${c.price_high}`
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </td>
                          <td className="p-3 text-center">
                            <div className="flex justify-center gap-1">
                              {c.verified && (
                                <Badge variant="outline" className="bg-green-500/10 text-green-500">
                                  <CheckCircle className="w-3 h-3 mr-1" />
                                  Verified
                                </Badge>
                              )}
                              {!c.is_active && (
                                <Badge variant="outline" className="bg-red-500/10 text-red-500">
                                  Inactive
                                </Badge>
                              )}
                            </div>
                          </td>
                          <td className="p-3 text-right">
                            <div className="flex justify-end gap-2">
                              <Button variant="ghost" size="sm" onClick={() => openEditModal(c)}>
                                <Edit className="w-4 h-4" />
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => deleteCommodity(c)}>
                                <Trash2 className="w-4 h-4 text-red-500" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {commodities.length === 0 && (
                    <p className="text-center py-8 text-muted-foreground">No commodities found</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Requests Tab */}
        <TabsContent value="requests" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Commodity Requests</CardTitle>
              <CardDescription>Review user-submitted commodity requests</CardDescription>
            </CardHeader>
            <CardContent>
              {/* Status filter */}
              <div className="flex gap-2 mb-4">
                {["all", "pending", "approved", "rejected"].map(status => (
                  <Button
                    key={status}
                    variant={requestStatusFilter === (status === "all" ? null : status) ? "default" : "outline"}
                    size="sm"
                    onClick={() => setRequestStatusFilter(status === "all" ? null : status)}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                    {status === "pending" && statusCounts.pending > 0 && (
                      <Badge variant="secondary" className="ml-1">{statusCounts.pending}</Badge>
                    )}
                  </Button>
                ))}
              </div>

              {requestsLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                </div>
              ) : requests.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">No requests found</p>
              ) : (
                <div className="space-y-3">
                  {requests.map(req => (
                    <div key={req.id} className="p-4 border rounded-lg">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{req.requested_name}</p>
                            <Badge variant={
                              req.status === "pending" ? "outline" :
                              req.status === "approved" ? "default" : "destructive"
                            }>
                              {req.status}
                            </Badge>
                          </div>
                          <div className="flex gap-4 mt-1 text-sm text-muted-foreground">
                            {req.suggested_category && <span>Category: {req.suggested_category}</span>}
                            {req.suggested_unit && <span>Unit: {req.suggested_unit}</span>}
                            {req.suggested_hs_code && <span>HS: {req.suggested_hs_code}</span>}
                          </div>
                          <p className="text-xs text-muted-foreground mt-2">
                            Submitted: {formatDate(req.created_at)}
                          </p>
                        </div>
                        {req.status === "pending" && (
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-green-600"
                              onClick={() => reviewRequest(req.id, "approve", true)}
                            >
                              <CheckCircle className="w-4 h-4 mr-1" />
                              Approve & Create
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-red-600"
                              onClick={() => reviewRequest(req.id, "reject")}
                            >
                              <XCircle className="w-4 h-4 mr-1" />
                              Reject
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Logs Tab */}
        <TabsContent value="audit" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Audit Logs</CardTitle>
                  <CardDescription>Recent price verification activity (last 7 days)</CardDescription>
                </div>
                <Button variant="outline" onClick={fetchAuditLogs}>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {logsLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                </div>
              ) : auditLogs.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">No audit logs found</p>
              ) : (
                <div className="space-y-2">
                  {auditLogs.map(log => (
                    <div key={log.id} className="flex items-center justify-between p-3 rounded-lg bg-muted/50 text-sm">
                      <div className="flex items-center gap-4">
                        <Badge variant={
                          log.details.verdict === "pass" ? "default" :
                          log.details.verdict === "warning" ? "outline" : "destructive"
                        } className="w-16 justify-center">
                          {log.details.verdict}
                        </Badge>
                        <div>
                          <p className="font-medium">{log.details.commodity}</p>
                          <p className="text-xs text-muted-foreground">
                            ${log.details.document_price?.toFixed(2) || "?"} vs ${log.details.market_price?.toFixed(2) || "?"}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">{formatDate(log.timestamp)}</p>
                        {log.ip_address && (
                          <p className="text-xs text-muted-foreground font-mono">{log.ip_address}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Commodity Edit/Create Modal */}
      <Dialog open={showCommodityModal} onOpenChange={setShowCommodityModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingCommodity ? "Edit Commodity" : "Add New Commodity"}
            </DialogTitle>
            <DialogDescription>
              {editingCommodity ? "Update commodity details" : "Create a new commodity in the database"}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Code *</Label>
                <Input
                  value={commodityForm.code}
                  onChange={(e) => setCommodityForm({ ...commodityForm, code: e.target.value })}
                  placeholder="e.g., DRY_FISH"
                  disabled={!!editingCommodity}
                />
              </div>
              <div className="space-y-2">
                <Label>Name *</Label>
                <Input
                  value={commodityForm.name}
                  onChange={(e) => setCommodityForm({ ...commodityForm, name: e.target.value })}
                  placeholder="e.g., Dry Fish"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Category *</Label>
                <Input
                  value={commodityForm.category}
                  onChange={(e) => setCommodityForm({ ...commodityForm, category: e.target.value })}
                  placeholder="e.g., seafood"
                />
              </div>
              <div className="space-y-2">
                <Label>Unit *</Label>
                <Select
                  value={commodityForm.unit}
                  onValueChange={(v) => setCommodityForm({ ...commodityForm, unit: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="kg">Kilogram (kg)</SelectItem>
                    <SelectItem value="mt">Metric Ton (mt)</SelectItem>
                    <SelectItem value="lb">Pound (lb)</SelectItem>
                    <SelectItem value="oz">Ounce (oz)</SelectItem>
                    <SelectItem value="bbl">Barrel (bbl)</SelectItem>
                    <SelectItem value="pcs">Pieces (pcs)</SelectItem>
                    <SelectItem value="m">Meter (m)</SelectItem>
                    <SelectItem value="sqm">Square Meter (sqm)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Aliases (comma-separated)</Label>
              <Input
                value={commodityForm.aliases}
                onChange={(e) => setCommodityForm({ ...commodityForm, aliases: e.target.value })}
                placeholder="e.g., dried fish, stockfish, salted fish"
              />
            </div>

            <div className="space-y-2">
              <Label>HS Codes (comma-separated)</Label>
              <Input
                value={commodityForm.hs_codes}
                onChange={(e) => setCommodityForm({ ...commodityForm, hs_codes: e.target.value })}
                placeholder="e.g., 0305.59, 0305.69"
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Price Low (USD)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={commodityForm.price_low}
                  onChange={(e) => setCommodityForm({ ...commodityForm, price_low: e.target.value })}
                  placeholder="e.g., 3.00"
                />
              </div>
              <div className="space-y-2">
                <Label>Price High (USD)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={commodityForm.price_high}
                  onChange={(e) => setCommodityForm({ ...commodityForm, price_high: e.target.value })}
                  placeholder="e.g., 20.00"
                />
              </div>
              <div className="space-y-2">
                <Label>Current Estimate (USD)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={commodityForm.current_estimate}
                  onChange={(e) => setCommodityForm({ ...commodityForm, current_estimate: e.target.value })}
                  placeholder="e.g., 8.00"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="verified"
                checked={commodityForm.verified}
                onChange={(e) => setCommodityForm({ ...commodityForm, verified: e.target.checked })}
                className="rounded"
              />
              <Label htmlFor="verified" className="font-normal cursor-pointer">
                Mark as verified (admin approved)
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCommodityModal(false)}>
              Cancel
            </Button>
            <Button onClick={saveCommodity} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              {editingCommodity ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


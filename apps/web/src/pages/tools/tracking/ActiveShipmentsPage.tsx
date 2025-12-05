/**
 * Active Shipments Page
 * 
 * Full view of all tracked shipments with filtering and management.
 */

import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Ship,
  Container,
  Search,
  Filter,
  MapPin,
  Clock,
  AlertTriangle,
  CheckCircle,
  Plus,
  RefreshCw,
  Trash2,
  MoreVertical,
  Download,
  ArrowUpDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/components/ui/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface Shipment {
  id: string;
  reference: string;
  tracking_type: string;
  nickname?: string;
  carrier?: string;
  status?: string;
  origin_port?: string;
  destination_port?: string;
  eta?: string;
  progress: number;
  vessel_name?: string;
  alerts_count: number;
  last_checked?: string;
  created_at: string;
}

const getStatusBadge = (status?: string) => {
  switch (status) {
    case "in_transit":
      return <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">In Transit</Badge>;
    case "at_port":
      return <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">At Port</Badge>;
    case "delivered":
      return <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">Delivered</Badge>;
    case "delayed":
      return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Delayed</Badge>;
    default:
      return <Badge className="bg-slate-500/20 text-slate-400 border-slate-500/30">Unknown</Badge>;
  }
};

export default function ActiveShipmentsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const fetchShipments = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/tracking/portfolio?limit=100`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        setShipments(data.shipments || []);
      }
    } catch (error) {
      console.error("Failed to fetch shipments:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchShipments();
    } else {
      setIsLoading(false);
    }
  }, [user]);

  const handleRemove = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/tracking/portfolio/${id}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (response.ok) {
        setShipments(shipments.filter(s => s.id !== id));
        toast({ title: "Removed", description: "Shipment removed from portfolio" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to remove shipment", variant: "destructive" });
    }
  };

  const handleRefresh = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/tracking/portfolio/${id}/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (response.ok) {
        const updated = await response.json();
        setShipments(shipments.map(s => s.id === id ? { ...s, ...updated } : s));
        toast({ title: "Refreshed", description: "Tracking data updated" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to refresh", variant: "destructive" });
    }
  };

  // Filter shipments
  const filteredShipments = shipments.filter(s => {
    const matchesSearch = !searchQuery || 
      s.reference.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.vessel_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.nickname?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || s.status === statusFilter;
    const matchesType = typeFilter === "all" || s.tracking_type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  const stats = {
    total: shipments.length,
    inTransit: shipments.filter(s => s.status === "in_transit").length,
    delayed: shipments.filter(s => s.status === "delayed").length,
    delivered: shipments.filter(s => s.status === "delivered").length,
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Active Shipments</h1>
          <p className="text-muted-foreground">Manage and monitor all your tracked shipments</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchShipments} disabled={isLoading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
            Refresh All
          </Button>
          <Button asChild>
            <Link to="/tracking/dashboard">
              <Plus className="w-4 h-4 mr-2" />
              Track New
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <Container className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.total}</p>
                <p className="text-xs text-muted-foreground">Total Tracked</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <Ship className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.inTransit}</p>
                <p className="text-xs text-muted-foreground">In Transit</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-500/10 rounded-lg flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.delayed}</p>
                <p className="text-xs text-muted-foreground">Delayed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-500/10 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.delivered}</p>
                <p className="text-xs text-muted-foreground">Delivered</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by reference, vessel, or nickname..."
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="in_transit">In Transit</SelectItem>
                <SelectItem value="at_port">At Port</SelectItem>
                <SelectItem value="delayed">Delayed</SelectItem>
                <SelectItem value="delivered">Delivered</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="container">Container</SelectItem>
                <SelectItem value="vessel">Vessel</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Shipments Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Reference</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Route</TableHead>
                <TableHead>Vessel</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Progress</TableHead>
                <TableHead>ETA</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                    <p className="text-muted-foreground">Loading shipments...</p>
                  </TableCell>
                </TableRow>
              ) : filteredShipments.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <Container className="w-8 h-8 mx-auto mb-2 text-muted-foreground opacity-50" />
                    <p className="text-muted-foreground">No shipments found</p>
                    <Button asChild variant="link" className="mt-2">
                      <Link to="/tracking/dashboard">Track your first shipment →</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ) : (
                filteredShipments.map((shipment) => (
                  <TableRow key={shipment.id}>
                    <TableCell>
                      <Link 
                        to={`/tracking/dashboard/${shipment.tracking_type}/${shipment.reference}`}
                        className="font-mono font-medium text-blue-500 hover:underline"
                      >
                        {shipment.reference}
                      </Link>
                      {shipment.nickname && (
                        <p className="text-xs text-muted-foreground">{shipment.nickname}</p>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {shipment.tracking_type === "container" ? (
                          <Container className="w-3 h-3 mr-1" />
                        ) : (
                          <Ship className="w-3 h-3 mr-1" />
                        )}
                        {shipment.tracking_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <p>{shipment.origin_port || "—"}</p>
                        <p className="text-muted-foreground">→ {shipment.destination_port || "—"}</p>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{shipment.vessel_name || "—"}</TableCell>
                    <TableCell>{getStatusBadge(shipment.status)}</TableCell>
                    <TableCell>
                      <div className="w-24">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span>{shipment.progress}%</span>
                        </div>
                        <Progress value={shipment.progress} className="h-1.5" />
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">
                      {shipment.eta ? new Date(shipment.eta).toLocaleDateString() : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link to={`/tracking/dashboard/${shipment.tracking_type}/${shipment.reference}`}>
                              View Details
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleRefresh(shipment.id)}>
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Refresh
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => handleRemove(shipment.id)}
                            className="text-red-500"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Remove
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}


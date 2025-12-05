/**
 * Exceptions Page
 * 
 * View and manage shipment exceptions and issues.
 */

import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  AlertCircle,
  Clock,
  Ship,
  Container,
  CheckCircle,
  XCircle,
  RefreshCw,
  Filter,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface Exception {
  id: string;
  reference: string;
  type: string;
  severity: "critical" | "warning" | "info";
  title: string;
  description: string;
  created_at: string;
  resolved: boolean;
  shipment_type: string;
}

// Generate mock exceptions from delayed shipments
const generateExceptions = (shipments: any[]): Exception[] => {
  const exceptions: Exception[] = [];
  
  shipments.forEach((s, i) => {
    if (s.status === "delayed") {
      exceptions.push({
        id: `exc-${i}-delay`,
        reference: s.reference,
        type: "delay",
        severity: "warning",
        title: "ETA Delay",
        description: `Shipment delayed. Original ETA was ${s.eta ? new Date(s.eta).toLocaleDateString() : 'unknown'}.`,
        created_at: new Date().toISOString(),
        resolved: false,
        shipment_type: s.tracking_type,
      });
    }
    
    // Add some mock LC risk exceptions
    if (s.lc_expiry && new Date(s.lc_expiry) < new Date(s.eta)) {
      exceptions.push({
        id: `exc-${i}-lc`,
        reference: s.reference,
        type: "lc_risk",
        severity: "critical",
        title: "LC Expiry Risk",
        description: `ETA exceeds LC expiry date. Documents may not be negotiable.`,
        created_at: new Date().toISOString(),
        resolved: false,
        shipment_type: s.tracking_type,
      });
    }
  });
  
  return exceptions;
};

const getSeverityBadge = (severity: string) => {
  switch (severity) {
    case "critical":
      return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Critical</Badge>;
    case "warning":
      return <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">Warning</Badge>;
    default:
      return <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">Info</Badge>;
  }
};

const getExceptionIcon = (type: string, severity: string) => {
  const colorClass = severity === "critical" ? "text-red-500" : severity === "warning" ? "text-amber-500" : "text-blue-500";
  switch (type) {
    case "delay":
      return <Clock className={`w-5 h-5 ${colorClass}`} />;
    case "lc_risk":
      return <AlertTriangle className={`w-5 h-5 ${colorClass}`} />;
    case "customs":
      return <AlertCircle className={`w-5 h-5 ${colorClass}`} />;
    default:
      return <AlertTriangle className={`w-5 h-5 ${colorClass}`} />;
  }
};

export default function ExceptionsPage() {
  const { user } = useAuth();
  const [exceptions, setExceptions] = useState<Exception[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("active");

  useEffect(() => {
    const fetchExceptions = async () => {
      try {
        const response = await fetch(`${API_BASE}/tracking/portfolio?limit=100`, {
          credentials: "include",
        });
        if (response.ok) {
          const data = await response.json();
          const generated = generateExceptions(data.shipments || []);
          setExceptions(generated);
        }
      } catch (error) {
        console.error("Failed to fetch exceptions:", error);
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      fetchExceptions();
    } else {
      setIsLoading(false);
    }
  }, [user]);

  const filteredExceptions = exceptions.filter((e) => {
    const matchesSeverity = severityFilter === "all" || e.severity === severityFilter;
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "active" && !e.resolved) ||
      (statusFilter === "resolved" && e.resolved);
    return matchesSeverity && matchesStatus;
  });

  const criticalCount = exceptions.filter((e) => e.severity === "critical" && !e.resolved).length;
  const warningCount = exceptions.filter((e) => e.severity === "warning" && !e.resolved).length;
  const resolvedCount = exceptions.filter((e) => e.resolved).length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Exceptions</h1>
          <p className="text-muted-foreground">
            Shipment issues requiring attention
          </p>
        </div>
        <Button variant="outline" disabled={isLoading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-red-500/10 rounded-lg flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{criticalCount}</p>
                <p className="text-xs text-muted-foreground">Critical</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-500/10 rounded-lg flex items-center justify-center">
                <AlertCircle className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{warningCount}</p>
                <p className="text-xs text-muted-foreground">Warnings</p>
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
                <p className="text-2xl font-bold">{resolvedCount}</p>
                <p className="text-xs text-muted-foreground">Resolved</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4">
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severity</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="info">Info</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Exceptions List */}
      <Card>
        <CardHeader>
          <CardTitle>Active Exceptions</CardTitle>
          <CardDescription>
            {filteredExceptions.length} exception{filteredExceptions.length !== 1 ? "s" : ""} found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
              <p className="text-muted-foreground">Loading exceptions...</p>
            </div>
          ) : filteredExceptions.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle className="w-8 h-8 mx-auto mb-2 text-emerald-500 opacity-50" />
              <p className="text-muted-foreground">No exceptions found</p>
              <p className="text-xs text-muted-foreground mt-1">
                All your shipments are on track
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredExceptions.map((exception) => (
                <div
                  key={exception.id}
                  className={`p-4 rounded-lg border ${
                    exception.resolved ? "bg-muted/30 opacity-60" : "bg-card"
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className="mt-0.5">
                      {getExceptionIcon(exception.type, exception.severity)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Link
                          to={`/tracking/dashboard/${exception.shipment_type}/${exception.reference}`}
                          className="font-mono text-blue-500 hover:underline"
                        >
                          {exception.reference}
                        </Link>
                        {getSeverityBadge(exception.severity)}
                        {exception.resolved && (
                          <Badge variant="outline" className="text-emerald-500">
                            Resolved
                          </Badge>
                        )}
                      </div>
                      <p className="font-medium">{exception.title}</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        {exception.description}
                      </p>
                      <p className="text-xs text-muted-foreground mt-2">
                        {new Date(exception.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" asChild>
                        <Link to={`/tracking/dashboard/${exception.shipment_type}/${exception.reference}`}>
                          View
                        </Link>
                      </Button>
                      {!exception.resolved && (
                        <Button size="sm" variant="ghost" className="text-emerald-500">
                          <CheckCircle className="w-4 h-4 mr-1" />
                          Resolve
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


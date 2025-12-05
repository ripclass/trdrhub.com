/**
 * History Page
 * 
 * View past tracking searches and delivered shipments.
 */

import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  History,
  Container,
  Ship,
  Search,
  Calendar,
  CheckCircle,
  Clock,
  Filter,
  Download,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

interface HistoryItem {
  id: string;
  reference: string;
  tracking_type: string;
  status: string;
  origin_port?: string;
  destination_port?: string;
  eta?: string;
  ata?: string;
  created_at: string;
  vessel_name?: string;
}

export default function HistoryPage() {
  const { user } = useAuth();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [dateFilter, setDateFilter] = useState("all");

  useEffect(() => {
    const fetchHistory = async () => {
      setIsLoading(true);
      try {
        // Fetch all shipments including inactive (delivered)
        const response = await fetch(`${API_BASE}/tracking/portfolio?active_only=false&limit=100`, {
          credentials: "include",
        });
        if (response.ok) {
          const data = await response.json();
          // Sort by created_at descending
          const sorted = (data.shipments || []).sort((a: HistoryItem, b: HistoryItem) => 
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
          setHistory(sorted);
        }
      } catch (error) {
        console.error("Failed to fetch history:", error);
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      fetchHistory();
    } else {
      setIsLoading(false);
    }
  }, [user]);

  // Filter by date
  const getDateCutoff = () => {
    const now = new Date();
    switch (dateFilter) {
      case "7d": return new Date(now.setDate(now.getDate() - 7));
      case "30d": return new Date(now.setDate(now.getDate() - 30));
      case "90d": return new Date(now.setDate(now.getDate() - 90));
      default: return null;
    }
  };

  const filteredHistory = history.filter(item => {
    const matchesSearch = !searchQuery || 
      item.reference.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.vessel_name?.toLowerCase().includes(searchQuery.toLowerCase());
    
    const cutoff = getDateCutoff();
    const matchesDate = !cutoff || new Date(item.created_at) >= cutoff;
    
    return matchesSearch && matchesDate;
  });

  const deliveredCount = history.filter(h => h.status === "delivered").length;
  const thisMonthCount = history.filter(h => {
    const date = new Date(h.created_at);
    const now = new Date();
    return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
  }).length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tracking History</h1>
          <p className="text-muted-foreground">View your past tracking searches and completed shipments</p>
        </div>
        <Button variant="outline">
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <History className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{history.length}</p>
                <p className="text-xs text-muted-foreground">Total Tracked</p>
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
                <p className="text-2xl font-bold">{deliveredCount}</p>
                <p className="text-xs text-muted-foreground">Delivered</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center">
                <Calendar className="w-5 h-5 text-purple-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{thisMonthCount}</p>
                <p className="text-xs text-muted-foreground">This Month</p>
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
                placeholder="Search by reference or vessel..."
                className="pl-9"
              />
            </div>
            <Select value={dateFilter} onValueChange={setDateFilter}>
              <SelectTrigger className="w-[150px]">
                <Calendar className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Date Range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Time</SelectItem>
                <SelectItem value="7d">Last 7 Days</SelectItem>
                <SelectItem value="30d">Last 30 Days</SelectItem>
                <SelectItem value="90d">Last 90 Days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* History List */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Tracking</CardTitle>
          <CardDescription>Click on any shipment to view details</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">
              <Clock className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
              <p className="text-muted-foreground">Loading history...</p>
            </div>
          ) : filteredHistory.length === 0 ? (
            <div className="text-center py-8">
              <History className="w-8 h-8 mx-auto mb-2 text-muted-foreground opacity-50" />
              <p className="text-muted-foreground">No tracking history</p>
              <Button asChild variant="link">
                <Link to="/tracking/dashboard">Start tracking →</Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredHistory.map((item) => (
                <Link
                  key={item.id}
                  to={`/tracking/dashboard/${item.tracking_type}/${item.reference}`}
                  className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-muted rounded-lg flex items-center justify-center">
                      {item.tracking_type === "container" ? (
                        <Container className="w-5 h-5 text-blue-500" />
                      ) : (
                        <Ship className="w-5 h-5 text-blue-500" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-mono font-medium">{item.reference}</p>
                        {item.status === "delivered" && (
                          <Badge className="bg-emerald-500/20 text-emerald-400 text-xs">Delivered</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {item.origin_port || "—"} → {item.destination_port || "—"}
                        {item.vessel_name && ` • ${item.vessel_name}`}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-sm text-muted-foreground">
                    <p>{new Date(item.created_at).toLocaleDateString()}</p>
                    <p className="text-xs">{new Date(item.created_at).toLocaleTimeString()}</p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


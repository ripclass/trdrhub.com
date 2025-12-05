/**
 * Tracking Overview Page
 * 
 * Main overview content for the tracking dashboard.
 * Shows search, stats, active shipments, and alerts.
 */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Ship,
  Container,
  Search,
  Bell,
  MapPin,
  Clock,
  AlertTriangle,
  CheckCircle,
  ChevronRight,
  Anchor,
  Calendar,
  TrendingUp,
  Package,
  RefreshCw,
  ExternalLink,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/components/ui/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

// Types
interface TrackedShipment {
  id: string;
  reference: string;
  type: "container" | "vessel";
  carrier?: string;
  vessel?: string;
  voyage?: string;
  origin: string;
  destination: string;
  status: "in_transit" | "at_port" | "delivered" | "delayed" | "exception";
  eta: string;
  etaConfidence: number;
  lastUpdate: string;
  lastLocation: string;
  progress: number;
  alerts: number;
}

interface TrackingAlert {
  id: string;
  shipmentId: string;
  reference: string;
  type: "delay" | "arrival" | "departure" | "exception" | "eta_change";
  severity: "info" | "warning" | "critical";
  message: string;
  timestamp: string;
  read: boolean;
}

// Mock data for demo
const MOCK_SHIPMENTS: TrackedShipment[] = [
  {
    id: "1",
    reference: "MSCU1234567",
    type: "container",
    carrier: "MSC",
    vessel: "MSC OSCAR",
    voyage: "FA234E",
    origin: "Shanghai, CN",
    destination: "Rotterdam, NL",
    status: "in_transit",
    eta: "2025-01-15",
    etaConfidence: 92,
    lastUpdate: "2h ago",
    lastLocation: "Suez Canal",
    progress: 68,
    alerts: 0,
  },
  {
    id: "2",
    reference: "MAEU987654321",
    type: "container",
    carrier: "Maersk",
    vessel: "MAERSK EDMONTON",
    voyage: "MA102E",
    origin: "Chittagong, BD",
    destination: "Hamburg, DE",
    status: "delayed",
    eta: "2025-01-18",
    etaConfidence: 78,
    lastUpdate: "4h ago",
    lastLocation: "Port Said, EG",
    progress: 55,
    alerts: 2,
  },
  {
    id: "3",
    reference: "HLCU5678901",
    type: "container",
    carrier: "Hapag-Lloyd",
    vessel: "BERLIN EXPRESS",
    voyage: "HL456W",
    origin: "Mumbai, IN",
    destination: "Los Angeles, US",
    status: "at_port",
    eta: "2025-01-12",
    etaConfidence: 99,
    lastUpdate: "1h ago",
    lastLocation: "Singapore, SG",
    progress: 42,
    alerts: 1,
  },
  {
    id: "4",
    reference: "OOLU2345678",
    type: "container",
    carrier: "OOCL",
    vessel: "OOCL HONG KONG",
    voyage: "OL789E",
    origin: "Ningbo, CN",
    destination: "New York, US",
    status: "delivered",
    eta: "2025-01-05",
    etaConfidence: 100,
    lastUpdate: "3d ago",
    lastLocation: "New York, US",
    progress: 100,
    alerts: 0,
  },
];

const MOCK_ALERTS: TrackingAlert[] = [
  {
    id: "a1",
    shipmentId: "2",
    reference: "MAEU987654321",
    type: "delay",
    severity: "warning",
    message: "ETA delayed by 2 days due to port congestion at Port Said",
    timestamp: "2h ago",
    read: false,
  },
  {
    id: "a2",
    shipmentId: "2",
    reference: "MAEU987654321",
    type: "eta_change",
    severity: "info",
    message: "ETA updated from Jan 16 to Jan 18",
    timestamp: "4h ago",
    read: false,
  },
  {
    id: "a3",
    shipmentId: "3",
    reference: "HLCU5678901",
    type: "arrival",
    severity: "info",
    message: "Vessel arrived at Singapore for transshipment",
    timestamp: "6h ago",
    read: true,
  },
];

const getStatusBadge = (status: TrackedShipment["status"]) => {
  switch (status) {
    case "in_transit":
      return <Badge className="bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30">In Transit</Badge>;
    case "at_port":
      return <Badge className="bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30">At Port</Badge>;
    case "delivered":
      return <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30">Delivered</Badge>;
    case "delayed":
      return <Badge className="bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30">Delayed</Badge>;
    case "exception":
      return <Badge className="bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/30">Exception</Badge>;
    default:
      return <Badge>Unknown</Badge>;
  }
};

const getAlertIcon = (type: TrackingAlert["type"], severity: TrackingAlert["severity"]) => {
  const colorClass = severity === "critical" ? "text-red-500" : severity === "warning" ? "text-amber-500" : "text-blue-500";
  switch (type) {
    case "delay":
      return <Clock className={`w-4 h-4 ${colorClass}`} />;
    case "arrival":
      return <Anchor className={`w-4 h-4 ${colorClass}`} />;
    case "departure":
      return <Ship className={`w-4 h-4 ${colorClass}`} />;
    case "exception":
      return <AlertTriangle className={`w-4 h-4 ${colorClass}`} />;
    case "eta_change":
      return <Calendar className={`w-4 h-4 ${colorClass}`} />;
    default:
      return <Bell className={`w-4 h-4 ${colorClass}`} />;
  }
};

export default function TrackingOverview() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchType, setSearchType] = useState<"container" | "vessel" | "bl">("container");
  const [shipments, setShipments] = useState<TrackedShipment[]>(MOCK_SHIPMENTS);
  const [alerts, setAlerts] = useState<TrackingAlert[]>(MOCK_ALERTS);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [portfolioStats, setPortfolioStats] = useState({
    active: 0,
    delivered_30d: 0,
    delayed: 0,
    on_time_rate: 92,
  });

  // Fetch portfolio on mount
  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const response = await fetch(`${API_BASE}/tracking/portfolio`, {
          credentials: "include",
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.shipments && data.shipments.length > 0) {
            const transformed = data.shipments.map((s: any) => ({
              id: s.id,
              reference: s.reference,
              type: s.type,
              carrier: s.carrier || "Unknown",
              origin: s.origin,
              destination: s.destination,
              status: s.status,
              eta: s.eta,
              etaConfidence: 90,
              lastUpdate: "just now",
              lastLocation: s.current_location || "In Transit",
              progress: s.progress || 50,
              alerts: s.alerts || 0,
            }));
            setShipments(transformed);
          }
          if (data.stats) {
            setPortfolioStats(data.stats);
          }
        }
      } catch (error) {
        console.error("Failed to fetch portfolio:", error);
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      fetchPortfolio();
    } else {
      setIsLoading(false);
    }
  }, [user]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    
    try {
      let endpoint = "";
      if (searchType === "container" || searchType === "bl") {
        endpoint = `/tracking/container/${encodeURIComponent(searchQuery.toUpperCase())}`;
      } else {
        endpoint = `/tracking/vessel/${encodeURIComponent(searchQuery)}?search_type=name`;
      }

      const response = await fetch(`${API_BASE}${endpoint}`, {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        if (searchType === "vessel") {
          navigate(`/tracking/dashboard/vessel/${data.imo || searchQuery}`);
        } else {
          navigate(`/tracking/dashboard/container/${data.container_number || searchQuery}`);
        }
      } else {
        const error = await response.json();
        toast({
          title: "Tracking Error",
          description: error.detail || "Container/vessel not found",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Search Failed",
        description: "Unable to search. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSearching(false);
    }
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/tracking/portfolio`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        if (data.stats) {
          setPortfolioStats(data.stats);
        }
        toast({
          title: "Refreshed",
          description: "Tracking data updated",
        });
      }
    } catch (error) {
      console.error("Refresh failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const unreadAlerts = alerts.filter((a) => !a.read).length;
  const activeShipments = portfolioStats.active || shipments.filter((s) => s.status !== "delivered").length;
  const delayedShipments = portfolioStats.delayed || shipments.filter((s) => s.status === "delayed").length;
  const deliveredShipments = portfolioStats.delivered_30d || shipments.filter(s => s.status === "delivered").length;
  const onTimeRate = portfolioStats.on_time_rate || 92;

  return (
    <div className="p-6 space-y-6">
      {/* Search Section */}
      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSearch}>
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Enter container number, vessel name, or B/L..."
                    className="pl-10 h-12"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Tabs value={searchType} onValueChange={(v) => setSearchType(v as any)} className="w-auto">
                  <TabsList className="h-12">
                    <TabsTrigger value="container" className="data-[state=active]:bg-blue-500/20">
                      <Container className="w-4 h-4 mr-1" />
                      Container
                    </TabsTrigger>
                    <TabsTrigger value="vessel" className="data-[state=active]:bg-blue-500/20">
                      <Ship className="w-4 h-4 mr-1" />
                      Vessel
                    </TabsTrigger>
                    <TabsTrigger value="bl" className="data-[state=active]:bg-blue-500/20">
                      B/L
                    </TabsTrigger>
                  </TabsList>
                </Tabs>
                <Button 
                  type="submit" 
                  className="bg-blue-500 hover:bg-blue-600 h-12 px-6"
                  disabled={isSearching}
                >
                  {isSearching ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    "Track"
                  )}
                </Button>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span>Examples:</span>
              <button type="button" onClick={() => setSearchQuery("MSCU1234567")} className="text-blue-500 hover:underline">
                MSCU1234567
              </button>
              <button type="button" onClick={() => { setSearchQuery("MSC OSCAR"); setSearchType("vessel"); }} className="text-blue-500 hover:underline">
                MSC OSCAR
              </button>
              <button type="button" onClick={() => { setSearchQuery("MAEU123456789"); setSearchType("bl"); }} className="text-blue-500 hover:underline">
                MAEU123456789
              </button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <Package className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{activeShipments}</p>
                <p className="text-xs text-muted-foreground">Active Shipments</p>
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
                <p className="text-2xl font-bold">{deliveredShipments}</p>
                <p className="text-xs text-muted-foreground">Delivered (30d)</p>
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
                <p className="text-2xl font-bold">{delayedShipments}</p>
                <p className="text-xs text-muted-foreground">Delayed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-purple-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{onTimeRate}%</p>
                <p className="text-xs text-muted-foreground">On-Time Rate</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Active Shipments */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Active Shipments</CardTitle>
                <CardDescription>Track your containers and vessels in real-time</CardDescription>
              </div>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={handleRefresh}
                disabled={isLoading}
              >
                <RefreshCw className={`w-4 h-4 mr-1 ${isLoading ? "animate-spin" : ""}`} />
                {isLoading ? "Loading..." : "Refresh"}
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y">
                {shipments.map((shipment) => (
                  <Link
                    key={shipment.id}
                    to={`/tracking/dashboard/${shipment.type}/${shipment.reference}`}
                    className="block p-4 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-muted rounded-lg flex items-center justify-center">
                          {shipment.type === "container" ? (
                            <Container className="w-5 h-5 text-blue-500" />
                          ) : (
                            <Ship className="w-5 h-5 text-blue-500" />
                          )}
                        </div>
                        <div>
                          <p className="font-mono font-medium">{shipment.reference}</p>
                          <p className="text-xs text-muted-foreground">{shipment.carrier} • {shipment.vessel}</p>
                        </div>
                      </div>
                      <div className="text-right flex items-center gap-2">
                        {getStatusBadge(shipment.status)}
                        {shipment.alerts > 0 && (
                          <Badge className="bg-red-500/20 text-red-500 border-red-500/30">
                            {shipment.alerts} alerts
                          </Badge>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 text-sm mb-3">
                      <div>
                        <p className="text-muted-foreground text-xs">Origin</p>
                        <p>{shipment.origin}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground text-xs">Destination</p>
                        <p>{shipment.destination}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-muted-foreground text-xs">ETA</p>
                        <p>{new Date(shipment.eta).toLocaleDateString()}</p>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {shipment.lastLocation}
                        </span>
                        <span className="text-muted-foreground">
                          {shipment.progress}% complete • Updated {shipment.lastUpdate}
                        </span>
                      </div>
                      <Progress value={shipment.progress} className="h-1.5" />
                    </div>
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Alerts Sidebar */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Bell className="w-5 h-5 text-amber-500" />
                  Alerts
                  {unreadAlerts > 0 && (
                    <Badge className="bg-red-500 text-white">{unreadAlerts}</Badge>
                  )}
                </CardTitle>
                <Button variant="ghost" size="sm" className="text-xs">
                  Mark all read
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y">
                {alerts.length === 0 ? (
                  <div className="p-6 text-center text-muted-foreground">
                    <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>No alerts</p>
                  </div>
                ) : (
                  alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-4 ${!alert.read ? "bg-muted/30" : ""}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">
                          {getAlertIcon(alert.type, alert.severity)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-mono text-blue-500 mb-1">
                            {alert.reference}
                          </p>
                          <p className="text-sm">{alert.message}</p>
                          <p className="text-xs text-muted-foreground mt-1">{alert.timestamp}</p>
                        </div>
                        {!alert.read && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full" />
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Quick Links */}
          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="text-sm">Quick Links</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Link
                to="/tracking/dashboard/vessel-search"
                className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Ship className="w-4 h-4 text-blue-500" />
                  <span className="text-sm">Browse Vessels</span>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </Link>
              <Link
                to="/tracking/dashboard/ports"
                className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Anchor className="w-4 h-4 text-emerald-500" />
                  <span className="text-sm">Port Schedules</span>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </Link>
              <a
                href="https://www.marinetraffic.com"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-amber-500" />
                  <span className="text-sm">Live Map</span>
                </div>
                <ExternalLink className="w-4 h-4 text-muted-foreground" />
              </a>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}


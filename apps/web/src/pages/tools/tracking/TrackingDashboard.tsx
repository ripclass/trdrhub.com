/**
 * Container & Vessel Tracking Dashboard
 * 
 * Main dashboard for tracking containers and vessels.
 * Features:
 * - Quick search by container/vessel/B-L
 * - Active shipments overview
 * - Recent tracking history
 * - Alerts & exceptions
 */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Ship,
  Container,
  Search,
  Plus,
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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/hooks/use-auth";

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

// Mock data
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
      return <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">In Transit</Badge>;
    case "at_port":
      return <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">At Port</Badge>;
    case "delivered":
      return <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">Delivered</Badge>;
    case "delayed":
      return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Delayed</Badge>;
    case "exception":
      return <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30">Exception</Badge>;
    default:
      return <Badge>Unknown</Badge>;
  }
};

const getAlertIcon = (type: TrackingAlert["type"], severity: TrackingAlert["severity"]) => {
  const colorClass = severity === "critical" ? "text-red-400" : severity === "warning" ? "text-amber-400" : "text-blue-400";
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

export default function TrackingDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchType, setSearchType] = useState<"container" | "vessel" | "bl">("container");
  const [shipments, setShipments] = useState<TrackedShipment[]>(MOCK_SHIPMENTS);
  const [alerts, setAlerts] = useState<TrackingAlert[]>(MOCK_ALERTS);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    // Navigate to search results
    navigate(`/tracking/search?q=${encodeURIComponent(searchQuery)}&type=${searchType}`);
  };

  const unreadAlerts = alerts.filter((a) => !a.read).length;
  const activeShipments = shipments.filter((s) => s.status !== "delivered").length;
  const delayedShipments = shipments.filter((s) => s.status === "delayed").length;

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="bg-slate-900/80 border-b border-slate-800 sticky top-0 z-40 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/hub" className="text-slate-400 hover:text-white text-sm">
                ← Back to Hub
              </Link>
              <div className="flex items-center gap-2">
                <Ship className="w-6 h-6 text-blue-400" />
                <h1 className="text-xl font-bold text-white">Container & Vessel Tracker</h1>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" className="relative border-slate-700 text-slate-300">
                <Bell className="w-4 h-4" />
                {unreadAlerts > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[10px] flex items-center justify-center">
                    {unreadAlerts}
                  </span>
                )}
              </Button>
              <Button size="sm" className="bg-blue-500 hover:bg-blue-600">
                <Plus className="w-4 h-4 mr-1" />
                Track New
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Search Section */}
        <Card className="bg-slate-900/50 border-slate-800 mb-8">
          <CardContent className="p-6">
            <form onSubmit={handleSearch}>
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                    <Input
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Enter container number, vessel name, or B/L..."
                      className="pl-10 bg-slate-800 border-slate-700 text-white placeholder-slate-500 h-12"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Tabs value={searchType} onValueChange={(v) => setSearchType(v as any)} className="w-auto">
                    <TabsList className="bg-slate-800 border border-slate-700 h-12">
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
                  <Button type="submit" className="bg-blue-500 hover:bg-blue-600 h-12 px-6">
                    Track
                  </Button>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                <span>Examples:</span>
                <button type="button" onClick={() => setSearchQuery("MSCU1234567")} className="text-blue-400 hover:underline">
                  MSCU1234567
                </button>
                <button type="button" onClick={() => { setSearchQuery("MSC OSCAR"); setSearchType("vessel"); }} className="text-blue-400 hover:underline">
                  MSC OSCAR
                </button>
                <button type="button" onClick={() => { setSearchQuery("MAEU123456789"); setSearchType("bl"); }} className="text-blue-400 hover:underline">
                  MAEU123456789
                </button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                  <Package className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{activeShipments}</p>
                  <p className="text-xs text-slate-500">Active Shipments</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-500/10 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{shipments.filter(s => s.status === "delivered").length}</p>
                  <p className="text-xs text-slate-500">Delivered (30d)</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-amber-500/10 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{delayedShipments}</p>
                  <p className="text-xs text-slate-500">Delayed</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">92%</p>
                  <p className="text-xs text-slate-500">On-Time Rate</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Active Shipments */}
          <div className="lg:col-span-2">
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-white">Active Shipments</CardTitle>
                  <CardDescription>Track your containers and vessels in real-time</CardDescription>
                </div>
                <Button variant="ghost" size="sm" className="text-slate-400">
                  <RefreshCw className="w-4 h-4 mr-1" />
                  Refresh
                </Button>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-slate-800">
                  {shipments.map((shipment) => (
                    <Link
                      key={shipment.id}
                      to={`/tracking/${shipment.type}/${shipment.reference}`}
                      className="block p-4 hover:bg-slate-800/50 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center">
                            {shipment.type === "container" ? (
                              <Container className="w-5 h-5 text-blue-400" />
                            ) : (
                              <Ship className="w-5 h-5 text-blue-400" />
                            )}
                          </div>
                          <div>
                            <p className="font-mono text-white font-medium">{shipment.reference}</p>
                            <p className="text-xs text-slate-500">{shipment.carrier} • {shipment.vessel}</p>
                          </div>
                        </div>
                        <div className="text-right flex items-center gap-2">
                          {getStatusBadge(shipment.status)}
                          {shipment.alerts > 0 && (
                            <Badge className="bg-red-500/20 text-red-400 border-red-500/30">
                              {shipment.alerts} alerts
                            </Badge>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-4 text-sm mb-3">
                        <div>
                          <p className="text-slate-500 text-xs">Origin</p>
                          <p className="text-white">{shipment.origin}</p>
                        </div>
                        <div>
                          <p className="text-slate-500 text-xs">Destination</p>
                          <p className="text-white">{shipment.destination}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-slate-500 text-xs">ETA</p>
                          <p className="text-white">{new Date(shipment.eta).toLocaleDateString()}</p>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-500 flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {shipment.lastLocation}
                          </span>
                          <span className="text-slate-500">
                            {shipment.progress}% complete • Updated {shipment.lastUpdate}
                          </span>
                        </div>
                        <Progress value={shipment.progress} className="h-1.5 bg-slate-800" />
                      </div>
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Alerts Sidebar */}
          <div className="lg:col-span-1">
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white flex items-center gap-2">
                    <Bell className="w-5 h-5 text-amber-400" />
                    Alerts
                    {unreadAlerts > 0 && (
                      <Badge className="bg-red-500 text-white">{unreadAlerts}</Badge>
                    )}
                  </CardTitle>
                  <Button variant="ghost" size="sm" className="text-xs text-slate-400">
                    Mark all read
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-slate-800">
                  {alerts.length === 0 ? (
                    <div className="p-6 text-center text-slate-500">
                      <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>No alerts</p>
                    </div>
                  ) : (
                    alerts.map((alert) => (
                      <div
                        key={alert.id}
                        className={`p-4 ${!alert.read ? "bg-slate-800/30" : ""}`}
                      >
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5">
                            {getAlertIcon(alert.type, alert.severity)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-mono text-blue-400 mb-1">
                              {alert.reference}
                            </p>
                            <p className="text-sm text-white">{alert.message}</p>
                            <p className="text-xs text-slate-500 mt-1">{alert.timestamp}</p>
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
            <Card className="bg-slate-900/50 border-slate-800 mt-4">
              <CardHeader>
                <CardTitle className="text-white text-sm">Quick Links</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Link
                  to="/tracking/vessels"
                  className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Ship className="w-4 h-4 text-blue-400" />
                    <span className="text-sm text-white">Browse Vessels</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500" />
                </Link>
                <Link
                  to="/tracking/ports"
                  className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Anchor className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-white">Port Schedules</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500" />
                </Link>
                <a
                  href="https://www.marinetraffic.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-amber-400" />
                    <span className="text-sm text-white">Live Map</span>
                  </div>
                  <ExternalLink className="w-4 h-4 text-slate-500" />
                </a>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}


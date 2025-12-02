/**
 * Container Tracking Detail Page
 * 
 * Shows detailed tracking information for a specific container.
 * Features:
 * - Timeline of events
 * - Map view (placeholder)
 * - Vessel info
 * - ETA predictions
 * - Document status
 */

import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/components/ui/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";
import {
  Ship,
  Container,
  ArrowLeft,
  MapPin,
  Clock,
  Calendar,
  Anchor,
  Package,
  FileText,
  AlertTriangle,
  CheckCircle,
  ChevronRight,
  Share2,
  Bell,
  Download,
  RefreshCw,
  Navigation,
  Thermometer,
  Weight,
  Box,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";

interface ContainerDetails {
  containerNumber: string;
  containerType: string;
  containerSize: string;
  carrier: string;
  carrierCode: string;
  bookingNumber: string;
  blNumber: string;
  shipper: string;
  consignee: string;
  origin: {
    port: string;
    portCode: string;
    country: string;
  };
  destination: {
    port: string;
    portCode: string;
    country: string;
  };
  vessel: {
    name: string;
    imo: string;
    mmsi: string;
    voyage: string;
    flag: string;
  };
  status: "booked" | "gate_in" | "loaded" | "in_transit" | "transshipment" | "discharged" | "gate_out" | "delivered";
  eta: string;
  etaConfidence: number;
  ata?: string;
  currentLocation: {
    type: "port" | "at_sea" | "terminal";
    name: string;
    coordinates?: { lat: number; lon: number };
  };
  weight: {
    gross: number;
    tare: number;
    cargo: number;
    unit: string;
  };
  seals: string[];
  temperature?: number;
  events: TrackingEvent[];
}

interface TrackingEvent {
  id: string;
  timestamp: string;
  event: string;
  location: string;
  description: string;
  status: "completed" | "current" | "upcoming";
  details?: Record<string, string>;
}

// Mock container data
const MOCK_CONTAINER: ContainerDetails = {
  containerNumber: "MSCU1234567",
  containerType: "Dry",
  containerSize: "40' HC",
  carrier: "Mediterranean Shipping Company",
  carrierCode: "MSC",
  bookingNumber: "MSC123456789",
  blNumber: "MSCUHAM123456",
  shipper: "ABC Trading Co.",
  consignee: "XYZ Imports Ltd.",
  origin: {
    port: "Shanghai",
    portCode: "CNSHA",
    country: "China",
  },
  destination: {
    port: "Rotterdam",
    portCode: "NLRTM",
    country: "Netherlands",
  },
  vessel: {
    name: "MSC OSCAR",
    imo: "9703318",
    mmsi: "353136000",
    voyage: "FA234E",
    flag: "Panama",
  },
  status: "in_transit",
  eta: "2025-01-15T08:00:00Z",
  etaConfidence: 92,
  currentLocation: {
    type: "at_sea",
    name: "Red Sea (Near Suez Canal)",
    coordinates: { lat: 28.9167, lon: 33.0667 },
  },
  weight: {
    gross: 28500,
    tare: 3750,
    cargo: 24750,
    unit: "kg",
  },
  seals: ["MSCSL12345", "MSCSL12346"],
  events: [
    {
      id: "1",
      timestamp: "2024-12-20T10:00:00Z",
      event: "Gate In",
      location: "Shanghai Yangshan Terminal",
      description: "Container arrived at origin terminal",
      status: "completed",
      details: { terminal: "Phase 4", gate: "Gate 12" },
    },
    {
      id: "2",
      timestamp: "2024-12-22T14:30:00Z",
      event: "Loaded on Vessel",
      location: "Shanghai Port",
      description: "Container loaded onto MSC OSCAR",
      status: "completed",
      details: { bayPosition: "Bay 42, Row 08, Tier 82" },
    },
    {
      id: "3",
      timestamp: "2024-12-22T22:00:00Z",
      event: "Vessel Departed",
      location: "Shanghai Port",
      description: "MSC OSCAR departed for Rotterdam",
      status: "completed",
    },
    {
      id: "4",
      timestamp: "2025-01-02T06:00:00Z",
      event: "Suez Canal Transit",
      location: "Suez Canal",
      description: "Vessel entered Suez Canal",
      status: "current",
    },
    {
      id: "5",
      timestamp: "2025-01-08T12:00:00Z",
      event: "Mediterranean Transit",
      location: "Mediterranean Sea",
      description: "Vessel transiting Mediterranean",
      status: "upcoming",
    },
    {
      id: "6",
      timestamp: "2025-01-15T08:00:00Z",
      event: "Arrival at Destination",
      location: "Rotterdam Europoort",
      description: "Expected arrival at Rotterdam",
      status: "upcoming",
      details: { terminal: "ECT Delta Terminal" },
    },
  ],
};

const getStatusBadge = (status: ContainerDetails["status"]) => {
  const statusConfig: Record<string, { label: string; color: string }> = {
    booked: { label: "Booked", color: "bg-slate-500/20 text-slate-400" },
    gate_in: { label: "At Origin Terminal", color: "bg-blue-500/20 text-blue-400" },
    loaded: { label: "Loaded", color: "bg-blue-500/20 text-blue-400" },
    in_transit: { label: "In Transit", color: "bg-emerald-500/20 text-emerald-400" },
    transshipment: { label: "Transshipment", color: "bg-amber-500/20 text-amber-400" },
    discharged: { label: "Discharged", color: "bg-purple-500/20 text-purple-400" },
    gate_out: { label: "Gate Out", color: "bg-indigo-500/20 text-indigo-400" },
    delivered: { label: "Delivered", color: "bg-green-500/20 text-green-400" },
  };
  const config = statusConfig[status] || statusConfig.booked;
  return <Badge className={`${config.color} border-current/30`}>{config.label}</Badge>;
};

export default function ContainerTrackPage() {
  const { containerId } = useParams<{ containerId: string }>();
  const { session } = useAuth();
  const { toast } = useToast();
  const [container, setContainer] = useState<ContainerDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("timeline");

  useEffect(() => {
    const fetchContainerData = async () => {
      if (!containerId) return;
      
      try {
        const response = await fetch(`${API_BASE}/tracking/container/${containerId}`, {
          headers: {
            "Authorization": `Bearer ${session?.access_token}`,
          },
          credentials: "include",
        });

        if (response.ok) {
          const data = await response.json();
          // Transform API response to local format
          const transformedData: ContainerDetails = {
            containerNumber: data.container_number,
            containerType: "Dry",
            containerSize: "40' HC",
            carrier: data.carrier || "Unknown Carrier",
            carrierCode: data.carrier_code || "UNKN",
            bookingNumber: data.booking_number || `BK${containerId?.slice(-8)}`,
            blNumber: data.bl_number || `BL${containerId?.slice(-8)}`,
            shipper: data.shipper || "Unknown Shipper",
            consignee: data.consignee || "Unknown Consignee",
            origin: {
              port: data.origin?.name || "Unknown",
              portCode: data.origin?.code || "UNKN",
              country: data.origin?.country || "",
            },
            destination: {
              port: data.destination?.name || "Unknown",
              portCode: data.destination?.code || "UNKN",
              country: data.destination?.country || "",
            },
            vessel: {
              name: data.vessel?.name || "Unknown Vessel",
              imo: data.vessel?.imo || "",
              mmsi: data.vessel?.mmsi || "",
              voyage: data.vessel?.voyage || "",
              flag: data.vessel?.flag || "",
            },
            status: data.status || "in_transit",
            eta: data.eta || new Date().toISOString(),
            etaConfidence: data.eta_confidence || 85,
            currentLocation: {
              type: data.position ? "at_sea" : "port",
              name: data.current_location || "Unknown",
              coordinates: data.position ? {
                lat: data.position.lat,
                lon: data.position.lon,
              } : undefined,
            },
            weight: {
              gross: 28500,
              tare: 3750,
              cargo: 24750,
              unit: "kg",
            },
            seals: data.seals || [],
            events: (data.events || []).map((e: any, idx: number) => ({
              id: String(idx),
              timestamp: e.timestamp,
              event: e.event,
              location: e.location,
              description: e.description,
              status: e.status,
              details: e.details,
            })),
          };
          
          // If no events from API, use default events
          if (transformedData.events.length === 0) {
            transformedData.events = MOCK_CONTAINER.events;
          }
          
          setContainer(transformedData);
        } else {
          // Fallback to mock data with the containerId
          console.warn("API returned error, using mock data");
          setContainer({ ...MOCK_CONTAINER, containerNumber: containerId || MOCK_CONTAINER.containerNumber });
        }
      } catch (error) {
        console.error("Failed to fetch container data:", error);
        // Fallback to mock data
        setContainer({ ...MOCK_CONTAINER, containerNumber: containerId || MOCK_CONTAINER.containerNumber });
      } finally {
        setLoading(false);
      }
    };

    fetchContainerData();
  }, [containerId, session?.access_token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading tracking data...</p>
        </div>
      </div>
    );
  }

  if (!container) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Container Not Found</h2>
          <p className="text-slate-400 mb-4">We couldn't find tracking data for this container.</p>
          <Button asChild>
            <Link to="/tracking">← Back to Tracker</Link>
          </Button>
        </div>
      </div>
    );
  }

  const completedEvents = container.events.filter((e) => e.status === "completed").length;
  const progress = Math.round((completedEvents / container.events.length) * 100);

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="bg-slate-900/80 border-b border-slate-800 sticky top-0 z-40 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/tracking" className="text-slate-400 hover:text-white flex items-center gap-1">
                <ArrowLeft className="w-4 h-4" />
                Back
              </Link>
              <Separator orientation="vertical" className="h-6" />
              <div className="flex items-center gap-2">
                <Container className="w-5 h-5 text-blue-400" />
                <span className="font-mono text-lg font-bold text-white">{container.containerNumber}</span>
                {getStatusBadge(container.status)}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                className="border-slate-700 text-slate-300"
                onClick={async () => {
                  try {
                    const response = await fetch(`${API_BASE}/tracking/alerts`, {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${session?.access_token}`,
                      },
                      credentials: "include",
                      body: JSON.stringify({
                        tracking_type: "container",
                        reference: container?.containerNumber,
                        alert_type: "arrival",
                        notify_email: true,
                        notify_sms: false,
                      }),
                    });
                    if (response.ok) {
                      toast({
                        title: "Alert Created",
                        description: "You'll be notified when this container arrives.",
                      });
                    } else {
                      throw new Error("Failed to create alert");
                    }
                  } catch (error) {
                    toast({
                      title: "Alert Creation Failed",
                      description: "Please try again later.",
                      variant: "destructive",
                    });
                  }
                }}
              >
                <Bell className="w-4 h-4 mr-1" />
                Set Alert
              </Button>
              <Button variant="outline" size="sm" className="border-slate-700 text-slate-300">
                <Share2 className="w-4 h-4 mr-1" />
                Share
              </Button>
              <Button variant="outline" size="sm" className="border-slate-700 text-slate-300">
                <Download className="w-4 h-4 mr-1" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Route Overview */}
        <Card className="bg-slate-900/50 border-slate-800 mb-6">
          <CardContent className="p-6">
            <div className="grid md:grid-cols-3 gap-6">
              {/* Origin */}
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Origin</p>
                <p className="text-lg font-semibold text-white">{container.origin.port}</p>
                <p className="text-sm text-slate-400">{container.origin.country} ({container.origin.portCode})</p>
              </div>

              {/* Journey Progress */}
              <div className="flex flex-col items-center justify-center">
                <div className="w-full mb-2">
                  <Progress value={progress} className="h-2 bg-slate-800" />
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Ship className="w-4 h-4 text-blue-400" />
                  <span className="text-white">{container.vessel.name}</span>
                  <span className="text-slate-500">({container.vessel.voyage})</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">{progress}% Complete</p>
              </div>

              {/* Destination */}
              <div className="text-right">
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Destination</p>
                <p className="text-lg font-semibold text-white">{container.destination.port}</p>
                <p className="text-sm text-slate-400">{container.destination.country} ({container.destination.portCode})</p>
              </div>
            </div>

            <Separator className="my-6 bg-slate-800" />

            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-800/50 rounded-lg p-4">
                <div className="flex items-center gap-2 text-slate-400 mb-1">
                  <Calendar className="w-4 h-4" />
                  <span className="text-xs uppercase">ETA</span>
                </div>
                <p className="text-lg font-semibold text-white">
                  {new Date(container.eta).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                </p>
                <p className="text-xs text-emerald-400">{container.etaConfidence}% confidence</p>
              </div>

              <div className="bg-slate-800/50 rounded-lg p-4">
                <div className="flex items-center gap-2 text-slate-400 mb-1">
                  <MapPin className="w-4 h-4" />
                  <span className="text-xs uppercase">Location</span>
                </div>
                <p className="text-lg font-semibold text-white truncate">{container.currentLocation.name}</p>
                <p className="text-xs text-slate-500">{container.currentLocation.type === "at_sea" ? "At Sea" : "In Port"}</p>
              </div>

              <div className="bg-slate-800/50 rounded-lg p-4">
                <div className="flex items-center gap-2 text-slate-400 mb-1">
                  <Box className="w-4 h-4" />
                  <span className="text-xs uppercase">Container</span>
                </div>
                <p className="text-lg font-semibold text-white">{container.containerSize}</p>
                <p className="text-xs text-slate-500">{container.containerType}</p>
              </div>

              <div className="bg-slate-800/50 rounded-lg p-4">
                <div className="flex items-center gap-2 text-slate-400 mb-1">
                  <Weight className="w-4 h-4" />
                  <span className="text-xs uppercase">Weight</span>
                </div>
                <p className="text-lg font-semibold text-white">{(container.weight.gross / 1000).toFixed(1)} t</p>
                <p className="text-xs text-slate-500">Gross weight</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tabs: Timeline, Details, Documents, Vessel */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-slate-800 border border-slate-700 mb-6">
            <TabsTrigger value="timeline" className="data-[state=active]:bg-blue-500/20">
              <Clock className="w-4 h-4 mr-1" />
              Timeline
            </TabsTrigger>
            <TabsTrigger value="details" className="data-[state=active]:bg-blue-500/20">
              <Package className="w-4 h-4 mr-1" />
              Details
            </TabsTrigger>
            <TabsTrigger value="vessel" className="data-[state=active]:bg-blue-500/20">
              <Ship className="w-4 h-4 mr-1" />
              Vessel
            </TabsTrigger>
            <TabsTrigger value="documents" className="data-[state=active]:bg-blue-500/20">
              <FileText className="w-4 h-4 mr-1" />
              Documents
            </TabsTrigger>
          </TabsList>

          {/* Timeline Tab */}
          <TabsContent value="timeline">
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white">Tracking Timeline</CardTitle>
                <CardDescription>Complete journey from origin to destination</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="relative">
                  {container.events.map((event, index) => (
                    <div key={event.id} className="flex gap-4 pb-8 last:pb-0">
                      {/* Timeline line & dot */}
                      <div className="relative flex flex-col items-center">
                        <div
                          className={`w-4 h-4 rounded-full border-2 z-10 ${
                            event.status === "completed"
                              ? "bg-emerald-500 border-emerald-500"
                              : event.status === "current"
                              ? "bg-blue-500 border-blue-500 animate-pulse"
                              : "bg-slate-800 border-slate-600"
                          }`}
                        />
                        {index < container.events.length - 1 && (
                          <div
                            className={`absolute top-4 w-0.5 h-full ${
                              event.status === "completed" ? "bg-emerald-500" : "bg-slate-700"
                            }`}
                          />
                        )}
                      </div>

                      {/* Event content */}
                      <div className="flex-1 pb-4">
                        <div className="flex items-center justify-between mb-1">
                          <h4 className={`font-semibold ${event.status === "upcoming" ? "text-slate-500" : "text-white"}`}>
                            {event.event}
                          </h4>
                          <span className="text-xs text-slate-500">
                            {new Date(event.timestamp).toLocaleDateString("en-US", {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                        <p className="text-sm text-slate-400 flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {event.location}
                        </p>
                        <p className="text-sm text-slate-500 mt-1">{event.description}</p>
                        {event.details && (
                          <div className="mt-2 bg-slate-800/50 rounded-lg p-3">
                            {Object.entries(event.details).map(([key, value]) => (
                              <div key={key} className="flex justify-between text-xs">
                                <span className="text-slate-500 capitalize">{key.replace(/([A-Z])/g, " $1").trim()}</span>
                                <span className="text-slate-300">{value}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Details Tab */}
          <TabsContent value="details">
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader>
                  <CardTitle className="text-white">Shipping Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Carrier</span>
                    <span className="text-white">{container.carrier}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Booking Number</span>
                    <span className="text-white font-mono">{container.bookingNumber}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">B/L Number</span>
                    <span className="text-white font-mono">{container.blNumber}</span>
                  </div>
                  <Separator className="bg-slate-800" />
                  <div className="flex justify-between">
                    <span className="text-slate-400">Shipper</span>
                    <span className="text-white">{container.shipper}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Consignee</span>
                    <span className="text-white">{container.consignee}</span>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader>
                  <CardTitle className="text-white">Container Specifications</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Size & Type</span>
                    <span className="text-white">{container.containerSize} {container.containerType}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Gross Weight</span>
                    <span className="text-white">{(container.weight.gross / 1000).toFixed(2)} tonnes</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Cargo Weight</span>
                    <span className="text-white">{(container.weight.cargo / 1000).toFixed(2)} tonnes</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Tare Weight</span>
                    <span className="text-white">{(container.weight.tare / 1000).toFixed(2)} tonnes</span>
                  </div>
                  <Separator className="bg-slate-800" />
                  <div className="flex justify-between">
                    <span className="text-slate-400">Seal Numbers</span>
                    <span className="text-white font-mono">{container.seals.join(", ")}</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Vessel Tab */}
          <TabsContent value="vessel">
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Ship className="w-5 h-5 text-blue-400" />
                  {container.vessel.name}
                </CardTitle>
                <CardDescription>Current carrying vessel</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <span className="text-slate-400">IMO Number</span>
                      <span className="text-white font-mono">{container.vessel.imo}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">MMSI</span>
                      <span className="text-white font-mono">{container.vessel.mmsi}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Voyage</span>
                      <span className="text-white">{container.vessel.voyage}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Flag</span>
                      <span className="text-white">{container.vessel.flag}</span>
                    </div>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-4 flex items-center justify-center">
                    <div className="text-center">
                      <Navigation className="w-12 h-12 text-blue-400 mx-auto mb-2" />
                      <p className="text-slate-400 text-sm">Live Position</p>
                      <p className="text-white font-mono text-sm">
                        {container.currentLocation.coordinates?.lat.toFixed(4)}°N, {container.currentLocation.coordinates?.lon.toFixed(4)}°E
                      </p>
                      <Button variant="outline" size="sm" className="mt-4 border-slate-600">
                        View on Map
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Documents Tab */}
          <TabsContent value="documents">
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white">Documents</CardTitle>
                <CardDescription>Shipping documentation status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    { name: "Bill of Lading", status: "released", date: "Dec 22, 2024" },
                    { name: "Commercial Invoice", status: "uploaded", date: "Dec 20, 2024" },
                    { name: "Packing List", status: "uploaded", date: "Dec 20, 2024" },
                    { name: "Certificate of Origin", status: "pending", date: null },
                    { name: "Customs Declaration", status: "pending", date: null },
                  ].map((doc, idx) => (
                    <div key={idx} className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-slate-400" />
                        <div>
                          <p className="text-white">{doc.name}</p>
                          {doc.date && <p className="text-xs text-slate-500">{doc.date}</p>}
                        </div>
                      </div>
                      <Badge
                        className={
                          doc.status === "released"
                            ? "bg-emerald-500/20 text-emerald-400"
                            : doc.status === "uploaded"
                            ? "bg-blue-500/20 text-blue-400"
                            : "bg-slate-500/20 text-slate-400"
                        }
                      >
                        {doc.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}


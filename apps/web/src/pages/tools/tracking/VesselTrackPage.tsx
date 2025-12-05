/**
 * Vessel Tracking Detail Page
 * 
 * Shows detailed information about a specific vessel.
 * Features:
 * - Current position
 * - Route & schedule
 * - Vessel specifications
 * - Port calls
 */

import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Ship,
  ArrowLeft,
  MapPin,
  Clock,
  Calendar,
  Anchor,
  Navigation,
  Gauge,
  Ruler,
  Flag,
  AlertTriangle,
  RefreshCw,
  Share2,
  Bell,
  ChevronRight,
  Waves,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/components/ui/use-toast";
import { VesselSanctionsCard } from "@/components/tracking";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface VesselDetails {
  name: string;
  imo: string;
  mmsi: string;
  callSign: string;
  flag: string;
  type: string;
  status: "underway" | "at_anchor" | "moored" | "not_available";
  position: {
    lat: number;
    lon: number;
    heading: number;
    course: number;
    speed: number;
    timestamp: string;
  };
  dimensions: {
    length: number;
    beam: number;
    draught: number;
  };
  capacity: {
    teu: number;
    deadweight: number;
    grossTonnage: number;
  };
  owner: string;
  operator: string;
  built: number;
  currentVoyage: {
    voyage: string;
    origin: string;
    destination: string;
    eta: string;
    departureTime?: string;
  };
  schedule: PortCall[];
}

interface PortCall {
  port: string;
  portCode: string;
  country: string;
  arrival: string;
  departure?: string;
  status: "completed" | "current" | "scheduled";
  terminal?: string;
}

// Mock vessel data
const MOCK_VESSEL: VesselDetails = {
  name: "MSC OSCAR",
  imo: "9703318",
  mmsi: "353136000",
  callSign: "3FQM9",
  flag: "Panama",
  type: "Container Ship",
  status: "underway",
  position: {
    lat: 28.9167,
    lon: 33.0667,
    heading: 315,
    course: 312,
    speed: 18.5,
    timestamp: "2025-01-02T14:30:00Z",
  },
  dimensions: {
    length: 395.4,
    beam: 59,
    draught: 16,
  },
  capacity: {
    teu: 19224,
    deadweight: 197362,
    grossTonnage: 193489,
  },
  owner: "Mediterranean Shipping Company",
  operator: "MSC Mediterranean Shipping Company",
  built: 2015,
  currentVoyage: {
    voyage: "FA234E",
    origin: "Shanghai, CN",
    destination: "Rotterdam, NL",
    eta: "2025-01-15T08:00:00Z",
    departureTime: "2024-12-22T22:00:00Z",
  },
  schedule: [
    {
      port: "Shanghai",
      portCode: "CNSHA",
      country: "China",
      arrival: "2024-12-20T06:00:00Z",
      departure: "2024-12-22T22:00:00Z",
      status: "completed",
      terminal: "Yangshan Phase 4",
    },
    {
      port: "Ningbo",
      portCode: "CNNGB",
      country: "China",
      arrival: "2024-12-23T14:00:00Z",
      departure: "2024-12-24T20:00:00Z",
      status: "completed",
      terminal: "Beilun Terminal",
    },
    {
      port: "Singapore",
      portCode: "SGSIN",
      country: "Singapore",
      arrival: "2024-12-30T08:00:00Z",
      departure: "2024-12-31T16:00:00Z",
      status: "completed",
      terminal: "PSA Terminal",
    },
    {
      port: "Port Said",
      portCode: "EGPSD",
      country: "Egypt",
      arrival: "2025-01-08T04:00:00Z",
      departure: "2025-01-08T18:00:00Z",
      status: "scheduled",
      terminal: "Suez Canal Transit",
    },
    {
      port: "Rotterdam",
      portCode: "NLRTM",
      country: "Netherlands",
      arrival: "2025-01-15T08:00:00Z",
      status: "scheduled",
      terminal: "ECT Delta Terminal",
    },
    {
      port: "Hamburg",
      portCode: "DEHAM",
      country: "Germany",
      arrival: "2025-01-17T06:00:00Z",
      status: "scheduled",
      terminal: "HHLA CTB",
    },
  ],
};

const getStatusBadge = (status: VesselDetails["status"]) => {
  const statusConfig: Record<string, { label: string; color: string }> = {
    underway: { label: "Underway", color: "bg-emerald-500/20 text-emerald-400" },
    at_anchor: { label: "At Anchor", color: "bg-amber-500/20 text-amber-400" },
    moored: { label: "Moored", color: "bg-blue-500/20 text-blue-400" },
    not_available: { label: "N/A", color: "bg-slate-500/20 text-slate-400" },
  };
  const config = statusConfig[status] || statusConfig.not_available;
  return <Badge className={`${config.color} border-current/30`}>{config.label}</Badge>;
};

export default function VesselTrackPage() {
  const { vesselId } = useParams<{ vesselId: string }>();
  const { user } = useAuth();
  const { toast } = useToast();
  const [vessel, setVessel] = useState<VesselDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("position");

  useEffect(() => {
    const fetchVesselData = async () => {
      if (!vesselId) return;
      
      try {
        // Try IMO first, then name
        const searchType = /^IMO\d+$/.test(vesselId) ? "imo" : /^\d{9}$/.test(vesselId) ? "mmsi" : "name";
        const response = await fetch(`${API_BASE}/tracking/vessel/${vesselId}?search_type=${searchType}`, {
          credentials: "include",
        });

        if (response.ok) {
          const data = await response.json();
          // Transform API response to local format
          const transformedData: VesselDetails = {
            name: data.name,
            imo: data.imo || vesselId,
            mmsi: data.mmsi || "",
            callSign: data.call_sign || "",
            flag: data.flag || "Unknown",
            type: data.vessel_type || "Container Ship",
            status: data.status || "underway",
            position: {
              lat: data.position?.lat || 0,
              lon: data.position?.lon || 0,
              heading: data.position?.heading || data.heading || 0,
              course: data.position?.course || data.course || 0,
              speed: data.position?.speed || data.speed || 0,
              timestamp: data.position?.timestamp || data.last_update,
            },
            dimensions: data.dimensions || {
              length: 0,
              beam: 0,
              draught: 0,
            },
            capacity: {
              teu: 0,
              deadweight: 0,
              grossTonnage: 0,
            },
            owner: "Unknown",
            operator: "Unknown",
            built: 0,
            currentVoyage: {
              voyage: "",
              origin: "",
              destination: data.destination || "Unknown",
              eta: data.eta || "",
            },
            schedule: [],
          };
          
          setVessel(transformedData);
        } else {
          // Fallback to mock data
          console.warn("API returned error, using mock data");
          setVessel({ ...MOCK_VESSEL, imo: vesselId, name: vesselId });
        }
      } catch (error) {
        console.error("Failed to fetch vessel data:", error);
        // Fallback to mock data
        setVessel({ ...MOCK_VESSEL, imo: vesselId, name: vesselId });
      } finally {
        setLoading(false);
      }
    };

    fetchVesselData();
  }, [vesselId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading vessel data...</p>
        </div>
      </div>
    );
  }

  if (!vessel) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Vessel Not Found</h2>
          <p className="text-slate-400 mb-4">We couldn't find data for this vessel.</p>
          <Button asChild>
            <Link to="/tracking">← Back to Tracker</Link>
          </Button>
        </div>
      </div>
    );
  }

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
                <Ship className="w-5 h-5 text-blue-400" />
                <span className="text-lg font-bold text-white">{vessel.name}</span>
                {getStatusBadge(vessel.status)}
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
                      },
                      credentials: "include",
                      body: JSON.stringify({
                        tracking_type: "vessel",
                        reference: vessel?.imo || vessel?.name,
                        alert_type: "arrival",
                        notify_email: true,
                        notify_sms: false,
                      }),
                    });
                    if (response.ok) {
                      toast({
                        title: "Alert Created",
                        description: "You'll be notified when this vessel arrives.",
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
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-4 text-center">
              <Navigation className="w-6 h-6 text-blue-400 mx-auto mb-2" />
              <p className="text-xs text-slate-500 uppercase">Heading</p>
              <p className="text-lg font-bold text-white">{vessel.position.heading}°</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-4 text-center">
              <Gauge className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
              <p className="text-xs text-slate-500 uppercase">Speed</p>
              <p className="text-lg font-bold text-white">{vessel.position.speed} kn</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-4 text-center">
              <MapPin className="w-6 h-6 text-amber-400 mx-auto mb-2" />
              <p className="text-xs text-slate-500 uppercase">Position</p>
              <p className="text-sm font-mono text-white">
                {vessel.position.lat.toFixed(2)}°, {vessel.position.lon.toFixed(2)}°
              </p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-4 text-center">
              <Anchor className="w-6 h-6 text-purple-400 mx-auto mb-2" />
              <p className="text-xs text-slate-500 uppercase">Next Port</p>
              <p className="text-lg font-bold text-white">{vessel.schedule.find(s => s.status === "scheduled")?.port || "N/A"}</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-4 text-center">
              <Calendar className="w-6 h-6 text-indigo-400 mx-auto mb-2" />
              <p className="text-xs text-slate-500 uppercase">ETA</p>
              <p className="text-lg font-bold text-white">
                {new Date(vessel.currentVoyage.eta).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Current Voyage */}
        <Card className="bg-slate-900/50 border-slate-800 mb-8">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Waves className="w-5 h-5 text-blue-400" />
              Current Voyage: {vessel.currentVoyage.voyage}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500 uppercase">Origin</p>
                <p className="text-lg font-semibold text-white">{vessel.currentVoyage.origin}</p>
                {vessel.currentVoyage.departureTime && (
                  <p className="text-sm text-slate-500">
                    Departed {new Date(vessel.currentVoyage.departureTime).toLocaleDateString()}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-4">
                <div className="h-0.5 w-32 bg-gradient-to-r from-emerald-500 to-blue-500" />
                <Ship className="w-6 h-6 text-blue-400" />
                <div className="h-0.5 w-32 bg-gradient-to-r from-blue-500 to-slate-600" />
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-500 uppercase">Destination</p>
                <p className="text-lg font-semibold text-white">{vessel.currentVoyage.destination}</p>
                <p className="text-sm text-slate-500">
                  ETA {new Date(vessel.currentVoyage.eta).toLocaleDateString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-slate-800 border border-slate-700 mb-6">
            <TabsTrigger value="position" className="data-[state=active]:bg-blue-500/20">
              <MapPin className="w-4 h-4 mr-1" />
              Position
            </TabsTrigger>
            <TabsTrigger value="schedule" className="data-[state=active]:bg-blue-500/20">
              <Calendar className="w-4 h-4 mr-1" />
              Schedule
            </TabsTrigger>
            <TabsTrigger value="specs" className="data-[state=active]:bg-blue-500/20">
              <Ruler className="w-4 h-4 mr-1" />
              Specifications
            </TabsTrigger>
            <TabsTrigger value="compliance" className="data-[state=active]:bg-emerald-500/20">
              <Shield className="w-4 h-4 mr-1" />
              Compliance
            </TabsTrigger>
          </TabsList>

          {/* Position Tab */}
          <TabsContent value="position">
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader>
                  <CardTitle className="text-white">Current Position</CardTitle>
                  <CardDescription>
                    Last update: {new Date(vessel.position.timestamp).toLocaleString()}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Latitude</span>
                    <span className="text-white font-mono">{vessel.position.lat.toFixed(4)}° N</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Longitude</span>
                    <span className="text-white font-mono">{vessel.position.lon.toFixed(4)}° E</span>
                  </div>
                  <Separator className="bg-slate-800" />
                  <div className="flex justify-between">
                    <span className="text-slate-400">Heading</span>
                    <span className="text-white">{vessel.position.heading}°</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Course</span>
                    <span className="text-white">{vessel.position.course}°</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Speed</span>
                    <span className="text-white">{vessel.position.speed} knots</span>
                  </div>
                </CardContent>
              </Card>

              {/* Map placeholder */}
              <Card className="bg-slate-900/50 border-slate-800">
                <CardContent className="p-0 h-[300px] flex items-center justify-center bg-slate-800/50 rounded-lg">
                  <div className="text-center">
                    <MapPin className="w-12 h-12 text-blue-400 mx-auto mb-3" />
                    <p className="text-slate-400">Live Map View</p>
                    <p className="text-xs text-slate-500 mt-1">Red Sea (Near Suez Canal)</p>
                    <Button variant="outline" size="sm" className="mt-4 border-slate-600">
                      Open Full Map
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Schedule Tab */}
          <TabsContent value="schedule">
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white">Port Schedule</CardTitle>
                <CardDescription>Voyage {vessel.currentVoyage.voyage} port calls</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {vessel.schedule.map((port, index) => (
                    <div
                      key={index}
                      className={`flex items-center gap-4 p-4 rounded-lg ${
                        port.status === "current" ? "bg-blue-500/10 border border-blue-500/30" :
                        port.status === "completed" ? "bg-slate-800/50" : "bg-slate-800/30"
                      }`}
                    >
                      <div className="flex-shrink-0">
                        <Anchor className={`w-5 h-5 ${
                          port.status === "completed" ? "text-emerald-400" :
                          port.status === "current" ? "text-blue-400" : "text-slate-500"
                        }`} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-semibold text-white">{port.port}</p>
                          <span className="text-xs text-slate-500">({port.portCode})</span>
                          <Badge
                            className={
                              port.status === "completed" ? "bg-emerald-500/20 text-emerald-400" :
                              port.status === "current" ? "bg-blue-500/20 text-blue-400" :
                              "bg-slate-500/20 text-slate-400"
                            }
                          >
                            {port.status}
                          </Badge>
                        </div>
                        <p className="text-sm text-slate-500">{port.terminal || port.country}</p>
                      </div>
                      <div className="text-right text-sm">
                        <p className="text-white">
                          {new Date(port.arrival).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                        {port.departure && (
                          <p className="text-slate-500">
                            → {new Date(port.departure).toLocaleTimeString("en-US", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Specifications Tab */}
          <TabsContent value="specs">
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader>
                  <CardTitle className="text-white">Vessel Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-slate-400">IMO Number</span>
                    <span className="text-white font-mono">{vessel.imo}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">MMSI</span>
                    <span className="text-white font-mono">{vessel.mmsi}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Call Sign</span>
                    <span className="text-white font-mono">{vessel.callSign}</span>
                  </div>
                  <Separator className="bg-slate-800" />
                  <div className="flex justify-between">
                    <span className="text-slate-400">Type</span>
                    <span className="text-white">{vessel.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Flag</span>
                    <span className="text-white flex items-center gap-1">
                      <Flag className="w-4 h-4" />
                      {vessel.flag}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Built</span>
                    <span className="text-white">{vessel.built}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Owner</span>
                    <span className="text-white">{vessel.owner}</span>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader>
                  <CardTitle className="text-white">Dimensions & Capacity</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Length</span>
                    <span className="text-white">{vessel.dimensions.length} m</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Beam</span>
                    <span className="text-white">{vessel.dimensions.beam} m</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Draught</span>
                    <span className="text-white">{vessel.dimensions.draught} m</span>
                  </div>
                  <Separator className="bg-slate-800" />
                  <div className="flex justify-between">
                    <span className="text-slate-400">TEU Capacity</span>
                    <span className="text-white">{vessel.capacity.teu.toLocaleString()} TEU</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Deadweight</span>
                    <span className="text-white">{vessel.capacity.deadweight.toLocaleString()} DWT</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Gross Tonnage</span>
                    <span className="text-white">{vessel.capacity.grossTonnage.toLocaleString()} GT</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Compliance Tab */}
          <TabsContent value="compliance">
            <div className="grid md:grid-cols-2 gap-6">
              <VesselSanctionsCard
                vesselName={vessel.name}
                imo={vessel.imo}
                mmsi={vessel.mmsi}
                flagState={vessel.flag}
                className="bg-slate-900/50 border-slate-800"
              />
              
              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Shield className="w-5 h-5 text-emerald-400" />
                    Compliance Overview
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                    <h4 className="font-medium text-emerald-400 mb-2">What We Check</h4>
                    <ul className="text-sm text-slate-400 space-y-2">
                      <li className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-emerald-500 rounded-full" />
                        OFAC SDN List (US Treasury)
                      </li>
                      <li className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-emerald-500 rounded-full" />
                        EU Consolidated Sanctions
                      </li>
                      <li className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-emerald-500 rounded-full" />
                        UN Security Council Sanctions
                      </li>
                      <li className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-emerald-500 rounded-full" />
                        Flag State Risk Assessment
                      </li>
                    </ul>
                  </div>
                  
                  <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                    <h4 className="font-medium text-blue-400 mb-2">Why It Matters</h4>
                    <p className="text-sm text-slate-400">
                      Banks and trade finance institutions require sanctions screening 
                      before processing Letters of Credit. Our automated screening helps 
                      you stay compliant with international regulations.
                    </p>
                  </div>
                  
                  <div className="text-xs text-slate-500">
                    <p>Data sources updated daily from official government databases.</p>
                    <p className="mt-1">This is a screening tool - always consult compliance for final decisions.</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}


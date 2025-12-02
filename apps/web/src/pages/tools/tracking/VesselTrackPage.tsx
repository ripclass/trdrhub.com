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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";

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
  const [vessel, setVessel] = useState<VesselDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("position");

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setVessel(MOCK_VESSEL);
      setLoading(false);
    }, 500);
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
              <Button variant="outline" size="sm" className="border-slate-700 text-slate-300">
                <Bell className="w-4 h-4 mr-1" />
                Track
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
        </Tabs>
      </main>
    </div>
  );
}


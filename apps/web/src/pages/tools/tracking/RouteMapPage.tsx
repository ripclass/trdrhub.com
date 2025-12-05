/**
 * Route Map Page
 * 
 * Interactive map showing shipment locations using Leaflet.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  MapPin,
  ExternalLink,
  Ship,
  Container,
  Globe,
  Navigation,
  Anchor,
  RefreshCw,
  Maximize2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";
import TrackingMap, { ShipmentLocation, PortLocation, RouteData } from "@/components/tracking/TrackingMap";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

// External map providers
const MAP_PROVIDERS = [
  {
    name: "MarineTraffic",
    description: "Live ship tracking with AIS data",
    url: "https://www.marinetraffic.com/en/ais/home",
    icon: Ship,
    color: "text-blue-500",
  },
  {
    name: "VesselFinder",
    description: "Real-time vessel positions worldwide",
    url: "https://www.vesselfinder.com/",
    icon: Globe,
    color: "text-emerald-500",
  },
  {
    name: "Container Tracker",
    description: "Track your container on carrier websites",
    url: "https://www.track-trace.com/container",
    icon: Container,
    color: "text-amber-500",
  },
];

// Sample port coordinates
const SAMPLE_PORTS: PortLocation[] = [
  { name: "Shanghai", code: "CNSHA", latitude: 31.2304, longitude: 121.4737, type: "origin" },
  { name: "Singapore", code: "SGSIN", latitude: 1.3521, longitude: 103.8198, type: "waypoint" },
  { name: "Rotterdam", code: "NLRTM", latitude: 51.9225, longitude: 4.4792, type: "destination" },
  { name: "Hamburg", code: "DEHAM", latitude: 53.5511, longitude: 9.9937, type: "destination" },
  { name: "Los Angeles", code: "USLAX", latitude: 33.7405, longitude: -118.2674, type: "destination" },
  { name: "Chittagong", code: "BDCGP", latitude: 22.3569, longitude: 91.7832, type: "origin" },
];

// Sample route (Shanghai to Rotterdam via Singapore/Suez)
const SAMPLE_ROUTE: RouteData = {
  coordinates: [
    [31.2304, 121.4737], // Shanghai
    [22.3, 114.2], // South China Sea
    [1.3521, 103.8198], // Singapore
    [10.5, 80], // Indian Ocean
    [12.8, 43.3], // Gulf of Aden
    [30.0, 32.5], // Suez Canal
    [35.5, 25], // Mediterranean
    [36, 5], // Gibraltar
    [48, -5], // Bay of Biscay
    [51.9225, 4.4792], // Rotterdam
  ],
  color: "#3b82f6",
};

export default function RouteMapPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [shipments, setShipments] = useState<ShipmentLocation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const fetchLocations = async () => {
      try {
        const response = await fetch(`${API_BASE}/tracking/portfolio?limit=50`, {
          credentials: "include",
        });
        if (response.ok) {
          const data = await response.json();
          // Transform to map format and add sample coordinates for demo
          const transformed: ShipmentLocation[] = (data.shipments || []).map((s: any, idx: number) => ({
            id: s.id,
            reference: s.reference,
            type: s.tracking_type || "container",
            status: s.status || "in_transit",
            // Use real coords if available, or generate demo coords
            latitude: s.latitude || (30 + (idx * 5) % 30),
            longitude: s.longitude || (50 + (idx * 20) % 100),
            vessel_name: s.vessel_name,
            carrier: s.carrier,
            origin: s.origin_port,
            destination: s.destination_port,
            eta: s.eta,
            progress: s.progress,
          }));
          setShipments(transformed);
        }
      } catch (error) {
        console.error("Failed to fetch locations:", error);
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      fetchLocations();
    } else {
      // Show demo data for non-logged-in users
      setShipments([
        {
          id: "demo-1",
          reference: "MSCU1234567",
          type: "container",
          status: "in_transit",
          latitude: 28.5,
          longitude: 55,
          vessel_name: "MSC OSCAR",
          carrier: "MSC",
          origin: "Shanghai, CN",
          destination: "Rotterdam, NL",
          eta: "2025-01-15",
          progress: 65,
        },
        {
          id: "demo-2",
          reference: "MAEU987654321",
          type: "container",
          status: "delayed",
          latitude: 30.5,
          longitude: 32.5,
          vessel_name: "MAERSK EDMONTON",
          carrier: "Maersk",
          origin: "Chittagong, BD",
          destination: "Hamburg, DE",
          eta: "2025-01-18",
          progress: 55,
        },
        {
          id: "demo-3",
          reference: "HLCU5678901",
          type: "container",
          status: "at_port",
          latitude: 1.35,
          longitude: 103.82,
          vessel_name: "BERLIN EXPRESS",
          carrier: "Hapag-Lloyd",
          origin: "Mumbai, IN",
          destination: "Los Angeles, US",
          eta: "2025-01-12",
          progress: 42,
        },
      ]);
      setIsLoading(false);
    }
  }, [user]);

  const handleShipmentClick = (shipment: ShipmentLocation) => {
    navigate(`/tracking/dashboard/${shipment.type}/${shipment.reference}`);
  };

  const handleRefresh = () => {
    setIsLoading(true);
    // Re-fetch
    setTimeout(() => setIsLoading(false), 1000);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Route Map</h1>
          <p className="text-muted-foreground">
            Visualize your shipment locations and routes
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button variant="outline" onClick={() => setIsFullscreen(!isFullscreen)}>
            <Maximize2 className="w-4 h-4 mr-2" />
            {isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
          </Button>
        </div>
      </div>

      {/* Interactive Map */}
      <Card className="overflow-hidden">
        <TrackingMap
          shipments={shipments}
          ports={SAMPLE_PORTS}
          routes={[SAMPLE_ROUTE]}
          onShipmentClick={handleShipmentClick}
          height={isFullscreen ? "calc(100vh - 200px)" : 500}
        />
      </Card>

      {/* Active Shipment Locations */}
      {shipments.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Your Shipment Locations</CardTitle>
            <CardDescription>
              {shipments.length} shipments on map • Click markers to view details
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {shipments.slice(0, 6).map((shipment) => (
                <div
                  key={shipment.id}
                  onClick={() => handleShipmentClick(shipment)}
                  className="p-4 rounded-lg border bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 bg-blue-500/10 rounded-lg flex items-center justify-center">
                      {shipment.type === "container" ? (
                        <Container className="w-4 h-4 text-blue-500" />
                      ) : (
                        <Ship className="w-4 h-4 text-blue-500" />
                      )}
                    </div>
                    <div>
                      <p className="font-mono font-medium text-sm">{shipment.reference}</p>
                      <p className="text-xs text-muted-foreground">
                        {shipment.vessel_name || shipment.carrier || "Tracking..."}
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    📍 {shipment.latitude.toFixed(2)}°, {shipment.longitude.toFixed(2)}°
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* External Map Links */}
      <div className="grid md:grid-cols-3 gap-4">
        {MAP_PROVIDERS.map((provider) => {
          const Icon = provider.icon;
          return (
            <Card key={provider.name} className="hover:bg-muted/50 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-muted rounded-lg flex items-center justify-center">
                    <Icon className={`w-6 h-6 ${provider.color}`} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium mb-1">{provider.name}</h3>
                    <p className="text-sm text-muted-foreground mb-3">
                      {provider.description}
                    </p>
                    <Button variant="outline" size="sm" asChild>
                      <a
                        href={provider.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="w-4 h-4 mr-2" />
                        Open Map
                      </a>
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}


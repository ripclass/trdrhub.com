/**
 * Route Map Page
 * 
 * Interactive map showing shipment locations.
 * Links to external tracking maps until we have our own.
 */

import { useState, useEffect } from "react";
import {
  MapPin,
  ExternalLink,
  Ship,
  Container,
  Globe,
  Navigation,
  Anchor,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface ShipmentLocation {
  reference: string;
  type: string;
  latitude?: number;
  longitude?: number;
  current_location?: string;
  status?: string;
}

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

export default function RouteMapPage() {
  const { user } = useAuth();
  const [locations, setLocations] = useState<ShipmentLocation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchLocations = async () => {
      try {
        const response = await fetch(`${API_BASE}/tracking/portfolio?limit=50`, {
          credentials: "include",
        });
        if (response.ok) {
          const data = await response.json();
          setLocations(data.shipments || []);
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
      setIsLoading(false);
    }
  }, [user]);

  const shipmentsWithLocation = locations.filter(
    (s) => s.latitude && s.longitude
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Route Map</h1>
        <p className="text-muted-foreground">
          Visualize your shipment locations and routes
        </p>
      </div>

      {/* Map Placeholder */}
      <Card className="overflow-hidden">
        <div className="relative h-[400px] bg-gradient-to-b from-slate-900 to-slate-800 flex items-center justify-center">
          {/* Grid overlay */}
          <div 
            className="absolute inset-0 opacity-10"
            style={{
              backgroundImage: `
                linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
              `,
              backgroundSize: "50px 50px",
            }}
          />
          
          {/* Globe visualization */}
          <div className="relative z-10 text-center">
            <div className="w-32 h-32 mx-auto mb-4 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center">
              <Globe className="w-16 h-16 text-blue-500/50" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              Interactive Map Coming Soon
            </h3>
            <p className="text-slate-400 mb-4 max-w-md">
              We're building an interactive map to visualize all your shipments.
              In the meantime, use the links below to track vessels and containers.
            </p>
            <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">
              Expected Q1 2025
            </Badge>
          </div>

          {/* Mock location dots */}
          <div className="absolute top-1/4 left-1/4 w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
          <div className="absolute top-1/3 right-1/3 w-3 h-3 bg-emerald-500 rounded-full animate-pulse delay-100" />
          <div className="absolute bottom-1/3 left-1/2 w-3 h-3 bg-amber-500 rounded-full animate-pulse delay-200" />
        </div>
      </Card>

      {/* Active Shipment Locations */}
      {locations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Your Shipment Locations</CardTitle>
            <CardDescription>
              {locations.length} shipments tracked • Click to view on carrier site
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {locations.slice(0, 6).map((shipment) => (
                <div
                  key={shipment.reference}
                  className="p-4 rounded-lg border bg-muted/30 hover:bg-muted/50 transition-colors"
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
                        {shipment.current_location || "Location updating..."}
                      </p>
                    </div>
                  </div>
                  {shipment.latitude && shipment.longitude && (
                    <p className="text-xs text-muted-foreground">
                      📍 {shipment.latitude.toFixed(4)}, {shipment.longitude.toFixed(4)}
                    </p>
                  )}
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


/**
 * Tracking Placeholder Page
 * 
 * Shown for tracking features that are coming soon.
 */

import { useLocation } from "react-router-dom";
import { 
  Ship, 
  MapPin, 
  Anchor, 
  Bell, 
  AlertTriangle, 
  History, 
  BarChart3, 
  Clock, 
  Settings, 
  HelpCircle,
  Container,
  Construction,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

// Map routes to their feature info
const featureInfo: Record<string, { title: string; description: string; icon: any; eta?: string }> = {
  "/tracking/dashboard/search": {
    title: "Track Container",
    description: "Search and track any container by number, B/L, or booking reference across 100+ carriers.",
    icon: Container,
  },
  "/tracking/dashboard/vessel-search": {
    title: "Track Vessel",
    description: "Search vessels by name, IMO, or MMSI and get real-time position, schedule, and voyage details.",
    icon: Ship,
  },
  "/tracking/dashboard/active": {
    title: "Active Shipments",
    description: "View all your tracked shipments in one place with real-time status updates.",
    icon: Ship,
    eta: "Coming Q1 2025",
  },
  "/tracking/dashboard/map": {
    title: "Route Map",
    description: "Interactive map showing your shipments' locations and routes in real-time.",
    icon: MapPin,
    eta: "Coming Q1 2025",
  },
  "/tracking/dashboard/ports": {
    title: "Port Schedule",
    description: "View vessel schedules and port congestion data for major ports worldwide.",
    icon: Anchor,
    eta: "Coming Q1 2025",
  },
  "/tracking/dashboard/alerts": {
    title: "Alerts",
    description: "Configure and manage alerts for delays, arrivals, departures, and custom milestones.",
    icon: Bell,
    eta: "Coming Q1 2025",
  },
  "/tracking/dashboard/exceptions": {
    title: "Exceptions",
    description: "View and manage shipment exceptions, holds, and issues requiring attention.",
    icon: AlertTriangle,
    eta: "Coming Q1 2025",
  },
  "/tracking/dashboard/history": {
    title: "History",
    description: "Access your complete tracking history with search and filtering capabilities.",
    icon: History,
    eta: "Coming Q1 2025",
  },
  "/tracking/dashboard/analytics": {
    title: "Analytics",
    description: "Carrier performance metrics, transit time analysis, and delay patterns.",
    icon: BarChart3,
    eta: "Coming Q1 2025",
  },
  "/tracking/dashboard/performance": {
    title: "Performance",
    description: "Track on-time delivery rates, carrier scorecards, and optimization insights.",
    icon: Clock,
    eta: "Coming Q1 2025",
  },
  "/tracking/dashboard/settings": {
    title: "Settings",
    description: "Configure your tracking preferences, alert channels, and API integrations.",
    icon: Settings,
    eta: "Coming Q1 2025",
  },
  "/tracking/dashboard/help": {
    title: "Help & Support",
    description: "Documentation, FAQs, and contact support for tracking-related questions.",
    icon: HelpCircle,
  },
};

export default function TrackingPlaceholder() {
  const location = useLocation();
  const feature = featureInfo[location.pathname] || {
    title: "Feature",
    description: "This feature is being developed.",
    icon: Construction,
    eta: "Coming Soon",
  };
  
  const Icon = feature.icon;

  return (
    <div className="p-6 flex items-center justify-center min-h-[60vh]">
      <Card className="max-w-lg w-full text-center">
        <CardHeader>
          <div className="mx-auto w-16 h-16 bg-blue-500/10 rounded-2xl flex items-center justify-center mb-4">
            <Icon className="w-8 h-8 text-blue-500" />
          </div>
          <CardTitle className="text-2xl">{feature.title}</CardTitle>
          <CardDescription className="text-base mt-2">
            {feature.description}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {feature.eta && (
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500/10 border border-amber-500/20 rounded-full">
              <Construction className="w-4 h-4 text-amber-500" />
              <span className="text-amber-600 dark:text-amber-400 text-sm font-medium">{feature.eta}</span>
            </div>
          )}
          
          <div className="pt-4">
            <Button asChild>
              <Link to="/tracking/dashboard">
                ← Back to Overview
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


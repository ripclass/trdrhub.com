/**
 * Port Schedule Page
 * 
 * View port schedules and vessel arrivals.
 */

import { useState } from "react";
import {
  Anchor,
  Search,
  ExternalLink,
  Ship,
  Clock,
  Calendar,
  MapPin,
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

// Major ports with external links
const MAJOR_PORTS = [
  {
    name: "Rotterdam",
    country: "Netherlands",
    code: "NLRTM",
    url: "https://www.portofrotterdam.com/en/shipping/schedule-and-planning",
    vessels: 234,
    avgWait: "4h",
  },
  {
    name: "Singapore",
    country: "Singapore",
    code: "SGSIN",
    url: "https://www.mpa.gov.sg/web/portal/home/maritime-singapore/port-operations",
    vessels: 312,
    avgWait: "6h",
  },
  {
    name: "Shanghai",
    country: "China",
    code: "CNSHA",
    url: "https://www.portshanghai.com.cn/en/",
    vessels: 456,
    avgWait: "8h",
  },
  {
    name: "Hamburg",
    country: "Germany",
    code: "DEHAM",
    url: "https://www.hafen-hamburg.de/en/shipping/",
    vessels: 178,
    avgWait: "3h",
  },
  {
    name: "Los Angeles",
    country: "USA",
    code: "USLAX",
    url: "https://www.portoflosangeles.org/business/statistics",
    vessels: 145,
    avgWait: "12h",
  },
  {
    name: "Chittagong",
    country: "Bangladesh",
    code: "BDCGP",
    url: "https://cpa.gov.bd/",
    vessels: 45,
    avgWait: "24h",
  },
  {
    name: "Mumbai (JNPT)",
    country: "India",
    code: "INNSA",
    url: "https://www.jnport.gov.in/",
    vessels: 89,
    avgWait: "10h",
  },
  {
    name: "Karachi",
    country: "Pakistan",
    code: "PKKHI",
    url: "https://www.kpt.gov.pk/",
    vessels: 52,
    avgWait: "18h",
  },
];

// External port schedule resources
const SCHEDULE_RESOURCES = [
  {
    name: "Port Economics",
    description: "Global port congestion data and analytics",
    url: "https://www.porteconomics.eu/",
  },
  {
    name: "FleetMon",
    description: "Port arrivals and departures",
    url: "https://www.fleetmon.com/ports/",
  },
  {
    name: "PortWatch",
    description: "Real-time port disruption monitoring",
    url: "https://portwatch.imf.org/",
  },
];

export default function PortSchedulePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [regionFilter, setRegionFilter] = useState("all");

  const filteredPorts = MAJOR_PORTS.filter((port) => {
    const matchesSearch =
      !searchQuery ||
      port.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      port.country.toLowerCase().includes(searchQuery.toLowerCase()) ||
      port.code.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesRegion =
      regionFilter === "all" ||
      (regionFilter === "asia" && ["Bangladesh", "Singapore", "China", "India", "Pakistan"].includes(port.country)) ||
      (regionFilter === "europe" && ["Netherlands", "Germany"].includes(port.country)) ||
      (regionFilter === "americas" && ["USA"].includes(port.country));

    return matchesSearch && matchesRegion;
  });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Port Schedules</h1>
        <p className="text-muted-foreground">
          View vessel schedules and port congestion information
        </p>
      </div>

      {/* Search & Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search ports by name, country, or UN/LOCODE..."
                className="pl-9"
              />
            </div>
            <Select value={regionFilter} onValueChange={setRegionFilter}>
              <SelectTrigger className="w-[150px]">
                <MapPin className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Region" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Regions</SelectItem>
                <SelectItem value="asia">Asia</SelectItem>
                <SelectItem value="europe">Europe</SelectItem>
                <SelectItem value="americas">Americas</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Port Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {filteredPorts.map((port) => (
          <Card key={port.code} className="hover:bg-muted/50 transition-colors">
            <CardContent className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-medium">{port.name}</h3>
                  <p className="text-xs text-muted-foreground">{port.country}</p>
                </div>
                <Badge variant="outline" className="font-mono text-xs">
                  {port.code}
                </Badge>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                <div>
                  <p className="text-muted-foreground text-xs">Vessels</p>
                  <p className="font-medium flex items-center gap-1">
                    <Ship className="w-3 h-3" />
                    {port.vessels}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Avg Wait</p>
                  <p className="font-medium flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {port.avgWait}
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" className="w-full" asChild>
                <a href={port.url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="w-3 h-3 mr-2" />
                  View Schedule
                </a>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* External Resources */}
      <Card>
        <CardHeader>
          <CardTitle>Port Intelligence Resources</CardTitle>
          <CardDescription>
            External resources for port schedules and congestion data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-4">
            {SCHEDULE_RESOURCES.map((resource) => (
              <a
                key={resource.name}
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-4 rounded-lg border hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Anchor className="w-5 h-5 text-blue-500" />
                  <span className="font-medium">{resource.name}</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {resource.description}
                </p>
              </a>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Coming Soon */}
      <Card className="bg-blue-500/5 border-blue-500/20">
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-500/10 rounded-lg flex items-center justify-center">
              <Calendar className="w-6 h-6 text-blue-500" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium">Integrated Port Schedules Coming Soon</h3>
              <p className="text-sm text-muted-foreground">
                We're building direct integrations with major ports to show
                real-time vessel schedules, berth availability, and congestion alerts.
              </p>
            </div>
            <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
              Q1 2025
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


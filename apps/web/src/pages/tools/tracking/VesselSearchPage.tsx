/**
 * Vessel Search Page
 * 
 * Dedicated page for searching and tracking vessels.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Ship,
  Search,
  Loader2,
  ArrowRight,
  Anchor,
  MapPin,
  ExternalLink,
  Radio,
  Navigation,
  Globe,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

// Popular vessels for quick search
const POPULAR_VESSELS = [
  { name: "MSC OSCAR", imo: "9703291", flag: "🇵🇦", type: "Container Ship" },
  { name: "EVER GIVEN", imo: "9811000", flag: "🇵🇦", type: "Container Ship" },
  { name: "MAERSK EDMONTON", imo: "9632129", flag: "🇩🇰", type: "Container Ship" },
  { name: "CMA CGM MARCO POLO", imo: "9454436", flag: "🇬🇧", type: "Container Ship" },
  { name: "BERLIN EXPRESS", imo: "9302158", flag: "🇩🇪", type: "Container Ship" },
  { name: "OOCL HONG KONG", imo: "9776171", flag: "🇭🇰", type: "Container Ship" },
];

// Search types
type SearchType = "name" | "imo" | "mmsi";

export default function VesselSearchPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchType, setSearchType] = useState<SearchType>("name");
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    const query = searchQuery.trim();
    setIsSearching(true);

    try {
      const response = await fetch(
        `${API_BASE}/tracking/vessel/${encodeURIComponent(query)}?search_type=${searchType}`,
        { credentials: "include" }
      );

      if (response.ok) {
        const data = await response.json();
        navigate(`/tracking/dashboard/vessel/${data.imo || query}`);
      } else {
        const error = await response.json();
        toast({
          title: "Vessel Not Found",
          description: error.detail || "Unable to find vessel information.",
          variant: "destructive",
        });
      }
    } catch (error) {
      // Navigate anyway to show mock data
      navigate(`/tracking/dashboard/vessel/${query}`);
    } finally {
      setIsSearching(false);
    }
  };

  const handleQuickSearch = (identifier: string) => {
    navigate(`/tracking/dashboard/vessel/${identifier}`);
  };

  const getPlaceholder = () => {
    switch (searchType) {
      case "imo": return "Enter IMO number (e.g., 9703291)";
      case "mmsi": return "Enter MMSI number (e.g., 352001234)";
      default: return "Enter vessel name (e.g., MSC OSCAR)";
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="w-16 h-16 bg-blue-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Ship className="w-8 h-8 text-blue-500" />
        </div>
        <h1 className="text-3xl font-bold mb-2">Track Vessel</h1>
        <p className="text-muted-foreground">
          Search vessels by name, IMO, or MMSI to get real-time position, schedule, and voyage details.
        </p>
      </div>

      {/* Search Form */}
      <Card className="max-w-2xl mx-auto">
        <CardContent className="p-6">
          <form onSubmit={handleSearch}>
            {/* Search Type Tabs */}
            <Tabs value={searchType} onValueChange={(v) => setSearchType(v as SearchType)} className="mb-4">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="name">
                  <Ship className="w-4 h-4 mr-2" />
                  Vessel Name
                </TabsTrigger>
                <TabsTrigger value="imo">
                  <Radio className="w-4 h-4 mr-2" />
                  IMO Number
                </TabsTrigger>
                <TabsTrigger value="mmsi">
                  <Navigation className="w-4 h-4 mr-2" />
                  MMSI
                </TabsTrigger>
              </TabsList>
            </Tabs>

            <div className="flex gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={getPlaceholder()}
                  className="pl-10 h-12 text-lg"
                  autoFocus
                />
              </div>
              <Button 
                type="submit" 
                className="h-12 px-6 bg-blue-500 hover:bg-blue-600"
                disabled={isSearching || !searchQuery.trim()}
              >
                {isSearching ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    Track
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            </div>
          </form>

          {/* Search Tips */}
          <div className="mt-4 p-3 bg-muted/50 rounded-lg">
            <p className="text-sm text-muted-foreground">
              <strong>Tip:</strong> IMO numbers are 7 digits. MMSI numbers are 9 digits. 
              For vessel names, partial matches are supported.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-3 gap-4 max-w-4xl mx-auto">
        <Card className="hover:bg-muted/50 transition-colors cursor-pointer" onClick={() => handleQuickSearch("9703291")}>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <Ship className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="font-medium">Try Demo</p>
                <p className="text-xs text-muted-foreground">MSC OSCAR</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <a
          href="https://www.marinetraffic.com"
          target="_blank"
          rel="noopener noreferrer"
          className="block"
        >
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-500/10 rounded-lg flex items-center justify-center">
                  <MapPin className="w-5 h-5 text-emerald-500" />
                </div>
                <div>
                  <p className="font-medium">Live Map</p>
                  <p className="text-xs text-muted-foreground">MarineTraffic</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </a>
        <Card className="hover:bg-muted/50 transition-colors cursor-pointer" onClick={() => navigate("/tracking/dashboard/ports")}>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-500/10 rounded-lg flex items-center justify-center">
                <Anchor className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className="font-medium">Port Schedules</p>
                <p className="text-xs text-muted-foreground">View arrivals</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Popular Vessels */}
      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <CardTitle className="text-lg">Popular Vessels</CardTitle>
          <CardDescription>Click to view vessel details</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-3">
            {POPULAR_VESSELS.map((vessel) => (
              <button
                key={vessel.imo}
                onClick={() => handleQuickSearch(vessel.imo)}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{vessel.flag}</span>
                  <div>
                    <p className="font-medium">{vessel.name}</p>
                    <p className="text-xs text-muted-foreground">
                      IMO: {vessel.imo} • {vessel.type}
                    </p>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground" />
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Vessel Types Info */}
      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <CardTitle className="text-lg">Vessel Identification</CardTitle>
          <CardDescription>Understanding vessel identifiers</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 mb-2">
                <Radio className="w-5 h-5 text-blue-500" />
                <span className="font-medium">IMO Number</span>
              </div>
              <p className="text-sm text-muted-foreground">
                International Maritime Organization number. 7 digits, unique to each vessel for its entire lifetime.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 mb-2">
                <Navigation className="w-5 h-5 text-emerald-500" />
                <span className="font-medium">MMSI</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Maritime Mobile Service Identity. 9 digits used for AIS tracking and radio communication.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 mb-2">
                <Globe className="w-5 h-5 text-amber-500" />
                <span className="font-medium">Call Sign</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Radio call sign assigned by flag state. Used for maritime radio communications.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* External Links */}
      <div className="max-w-4xl mx-auto text-center text-sm text-muted-foreground">
        <p>
          Need more vessel data?{" "}
          <a
            href="https://www.vesselfinder.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline inline-flex items-center gap-1"
          >
            Try VesselFinder <ExternalLink className="w-3 h-3" />
          </a>
          {" or "}
          <a
            href="https://www.marinetraffic.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline inline-flex items-center gap-1"
          >
            MarineTraffic <ExternalLink className="w-3 h-3" />
          </a>
        </p>
      </div>
    </div>
  );
}


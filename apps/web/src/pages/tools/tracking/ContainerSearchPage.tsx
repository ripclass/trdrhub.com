/**
 * Container Search Page
 * 
 * Dedicated page for searching and tracking containers.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Container,
  Search,
  Loader2,
  ArrowRight,
  Package,
  Ship,
  FileText,
  Clock,
  CheckCircle,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

// Sample container formats by carrier
const CONTAINER_FORMATS = [
  { carrier: "MSC", prefix: "MSCU", example: "MSCU1234567" },
  { carrier: "Maersk", prefix: "MAEU/MSKU", example: "MAEU1234567" },
  { carrier: "CMA CGM", prefix: "CMAU", example: "CMAU1234567" },
  { carrier: "Hapag-Lloyd", prefix: "HLCU/HLXU", example: "HLCU1234567" },
  { carrier: "OOCL", prefix: "OOLU", example: "OOLU1234567" },
  { carrier: "Evergreen", prefix: "EGHU/EMCU", example: "EGHU1234567" },
  { carrier: "ONE", prefix: "ONEU", example: "ONEU1234567" },
  { carrier: "Yang Ming", prefix: "YMLU", example: "YMLU1234567" },
];

// Recent searches (would come from localStorage in production)
const RECENT_SEARCHES = [
  { id: "1", reference: "MSCU1234567", carrier: "MSC", date: "Today" },
  { id: "2", reference: "MAEU987654321", carrier: "Maersk", date: "Yesterday" },
  { id: "3", reference: "HLCU5678901", carrier: "Hapag-Lloyd", date: "2 days ago" },
];

export default function ContainerSearchPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    const query = searchQuery.toUpperCase().trim();
    setIsSearching(true);

    try {
      const response = await fetch(`${API_BASE}/tracking/container/${encodeURIComponent(query)}`, {
        credentials: "include",
      });

      if (response.ok) {
        navigate(`/tracking/dashboard/container/${query}`);
      } else {
        const error = await response.json();
        toast({
          title: "Container Not Found",
          description: error.detail || "Unable to find tracking information for this container.",
          variant: "destructive",
        });
      }
    } catch (error) {
      // Navigate anyway to show mock data
      navigate(`/tracking/dashboard/container/${query}`);
    } finally {
      setIsSearching(false);
    }
  };

  const handleQuickSearch = (reference: string) => {
    setSearchQuery(reference);
    navigate(`/tracking/dashboard/container/${reference}`);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="w-16 h-16 bg-blue-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Container className="w-8 h-8 text-blue-500" />
        </div>
        <h1 className="text-3xl font-bold mb-2">Track Container</h1>
        <p className="text-muted-foreground">
          Enter your container number to get real-time tracking updates, ETA predictions, and route information.
        </p>
      </div>

      {/* Search Form */}
      <Card className="max-w-2xl mx-auto">
        <CardContent className="p-6">
          <form onSubmit={handleSearch}>
            <div className="flex gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
                  placeholder="Enter container number (e.g., MSCU1234567)"
                  className="pl-10 h-12 font-mono text-lg"
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
                    Tracking...
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
              <strong>Tip:</strong> Container numbers are 11 characters: 4 letters (owner code) + 7 digits. 
              You can also search by Bill of Lading (B/L) number or booking reference.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-3 gap-4 max-w-4xl mx-auto">
        <Card className="hover:bg-muted/50 transition-colors cursor-pointer" onClick={() => handleQuickSearch("MSCU1234567")}>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <Package className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="font-medium">Try Demo</p>
                <p className="text-xs text-muted-foreground">MSCU1234567</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:bg-muted/50 transition-colors cursor-pointer" onClick={() => navigate("/tracking/dashboard/active")}>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-500/10 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <p className="font-medium">My Shipments</p>
                <p className="text-xs text-muted-foreground">View portfolio</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:bg-muted/50 transition-colors cursor-pointer" onClick={() => navigate("/tracking/dashboard/alerts")}>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-500/10 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className="font-medium">Set Alert</p>
                <p className="text-xs text-muted-foreground">Get notified</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Searches */}
      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <CardTitle className="text-lg">Recent Searches</CardTitle>
          <CardDescription>Click to search again</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {RECENT_SEARCHES.map((search) => (
              <button
                key={search.id}
                onClick={() => handleQuickSearch(search.reference)}
                className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  <Container className="w-5 h-5 text-blue-500" />
                  <div>
                    <p className="font-mono font-medium">{search.reference}</p>
                    <p className="text-xs text-muted-foreground">{search.carrier}</p>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">{search.date}</span>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Supported Carriers */}
      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <CardTitle className="text-lg">Supported Carriers</CardTitle>
          <CardDescription>We support tracking across 100+ shipping lines</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {CONTAINER_FORMATS.map((format) => (
              <div
                key={format.carrier}
                className="p-3 rounded-lg bg-muted/50 text-center"
              >
                <p className="font-medium text-sm">{format.carrier}</p>
                <p className="text-xs text-muted-foreground font-mono">{format.prefix}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* External Links */}
      <div className="max-w-4xl mx-auto text-center text-sm text-muted-foreground">
        <p>
          Can't find your container?{" "}
          <a
            href="https://www.track-trace.com/container"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline inline-flex items-center gap-1"
          >
            Try Track & Trace <ExternalLink className="w-3 h-3" />
          </a>
        </p>
      </div>
    </div>
  );
}


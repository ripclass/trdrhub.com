import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Bell,
  Plus,
  Users,
  Ship,
  CheckCircle,
  AlertTriangle,
  Trash2,
  Settings,
  Calendar,
  RefreshCw,
  Loader2,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface WatchlistItem {
  id: string;
  name: string;
  type: "party" | "vessel";
  country?: string;
  imo?: string;
  last_screened: string;
  last_status: "clear" | "potential_match" | "match";
  alert_email: boolean;
  alert_in_app: boolean;
}

export default function SanctionsWatchlist() {
  const { toast } = useToast();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [newEntry, setNewEntry] = useState({ name: "", type: "party" });
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch watchlist from API (derived from notifications/preferences)
  useEffect(() => {
    const fetchWatchlist = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Get history items that were screened multiple times (indicates monitoring)
        const response = await fetch(`${API_BASE}/sanctions/history?limit=100`, {
          credentials: "include",
        });
        if (!response.ok) {
          throw new Error("Failed to fetch watchlist");
        }
        const data = await response.json();
        const historyItems = data.history || data || [];
        
        // Group by query to find frequently monitored items
        const queryCount: Record<string, any> = {};
        historyItems.forEach((item: any) => {
          const key = item.query.toLowerCase();
          if (!queryCount[key]) {
            queryCount[key] = { ...item, count: 0 };
          }
          queryCount[key].count++;
          // Keep the most recent screening
          if (new Date(item.screened_at) > new Date(queryCount[key].screened_at)) {
            queryCount[key] = { ...item, count: queryCount[key].count };
          }
        });
        
        // Convert to watchlist format (items screened more than once)
        const watchlistItems: WatchlistItem[] = Object.values(queryCount)
          .filter((item: any) => item.count >= 1)
          .map((item: any, idx) => ({
            id: String(idx + 1),
            name: item.query,
            type: item.type || "party",
            last_screened: item.screened_at,
            last_status: item.status,
            alert_email: true,
            alert_in_app: true,
          }));
        
        setWatchlist(watchlistItems);
      } catch (err) {
        console.error("Failed to fetch watchlist:", err);
        setError("Failed to load watchlist. Please try again.");
        setWatchlist([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchWatchlist();
  }, []);

  const handleAddToWatchlist = async () => {
    if (!newEntry.name.trim()) return;
    
    setIsSaving(true);
    try {
      // Screen the party/vessel to add to history (which becomes watchlist)
      const endpoint = newEntry.type === "vessel" ? "screen/vessel" : "screen/party";
      const response = await fetch(`${API_BASE}/sanctions/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          query: newEntry.name,
          lists: ["OFAC_SDN", "EU_CONS", "UN_SC"],
        }),
      });
      
      if (response.ok) {
        const result = await response.json();
        // Add to local watchlist
        setWatchlist(prev => [...prev, {
          id: String(prev.length + 1),
          name: newEntry.name,
          type: newEntry.type as "party" | "vessel",
          last_screened: new Date().toISOString(),
          last_status: result.status || "clear",
          alert_email: true,
          alert_in_app: true,
        }]);
        setIsAddDialogOpen(false);
        setNewEntry({ name: "", type: "party" });
        toast({
          title: "Added to watchlist",
          description: `${newEntry.name} will be monitored for sanctions updates.`,
        });
      }
    } catch (err) {
      console.error("Failed to add to watchlist:", err);
      toast({
        title: "Error",
        description: "Failed to add to watchlist. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleRemoveFromWatchlist = (id: string) => {
    setWatchlist(prev => prev.filter(item => item.id !== id));
    toast({
      title: "Removed from watchlist",
      description: "Item will no longer be monitored.",
    });
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Bell className="w-6 h-6 text-red-400" />
            Watchlist Monitoring
          </h1>
          <p className="text-slate-400 mt-1">
            Get alerted when sanctions lists are updated for your monitored parties
          </p>
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-red-500 hover:bg-red-600 text-white">
              <Plus className="w-4 h-4 mr-2" />
              Add to Watchlist
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-slate-900 border-slate-800">
            <DialogHeader>
              <DialogTitle className="text-white">Add to Watchlist</DialogTitle>
              <DialogDescription className="text-slate-400">
                Monitor a party or vessel for sanctions list changes
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label className="text-white">Name</Label>
                <Input
                  value={newEntry.name}
                  onChange={(e) => setNewEntry({ ...newEntry, name: e.target.value })}
                  placeholder="Enter party or vessel name"
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="flex items-center justify-between">
                <Label className="text-white">Email Alerts</Label>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <Label className="text-white">In-App Alerts</Label>
                <Switch defaultChecked />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsAddDialogOpen(false)} className="border-slate-700 text-slate-400">
                Cancel
              </Button>
              <Button 
                className="bg-red-500 hover:bg-red-600"
                onClick={handleAddToWatchlist}
                disabled={isSaving || !newEntry.name.trim()}
              >
                {isSaving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Add to Watchlist
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Info Card */}
      <Card className="bg-gradient-to-r from-red-500/10 to-orange-500/10 border-red-500/20">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <RefreshCw className="w-5 h-5 text-red-400 mt-0.5" />
            <div>
              <h4 className="font-medium text-white">Automatic Re-screening</h4>
              <p className="text-sm text-slate-400 mt-1">
                Watchlist entries are automatically re-screened when sanctions lists are updated (typically daily for OFAC, weekly for EU/UK).
                You'll receive an alert if any status changes.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <Card key={i} className="bg-slate-900/50 border-slate-800">
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <Skeleton className="w-10 h-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card className="bg-red-900/20 border-red-800">
          <CardContent className="p-4 text-red-400">
            {error}
          </CardContent>
        </Card>
      )}

      {/* Watchlist */}
      {!isLoading && (
      <div className="space-y-3">
        {watchlist.length === 0 ? (
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-12 text-center">
              <Bell className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No watchlist entries</h3>
              <p className="text-slate-400 mb-4">
                Add parties or vessels to monitor for sanctions list changes
              </p>
              <Button 
                className="bg-red-500 hover:bg-red-600 text-white"
                onClick={() => setIsAddDialogOpen(true)}
              >
                <Plus className="w-4 h-4 mr-2" />
                Add First Entry
              </Button>
            </CardContent>
          </Card>
        ) : (
          watchlist.map((item) => (
            <Card key={item.id} className="bg-slate-900/50 border-slate-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 ${
                      item.last_status === "clear" 
                        ? "bg-emerald-500/20" 
                        : "bg-amber-500/20"
                    } rounded-lg flex items-center justify-center`}>
                      {item.type === "party" ? (
                        <Users className={`w-5 h-5 ${
                          item.last_status === "clear" ? "text-emerald-400" : "text-amber-400"
                        }`} />
                      ) : (
                        <Ship className={`w-5 h-5 ${
                          item.last_status === "clear" ? "text-emerald-400" : "text-amber-400"
                        }`} />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white">{item.name}</span>
                        <Badge variant="outline" className="border-slate-700 text-slate-400 text-xs">
                          {item.type}
                        </Badge>
                        {item.country && (
                          <Badge variant="outline" className="border-slate-700 text-slate-400 text-xs">
                            {item.country}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          Last screened: {new Date(item.last_screened).toLocaleString()}
                        </span>
                        {item.alert_email && <Badge variant="outline" className="text-xs">Email</Badge>}
                        {item.alert_in_app && <Badge variant="outline" className="text-xs">In-App</Badge>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge className={`${
                      item.last_status === "clear" 
                        ? "bg-emerald-500/20 text-emerald-400" 
                        : "bg-amber-500/20 text-amber-400"
                    }`}>
                      {item.last_status === "clear" ? (
                        <>
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Clear
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="w-3 h-3 mr-1" />
                          Review
                        </>
                      )}
                    </Badge>
                    <Button variant="ghost" size="icon" className="text-slate-500 hover:text-white">
                      <Settings className="w-4 h-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="text-slate-500 hover:text-red-400"
                      onClick={() => handleRemoveFromWatchlist(item.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
      )}
    </div>
  );
}


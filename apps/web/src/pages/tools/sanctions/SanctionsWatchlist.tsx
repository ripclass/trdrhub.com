import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
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
} from "lucide-react";

// Mock watchlist
const mockWatchlist = [
  {
    id: "1",
    name: "ABC Trading Partners",
    type: "party",
    country: "CN",
    last_screened: "2025-12-06T10:00:00Z",
    last_status: "clear",
    alert_email: true,
    alert_in_app: true,
  },
  {
    id: "2",
    name: "XYZ Shipping Ltd",
    type: "party",
    country: "SG",
    last_screened: "2025-12-05T14:30:00Z",
    last_status: "clear",
    alert_email: true,
    alert_in_app: false,
  },
  {
    id: "3",
    name: "M/V OCEAN STAR",
    type: "vessel",
    imo: "9876543",
    last_screened: "2025-12-06T08:15:00Z",
    last_status: "potential_match",
    alert_email: true,
    alert_in_app: true,
  },
];

export default function SanctionsWatchlist() {
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [newEntry, setNewEntry] = useState({ name: "", type: "party" });

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
              <Button className="bg-red-500 hover:bg-red-600">
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

      {/* Watchlist */}
      <div className="space-y-3">
        {mockWatchlist.length === 0 ? (
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-12 text-center">
              <Bell className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No watchlist entries</h3>
              <p className="text-slate-400 mb-4">
                Add parties or vessels to monitor for sanctions list changes
              </p>
              <Button className="bg-red-500 hover:bg-red-600 text-white">
                <Plus className="w-4 h-4 mr-2" />
                Add First Entry
              </Button>
            </CardContent>
          </Card>
        ) : (
          mockWatchlist.map((item) => (
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
                    <Button variant="ghost" size="icon" className="text-slate-500 hover:text-red-400">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}


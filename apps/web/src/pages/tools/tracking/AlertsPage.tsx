/**
 * Alerts Page
 * 
 * Manage tracking alerts and notification preferences.
 */

import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Bell,
  Plus,
  Trash2,
  ToggleLeft,
  ToggleRight,
  Clock,
  Ship,
  Container,
  Mail,
  Smartphone,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/components/ui/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface Alert {
  id: string;
  reference: string;
  tracking_type: string;
  alert_type: string;
  threshold_hours?: number;
  threshold_days?: number;
  notify_email: boolean;
  notify_sms: boolean;
  is_active: boolean;
  last_triggered?: string;
  trigger_count: number;
  created_at: string;
}

const alertTypeLabels: Record<string, { label: string; icon: any; color: string }> = {
  arrival: { label: "Arrival", icon: CheckCircle, color: "text-emerald-500" },
  departure: { label: "Departure", icon: Ship, color: "text-blue-500" },
  delay: { label: "Delay", icon: Clock, color: "text-amber-500" },
  eta_change: { label: "ETA Change", icon: Clock, color: "text-purple-500" },
  lc_risk: { label: "LC Risk", icon: AlertTriangle, color: "text-red-500" },
  exception: { label: "Exception", icon: AlertTriangle, color: "text-red-500" },
};

export default function AlertsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  
  // New alert form
  const [newAlert, setNewAlert] = useState({
    reference: "",
    tracking_type: "container",
    alert_type: "arrival",
    threshold_hours: 24,
    notify_email: true,
    notify_sms: false,
  });

  const fetchAlerts = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/tracking/alerts`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        setAlerts(data);
      }
    } catch (error) {
      console.error("Failed to fetch alerts:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchAlerts();
    } else {
      setIsLoading(false);
    }
  }, [user]);

  const handleCreate = async () => {
    setIsCreating(true);
    try {
      const response = await fetch(`${API_BASE}/tracking/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(newAlert),
      });
      
      if (response.ok) {
        const created = await response.json();
        setAlerts([created, ...alerts]);
        setShowCreateDialog(false);
        setNewAlert({
          reference: "",
          tracking_type: "container",
          alert_type: "arrival",
          threshold_hours: 24,
          notify_email: true,
          notify_sms: false,
        });
        toast({ title: "Created", description: "Alert created successfully" });
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to create alert", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to create alert", variant: "destructive" });
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggle = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/tracking/alerts/${id}/toggle`, {
        method: "POST",
        credentials: "include",
      });
      if (response.ok) {
        const updated = await response.json();
        setAlerts(alerts.map(a => a.id === id ? { ...a, is_active: updated.is_active } : a));
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to toggle alert", variant: "destructive" });
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/tracking/alerts/${id}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (response.ok) {
        setAlerts(alerts.filter(a => a.id !== id));
        toast({ title: "Deleted", description: "Alert deleted" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to delete alert", variant: "destructive" });
    }
  };

  const activeAlerts = alerts.filter(a => a.is_active);
  const inactiveAlerts = alerts.filter(a => !a.is_active);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tracking Alerts</h1>
          <p className="text-muted-foreground">Get notified about shipment events</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Create Alert
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Tracking Alert</DialogTitle>
              <DialogDescription>
                Set up notifications for container or vessel events.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Reference Number</Label>
                <Input
                  value={newAlert.reference}
                  onChange={(e) => setNewAlert({ ...newAlert, reference: e.target.value.toUpperCase() })}
                  placeholder="e.g., MSCU1234567"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Select
                    value={newAlert.tracking_type}
                    onValueChange={(v) => setNewAlert({ ...newAlert, tracking_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="container">Container</SelectItem>
                      <SelectItem value="vessel">Vessel</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Alert Type</Label>
                  <Select
                    value={newAlert.alert_type}
                    onValueChange={(v) => setNewAlert({ ...newAlert, alert_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="arrival">Arrival</SelectItem>
                      <SelectItem value="departure">Departure</SelectItem>
                      <SelectItem value="delay">Delay</SelectItem>
                      <SelectItem value="eta_change">ETA Change</SelectItem>
                      <SelectItem value="lc_risk">LC Risk</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {newAlert.alert_type === "delay" && (
                <div className="space-y-2">
                  <Label>Delay Threshold (hours)</Label>
                  <Input
                    type="number"
                    value={newAlert.threshold_hours}
                    onChange={(e) => setNewAlert({ ...newAlert, threshold_hours: parseInt(e.target.value) })}
                  />
                </div>
              )}
              <div className="space-y-3">
                <Label>Notification Channels</Label>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">Email</span>
                  </div>
                  <Switch
                    checked={newAlert.notify_email}
                    onCheckedChange={(c) => setNewAlert({ ...newAlert, notify_email: c })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Smartphone className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">SMS</span>
                  </div>
                  <Switch
                    checked={newAlert.notify_sms}
                    onCheckedChange={(c) => setNewAlert({ ...newAlert, notify_sms: c })}
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={!newAlert.reference || isCreating}>
                {isCreating ? "Creating..." : "Create Alert"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <Bell className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{alerts.length}</p>
                <p className="text-xs text-muted-foreground">Total Alerts</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-500/10 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{activeAlerts.length}</p>
                <p className="text-xs text-muted-foreground">Active</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-500/10 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{alerts.reduce((sum, a) => sum + a.trigger_count, 0)}</p>
                <p className="text-xs text-muted-foreground">Triggered</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Alerts List */}
      <Card>
        <CardHeader>
          <CardTitle>Your Alerts</CardTitle>
          <CardDescription>Configure notifications for your tracked shipments</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
              <p className="text-muted-foreground">Loading alerts...</p>
            </div>
          ) : alerts.length === 0 ? (
            <div className="text-center py-8">
              <Bell className="w-8 h-8 mx-auto mb-2 text-muted-foreground opacity-50" />
              <p className="text-muted-foreground">No alerts configured</p>
              <Button variant="link" onClick={() => setShowCreateDialog(true)}>
                Create your first alert →
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert) => {
                const typeInfo = alertTypeLabels[alert.alert_type] || { 
                  label: alert.alert_type, 
                  icon: Bell, 
                  color: "text-blue-500" 
                };
                const TypeIcon = typeInfo.icon;
                
                return (
                  <div
                    key={alert.id}
                    className={`p-4 rounded-lg border ${alert.is_active ? "bg-card" : "bg-muted/30 opacity-60"}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-opacity-10 ${alert.is_active ? "bg-blue-500/10" : "bg-slate-500/10"}`}>
                          {alert.tracking_type === "container" ? (
                            <Container className={`w-5 h-5 ${alert.is_active ? "text-blue-500" : "text-slate-500"}`} />
                          ) : (
                            <Ship className={`w-5 h-5 ${alert.is_active ? "text-blue-500" : "text-slate-500"}`} />
                          )}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-mono font-medium">{alert.reference}</p>
                            <Badge variant="outline" className="text-xs">
                              <TypeIcon className={`w-3 h-3 mr-1 ${typeInfo.color}`} />
                              {typeInfo.label}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                            {alert.notify_email && (
                              <span className="flex items-center gap-1">
                                <Mail className="w-3 h-3" /> Email
                              </span>
                            )}
                            {alert.notify_sms && (
                              <span className="flex items-center gap-1">
                                <Smartphone className="w-3 h-3" /> SMS
                              </span>
                            )}
                            <span>•</span>
                            <span>Triggered {alert.trigger_count}x</span>
                            {alert.last_triggered && (
                              <>
                                <span>•</span>
                                <span>Last: {new Date(alert.last_triggered).toLocaleDateString()}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={alert.is_active}
                          onCheckedChange={() => handleToggle(alert.id)}
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-red-500 hover:text-red-600 hover:bg-red-500/10"
                          onClick={() => handleDelete(alert.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


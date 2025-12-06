/**
 * Rate Alerts Page
 * Phase 2: Subscribe to rate change notifications
 */
import { useState, useEffect } from "react";
import { 
  Bell, BellOff, Plus, Trash2, TrendingUp, TrendingDown,
  Loader2, Mail, AlertTriangle, CheckCircle2, RefreshCw
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

interface RateAlert {
  id: string;
  hs_code: string;
  import_country: string;
  export_country?: string;
  alert_type: string;
  threshold_percent?: number;
  baseline_rate?: number;
  current_rate?: number;
  rate_changed: boolean;
  rate_change: number;
  email_notification: boolean;
  last_notified?: string;
  notification_count: number;
  created_at: string;
}

interface RateChange {
  hs_code: string;
  description: string;
  rate_type: string;
  current_rate: number;
  effective_from?: string;
  updated_at?: string;
  is_excluded?: boolean;
}

const COUNTRIES = [
  { code: "US", name: "United States" },
  { code: "CN", name: "China" },
  { code: "DE", name: "Germany" },
  { code: "JP", name: "Japan" },
  { code: "MX", name: "Mexico" },
  { code: "CA", name: "Canada" },
  { code: "VN", name: "Vietnam" },
  { code: "TW", name: "Taiwan" },
];

export default function HSCodeAlerts() {
  const { token, isAuthenticated } = useAuth();
  const { toast } = useToast();
  
  const [alerts, setAlerts] = useState<RateAlert[]>([]);
  const [recentChanges, setRecentChanges] = useState<RateChange[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  
  // New alert form
  const [showForm, setShowForm] = useState(false);
  const [newHsCode, setNewHsCode] = useState("");
  const [newImportCountry, setNewImportCountry] = useState("US");
  const [newExportCountry, setNewExportCountry] = useState("");
  const [newAlertType, setNewAlertType] = useState("any");
  const [newThreshold, setNewThreshold] = useState("");
  const [newEmailNotify, setNewEmailNotify] = useState(true);

  useEffect(() => {
    if (isAuthenticated) {
      loadAlerts();
    }
    loadRecentChanges();
  }, [isAuthenticated]);

  const loadAlerts = async () => {
    if (!token) return;
    
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/alerts`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error('Failed to load alerts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadRecentChanges = async () => {
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/rate-changes?country=US&days=30`
      );

      if (response.ok) {
        const data = await response.json();
        setRecentChanges(data.changes || []);
      }
    } catch (error) {
      console.error('Failed to load rate changes:', error);
    }
  };

  const createAlert = async () => {
    if (!token || !newHsCode.trim()) {
      toast({
        title: "HS Code required",
        description: "Please enter an HS code to monitor",
        variant: "destructive"
      });
      return;
    }

    setIsCreating(true);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/alerts/subscribe`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            hs_code: newHsCode,
            import_country: newImportCountry,
            export_country: newExportCountry || undefined,
            alert_type: newAlertType,
            threshold_percent: newThreshold ? parseFloat(newThreshold) : undefined,
            email_notification: newEmailNotify
          })
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create alert');
      }

      toast({
        title: "Alert created",
        description: `You'll be notified when rates change for ${newHsCode}`
      });

      // Reset form and reload
      setShowForm(false);
      setNewHsCode("");
      setNewExportCountry("");
      setNewThreshold("");
      loadAlerts();
    } catch (error) {
      toast({
        title: "Failed to create alert",
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: "destructive"
      });
    } finally {
      setIsCreating(false);
    }
  };

  const deleteAlert = async (alertId: string) => {
    if (!token) return;

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/alerts/${alertId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        setAlerts(alerts.filter(a => a.id !== alertId));
        toast({
          title: "Alert removed",
          description: "You will no longer receive notifications"
        });
      }
    } catch (error) {
      toast({
        title: "Failed to remove alert",
        description: "Please try again",
        variant: "destructive"
      });
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-950 text-white">
        <div className="border-b border-slate-800 bg-slate-900/50">
          <div className="px-6 py-4">
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Bell className="h-5 w-5 text-emerald-400" />
              Rate Change Alerts
            </h1>
            <p className="text-sm text-slate-400">
              Get notified when duty rates change for your products
            </p>
          </div>
        </div>
        
        <div className="container mx-auto px-6 py-16 text-center">
          <Bell className="h-16 w-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Sign in to set up alerts</h2>
          <p className="text-slate-400 mb-6">
            Create an account to receive notifications when duty rates change
          </p>
          <Button className="bg-emerald-600 hover:bg-emerald-700">
            Sign In
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Bell className="h-5 w-5 text-emerald-400" />
              Rate Change Alerts
            </h1>
            <p className="text-sm text-slate-400">
              Get notified when duty rates change for your products
            </p>
          </div>
          <Button 
            onClick={() => setShowForm(!showForm)}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Alert
          </Button>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {/* Create Alert Form */}
        {showForm && (
          <Card className="bg-slate-800 border-slate-700 mb-8">
            <CardHeader>
              <CardTitle className="text-white text-base">Create Rate Alert</CardTitle>
              <CardDescription>
                Monitor an HS code for duty rate changes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                <div>
                  <label className="text-sm text-slate-400 mb-1 block">HS Code *</label>
                  <Input
                    placeholder="e.g., 6109.10.00"
                    value={newHsCode}
                    onChange={(e) => setNewHsCode(e.target.value)}
                    className="bg-slate-900 border-slate-700"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 mb-1 block">Import Country</label>
                  <Select value={newImportCountry} onValueChange={setNewImportCountry}>
                    <SelectTrigger className="bg-slate-900 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {COUNTRIES.map(c => (
                        <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm text-slate-400 mb-1 block">Export Country</label>
                  <Select value={newExportCountry || "none"} onValueChange={(val) => setNewExportCountry(val === "none" ? "" : val)}>
                    <SelectTrigger className="bg-slate-900 border-slate-700">
                      <SelectValue placeholder="Any origin" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Any origin</SelectItem>
                      {COUNTRIES.map(c => (
                        <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm text-slate-400 mb-1 block">Alert When</label>
                  <Select value={newAlertType} onValueChange={setNewAlertType}>
                    <SelectTrigger className="bg-slate-900 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="any">Any change</SelectItem>
                      <SelectItem value="increase">Rate increases</SelectItem>
                      <SelectItem value="decrease">Rate decreases</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="flex flex-col md:flex-row items-start md:items-center gap-4">
                <div className="w-48">
                  <label className="text-sm text-slate-400 mb-1 block">Threshold (%)</label>
                  <Input
                    type="number"
                    placeholder="e.g., 5"
                    value={newThreshold}
                    onChange={(e) => setNewThreshold(e.target.value)}
                    className="bg-slate-900 border-slate-700"
                  />
                  <p className="text-xs text-slate-500 mt-1">Only alert if change exceeds this %</p>
                </div>
                
                <div className="flex items-center gap-3 pt-4 md:pt-6">
                  <Switch
                    checked={newEmailNotify}
                    onCheckedChange={setNewEmailNotify}
                  />
                  <label className="text-sm text-slate-400 flex items-center gap-1">
                    <Mail className="h-4 w-4" />
                    Email notifications
                  </label>
                </div>
                
                <div className="flex-1" />
                
                <div className="flex gap-2 pt-4 md:pt-6">
                  <Button 
                    variant="outline" 
                    onClick={() => setShowForm(false)}
                  >
                    Cancel
                  </Button>
                  <Button 
                    onClick={createAlert}
                    disabled={isCreating}
                    className="bg-emerald-600 hover:bg-emerald-700"
                  >
                    {isCreating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Create Alert"
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Active Alerts */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">Your Alerts</h2>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={loadAlerts}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>

            {isLoading ? (
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-8 text-center">
                  <Loader2 className="h-8 w-8 animate-spin text-emerald-400 mx-auto" />
                </CardContent>
              </Card>
            ) : alerts.length > 0 ? (
              <div className="space-y-4">
                {alerts.map((alert) => (
                  <Card key={alert.id} className="bg-slate-800 border-slate-700">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="outline" className="font-mono text-emerald-400">
                              {alert.hs_code}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {alert.import_country}
                              {alert.export_country && ` ← ${alert.export_country}`}
                            </Badge>
                            {alert.rate_changed && (
                              <Badge className={alert.rate_change > 0 ? 'bg-red-500' : 'bg-green-500'}>
                                {alert.rate_change > 0 ? (
                                  <TrendingUp className="h-3 w-3 mr-1" />
                                ) : (
                                  <TrendingDown className="h-3 w-3 mr-1" />
                                )}
                                {alert.rate_change > 0 ? '+' : ''}{alert.rate_change}%
                              </Badge>
                            )}
                          </div>
                          
                          <div className="grid grid-cols-3 gap-4 text-sm">
                            <div>
                              <div className="text-slate-400">Baseline Rate</div>
                              <div className="text-white">{alert.baseline_rate?.toFixed(1) || 0}%</div>
                            </div>
                            <div>
                              <div className="text-slate-400">Current Rate</div>
                              <div className={alert.rate_changed ? (alert.rate_change > 0 ? 'text-red-400' : 'text-green-400') : 'text-white'}>
                                {alert.current_rate?.toFixed(1) || 0}%
                              </div>
                            </div>
                            <div>
                              <div className="text-slate-400">Alert Type</div>
                              <div className="text-white capitalize">{alert.alert_type}</div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                            {alert.email_notification && (
                              <span className="flex items-center gap-1">
                                <Mail className="h-3 w-3" /> Email enabled
                              </span>
                            )}
                            {alert.threshold_percent && (
                              <span>Threshold: {alert.threshold_percent}%</span>
                            )}
                            <span>Created: {new Date(alert.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteAlert(alert.id)}
                          className="text-slate-400 hover:text-red-400"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-8 text-center">
                  <BellOff className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-white font-medium mb-2">No alerts configured</h3>
                  <p className="text-slate-400 text-sm mb-4">
                    Set up alerts to get notified when duty rates change
                  </p>
                  <Button 
                    onClick={() => setShowForm(true)}
                    className="bg-emerald-600 hover:bg-emerald-700"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Create First Alert
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Recent Changes */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">Recent Rate Changes</h2>
            
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="p-4">
                {recentChanges.length > 0 ? (
                  <div className="space-y-3">
                    {recentChanges.slice(0, 10).map((change, idx) => (
                      <div 
                        key={idx}
                        className="bg-slate-900 p-3 rounded-lg"
                      >
                        <div className="flex items-start justify-between mb-1">
                          <Badge variant="outline" className="font-mono text-xs">
                            {change.hs_code}
                          </Badge>
                          {change.rate_type === 'section_301' ? (
                            <Badge className="bg-red-500 text-xs">301</Badge>
                          ) : (
                            <span className="text-emerald-400 text-sm font-medium">
                              {change.current_rate}%
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 truncate">
                          {change.description}
                        </p>
                        {change.effective_from && (
                          <p className="text-xs text-slate-500 mt-1">
                            Effective: {new Date(change.effective_from).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
                    <p className="text-sm text-slate-400">No recent rate changes</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Tips */}
            <Card className="bg-blue-900/20 border-blue-800/50 mt-4">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-blue-400 mb-1">Stay Compliant</p>
                    <p className="text-slate-400">
                      Rate changes can affect your costs and compliance. 
                      Set up alerts for HS codes you frequently import.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}


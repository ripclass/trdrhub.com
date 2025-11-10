import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Shield,
  FileText,
  Calendar,
  Globe,
  AlertCircle,
  CheckCircle2,
  Plus,
  Trash2,
  Settings,
  BarChart3,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { useToast } from "@/hooks/use-toast";
import { format } from "date-fns";
import { useBankAuth } from "@/lib/bank/auth";
import { bankPolicyApi, type PolicyAnalytics } from "@/api/bank";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Mock data - replace with API calls
const mockActiveRulesets = [
  {
    domain: "icc",
    jurisdiction: "global",
    ruleset_version: "1.0.0",
    rulebook_version: "UCP600",
    effective_from: "2024-01-01T00:00:00Z",
    effective_to: null,
    rule_count: 39,
  },
  {
    domain: "icc",
    jurisdiction: "global",
    ruleset_version: "2.1.0",
    rulebook_version: "eUCP v2.1",
    effective_from: "2024-01-15T00:00:00Z",
    effective_to: null,
    rule_count: 14,
  },
];

const mockPolicyHistory = [
  {
    id: "policy-1",
    action: "published",
    ruleset_version: "1.0.0",
    rulebook_version: "UCP600",
    domain: "icc",
    jurisdiction: "global",
    published_by: "admin@example.com",
    published_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "policy-2",
    action: "published",
    ruleset_version: "2.1.0",
    rulebook_version: "eUCP v2.1",
    domain: "icc",
    jurisdiction: "global",
    published_by: "admin@example.com",
    published_at: "2024-01-15T00:00:00Z",
  },
];

function OverlaysTab() {
  const { toast } = useToast();
  const { user } = useAuth();
  const isBankAdmin = user?.role === "bank_admin" || user?.role === "system_admin";
  
  const [overlays, setOverlays] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [editOpen, setEditOpen] = React.useState(false);
  const [overlayConfig, setOverlayConfig] = React.useState({
    stricter_checks: {
      max_date_slippage_days: 0,
      mandatory_documents: [] as string[],
      require_expiry_date: false,
      min_amount_threshold: 0,
    },
    thresholds: {
      discrepancy_severity_override: "",
      auto_reject_on: [] as string[],
    },
  });

  React.useEffect(() => {
    loadOverlays();
  }, []);

  const loadOverlays = async () => {
    setLoading(true);
    try {
      const data = await bankPolicyApi.listOverlays();
      setOverlays(data);
    } catch (error) {
      console.error("Failed to load overlays", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveOverlay = async () => {
    if (!isBankAdmin) {
      toast({
        title: "Permission Denied",
        description: "Only bank admins can modify policy overlays",
        variant: "destructive",
      });
      return;
    }

    try {
      await bankPolicyApi.createOverlay({ config: overlayConfig });
      toast({
        title: "Success",
        description: "Policy overlay saved. Click 'Publish' to activate it.",
      });
      setEditOpen(false);
      loadOverlays();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to save overlay",
        variant: "destructive",
      });
    }
  };

  const handlePublishOverlay = async (overlayId: string) => {
    if (!isBankAdmin) {
      toast({
        title: "Permission Denied",
        description: "Only bank admins can publish policy overlays",
        variant: "destructive",
      });
      return;
    }

    try {
      await bankPolicyApi.publishOverlay(overlayId);
      toast({
        title: "Success",
        description: "Policy overlay published and activated",
      });
      loadOverlays();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to publish overlay",
        variant: "destructive",
      });
    }
  };

  const activeOverlay = overlays.find((o) => o.active);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Policy Overlays</h3>
          <p className="text-sm text-muted-foreground">
            Configure stricter validation rules for your bank
          </p>
        </div>
        {isBankAdmin && (
          <Dialog open={editOpen} onOpenChange={setEditOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                {activeOverlay ? "Edit Overlay" : "Create Overlay"}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Policy Overlay Configuration</DialogTitle>
                <DialogDescription>
                  Configure stricter validation checks and thresholds
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-6 max-h-[60vh] overflow-y-auto">
                <div className="space-y-4">
                  <h4 className="font-medium">Stricter Checks</h4>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label>Max Date Slippage (days)</Label>
                        <p className="text-xs text-muted-foreground">
                          Maximum allowed date difference (0 = no tolerance)
                        </p>
                      </div>
                      <Input
                        type="number"
                        className="w-24"
                        value={overlayConfig.stricter_checks.max_date_slippage_days}
                        onChange={(e) =>
                          setOverlayConfig({
                            ...overlayConfig,
                            stricter_checks: {
                              ...overlayConfig.stricter_checks,
                              max_date_slippage_days: parseInt(e.target.value) || 0,
                            },
                          })
                        }
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <Label>Require Expiry Date</Label>
                        <p className="text-xs text-muted-foreground">
                          Make expiry date mandatory
                        </p>
                      </div>
                      <Switch
                        checked={overlayConfig.stricter_checks.require_expiry_date}
                        onCheckedChange={(checked) =>
                          setOverlayConfig({
                            ...overlayConfig,
                            stricter_checks: {
                              ...overlayConfig.stricter_checks,
                              require_expiry_date: checked,
                            },
                          })
                        }
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <Label>Min Amount Threshold</Label>
                        <p className="text-xs text-muted-foreground">
                          Minimum LC amount (0 = no threshold)
                        </p>
                      </div>
                      <Input
                        type="number"
                        className="w-32"
                        value={overlayConfig.stricter_checks.min_amount_threshold}
                        onChange={(e) =>
                          setOverlayConfig({
                            ...overlayConfig,
                            stricter_checks: {
                              ...overlayConfig.stricter_checks,
                              min_amount_threshold: parseFloat(e.target.value) || 0,
                            },
                          })
                        }
                      />
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <h4 className="font-medium">Thresholds</h4>
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label>Discrepancy Severity Override</Label>
                      <select
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={overlayConfig.thresholds.discrepancy_severity_override}
                        onChange={(e) =>
                          setOverlayConfig({
                            ...overlayConfig,
                            thresholds: {
                              ...overlayConfig.thresholds,
                              discrepancy_severity_override: e.target.value,
                            },
                          })
                        }
                      >
                        <option value="">None</option>
                        <option value="critical">Treat all as Critical</option>
                        <option value="major">Treat all as Major</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setEditOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSaveOverlay}>Save Overlay</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {loading ? (
        <div className="text-center py-8 text-muted-foreground">Loading...</div>
      ) : activeOverlay ? (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Active Overlay (Version {activeOverlay.version})
                </CardTitle>
                <CardDescription>
                  Published {activeOverlay.published_at ? format(new Date(activeOverlay.published_at), "PPp") : "N/A"}
                </CardDescription>
              </div>
              <Badge variant="default">Active</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">Stricter Checks</h4>
                <div className="space-y-2 text-sm">
                  <div>Max Date Slippage: {activeOverlay.config.stricter_checks?.max_date_slippage_days ?? 0} days</div>
                  <div>Require Expiry Date: {activeOverlay.config.stricter_checks?.require_expiry_date ? "Yes" : "No"}</div>
                  <div>Min Amount Threshold: {activeOverlay.config.stricter_checks?.min_amount_threshold ?? 0}</div>
                </div>
              </div>
              {activeOverlay.config.thresholds && (
                <div>
                  <h4 className="font-medium mb-2">Thresholds</h4>
                  <div className="text-sm">
                    Severity Override: {activeOverlay.config.thresholds.discrepancy_severity_override || "None"}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : overlays.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Draft Overlay (Version {overlays[0].version})
            </CardTitle>
            <CardDescription>
              Created {overlays[0].created_at ? format(new Date(overlays[0].created_at), "PPp") : "N/A"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">Stricter Checks</h4>
                <div className="space-y-2 text-sm">
                  <div>Max Date Slippage: {overlays[0].config.stricter_checks?.max_date_slippage_days ?? 0} days</div>
                  <div>Require Expiry Date: {overlays[0].config.stricter_checks?.require_expiry_date ? "Yes" : "No"}</div>
                  <div>Min Amount Threshold: {overlays[0].config.stricter_checks?.min_amount_threshold ?? 0}</div>
                </div>
              </div>
              {overlays[0].config.thresholds && (
                <div>
                  <h4 className="font-medium mb-2">Thresholds</h4>
                  <div className="text-sm">
                    Severity Override: {overlays[0].config.thresholds.discrepancy_severity_override || "None"}
                  </div>
                </div>
              )}
              {isBankAdmin && (
                <div className="pt-4">
                  <Button onClick={() => handlePublishOverlay(overlays[0].id)}>
                    Publish Overlay
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No policy overlay. Create one to enforce stricter validation rules.
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ExceptionsTab() {
  const { toast } = useToast();
  const { user } = useAuth();
  const isBankAdmin = user?.role === "bank_admin" || user?.role === "system_admin";
  
  const [exceptions, setExceptions] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [addOpen, setAddOpen] = React.useState(false);
  const [newException, setNewException] = React.useState({
    rule_code: "",
    scope: { client: "", branch: "", product: "" },
    reason: "",
    expires_at: "",
    effect: "waive" as "waive" | "downgrade" | "override",
  });

  React.useEffect(() => {
    loadExceptions();
  }, []);

  const loadExceptions = async () => {
    setLoading(true);
    try {
      const data = await bankPolicyApi.listExceptions();
      setExceptions(data);
    } catch (error) {
      console.error("Failed to load exceptions", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddException = async () => {
    if (!isBankAdmin) {
      toast({
        title: "Permission Denied",
        description: "Only bank admins can add exceptions",
        variant: "destructive",
      });
      return;
    }

    if (!newException.rule_code || !newException.reason) {
      toast({
        title: "Validation Error",
        description: "Rule code and reason are required",
        variant: "destructive",
      });
      return;
    }

    try {
      await bankPolicyApi.createException({
        ...newException,
        expires_at: newException.expires_at || undefined,
      });
      toast({
        title: "Success",
        description: "Exception added",
      });
      setAddOpen(false);
      setNewException({
        rule_code: "",
        scope: { client: "", branch: "", product: "" },
        reason: "",
        expires_at: "",
        effect: "waive",
      });
      loadExceptions();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to add exception",
        variant: "destructive",
      });
    }
  };

  const handleDeleteException = async (id: string) => {
    if (!isBankAdmin) {
      toast({
        title: "Permission Denied",
        description: "Only bank admins can delete exceptions",
        variant: "destructive",
      });
      return;
    }

    try {
      await bankPolicyApi.deleteException(id);
      toast({
        title: "Success",
        description: "Exception removed",
      });
      loadExceptions();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete exception",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Policy Exceptions</h3>
          <p className="text-sm text-muted-foreground">
            Define exceptions to policy rules for specific scopes
          </p>
        </div>
        {isBankAdmin && (
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Add Exception
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Policy Exception</DialogTitle>
                <DialogDescription>
                  Create an exception to waive or modify a rule for specific clients/branches/products
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="rule-code">Rule Code</Label>
                  <Input
                    id="rule-code"
                    placeholder="e.g., UCP600_ARTICLE_14_B"
                    value={newException.rule_code}
                    onChange={(e) =>
                      setNewException({ ...newException, rule_code: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Scope (optional)</Label>
                  <div className="grid grid-cols-3 gap-2">
                    <Input
                      placeholder="Client"
                      value={newException.scope.client}
                      onChange={(e) =>
                        setNewException({
                          ...newException,
                          scope: { ...newException.scope, client: e.target.value },
                        })
                      }
                    />
                    <Input
                      placeholder="Branch"
                      value={newException.scope.branch}
                      onChange={(e) =>
                        setNewException({
                          ...newException,
                          scope: { ...newException.scope, branch: e.target.value },
                        })
                      }
                    />
                    <Input
                      placeholder="Product"
                      value={newException.scope.product}
                      onChange={(e) =>
                        setNewException({
                          ...newException,
                          scope: { ...newException.scope, product: e.target.value },
                        })
                      }
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reason">Reason</Label>
                  <textarea
                    id="reason"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[80px]"
                    placeholder="Justification for this exception"
                    value={newException.reason}
                    onChange={(e) =>
                      setNewException({ ...newException, reason: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="effect">Effect</Label>
                  <select
                    id="effect"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={newException.effect}
                    onChange={(e) =>
                      setNewException({
                        ...newException,
                        effect: e.target.value as "waive" | "downgrade" | "override",
                      })
                    }
                  >
                    <option value="waive">Waive (rule failure is waived)</option>
                    <option value="downgrade">Downgrade (reduce severity)</option>
                    <option value="override">Override (rule result overridden)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="expires-at">Expires At (optional)</Label>
                  <Input
                    id="expires-at"
                    type="datetime-local"
                    value={newException.expires_at}
                    onChange={(e) =>
                      setNewException({ ...newException, expires_at: e.target.value })
                    }
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setAddOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleAddException}>Add Exception</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {loading ? (
        <div className="text-center py-8 text-muted-foreground">Loading...</div>
      ) : exceptions.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No exceptions defined. Add exceptions to waive or modify rules for specific scopes.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Active Exceptions</CardTitle>
            <CardDescription>
              Exceptions that modify or waive validation rules
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule Code</TableHead>
                  <TableHead>Scope</TableHead>
                  <TableHead>Effect</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {exceptions.map((exception) => (
                  <TableRow key={exception.id}>
                    <TableCell className="font-mono text-sm">
                      {exception.rule_code}
                    </TableCell>
                    <TableCell>
                      {Object.entries(exception.scope || {})
                        .filter(([_, v]) => v)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(", ") || "All"}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{exception.effect}</Badge>
                    </TableCell>
                    <TableCell>
                      {exception.expires_at
                        ? format(new Date(exception.expires_at), "PPp")
                        : "Never"}
                    </TableCell>
                    <TableCell className="text-right">
                      {isBankAdmin && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteException(exception.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function AnalyticsTab() {
  const { toast } = useToast();
  const [analytics, setAnalytics] = React.useState<PolicyAnalytics | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [timeRange, setTimeRange] = React.useState("30d");

  React.useEffect(() => {
    loadAnalytics();
  }, [timeRange]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const data = await bankPolicyApi.getAnalytics(timeRange);
      setAnalytics(data);
    } catch (error) {
      console.error("Failed to load analytics", error);
      toast({
        title: "Error",
        description: "Failed to load analytics data",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading analytics...</div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No analytics data available
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Time Range Selector */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" /> Policy Analytics
              </CardTitle>
              <CardDescription>
                Usage statistics and effectiveness metrics for policy overlays and exceptions
              </CardDescription>
            </div>
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="90d">Last 90 days</SelectItem>
                <SelectItem value="365d">Last year</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
      </Card>

      {/* Impact Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Policy Usage Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{analytics.impact_metrics.policy_usage_rate}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              {analytics.impact_metrics.validations_with_policy} of {analytics.impact_metrics.total_validations} validations
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Discrepancy Reduction
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold flex items-center gap-2">
              {analytics.impact_metrics.total_discrepancy_reduction}
              <TrendingDown className="h-5 w-5 text-green-600" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Avg {analytics.impact_metrics.avg_discrepancy_reduction_per_validation.toFixed(1)} per validation
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Overlay Applications
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {analytics.overlay_stats.reduce((sum, stat) => sum + stat.total_applications, 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Across {analytics.overlay_stats.length} overlay version(s)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Exception Applications
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {analytics.exception_stats.reduce((sum, stat) => sum + stat.total_applications, 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Across {analytics.exception_stats.length} exception(s)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Overlay Statistics */}
      {analytics.overlay_stats.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Overlay Usage Statistics</CardTitle>
            <CardDescription>Performance metrics for policy overlay versions</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Version</TableHead>
                  <TableHead>Applications</TableHead>
                  <TableHead>Unique Sessions</TableHead>
                  <TableHead>Avg Reduction</TableHead>
                  <TableHead>Avg Processing Time</TableHead>
                  <TableHead>Last Applied</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analytics.overlay_stats.map((stat, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <Badge variant="outline">v{stat.overlay_version}</Badge>
                    </TableCell>
                    <TableCell>{stat.total_applications}</TableCell>
                    <TableCell>{stat.unique_sessions}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {stat.avg_discrepancy_reduction > 0 ? (
                          <>
                            <TrendingDown className="h-4 w-4 text-green-600" />
                            <span className="text-green-600">{stat.avg_discrepancy_reduction.toFixed(1)}</span>
                          </>
                        ) : (
                          <span>{stat.avg_discrepancy_reduction.toFixed(1)}</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{stat.avg_processing_time_ms.toFixed(0)}ms</TableCell>
                    <TableCell>
                      {stat.last_applied_at
                        ? format(new Date(stat.last_applied_at), "MMM d, yyyy HH:mm")
                        : "Never"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Exception Effectiveness */}
      {analytics.exception_stats.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Exception Effectiveness</CardTitle>
            <CardDescription>Metrics for policy exceptions by rule</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule Code</TableHead>
                  <TableHead>Effect</TableHead>
                  <TableHead>Applications</TableHead>
                  <TableHead>Waived</TableHead>
                  <TableHead>Downgraded</TableHead>
                  <TableHead>Overridden</TableHead>
                  <TableHead>Avg Reduction</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analytics.exception_stats.map((stat, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="font-mono text-sm">{stat.rule_code}</TableCell>
                    <TableCell>
                      <Badge variant={stat.effect === "waive" ? "default" : "secondary"}>
                        {stat.effect}
                      </Badge>
                    </TableCell>
                    <TableCell>{stat.total_applications}</TableCell>
                    <TableCell>{stat.waived_count}</TableCell>
                    <TableCell>{stat.downgraded_count}</TableCell>
                    <TableCell>{stat.overridden_count}</TableCell>
                    <TableCell>
                      {stat.avg_discrepancy_reduction > 0 ? (
                        <span className="text-green-600">{stat.avg_discrepancy_reduction.toFixed(1)}</span>
                      ) : (
                        <span>{stat.avg_discrepancy_reduction.toFixed(1)}</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Top Exceptions */}
      {analytics.top_exceptions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Top Exceptions by Usage</CardTitle>
            <CardDescription>Most frequently applied exceptions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {analytics.top_exceptions.map((exc, idx) => (
                <div key={idx} className="flex items-center justify-between border-b pb-3 last:border-0">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm">{exc.rule_code}</span>
                      <Badge variant="outline">{exc.effect}</Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {exc.total_applications} applications • Avg reduction: {exc.avg_discrepancy_reduction.toFixed(1)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Most Affected Rules */}
      {analytics.impact_metrics.most_affected_rules.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Most Affected Rules</CardTitle>
            <CardDescription>Rules most frequently impacted by policy applications</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {analytics.impact_metrics.most_affected_rules.map((rule, idx) => (
                <div key={idx} className="flex items-center justify-between border-b pb-3 last:border-0">
                  <div className="space-y-1">
                    <span className="font-mono text-sm">{rule.rule_code}</span>
                    <div className="text-sm text-muted-foreground">
                      {rule.application_count} applications • Avg reduction: {rule.avg_discrepancy_reduction.toFixed(1)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Severity Changes */}
      {Object.keys(analytics.impact_metrics.severity_changes).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Severity Changes</CardTitle>
            <CardDescription>Net changes in discrepancy severity due to policy applications</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(analytics.impact_metrics.severity_changes).map(([severity, change]) => (
                <div key={severity} className="flex items-center justify-between">
                  <span className="capitalize">{severity}</span>
                  <div className="flex items-center gap-2">
                    {change > 0 ? (
                      <>
                        <TrendingUp className="h-4 w-4 text-red-600" />
                        <span className="text-red-600 font-semibold">+{change}</span>
                      </>
                    ) : change < 0 ? (
                      <>
                        <TrendingDown className="h-4 w-4 text-green-600" />
                        <span className="text-green-600 font-semibold">{change}</span>
                      </>
                    ) : (
                      <span>{change}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Overlay Adoption */}
      {analytics.overlay_adoption.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Overlay Version Adoption</CardTitle>
            <CardDescription>Session count by overlay version</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {analytics.overlay_adoption.map((adoption, idx) => (
                <div key={idx} className="flex items-center justify-between border-b pb-3 last:border-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">v{adoption.version}</Badge>
                    <span className="text-sm text-muted-foreground">
                      {adoption.session_count} validation session(s)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export function PolicySurface({ embedded = false }: { embedded?: boolean }) {
  const { user } = useAuth();
  const isBankAdmin = user?.role === "bank_admin" || user?.role === "system_admin";
  
  // Early return if not admin - defense in depth
  if (!isBankAdmin) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Access Denied</CardTitle>
          <CardDescription>
            Policy configuration is restricted to bank administrators only.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Bank officers can view active policies but cannot modify them. Contact your bank administrator for policy changes.
          </p>
        </CardContent>
      </Card>
    );
  }
  
  const [activeTab, setActiveTab] = React.useState("rulesets");

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Policy Surface</h2>
          <p className="text-muted-foreground">View active rulesets, configure overlays, and manage exceptions.</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="rulesets">Active Rulesets</TabsTrigger>
          <TabsTrigger value="overlays">Overlays</TabsTrigger>
          <TabsTrigger value="exceptions">Exceptions</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="rulesets" className="space-y-6">
          {/* Active Rulesets */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" /> Active Rulesets
              </CardTitle>
              <CardDescription>Currently active validation rulesets by domain and jurisdiction</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockActiveRulesets.map((ruleset, index) => (
                  <div key={index} className="border rounded-lg p-4 space-y-3">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-lg">{ruleset.rulebook_version}</h3>
                          <Badge variant="outline">{ruleset.ruleset_version}</Badge>
                          <StatusBadge status="success">
                            <CheckCircle2 className="h-3 w-3 mr-1" /> Active
                          </StatusBadge>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <Globe className="h-4 w-4" />
                            {ruleset.domain.toUpperCase()} / {ruleset.jurisdiction}
                          </div>
                          <div className="flex items-center gap-1">
                            <FileText className="h-4 w-4" />
                            {ruleset.rule_count} rules
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            Effective from {new Date(ruleset.effective_from).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                    </div>
                    {ruleset.effective_to && (
                      <div className="text-sm text-muted-foreground">
                        <AlertCircle className="h-4 w-4 inline mr-1" />
                        Scheduled to expire on {new Date(ruleset.effective_to).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Policy History */}
          <Card>
            <CardHeader>
              <CardTitle>Policy History</CardTitle>
              <CardDescription>Recent ruleset publication and rollback events</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockPolicyHistory.map((event) => (
                  <div key={event.id} className="flex items-center justify-between border-b pb-3 last:border-0">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={event.action === "published" ? "default" : "secondary"}>
                          {event.action}
                        </Badge>
                        <span className="font-medium">{event.rulebook_version}</span>
                        <Badge variant="outline">{event.ruleset_version}</Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {event.domain.toUpperCase()} / {event.jurisdiction} • Published by {event.published_by} • {new Date(event.published_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="overlays">
          <OverlaysTab />
        </TabsContent>

        <TabsContent value="exceptions">
          <ExceptionsTab />
        </TabsContent>

        <TabsContent value="analytics">
          <AnalyticsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

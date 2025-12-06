import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { 
  PieChart, 
  Search, 
  AlertTriangle,
  CheckCircle,
  Loader2,
  Clock,
  TrendingUp,
  Bell
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Quota {
  quota_number: string;
  quota_name: string;
  hs_codes: string[];
  fta_code?: string;
  quota_quantity: number;
  quota_unit?: string;
  quantity_used: number;
  fill_rate_percent: number;
  status: string;
  in_quota_rate?: number;
  over_quota_rate?: number;
  period_end?: string;
  days_remaining?: number;
  recommendation?: string;
}

interface QuotaAlert {
  quota_number: string;
  quota_name: string;
  fill_rate_percent: number;
  status: string;
  days_remaining?: number;
  in_quota_rate?: number;
  over_quota_rate?: number;
  rate_impact: number;
}

export default function HSCodeQuotas() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [alertsLoading, setAlertsLoading] = useState(false);
  
  // Search
  const [hsCode, setHsCode] = useState('');
  const [fta, setFta] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [quotas, setQuotas] = useState<Quota[]>([]);
  
  // Alerts
  const [threshold, setThreshold] = useState(75);
  const [alerts, setAlerts] = useState<QuotaAlert[]>([]);

  useEffect(() => {
    loadAlerts();
  }, [threshold]);

  const loadAlerts = async () => {
    setAlertsLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/hs-code/compliance/quotas/alerts?threshold=${threshold}`
      );
      if (response.ok) {
        const data = await response.json();
        setAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error('Failed to load alerts:', error);
    } finally {
      setAlertsLoading(false);
    }
  };

  const handleSearch = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (hsCode) params.append('hs_code', hsCode);
      if (fta !== 'all') params.append('fta', fta);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      
      const response = await fetch(`${API_BASE}/hs-code/compliance/quotas/search?${params}`);
      if (!response.ok) throw new Error('Search failed');
      
      const data = await response.json();
      setQuotas(data.quotas || []);
    } catch (error) {
      toast({
        title: 'Search failed',
        description: 'Could not search quotas',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCheckCode = async () => {
    if (!hsCode) {
      toast({
        title: 'Missing HS Code',
        description: 'Please enter an HS code to check',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/hs-code/compliance/quotas/check/${hsCode}${fta !== 'all' ? `?fta=${fta}` : ''}`
      );
      if (!response.ok) throw new Error('Check failed');
      
      const data = await response.json();
      setQuotas(data.quotas || []);
      
      if (!data.has_quotas) {
        toast({
          title: 'No quotas found',
          description: data.message || 'No active quotas for this HS code',
        });
      }
    } catch (error) {
      toast({
        title: 'Check failed',
        description: 'Could not check quota status',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'open':
        return <Badge className="bg-emerald-500">Open</Badge>;
      case 'near_full':
        return <Badge className="bg-amber-500">Near Full</Badge>;
      case 'full':
        return <Badge variant="destructive">Full</Badge>;
      case 'closed':
        return <Badge variant="secondary">Closed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getFillColor = (fillRate: number) => {
    if (fillRate >= 100) return 'bg-red-500';
    if (fillRate >= 90) return 'bg-red-400';
    if (fillRate >= 75) return 'bg-amber-500';
    if (fillRate >= 50) return 'bg-amber-400';
    return 'bg-emerald-500';
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Quota Status Monitoring</h1>
        <p className="text-slate-600 mt-1">
          Track tariff rate quota (TRQ) fill rates and availability
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Search/Check */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5 text-blue-600" />
              Check Quota Status
            </CardTitle>
            <CardDescription>
              Find applicable quotas for your product
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>HS Code</Label>
                <Input
                  placeholder="e.g., 0201.30.00"
                  value={hsCode}
                  onChange={(e) => setHsCode(e.target.value)}
                />
              </div>
              
              <div className="space-y-2">
                <Label>FTA/Agreement</Label>
                <Select value={fta} onValueChange={setFta}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Agreements</SelectItem>
                    <SelectItem value="USMCA">USMCA</SelectItem>
                    <SelectItem value="KORUS">Korea FTA</SelectItem>
                    <SelectItem value="CAFTA">CAFTA-DR</SelectItem>
                    <SelectItem value="AUSFTA">Australia FTA</SelectItem>
                    <SelectItem value="WTO">WTO/MFN</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="open">Open</SelectItem>
                    <SelectItem value="near_full">Near Full</SelectItem>
                    <SelectItem value="full">Full</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex gap-2">
              <Button onClick={handleCheckCode} disabled={loading}>
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Check HS Code
                  </>
                )}
              </Button>
              <Button variant="outline" onClick={handleSearch} disabled={loading}>
                Browse All Quotas
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-amber-500" />
              High Fill Alerts
            </CardTitle>
            <CardDescription>
              Quotas above {threshold}% capacity
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 mb-4">
              <Label className="text-xs">Alert Threshold</Label>
              <div className="flex gap-2">
                {[50, 75, 90].map((t) => (
                  <Button
                    key={t}
                    variant={threshold === t ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setThreshold(t)}
                  >
                    {t}%
                  </Button>
                ))}
              </div>
            </div>

            {alertsLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
              </div>
            ) : alerts.length > 0 ? (
              <div className="space-y-3">
                {alerts.slice(0, 5).map((alert, i) => (
                  <div key={i} className="p-3 border rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium truncate pr-2">
                        {alert.quota_name}
                      </span>
                      {getStatusBadge(alert.status)}
                    </div>
                    <div className="flex items-center gap-2">
                      <Progress 
                        value={Math.min(alert.fill_rate_percent, 100)} 
                        className="h-2 flex-1"
                      />
                      <span className="text-xs font-medium">
                        {alert.fill_rate_percent.toFixed(0)}%
                      </span>
                    </div>
                    {alert.rate_impact > 0 && (
                      <p className="text-xs text-amber-600 mt-1">
                        +{alert.rate_impact}% over-quota rate
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-slate-500">
                <CheckCircle className="h-8 w-8 mx-auto mb-2 text-emerald-500" />
                <p className="text-sm">No high-fill quotas</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quota Results */}
      {quotas.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Quota Results ({quotas.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {quotas.map((quota, i) => (
                <div key={i} className="p-4 border rounded-lg hover:bg-slate-50">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="font-mono text-xs">
                          {quota.quota_number}
                        </Badge>
                        {getStatusBadge(quota.status)}
                        {quota.fta_code && (
                          <Badge variant="secondary">{quota.fta_code}</Badge>
                        )}
                      </div>
                      <h3 className="font-medium">{quota.quota_name}</h3>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold">
                        {quota.fill_rate_percent.toFixed(1)}%
                      </div>
                      <span className="text-xs text-slate-500">fill rate</span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-slate-500 mb-1">
                      <span>
                        {quota.quantity_used.toLocaleString()} / {quota.quota_quantity.toLocaleString()} {quota.quota_unit || 'units'}
                      </span>
                      <span>
                        {(quota.quota_quantity - quota.quantity_used).toLocaleString()} remaining
                      </span>
                    </div>
                    <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all ${getFillColor(quota.fill_rate_percent)}`}
                        style={{ width: `${Math.min(quota.fill_rate_percent, 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* Rates */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-3 bg-slate-50 rounded-lg text-sm">
                    <div>
                      <span className="text-slate-500">In-Quota Rate</span>
                      <div className="font-medium text-emerald-600">
                        {quota.in_quota_rate !== undefined ? `${quota.in_quota_rate}%` : 'N/A'}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-500">Over-Quota Rate</span>
                      <div className="font-medium text-amber-600">
                        {quota.over_quota_rate !== undefined ? `${quota.over_quota_rate}%` : 'N/A'}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-500">Period Ends</span>
                      <div className="font-medium">
                        {quota.period_end 
                          ? new Date(quota.period_end).toLocaleDateString() 
                          : 'N/A'}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-500">Days Left</span>
                      <div className="font-medium flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {quota.days_remaining ?? 'N/A'}
                      </div>
                    </div>
                  </div>

                  {/* HS Codes */}
                  {quota.hs_codes && quota.hs_codes.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      <span className="text-xs text-slate-500">HS Codes:</span>
                      {quota.hs_codes.slice(0, 8).map((code, j) => (
                        <Badge key={j} variant="outline" className="text-xs font-mono">
                          {code}
                        </Badge>
                      ))}
                      {quota.hs_codes.length > 8 && (
                        <Badge variant="outline" className="text-xs">
                          +{quota.hs_codes.length - 8} more
                        </Badge>
                      )}
                    </div>
                  )}

                  {/* Recommendation */}
                  {quota.recommendation && (
                    <div className={`mt-3 p-2 rounded text-sm ${
                      quota.fill_rate_percent >= 90 
                        ? 'bg-red-50 text-red-700' 
                        : quota.fill_rate_percent >= 75 
                        ? 'bg-amber-50 text-amber-700'
                        : 'bg-emerald-50 text-emerald-700'
                    }`}>
                      <div className="flex items-center gap-2">
                        {quota.fill_rate_percent >= 90 ? (
                          <AlertTriangle className="h-4 w-4" />
                        ) : (
                          <TrendingUp className="h-4 w-4" />
                        )}
                        {quota.recommendation}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Info */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <h3 className="font-medium text-blue-900 mb-2">About Tariff Rate Quotas (TRQ)</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• TRQs allow a certain quantity of goods to enter at a lower "in-quota" duty rate</li>
            <li>• Once the quota is filled, additional imports face higher "over-quota" rates</li>
            <li>• Quotas typically reset annually or quarterly</li>
            <li>• Some quotas are first-come-first-served, others require licenses</li>
            <li>• Monitor fill rates closely to secure preferential rates</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}


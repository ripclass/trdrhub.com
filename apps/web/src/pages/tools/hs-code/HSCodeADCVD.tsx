import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Scale, 
  Search, 
  AlertTriangle,
  CheckCircle,
  Loader2,
  Globe,
  Percent,
  Calendar,
  FileText
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ADCVDOrder {
  case_number: string;
  order_type: string;
  product_name: string;
  country: string;
  country_name?: string;
  hs_codes: string[];
  all_others_rate?: number;
  current_deposit_rate?: number;
  status: string;
  order_date?: string;
  next_review_due?: string;
}

interface ADCVDCheck {
  hs_code: string;
  country: string;
  has_ad_cvd: boolean;
  orders: Array<{
    case_number: string;
    order_type: string;
    product_name: string;
    deposit_rate: number;
    scope?: string;
    company_specific_rates?: any[];
    next_review?: string;
    fr_citation?: string;
  }>;
  total_estimated_duty: number;
  message: string;
  recommendations?: string[];
}

interface Country {
  code: string;
  name: string;
  active_orders: number;
}

export default function HSCodeADCVD() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [countriesLoading, setCountriesLoading] = useState(false);
  
  // Check form
  const [hsCode, setHsCode] = useState('');
  const [country, setCountry] = useState('');
  const [checkResult, setCheckResult] = useState<ADCVDCheck | null>(null);
  
  // Search form
  const [searchProduct, setSearchProduct] = useState('');
  const [searchCountry, setSearchCountry] = useState('all');
  const [orderType, setOrderType] = useState('all');
  const [orders, setOrders] = useState<ADCVDOrder[]>([]);
  
  // Countries with orders
  const [countries, setCountries] = useState<Country[]>([]);

  useEffect(() => {
    loadCountries();
  }, []);

  const loadCountries = async () => {
    setCountriesLoading(true);
    try {
      const response = await fetch(`${API_BASE}/hs-code/compliance/ad-cvd/countries`);
      if (response.ok) {
        const data = await response.json();
        setCountries(data.countries || []);
      }
    } catch (error) {
      console.error('Failed to load countries:', error);
    } finally {
      setCountriesLoading(false);
    }
  };

  const handleCheck = async () => {
    if (!hsCode || !country) {
      toast({
        title: 'Missing information',
        description: 'Please enter both HS code and country',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/hs-code/compliance/ad-cvd/check?hs_code=${hsCode}&country=${country}`
      );
      if (!response.ok) throw new Error('Check failed');
      
      const data = await response.json();
      setCheckResult(data);
    } catch (error) {
      toast({
        title: 'Check failed',
        description: 'Could not check AD/CVD status',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    setSearchLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchProduct) params.append('product', searchProduct);
      if (searchCountry !== 'all') params.append('country', searchCountry);
      if (orderType !== 'all') params.append('order_type', orderType);
      
      const response = await fetch(`${API_BASE}/hs-code/compliance/ad-cvd/search?${params}`);
      if (!response.ok) throw new Error('Search failed');
      
      const data = await response.json();
      setOrders(data.orders || []);
    } catch (error) {
      toast({
        title: 'Search failed',
        description: 'Could not search AD/CVD orders',
        variant: 'destructive',
      });
    } finally {
      setSearchLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">AD/CVD Orders</h1>
        <p className="text-slate-600 mt-1">
          Check Antidumping (AD) and Countervailing Duty (CVD) orders on imports
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Check */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-blue-600" />
              Check AD/CVD Applicability
            </CardTitle>
            <CardDescription>
              Determine if AD/CVD duties apply to your product and country
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>HS Code *</Label>
                <Input
                  placeholder="e.g., 7306.30.5028"
                  value={hsCode}
                  onChange={(e) => setHsCode(e.target.value)}
                />
              </div>
              
              <div className="space-y-2">
                <Label>Origin Country *</Label>
                <Select value={country} onValueChange={setCountry}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select country..." />
                  </SelectTrigger>
                  <SelectContent>
                    {countries.map((c) => (
                      <SelectItem key={c.code} value={c.code}>
                        {c.name || c.code} ({c.active_orders} orders)
                      </SelectItem>
                    ))}
                    {countries.length === 0 && (
                      <>
                        <SelectItem value="CN">China</SelectItem>
                        <SelectItem value="IN">India</SelectItem>
                        <SelectItem value="KR">South Korea</SelectItem>
                        <SelectItem value="VN">Vietnam</SelectItem>
                        <SelectItem value="TW">Taiwan</SelectItem>
                        <SelectItem value="TH">Thailand</SelectItem>
                        <SelectItem value="MX">Mexico</SelectItem>
                        <SelectItem value="JP">Japan</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button onClick={handleCheck} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Checking...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Check AD/CVD Status
                </>
              )}
            </Button>

            {/* Check Results */}
            {checkResult && (
              <div className="mt-4 space-y-4">
                <div className={`p-4 rounded-lg border ${
                  checkResult.has_ad_cvd 
                    ? 'bg-amber-50 border-amber-200' 
                    : 'bg-emerald-50 border-emerald-200'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {checkResult.has_ad_cvd ? (
                      <AlertTriangle className="h-5 w-5 text-amber-600" />
                    ) : (
                      <CheckCircle className="h-5 w-5 text-emerald-600" />
                    )}
                    <span className="font-medium">
                      {checkResult.has_ad_cvd 
                        ? `AD/CVD Duties May Apply (${checkResult.total_estimated_duty}%)` 
                        : 'No AD/CVD Orders Found'}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600">{checkResult.message}</p>
                </div>

                {checkResult.orders.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-slate-700">Applicable Orders</h4>
                    {checkResult.orders.map((order, i) => (
                      <div key={i} className="p-4 border rounded-lg">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="outline" className="font-mono">
                                {order.case_number}
                              </Badge>
                              <Badge className={
                                order.order_type === 'AD' ? 'bg-blue-500' : 
                                order.order_type === 'CVD' ? 'bg-purple-500' : 'bg-slate-500'
                              }>
                                {order.order_type}
                              </Badge>
                            </div>
                            <p className="font-medium">{order.product_name}</p>
                          </div>
                          <div className="text-right">
                            <div className="flex items-center gap-1 text-amber-600 font-medium">
                              <Percent className="h-4 w-4" />
                              {order.deposit_rate}%
                            </div>
                            <span className="text-xs text-slate-500">deposit rate</span>
                          </div>
                        </div>
                        
                        {order.scope && (
                          <p className="text-sm text-slate-600 mb-2">{order.scope}</p>
                        )}
                        
                        <div className="flex items-center gap-4 text-xs text-slate-500">
                          {order.next_review && (
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              Next review: {new Date(order.next_review).toLocaleDateString()}
                            </span>
                          )}
                          {order.fr_citation && (
                            <span className="flex items-center gap-1">
                              <FileText className="h-3 w-3" />
                              {order.fr_citation}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {checkResult.recommendations && checkResult.recommendations.length > 0 && (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h4 className="font-medium text-blue-900 mb-2">Recommendations</h4>
                    <ul className="text-sm text-blue-800 space-y-1">
                      {checkResult.recommendations.map((rec, i) => (
                        <li key={i}>• {rec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Countries Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Countries with Orders
            </CardTitle>
          </CardHeader>
          <CardContent>
            {countriesLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
              </div>
            ) : countries.length > 0 ? (
              <div className="space-y-2">
                {countries.slice(0, 15).map((c) => (
                  <button
                    key={c.code}
                    onClick={() => {
                      setSearchCountry(c.code);
                      handleSearch();
                    }}
                    className="w-full flex items-center justify-between p-2 rounded hover:bg-slate-50 text-left"
                  >
                    <span className="text-sm">{c.name || c.code}</span>
                    <Badge variant="secondary">{c.active_orders}</Badge>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500 text-center py-4">
                No country data available
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Search Orders */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Search AD/CVD Orders
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-2 space-y-2">
              <Label>Product Name</Label>
              <Input
                placeholder="e.g., steel, aluminum, solar cells..."
                value={searchProduct}
                onChange={(e) => setSearchProduct(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Country</Label>
              <Select value={searchCountry} onValueChange={setSearchCountry}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Countries</SelectItem>
                  {countries.map((c) => (
                    <SelectItem key={c.code} value={c.code}>
                      {c.name || c.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Order Type</Label>
              <Select value={orderType} onValueChange={setOrderType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="AD">Antidumping (AD)</SelectItem>
                  <SelectItem value="CVD">Countervailing (CVD)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button onClick={handleSearch} disabled={searchLoading}>
            {searchLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Search Orders
              </>
            )}
          </Button>

          {/* Orders Results */}
          {orders.length > 0 && (
            <div className="mt-4 space-y-3">
              <p className="text-sm text-slate-500">{orders.length} orders found</p>
              {orders.map((order, i) => (
                <div key={i} className="p-4 border rounded-lg hover:bg-slate-50">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="font-mono text-xs">
                          {order.case_number}
                        </Badge>
                        <Badge className={
                          order.order_type === 'AD' ? 'bg-blue-500' : 
                          order.order_type === 'CVD' ? 'bg-purple-500' : 'bg-slate-500'
                        }>
                          {order.order_type}
                        </Badge>
                        <Badge variant={order.status === 'active' ? 'default' : 'secondary'}>
                          {order.status}
                        </Badge>
                      </div>
                      <p className="font-medium">{order.product_name}</p>
                      <p className="text-sm text-slate-500">
                        {order.country_name || order.country}
                      </p>
                    </div>
                    {(order.current_deposit_rate || order.all_others_rate) && (
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-amber-600 font-medium">
                          <Percent className="h-4 w-4" />
                          {order.current_deposit_rate || order.all_others_rate}%
                        </div>
                        <span className="text-xs text-slate-500">
                          {order.current_deposit_rate ? 'deposit rate' : 'all others rate'}
                        </span>
                      </div>
                    )}
                  </div>
                  
                  {order.hs_codes && order.hs_codes.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {order.hs_codes.slice(0, 5).map((code: string, j: number) => (
                        <Badge key={j} variant="outline" className="text-xs font-mono">
                          {code}
                        </Badge>
                      ))}
                      {order.hs_codes.length > 5 && (
                        <Badge variant="outline" className="text-xs">
                          +{order.hs_codes.length - 5} more
                        </Badge>
                      )}
                    </div>
                  )}
                  
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                    {order.order_date && (
                      <span>Order date: {new Date(order.order_date).toLocaleDateString()}</span>
                    )}
                    {order.next_review_due && (
                      <span>Next review: {new Date(order.next_review_due).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <h3 className="font-medium text-blue-900 mb-2">About AD/CVD Duties</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-blue-800">
            <div>
              <h4 className="font-medium mb-1">Antidumping (AD)</h4>
              <p>Duties imposed when foreign goods are sold in the US at less than fair value, injuring US industry.</p>
            </div>
            <div>
              <h4 className="font-medium mb-1">Countervailing Duties (CVD)</h4>
              <p>Duties imposed to offset subsidies provided by foreign governments to their exporters.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


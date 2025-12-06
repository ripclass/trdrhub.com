import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  FileText, 
  Search, 
  AlertTriangle, 
  CheckCircle,
  Clock,
  Loader2,
  ExternalLink,
  Calendar
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Section301Status {
  hs_code: string;
  is_subject_to_301: boolean;
  rate_info: {
    list_number: string;
    additional_duty_rate: number;
    effective_date: string;
    countries_affected?: string[];
  } | null;
  exclusions: Array<{
    exclusion_number: string;
    product_description: string;
    effective_to: string;
    days_remaining: number;
  }>;
  net_effect: string;
}

interface Exclusion {
  exclusion_number: string;
  list_number: string;
  hs_code: string;
  product_description: string;
  product_scope?: string;
  status: string;
  effective_from: string;
  effective_to: string;
  days_remaining: number;
  fr_citation?: string;
  extensions_count: number;
}

export default function HSCodeSection301() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  
  // Check status
  const [hsCode, setHsCode] = useState('');
  const [exportCountry, setExportCountry] = useState('CN');
  const [status, setStatus] = useState<Section301Status | null>(null);
  
  // Search exclusions
  const [searchHsCode, setSearchHsCode] = useState('');
  const [searchList, setSearchList] = useState('all');
  const [searchStatus, setSearchStatus] = useState('active');
  const [exclusions, setExclusions] = useState<Exclusion[]>([]);

  const handleCheckStatus = async () => {
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
        `${API_BASE}/hs-code/compliance/section-301/check/${hsCode}?export_country=${exportCountry}`
      );
      if (!response.ok) throw new Error('Check failed');
      
      const data = await response.json();
      setStatus(data);
    } catch (error) {
      toast({
        title: 'Check failed',
        description: 'Could not check Section 301 status',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSearchExclusions = async () => {
    setSearchLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchHsCode) params.append('hs_code', searchHsCode);
      if (searchList !== 'all') params.append('list_number', searchList);
      params.append('status', searchStatus);
      
      const response = await fetch(
        `${API_BASE}/hs-code/compliance/section-301/exclusions?${params}`
      );
      if (!response.ok) throw new Error('Search failed');
      
      const data = await response.json();
      setExclusions(data.exclusions || []);
    } catch (error) {
      toast({
        title: 'Search failed',
        description: 'Could not search exclusions',
        variant: 'destructive',
      });
    } finally {
      setSearchLoading(false);
    }
  };

  const getStatusBadge = (stat: string) => {
    switch (stat) {
      case 'active':
        return <Badge className="bg-emerald-500">Active</Badge>;
      case 'expired':
        return <Badge variant="secondary">Expired</Badge>;
      case 'extended':
        return <Badge className="bg-blue-500">Extended</Badge>;
      default:
        return <Badge variant="outline">{stat}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Section 301 Tariffs & Exclusions</h1>
        <p className="text-slate-600 mt-1">
          Check Section 301 tariff applicability and search for product exclusions
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Checker */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-600" />
              Check Section 301 Status
            </CardTitle>
            <CardDescription>
              Determine if your product is subject to Section 301 tariffs
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>HS Code *</Label>
              <Input
                placeholder="e.g., 8471.30.0100"
                value={hsCode}
                onChange={(e) => setHsCode(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Origin Country</Label>
              <Select value={exportCountry} onValueChange={setExportCountry}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CN">China</SelectItem>
                  <SelectItem value="HK">Hong Kong</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-slate-500">Section 301 tariffs primarily apply to China-origin goods</p>
            </div>

            <Button onClick={handleCheckStatus} disabled={loading} className="w-full">
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Checking...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Check Status
                </>
              )}
            </Button>

            {/* Status Results */}
            {status && (
              <div className="mt-4 space-y-4">
                <div className={`p-4 rounded-lg border ${
                  status.is_subject_to_301 
                    ? 'bg-amber-50 border-amber-200' 
                    : 'bg-emerald-50 border-emerald-200'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {status.is_subject_to_301 ? (
                      <AlertTriangle className="h-5 w-5 text-amber-600" />
                    ) : (
                      <CheckCircle className="h-5 w-5 text-emerald-600" />
                    )}
                    <span className="font-medium">
                      {status.is_subject_to_301 
                        ? 'Subject to Section 301 Tariffs' 
                        : 'Not Subject to Section 301 Tariffs'}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600">{status.net_effect}</p>
                </div>

                {status.rate_info && (
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium mb-2">Tariff Details</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <span className="text-slate-500">List:</span>
                      <span>List {status.rate_info.list_number}</span>
                      <span className="text-slate-500">Additional Duty:</span>
                      <span className="font-medium text-amber-600">
                        {status.rate_info.additional_duty_rate}%
                      </span>
                      {status.rate_info.effective_date && (
                        <>
                          <span className="text-slate-500">Effective:</span>
                          <span>{new Date(status.rate_info.effective_date).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {status.exclusions && status.exclusions.length > 0 && (
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                    <h4 className="font-medium text-emerald-700 mb-2">
                      Exclusions Available
                    </h4>
                    {status.exclusions.map((excl, i) => (
                      <div key={i} className="text-sm space-y-1 pb-2 border-b last:border-0">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {excl.exclusion_number}
                          </Badge>
                          <span className="text-xs text-slate-500">
                            {excl.days_remaining} days remaining
                          </span>
                        </div>
                        <p className="text-slate-600">{excl.product_description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Exclusions Search */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Search Exclusions
            </CardTitle>
            <CardDescription>
              Find Section 301 product exclusions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>HS Code (optional)</Label>
              <Input
                placeholder="Filter by HS code..."
                value={searchHsCode}
                onChange={(e) => setSearchHsCode(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>List</Label>
                <Select value={searchList} onValueChange={setSearchList}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Lists</SelectItem>
                    <SelectItem value="1">List 1 ($34B)</SelectItem>
                    <SelectItem value="2">List 2 ($16B)</SelectItem>
                    <SelectItem value="3">List 3 ($200B)</SelectItem>
                    <SelectItem value="4A">List 4A ($120B)</SelectItem>
                    <SelectItem value="4B">List 4B</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={searchStatus} onValueChange={setSearchStatus}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active Only</SelectItem>
                    <SelectItem value="expired">Expired</SelectItem>
                    <SelectItem value="all">All</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button onClick={handleSearchExclusions} disabled={searchLoading} className="w-full">
              {searchLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Search Exclusions'
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Exclusions Results */}
      {exclusions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Search Results ({exclusions.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {exclusions.map((excl, i) => (
                <div key={i} className="p-4 border rounded-lg hover:bg-slate-50">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-mono text-xs">
                        {excl.exclusion_number}
                      </Badge>
                      <Badge variant="secondary">List {excl.list_number}</Badge>
                      {getStatusBadge(excl.status)}
                    </div>
                    <span className="text-xs text-slate-500 font-mono">{excl.hs_code}</span>
                  </div>
                  
                  <p className="text-sm text-slate-700 mb-2">{excl.product_description}</p>
                  
                  {excl.product_scope && (
                    <p className="text-xs text-slate-500 mb-2">{excl.product_scope}</p>
                  )}
                  
                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {new Date(excl.effective_from).toLocaleDateString()} - {new Date(excl.effective_to).toLocaleDateString()}
                    </span>
                    
                    {excl.status === 'active' && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {excl.days_remaining} days remaining
                      </span>
                    )}
                    
                    {excl.extensions_count > 0 && (
                      <Badge variant="outline" className="text-xs">
                        {excl.extensions_count} extension{excl.extensions_count > 1 ? 's' : ''}
                      </Badge>
                    )}
                    
                    {excl.fr_citation && (
                      <a 
                        href={`https://www.federalregister.gov/documents/search?conditions%5Bterm%5D=${excl.fr_citation}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-blue-600 hover:underline"
                      >
                        <ExternalLink className="h-3 w-3" />
                        {excl.fr_citation}
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Info Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <h3 className="font-medium text-blue-900 mb-2">About Section 301 Tariffs</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Section 301 tariffs are additional duties on Chinese-origin goods</li>
            <li>• Rates range from 7.5% to 25% depending on the product list</li>
            <li>• Exclusions may be available for specific products</li>
            <li>• Exclusions have expiration dates and may be extended</li>
            <li>• Check if your product qualifies for an existing exclusion before importing</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}


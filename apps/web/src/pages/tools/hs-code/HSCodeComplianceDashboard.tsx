import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ShieldCheck, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  FileText,
  Scale,
  PieChart,
  Shield,
  ChevronRight
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Link } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface FullScreeningResult {
  product: string;
  hs_code?: string;
  export_country: string;
  import_country: string;
  screening_date: string;
  export_controls: {
    risk_level: string;
    license_required: boolean;
    eccn?: string;
    flags: string[];
  } | null;
  section_301: {
    is_subject: boolean;
    rate_info?: {
      list_number: string;
      additional_duty_rate: number;
    };
    exclusions_available: boolean;
  } | null;
  ad_cvd: {
    has_orders: boolean;
    total_duty: number;
    order_count: number;
  } | null;
  quotas: {
    has_quotas: boolean;
    quota_count: number;
    quotas: any[];
  } | null;
  overall_risk: string;
  total_flags: number;
  all_flags: string[];
  all_recommendations: string[];
  screening_id?: string;
}

export default function HSCodeComplianceDashboard() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  
  // Form
  const [productDescription, setProductDescription] = useState('');
  const [hsCode, setHsCode] = useState('');
  const [exportCountry, setExportCountry] = useState('CN');
  const [importCountry, setImportCountry] = useState('US');
  const [endUse, setEndUse] = useState('');
  const [endUser, setEndUser] = useState('');
  
  const [result, setResult] = useState<FullScreeningResult | null>(null);

  const handleFullScreening = async () => {
    if (!productDescription) {
      toast({
        title: 'Missing information',
        description: 'Please provide a product description',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/hs-code/compliance/full-screening`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_description: productDescription,
          hs_code: hsCode || undefined,
          export_country: exportCountry,
          import_country: importCountry,
          end_use: endUse || undefined,
          end_user: endUser || undefined,
        }),
      });

      if (!response.ok) throw new Error('Screening failed');
      
      const data = await response.json();
      setResult(data);
    } catch (error) {
      toast({
        title: 'Screening failed',
        description: 'Could not complete compliance screening',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const getRiskBadge = (risk: string) => {
    switch (risk) {
      case 'prohibited':
        return (
          <Badge variant="destructive" className="text-lg px-4 py-1">
            <XCircle className="h-4 w-4 mr-1" /> PROHIBITED
          </Badge>
        );
      case 'high':
        return (
          <Badge variant="destructive" className="text-lg px-4 py-1">
            <AlertTriangle className="h-4 w-4 mr-1" /> HIGH RISK
          </Badge>
        );
      case 'medium':
        return (
          <Badge className="bg-amber-500 text-lg px-4 py-1">
            <AlertTriangle className="h-4 w-4 mr-1" /> MEDIUM RISK
          </Badge>
        );
      default:
        return (
          <Badge className="bg-emerald-500 text-lg px-4 py-1">
            <CheckCircle className="h-4 w-4 mr-1" /> LOW RISK
          </Badge>
        );
    }
  };

  const complianceAreas = [
    {
      title: 'Export Controls',
      description: 'EAR/ITAR screening',
      icon: Shield,
      link: '/tools/hs-code/export-controls',
      color: 'text-blue-600',
    },
    {
      title: 'Section 301',
      description: 'Tariffs & exclusions',
      icon: FileText,
      link: '/tools/hs-code/section-301',
      color: 'text-purple-600',
    },
    {
      title: 'AD/CVD Orders',
      description: 'Trade remedy duties',
      icon: Scale,
      link: '/tools/hs-code/ad-cvd',
      color: 'text-amber-600',
    },
    {
      title: 'Quota Status',
      description: 'TRQ monitoring',
      icon: PieChart,
      link: '/tools/hs-code/quotas',
      color: 'text-emerald-600',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Compliance Suite</h1>
        <p className="text-slate-600 mt-1">
          Comprehensive trade compliance screening and monitoring
        </p>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {complianceAreas.map((area) => (
          <Link key={area.title} to={area.link}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
              <CardContent className="pt-4">
                <area.icon className={`h-8 w-8 ${area.color} mb-2`} />
                <h3 className="font-medium">{area.title}</h3>
                <p className="text-sm text-slate-500">{area.description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Full Screening Form */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-blue-600" />
              Full Compliance Screening
            </CardTitle>
            <CardDescription>
              Run comprehensive screening across all compliance areas
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Product Description *</Label>
              <Textarea
                placeholder="Describe the product, its specifications, materials, and intended use..."
                value={productDescription}
                onChange={(e) => setProductDescription(e.target.value)}
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label>HS Code (if known)</Label>
              <Input
                placeholder="e.g., 8471.30.0100"
                value={hsCode}
                onChange={(e) => setHsCode(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Origin Country</Label>
                <Select value={exportCountry} onValueChange={setExportCountry}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CN">China</SelectItem>
                    <SelectItem value="US">United States</SelectItem>
                    <SelectItem value="DE">Germany</SelectItem>
                    <SelectItem value="JP">Japan</SelectItem>
                    <SelectItem value="KR">South Korea</SelectItem>
                    <SelectItem value="IN">India</SelectItem>
                    <SelectItem value="VN">Vietnam</SelectItem>
                    <SelectItem value="MX">Mexico</SelectItem>
                    <SelectItem value="CA">Canada</SelectItem>
                    <SelectItem value="TW">Taiwan</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Destination Country</Label>
                <Select value={importCountry} onValueChange={setImportCountry}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="US">United States</SelectItem>
                    <SelectItem value="CA">Canada</SelectItem>
                    <SelectItem value="MX">Mexico</SelectItem>
                    <SelectItem value="DE">Germany</SelectItem>
                    <SelectItem value="GB">United Kingdom</SelectItem>
                    <SelectItem value="JP">Japan</SelectItem>
                    <SelectItem value="AU">Australia</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>End Use (optional)</Label>
                <Input
                  placeholder="Intended use"
                  value={endUse}
                  onChange={(e) => setEndUse(e.target.value)}
                />
              </div>
              
              <div className="space-y-2">
                <Label>End User (optional)</Label>
                <Input
                  placeholder="Company name"
                  value={endUser}
                  onChange={(e) => setEndUser(e.target.value)}
                />
              </div>
            </div>

            <Button onClick={handleFullScreening} disabled={loading} className="w-full">
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running Full Screening...
                </>
              ) : (
                <>
                  <ShieldCheck className="h-4 w-4 mr-2" />
                  Run Full Compliance Screening
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Screening Results</CardTitle>
          </CardHeader>
          <CardContent>
            {!result ? (
              <div className="text-center py-12 text-slate-500">
                <ShieldCheck className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Enter product details and run screening to see results</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Overall Risk */}
                <div className="text-center p-6 bg-slate-50 rounded-lg">
                  <p className="text-sm text-slate-500 mb-2">Overall Risk Assessment</p>
                  {getRiskBadge(result.overall_risk)}
                  <p className="text-sm text-slate-600 mt-2">
                    {result.total_flags} compliance flag{result.total_flags !== 1 ? 's' : ''} detected
                  </p>
                </div>

                {/* Area Summaries */}
                <div className="space-y-3">
                  {/* Export Controls */}
                  {result.export_controls && (
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Shield className="h-5 w-5 text-blue-600" />
                        <div>
                          <p className="font-medium">Export Controls</p>
                          <p className="text-sm text-slate-500">
                            {result.export_controls.eccn || 'EAR99'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {result.export_controls.license_required ? (
                          <Badge variant="destructive">License Required</Badge>
                        ) : (
                          <Badge className="bg-emerald-500">No License</Badge>
                        )}
                        <Link to="/tools/hs-code/export-controls">
                          <ChevronRight className="h-5 w-5 text-slate-400" />
                        </Link>
                      </div>
                    </div>
                  )}

                  {/* Section 301 */}
                  {result.section_301 && (
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 text-purple-600" />
                        <div>
                          <p className="font-medium">Section 301</p>
                          <p className="text-sm text-slate-500">
                            {result.section_301.is_subject
                              ? `${result.section_301.rate_info?.additional_duty_rate || 0}% additional duty`
                              : 'Not subject'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {result.section_301.is_subject ? (
                          <>
                            <Badge className="bg-amber-500">
                              +{result.section_301.rate_info?.additional_duty_rate || 0}%
                            </Badge>
                            {result.section_301.exclusions_available && (
                              <Badge variant="outline" className="text-emerald-600">
                                Exclusion Available
                              </Badge>
                            )}
                          </>
                        ) : (
                          <Badge className="bg-emerald-500">Clear</Badge>
                        )}
                        <Link to="/tools/hs-code/section-301">
                          <ChevronRight className="h-5 w-5 text-slate-400" />
                        </Link>
                      </div>
                    </div>
                  )}

                  {/* AD/CVD */}
                  {result.ad_cvd && (
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Scale className="h-5 w-5 text-amber-600" />
                        <div>
                          <p className="font-medium">AD/CVD</p>
                          <p className="text-sm text-slate-500">
                            {result.ad_cvd.has_orders
                              ? `${result.ad_cvd.order_count} order(s), ${result.ad_cvd.total_duty}% duty`
                              : 'No orders found'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {result.ad_cvd.has_orders ? (
                          <Badge className="bg-amber-500">
                            +{result.ad_cvd.total_duty}%
                          </Badge>
                        ) : (
                          <Badge className="bg-emerald-500">Clear</Badge>
                        )}
                        <Link to="/tools/hs-code/ad-cvd">
                          <ChevronRight className="h-5 w-5 text-slate-400" />
                        </Link>
                      </div>
                    </div>
                  )}

                  {/* Quotas */}
                  {result.quotas && (
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <PieChart className="h-5 w-5 text-emerald-600" />
                        <div>
                          <p className="font-medium">Quotas</p>
                          <p className="text-sm text-slate-500">
                            {result.quotas.has_quotas
                              ? `${result.quotas.quota_count} quota(s) apply`
                              : 'No quotas found'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {result.quotas.has_quotas ? (
                          <Badge variant="outline">Check Status</Badge>
                        ) : (
                          <Badge className="bg-emerald-500">N/A</Badge>
                        )}
                        <Link to="/tools/hs-code/quotas">
                          <ChevronRight className="h-5 w-5 text-slate-400" />
                        </Link>
                      </div>
                    </div>
                  )}
                </div>

                {/* Flags */}
                {result.all_flags && result.all_flags.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-slate-700">Compliance Flags</h4>
                    <ul className="space-y-1">
                      {result.all_flags.map((flag: string, i: number) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                          <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                          {flag}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Recommendations */}
                {result.all_recommendations && result.all_recommendations.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-slate-700">Recommendations</h4>
                    <ul className="space-y-1">
                      {result.all_recommendations.map((rec: string, i: number) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                          <CheckCircle className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}


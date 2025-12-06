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
  Shield, 
  Search, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  FileWarning,
  Loader2,
  Info,
  AlertCircle
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ScreeningResult {
  product: string;
  hs_code: string;
  export_country: string;
  import_country: string;
  ear_results: {
    eccn: string;
    category?: string;
    description?: string;
    control_reasons?: string[];
    license_exceptions?: string[];
    is_itar?: boolean;
  } | null;
  itar_results: {
    usml_category: string;
    description?: string;
    significant_military_equipment?: boolean;
    missile_technology?: boolean;
  } | null;
  overall_risk: string;
  license_required: boolean;
  flags: string[];
  recommendations: string[];
}

export default function HSCodeExportControls() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  
  // Screening form
  const [productDescription, setProductDescription] = useState('');
  const [hsCode, setHsCode] = useState('');
  const [exportCountry, setExportCountry] = useState('US');
  const [importCountry, setImportCountry] = useState('');
  const [endUse, setEndUse] = useState('');
  const [endUser, setEndUser] = useState('');
  
  const [result, setResult] = useState<ScreeningResult | null>(null);
  
  // ECCN search
  const [eccnQuery, setEccnQuery] = useState('');
  const [eccnResults, setEccnResults] = useState<any[]>([]);

  const handleScreen = async () => {
    if (!productDescription || !importCountry) {
      toast({
        title: 'Missing information',
        description: 'Please provide product description and destination country',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/hs-code/compliance/export-control/screen`, {
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
        description: 'Could not complete export control screening',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSearchECCN = async () => {
    if (!eccnQuery) return;
    
    setSearchLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/hs-code/compliance/eccn/search?query=${encodeURIComponent(eccnQuery)}`
      );
      if (!response.ok) throw new Error('Search failed');
      
      const data = await response.json();
      setEccnResults(data.results || []);
    } catch (error) {
      toast({
        title: 'Search failed',
        description: 'Could not search ECCN database',
        variant: 'destructive',
      });
    } finally {
      setSearchLoading(false);
    }
  };

  const getRiskBadge = (risk: string) => {
    switch (risk) {
      case 'prohibited':
        return <Badge variant="destructive" className="text-sm">PROHIBITED</Badge>;
      case 'high':
        return <Badge variant="destructive" className="text-sm">HIGH RISK</Badge>;
      case 'medium':
        return <Badge className="bg-amber-500 text-sm">MEDIUM RISK</Badge>;
      default:
        return <Badge variant="secondary" className="bg-emerald-500 text-white text-sm">LOW RISK</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Export Controls Screening</h1>
        <p className="text-slate-600 mt-1">
          Screen products against EAR (Export Administration Regulations) and ITAR controls
        </p>
      </div>

      <Tabs defaultValue="screen" className="space-y-4">
        <TabsList>
          <TabsTrigger value="screen">Product Screening</TabsTrigger>
          <TabsTrigger value="eccn">ECCN Search</TabsTrigger>
          <TabsTrigger value="itar">ITAR Categories</TabsTrigger>
        </TabsList>

        <TabsContent value="screen" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Screening Form */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-blue-600" />
                  Export Control Screening
                </CardTitle>
                <CardDescription>
                  Check if your product requires an export license
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Product Description *</Label>
                  <Textarea
                    placeholder="Describe the product, its technical specifications, and intended use..."
                    value={productDescription}
                    onChange={(e) => setProductDescription(e.target.value)}
                    rows={4}
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
                    <Label>Export From *</Label>
                    <Select value={exportCountry} onValueChange={setExportCountry}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="US">United States</SelectItem>
                        <SelectItem value="CA">Canada</SelectItem>
                        <SelectItem value="MX">Mexico</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Destination Country *</Label>
                    <Input
                      placeholder="e.g., DE, CN, JP"
                      value={importCountry}
                      onChange={(e) => setImportCountry(e.target.value.toUpperCase())}
                      maxLength={2}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>End Use (optional)</Label>
                  <Input
                    placeholder="Intended use of the product"
                    value={endUse}
                    onChange={(e) => setEndUse(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>End User (optional)</Label>
                  <Input
                    placeholder="Name of the end user/company"
                    value={endUser}
                    onChange={(e) => setEndUser(e.target.value)}
                  />
                </div>

                <Button onClick={handleScreen} disabled={loading} className="w-full">
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Screening...
                    </>
                  ) : (
                    <>
                      <Shield className="h-4 w-4 mr-2" />
                      Run Export Control Screening
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Results */}
            <Card>
              <CardHeader>
                <CardTitle>Screening Results</CardTitle>
              </CardHeader>
              <CardContent>
                {!result ? (
                  <div className="text-center py-12 text-slate-500">
                    <Shield className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>Enter product details and run screening to see results</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Risk Level */}
                    <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                      <span className="font-medium">Overall Risk Level</span>
                      {getRiskBadge(result.overall_risk)}
                    </div>

                    {/* License Required */}
                    <div className="flex items-center gap-3 p-4 border rounded-lg">
                      {result.license_required ? (
                        <AlertTriangle className="h-6 w-6 text-amber-500" />
                      ) : (
                        <CheckCircle className="h-6 w-6 text-emerald-500" />
                      )}
                      <div>
                        <p className="font-medium">
                          {result.license_required ? 'Export License May Be Required' : 'No License Required'}
                        </p>
                        <p className="text-sm text-slate-600">
                          {result.license_required 
                            ? 'Consult with compliance officer before proceeding'
                            : 'Product appears to be EAR99 or not controlled'}
                        </p>
                      </div>
                    </div>

                    {/* EAR Classification */}
                    {result.ear_results && (
                      <div className="space-y-2">
                        <h4 className="font-medium text-slate-700">EAR Classification</h4>
                        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="outline">{result.ear_results.eccn}</Badge>
                            {result.ear_results.category && (
                              <Badge variant="secondary">Category {result.ear_results.category}</Badge>
                            )}
                          </div>
                          {result.ear_results.description && (
                            <p className="text-sm text-slate-600">{result.ear_results.description}</p>
                          )}
                          {result.ear_results.control_reasons && result.ear_results.control_reasons.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {result.ear_results.control_reasons.map((reason: string) => (
                                <Badge key={reason} variant="outline" className="text-xs">
                                  {reason}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* ITAR Results */}
                    {result.itar_results && (
                      <div className="space-y-2">
                        <h4 className="font-medium text-slate-700">ITAR Classification</h4>
                        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                          <div className="flex items-center gap-2 mb-2">
                            <AlertCircle className="h-5 w-5 text-red-600" />
                            <span className="font-medium">USML Category {result.itar_results.usml_category}</span>
                          </div>
                          {result.itar_results.description && (
                            <p className="text-sm text-slate-600">{result.itar_results.description}</p>
                          )}
                          {result.itar_results.significant_military_equipment && (
                            <Badge variant="destructive" className="mt-2">
                              Significant Military Equipment
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Flags */}
                    {result.flags && result.flags.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="font-medium text-slate-700">Compliance Flags</h4>
                        <ul className="space-y-2">
                          {result.flags.map((flag: string, i: number) => (
                            <li key={i} className="flex items-start gap-2 text-sm">
                              <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                              {flag}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Recommendations */}
                    {result.recommendations && result.recommendations.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="font-medium text-slate-700">Recommendations</h4>
                        <ul className="space-y-2">
                          {result.recommendations.map((rec: string, i: number) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                              <Info className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
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
        </TabsContent>

        <TabsContent value="eccn" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                ECCN Database Search
              </CardTitle>
              <CardDescription>
                Search the Commerce Control List for Export Control Classification Numbers
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Search by ECCN (e.g., 3A001) or product description..."
                  value={eccnQuery}
                  onChange={(e) => setEccnQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearchECCN()}
                />
                <Button onClick={handleSearchECCN} disabled={searchLoading}>
                  {searchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                </Button>
              </div>

              {eccnResults.length > 0 && (
                <div className="space-y-3">
                  {eccnResults.map((item: any, i: number) => (
                    <div key={i} className="p-4 border rounded-lg hover:bg-slate-50">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className="font-mono">{item.eccn}</Badge>
                        {item.category && <Badge variant="outline">Category {item.category}</Badge>}
                        {item.is_itar && <Badge variant="destructive">ITAR</Badge>}
                      </div>
                      <p className="text-sm text-slate-600">{item.description}</p>
                      {item.control_reasons && item.control_reasons.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          <span className="text-xs text-slate-500">Control reasons:</span>
                          {item.control_reasons.map((reason: string) => (
                            <Badge key={reason} variant="secondary" className="text-xs">
                              {reason}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="itar" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileWarning className="h-5 w-5 text-red-600" />
                USML Categories (ITAR)
              </CardTitle>
              <CardDescription>
                US Munitions List categories under International Traffic in Arms Regulations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {[
                  { cat: 'I', name: 'Firearms, Close Assault Weapons and Combat Shotguns' },
                  { cat: 'II', name: 'Guns and Armament' },
                  { cat: 'III', name: 'Ammunition/Ordnance' },
                  { cat: 'IV', name: 'Launch Vehicles, Guided Missiles, Ballistic Missiles' },
                  { cat: 'V', name: 'Explosives and Energetic Materials' },
                  { cat: 'VI', name: 'Surface Vessels of War' },
                  { cat: 'VII', name: 'Ground Vehicles' },
                  { cat: 'VIII', name: 'Aircraft and Related Articles' },
                  { cat: 'IX', name: 'Military Training Equipment and Training' },
                  { cat: 'X', name: 'Personal Protective Equipment' },
                  { cat: 'XI', name: 'Military Electronics' },
                  { cat: 'XII', name: 'Fire Control, Range Finder, Optical and Guidance' },
                  { cat: 'XIII', name: 'Materials and Miscellaneous Articles' },
                  { cat: 'XIV', name: 'Toxicological Agents' },
                  { cat: 'XV', name: 'Spacecraft and Related Articles' },
                  { cat: 'XVI', name: 'Nuclear Weapons Related Articles' },
                  { cat: 'XVII', name: 'Classified Articles' },
                  { cat: 'XVIII', name: 'Directed Energy Weapons' },
                  { cat: 'XIX', name: 'Gas Turbine Engines and Associated Equipment' },
                  { cat: 'XX', name: 'Submersible Vessels and Related Articles' },
                  { cat: 'XXI', name: 'Articles, Technical Data, and Defense Services' },
                ].map((item) => (
                  <div key={item.cat} className="p-3 border rounded-lg">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-mono">
                        {item.cat}
                      </Badge>
                      <span className="text-sm">{item.name}</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}


/**
 * Binding Rulings Search Page
 * Phase 2: Search CBP CROSS rulings for classification precedent
 */
import { useState } from "react";
import { 
  Scale, Search, ExternalLink, FileText, Calendar,
  Info, Loader2, ChevronRight, BookOpen
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";

interface Ruling {
  ruling_number: string;
  ruling_type: string;
  product_description: string;
  hs_code: string;
  reasoning?: string;
  legal_reference?: string;
  ruling_date?: string;
  keywords?: string[];
}

interface RulingDetail extends Ruling {
  effective_date?: string;
  country: string;
  related_rulings: {
    ruling_number: string;
    product_description: string;
    hs_code: string;
  }[];
}

export default function HSCodeRulings() {
  const { toast } = useToast();
  
  const [searchQuery, setSearchQuery] = useState("");
  const [hsCodeFilter, setHsCodeFilter] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [rulings, setRulings] = useState<Ruling[]>([]);
  const [selectedRuling, setSelectedRuling] = useState<RulingDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  const searchRulings = async () => {
    if (!searchQuery.trim()) {
      toast({
        title: "Search required",
        description: "Please enter a search term",
        variant: "destructive"
      });
      return;
    }

    setIsSearching(true);
    setSelectedRuling(null);

    try {
      const params = new URLSearchParams({
        q: searchQuery,
        country: "US",
        limit: "20"
      });
      
      if (hsCodeFilter) {
        params.append("hs_code", hsCodeFilter);
      }

      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/rulings/search?${params}`
      );

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      setRulings(data.rulings || []);

      if (data.rulings.length === 0) {
        toast({
          title: "No rulings found",
          description: "Try different search terms or broaden your criteria"
        });
      }
    } catch (error) {
      toast({
        title: "Search failed",
        description: "Could not search binding rulings",
        variant: "destructive"
      });
    } finally {
      setIsSearching(false);
    }
  };

  const loadRulingDetail = async (rulingNumber: string) => {
    setIsLoadingDetail(true);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/rulings/${rulingNumber}`
      );

      if (!response.ok) {
        throw new Error('Failed to load ruling');
      }

      const data: RulingDetail = await response.json();
      setSelectedRuling(data);
    } catch (error) {
      toast({
        title: "Failed to load ruling",
        description: "Could not load ruling details",
        variant: "destructive"
      });
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      searchRulings();
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Scale className="h-5 w-5 text-emerald-400" />
            Binding Rulings Search
          </h1>
          <p className="text-sm text-slate-400">
            Search CBP CROSS database for classification precedent and rulings
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {/* Search Section */}
        <Card className="bg-slate-800 border-slate-700 mb-8">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <label className="text-sm text-slate-400 mb-1 block">Search Product or Ruling</label>
                <Input
                  placeholder="e.g., cotton t-shirt, laptop, N123456"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="bg-slate-900 border-slate-700"
                />
              </div>
              <div className="w-full md:w-48">
                <label className="text-sm text-slate-400 mb-1 block">HS Code Filter (Optional)</label>
                <Input
                  placeholder="e.g., 6109"
                  value={hsCodeFilter}
                  onChange={(e) => setHsCodeFilter(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="bg-slate-900 border-slate-700"
                />
              </div>
              <div className="flex items-end">
                <Button 
                  onClick={searchRulings}
                  disabled={isSearching}
                  className="bg-emerald-600 hover:bg-emerald-700 w-full md:w-auto"
                >
                  {isSearching ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Search className="h-4 w-4 mr-2" />
                      Search
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Search Tips */}
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="text-xs text-slate-500">Try:</span>
              {["laptop computer", "cotton textile", "plastic toys", "automotive parts"].map(term => (
                <Button
                  key={term}
                  variant="ghost"
                  size="sm"
                  className="text-xs h-6 text-slate-400 hover:text-white"
                  onClick={() => {
                    setSearchQuery(term);
                    setTimeout(searchRulings, 100);
                  }}
                >
                  {term}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Results List */}
          <div className="lg:col-span-2 space-y-4">
            {rulings.length > 0 ? (
              <>
                <div className="text-sm text-slate-400 mb-2">
                  Found {rulings.length} ruling{rulings.length !== 1 ? 's' : ''}
                </div>
                
                {rulings.map((ruling) => (
                  <Card 
                    key={ruling.ruling_number}
                    className={`bg-slate-800 border-slate-700 cursor-pointer transition-colors hover:border-emerald-600 ${
                      selectedRuling?.ruling_number === ruling.ruling_number ? 'border-emerald-500' : ''
                    }`}
                    onClick={() => loadRulingDetail(ruling.ruling_number)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="outline" className="font-mono">
                              {ruling.ruling_number}
                            </Badge>
                            <Badge 
                              variant="outline" 
                              className={ruling.ruling_type === 'HQ' ? 'border-purple-500 text-purple-400' : 'border-blue-500 text-blue-400'}
                            >
                              {ruling.ruling_type || 'NY'}
                            </Badge>
                            <Badge variant="outline" className="font-mono text-emerald-400">
                              {ruling.hs_code}
                            </Badge>
                          </div>
                          
                          <p className="text-white text-sm mb-2">
                            {ruling.product_description.substring(0, 200)}
                            {ruling.product_description.length > 200 ? '...' : ''}
                          </p>
                          
                          {ruling.ruling_date && (
                            <div className="flex items-center gap-1 text-xs text-slate-500">
                              <Calendar className="h-3 w-3" />
                              {new Date(ruling.ruling_date).toLocaleDateString()}
                            </div>
                          )}
                          
                          {ruling.keywords && ruling.keywords.length > 0 && (
                            <div className="flex gap-1 mt-2 flex-wrap">
                              {ruling.keywords.slice(0, 5).map((kw, idx) => (
                                <Badge key={idx} variant="secondary" className="text-xs">
                                  {kw}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                        
                        <ChevronRight className="h-5 w-5 text-slate-600 flex-shrink-0" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </>
            ) : (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-8 text-center">
                  <BookOpen className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-white font-medium mb-2">Search Binding Rulings</h3>
                  <p className="text-slate-400 text-sm">
                    Enter a product description or ruling number to find CBP classification precedents
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Detail Panel */}
          <div>
            {isLoadingDetail ? (
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-8 text-center">
                  <Loader2 className="h-8 w-8 animate-spin text-emerald-400 mx-auto" />
                  <p className="text-slate-400 mt-2">Loading ruling details...</p>
                </CardContent>
              </Card>
            ) : selectedRuling ? (
              <Card className="bg-slate-800 border-slate-700 sticky top-4">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-white text-base flex items-center gap-2">
                      <FileText className="h-4 w-4 text-emerald-400" />
                      {selectedRuling.ruling_number}
                    </CardTitle>
                    <a
                      href={`https://rulings.cbp.gov/ruling/${selectedRuling.ruling_number}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                  <CardDescription>
                    {selectedRuling.ruling_type === 'HQ' ? 'Headquarters Ruling' : 'New York Ruling'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="text-sm text-slate-400 mb-1">HS Code</div>
                    <Badge variant="outline" className="font-mono text-lg px-3 py-1 text-emerald-400">
                      {selectedRuling.hs_code}
                    </Badge>
                  </div>
                  
                  <div>
                    <div className="text-sm text-slate-400 mb-1">Product Description</div>
                    <p className="text-white text-sm">{selectedRuling.product_description}</p>
                  </div>
                  
                  {selectedRuling.reasoning && (
                    <div>
                      <div className="text-sm text-slate-400 mb-1">Classification Reasoning</div>
                      <p className="text-white text-sm bg-slate-900 p-3 rounded">
                        {selectedRuling.reasoning}
                      </p>
                    </div>
                  )}
                  
                  {selectedRuling.legal_reference && (
                    <div>
                      <div className="text-sm text-slate-400 mb-1">Legal Reference</div>
                      <p className="text-slate-300 text-xs font-mono bg-slate-900 p-2 rounded">
                        {selectedRuling.legal_reference}
                      </p>
                    </div>
                  )}
                  
                  <div className="flex gap-4 text-sm">
                    {selectedRuling.ruling_date && (
                      <div>
                        <div className="text-slate-400">Ruling Date</div>
                        <div className="text-white">
                          {new Date(selectedRuling.ruling_date).toLocaleDateString()}
                        </div>
                      </div>
                    )}
                    {selectedRuling.effective_date && (
                      <div>
                        <div className="text-slate-400">Effective</div>
                        <div className="text-white">
                          {new Date(selectedRuling.effective_date).toLocaleDateString()}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Related Rulings */}
                  {selectedRuling.related_rulings && selectedRuling.related_rulings.length > 0 && (
                    <div>
                      <div className="text-sm text-slate-400 mb-2">Related Rulings</div>
                      <div className="space-y-2">
                        {selectedRuling.related_rulings.map((r) => (
                          <div 
                            key={r.ruling_number}
                            className="bg-slate-900 p-2 rounded cursor-pointer hover:bg-slate-800"
                            onClick={() => loadRulingDetail(r.ruling_number)}
                          >
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="font-mono text-xs">
                                {r.ruling_number}
                              </Badge>
                              <Badge variant="outline" className="font-mono text-xs text-emerald-400">
                                {r.hs_code}
                              </Badge>
                            </div>
                            <p className="text-xs text-slate-400 mt-1">
                              {r.product_description.substring(0, 80)}...
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <Info className="h-8 w-8 text-blue-400 mb-3" />
                  <h4 className="text-white font-medium mb-2">About Binding Rulings</h4>
                  <p className="text-sm text-slate-400 mb-4">
                    CBP binding rulings provide official classification decisions that can be cited 
                    as precedent for similar products.
                  </p>
                  <div className="space-y-2 text-xs text-slate-500">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="border-blue-500 text-blue-400">NY</Badge>
                      <span>New York rulings (most common)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="border-purple-500 text-purple-400">HQ</Badge>
                      <span>Headquarters rulings (appeals)</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


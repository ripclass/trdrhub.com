/**
 * Bulk Classification Page
 * Phase 2: CSV upload/download, bulk processing
 */
import { useState, useCallback } from "react";
import { 
  Upload, FileSpreadsheet, Download, Info, CheckCircle2, 
  XCircle, Loader2, ArrowRight, FileText 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

interface BulkResult {
  row_id: string;
  description: string;
  hs_code: string;
  hs_description: string;
  confidence: number;
  mfn_rate: number;
  import_country: string;
  export_country?: string;
  fta_options?: { code: string; name: string }[];
}

interface BulkError {
  row_id: string;
  description: string;
  error: string;
}

interface BulkResponse {
  status: string;
  total_items: number;
  successful: number;
  failed: number;
  processing_time_seconds: number;
  results: BulkResult[];
  errors: BulkError[];
}

export default function HSCodeBulk() {
  const { token } = useAuth();
  const { toast } = useToast();
  
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<BulkResponse | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.name.endsWith('.csv')) {
      setFile(droppedFile);
      setResults(null);
    } else {
      toast({
        title: "Invalid file",
        description: "Please upload a CSV file",
        variant: "destructive"
      });
    }
  }, [toast]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile?.name.endsWith('.csv')) {
      setFile(selectedFile);
      setResults(null);
    } else {
      toast({
        title: "Invalid file",
        description: "Please upload a CSV file",
        variant: "destructive"
      });
    }
  }, [toast]);

  const downloadTemplate = async () => {
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/bulk-classify/download-template`
      );
      
      if (!response.ok) throw new Error('Failed to download template');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'bulk_classification_template.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast({
        title: "Download failed",
        description: "Could not download template",
        variant: "destructive"
      });
    }
  };

  const processFile = async () => {
    if (!file || !token) {
      toast({
        title: "Authentication required",
        description: "Please sign in to use bulk classification",
        variant: "destructive"
      });
      return;
    }

    setIsProcessing(true);
    setProgress(10);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 500);

      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/bulk-classify/upload?include_fta=true`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        }
      );

      clearInterval(progressInterval);
      setProgress(100);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Processing failed');
      }

      const data: BulkResponse = await response.json();
      setResults(data);

      toast({
        title: "Processing complete",
        description: `Classified ${data.successful} of ${data.total_items} products`
      });
    } catch (error) {
      toast({
        title: "Processing failed",
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: "destructive"
      });
    } finally {
      setIsProcessing(false);
      setProgress(0);
    }
  };

  const exportResults = async (format: 'csv' | 'json') => {
    if (!results || !token) return;

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/bulk-classify/export/latest?format=${format}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) throw new Error('Export failed');

      if (format === 'csv') {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `classifications_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } else {
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `classifications_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }
    } catch (error) {
      toast({
        title: "Export failed",
        description: "Could not export results",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Upload className="h-5 w-5 text-emerald-400" />
            Bulk Classification
          </h1>
          <p className="text-sm text-slate-400">
            Classify multiple products at once using CSV upload
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Upload Section */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Upload Products</CardTitle>
              <CardDescription>
                Upload a CSV file with product descriptions (max 500 rows)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div 
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
                  isDragging 
                    ? 'border-emerald-500 bg-emerald-500/10' 
                    : 'border-slate-600 hover:border-emerald-500'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-input')?.click()}
              >
                <input
                  id="file-input"
                  type="file"
                  accept=".csv"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                
                {file ? (
                  <>
                    <FileSpreadsheet className="h-10 w-10 mx-auto text-emerald-400 mb-3" />
                    <p className="text-white font-medium">{file.name}</p>
                    <p className="text-sm text-slate-400 mt-1">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="mt-2 text-slate-400"
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                        setResults(null);
                      }}
                    >
                      Change file
                    </Button>
                  </>
                ) : (
                  <>
                    <Upload className="h-10 w-10 mx-auto text-slate-500 mb-3" />
                    <p className="text-slate-400">Drag and drop your CSV file here</p>
                    <p className="text-sm text-slate-500 mt-1">or click to browse</p>
                    <Badge variant="outline" className="mt-3 border-slate-600">
                      <FileSpreadsheet className="h-3 w-3 mr-1" />
                      CSV up to 500 rows
                    </Badge>
                  </>
                )}
              </div>

              {isProcessing && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">Processing...</span>
                    <span className="text-emerald-400">{progress}%</span>
                  </div>
                  <Progress value={progress} className="h-2" />
                </div>
              )}

              <Button 
                className="w-full bg-emerald-600 hover:bg-emerald-700" 
                disabled={!file || isProcessing}
                onClick={processFile}
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <ArrowRight className="h-4 w-4 mr-2" />
                    Process File
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Template & Info Section */}
          <div className="space-y-4">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white text-base">Template Format</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-mono text-xs bg-slate-900 p-3 rounded overflow-x-auto">
                  <p className="text-slate-500"># Required columns:</p>
                  <p className="text-emerald-400">description, import_country, export_country, product_value</p>
                  <p className="text-slate-400 mt-2">"Cotton t-shirts",US,CN,10000</p>
                  <p className="text-slate-400">"Laptop computers",US,TW,50000</p>
                  <p className="text-slate-400">"Fresh organic apples",US,NZ,5000</p>
                </div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="mt-3"
                  onClick={downloadTemplate}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download Template
                </Button>
              </CardContent>
            </Card>

            <Card className="bg-blue-900/20 border-blue-800/50">
              <CardContent className="p-4 flex items-start gap-3">
                <Info className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-slate-400">
                  <p className="font-medium text-blue-400 mb-1">Bulk Classification Features</p>
                  <ul className="space-y-1">
                    <li>• AI-powered classification for each product</li>
                    <li>• MFN duty rates with Section 301 rates</li>
                    <li>• FTA eligibility identification</li>
                    <li>• Export results as CSV or JSON</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Results Section */}
        {results && (
          <Card className="mt-8 bg-slate-800 border-slate-700">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-white">Classification Results</CardTitle>
                <CardDescription>
                  Processed in {results.processing_time_seconds}s
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => exportResults('csv')}
                >
                  <FileSpreadsheet className="h-4 w-4 mr-2" />
                  Export CSV
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => exportResults('json')}
                >
                  <FileText className="h-4 w-4 mr-2" />
                  Export JSON
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {/* Summary */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-slate-900 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-white">{results.total_items}</div>
                  <div className="text-sm text-slate-400">Total Items</div>
                </div>
                <div className="bg-emerald-900/30 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-emerald-400">{results.successful}</div>
                  <div className="text-sm text-slate-400">Classified</div>
                </div>
                <div className="bg-red-900/30 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-red-400">{results.failed}</div>
                  <div className="text-sm text-slate-400">Failed</div>
                </div>
              </div>

              {/* Results Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-2 px-3 text-slate-400">#</th>
                      <th className="text-left py-2 px-3 text-slate-400">Product</th>
                      <th className="text-left py-2 px-3 text-slate-400">HS Code</th>
                      <th className="text-left py-2 px-3 text-slate-400">Confidence</th>
                      <th className="text-left py-2 px-3 text-slate-400">MFN Rate</th>
                      <th className="text-left py-2 px-3 text-slate-400">FTAs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.results.map((item, idx) => (
                      <tr key={idx} className="border-b border-slate-800">
                        <td className="py-2 px-3 text-slate-500">{item.row_id}</td>
                        <td className="py-2 px-3">
                          <div className="text-white">{item.description.substring(0, 40)}...</div>
                          <div className="text-xs text-slate-500">{item.hs_description?.substring(0, 50)}</div>
                        </td>
                        <td className="py-2 px-3">
                          <Badge variant="outline" className="font-mono">
                            {item.hs_code}
                          </Badge>
                        </td>
                        <td className="py-2 px-3">
                          <div className="flex items-center gap-2">
                            {item.confidence >= 0.8 ? (
                              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                            ) : (
                              <span className="h-4 w-4 rounded-full bg-yellow-500/20 border border-yellow-500" />
                            )}
                            <span className={item.confidence >= 0.8 ? 'text-emerald-400' : 'text-yellow-400'}>
                              {(item.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td className="py-2 px-3 text-white">{item.mfn_rate}%</td>
                        <td className="py-2 px-3">
                          {item.fta_options && item.fta_options.length > 0 ? (
                            <div className="flex gap-1 flex-wrap">
                              {item.fta_options.slice(0, 2).map(fta => (
                                <Badge 
                                  key={fta.code} 
                                  variant="outline" 
                                  className="text-xs border-blue-500/50 text-blue-400"
                                >
                                  {fta.code}
                                </Badge>
                              ))}
                              {item.fta_options.length > 2 && (
                                <Badge variant="outline" className="text-xs">
                                  +{item.fta_options.length - 2}
                                </Badge>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Errors */}
              {results.errors.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-red-400 font-medium mb-2 flex items-center gap-2">
                    <XCircle className="h-4 w-4" />
                    Failed Classifications ({results.errors.length})
                  </h4>
                  <div className="space-y-2">
                    {results.errors.map((error, idx) => (
                      <div key={idx} className="bg-red-900/20 border border-red-800/50 rounded p-3 text-sm">
                        <div className="text-white">Row {error.row_id}: {error.description}</div>
                        <div className="text-red-400 text-xs mt-1">{error.error}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

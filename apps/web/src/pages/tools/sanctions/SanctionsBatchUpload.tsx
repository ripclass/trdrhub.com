import { useState, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import {
  Upload,
  FileSpreadsheet,
  Download,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Loader2,
  FileText,
  Info,
} from "lucide-react";

interface BatchJob {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  total: number;
  processed: number;
  clear: number;
  potential_match: number;
  match: number;
  errors: number;
  started_at?: string;
  completed_at?: string;
}

export default function SanctionsBatchUpload() {
  const { toast } = useToast();
  const [screeningType, setScreeningType] = useState("party");
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [currentJob, setCurrentJob] = useState<BatchJob | null>(null);

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
    if (droppedFile && droppedFile.name.endsWith(".csv")) {
      setFile(droppedFile);
    } else {
      toast({
        title: "Invalid file",
        description: "Please upload a CSV file",
        variant: "destructive",
      });
    }
  }, [toast]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);

    try {
      // Simulate upload and processing
      // In production, would POST to /api/sanctions/batch/upload-csv
      
      await new Promise(resolve => setTimeout(resolve, 1000));

      const mockJob: BatchJob = {
        job_id: `batch-${Date.now()}`,
        status: "processing",
        total: 50,
        processed: 0,
        clear: 0,
        potential_match: 0,
        match: 0,
        errors: 0,
        started_at: new Date().toISOString(),
      };

      setCurrentJob(mockJob);

      // Simulate progress
      for (let i = 0; i <= 50; i++) {
        await new Promise(resolve => setTimeout(resolve, 100));
        setCurrentJob(prev => prev ? {
          ...prev,
          processed: i,
          clear: Math.floor(i * 0.8),
          potential_match: Math.floor(i * 0.15),
          match: Math.floor(i * 0.02),
          errors: Math.floor(i * 0.03),
          status: i === 50 ? "completed" : "processing",
          completed_at: i === 50 ? new Date().toISOString() : undefined,
        } : null);
      }

      toast({
        title: "Batch screening complete",
        description: "50 entities screened successfully",
      });

    } catch (error) {
      toast({
        title: "Upload failed",
        description: "Please try again",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownloadTemplate = () => {
    const templates: Record<string, string> = {
      party: "name,country\nAcme Trading Co,US\nGlobal Imports Ltd,GB\n",
      vessel: "name,imo,mmsi,flag_code\nM/V PACIFIC TRADER,9123456,123456789,PA\n",
      goods: "description,hs_code,destination_country\nIndustrial centrifuge,8421.19,IR\n",
    };

    const blob = new Blob([templates[screeningType]], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sanctions_screening_template_${screeningType}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadResults = () => {
    if (!currentJob) return;

    const csv = `name,status,risk_level,matches,certificate_id
Sample Company 1,clear,low,0,TRDR-${currentJob.job_id}-001
Sample Company 2,potential_match,medium,1,TRDR-${currentJob.job_id}-002
`;

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `screening_results_${currentJob.job_id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Upload className="w-6 h-6 text-red-400" />
          Batch Screening
        </h1>
        <p className="text-slate-400 mt-1">
          Upload a CSV file to screen multiple entities at once
        </p>
      </div>

      {/* Upload Card */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Upload CSV File</CardTitle>
          <CardDescription className="text-slate-400">
            Upload up to 1,000 entities per file
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Screening Type */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-white">Screening Type</label>
            <Select value={screeningType} onValueChange={setScreeningType}>
              <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="party" className="text-white">Party / Entity</SelectItem>
                <SelectItem value="vessel" className="text-white">Vessel</SelectItem>
                <SelectItem value="goods" className="text-white">Goods</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging
                ? "border-red-500 bg-red-500/10"
                : file
                ? "border-emerald-500/50 bg-emerald-500/5"
                : "border-slate-700 hover:border-slate-600"
            }`}
          >
            {file ? (
              <div className="space-y-2">
                <FileSpreadsheet className="w-12 h-12 text-emerald-400 mx-auto" />
                <p className="text-white font-medium">{file.name}</p>
                <p className="text-sm text-slate-400">{(file.size / 1024).toFixed(1)} KB</p>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setFile(null)}
                  className="text-slate-400 hover:text-white"
                >
                  Remove
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <Upload className="w-12 h-12 text-slate-500 mx-auto" />
                <div>
                  <p className="text-white font-medium">Drag and drop your CSV file here</p>
                  <p className="text-sm text-slate-400">or click to browse</p>
                </div>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="file-upload"
                />
                <Button
                  variant="outline"
                  className="border-slate-700 text-slate-400 hover:text-white"
                  onClick={() => document.getElementById("file-upload")?.click()}
                >
                  Select File
                </Button>
              </div>
            )}
          </div>

          {/* Template Download */}
          <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-slate-500" />
              <div>
                <p className="text-sm font-medium text-white">Need a template?</p>
                <p className="text-xs text-slate-500">Download our CSV template</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownloadTemplate}
              className="text-red-400 hover:text-red-300"
            >
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
          </div>

          {/* Upload Button */}
          <Button
            onClick={handleUpload}
            disabled={!file || isUploading}
            className="w-full bg-red-500 hover:bg-red-600 text-white"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                Start Batch Screening
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Progress / Results */}
      {currentJob && (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-white flex items-center gap-2">
                  {currentJob.status === "completed" ? (
                    <CheckCircle className="w-5 h-5 text-emerald-400" />
                  ) : currentJob.status === "failed" ? (
                    <XCircle className="w-5 h-5 text-red-400" />
                  ) : (
                    <Loader2 className="w-5 h-5 text-red-400 animate-spin" />
                  )}
                  {currentJob.status === "completed" ? "Screening Complete" : "Processing..."}
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Job ID: {currentJob.job_id}
                </CardDescription>
              </div>
              <Badge className={`${
                currentJob.status === "completed"
                  ? "bg-emerald-500/20 text-emerald-400"
                  : currentJob.status === "failed"
                  ? "bg-red-500/20 text-red-400"
                  : "bg-amber-500/20 text-amber-400"
              }`}>
                {currentJob.status}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Progress</span>
                <span className="text-white">{currentJob.processed} / {currentJob.total}</span>
              </div>
              <Progress 
                value={(currentJob.processed / currentJob.total) * 100} 
                className="h-2"
              />
            </div>

            {/* Results Summary */}
            <div className="grid grid-cols-4 gap-3">
              <div className="p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/30 text-center">
                <CheckCircle className="w-5 h-5 text-emerald-400 mx-auto mb-1" />
                <p className="text-lg font-bold text-emerald-400">{currentJob.clear}</p>
                <p className="text-xs text-slate-400">Clear</p>
              </div>
              <div className="p-3 bg-amber-500/10 rounded-lg border border-amber-500/30 text-center">
                <AlertTriangle className="w-5 h-5 text-amber-400 mx-auto mb-1" />
                <p className="text-lg font-bold text-amber-400">{currentJob.potential_match}</p>
                <p className="text-xs text-slate-400">Review</p>
              </div>
              <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/30 text-center">
                <XCircle className="w-5 h-5 text-red-400 mx-auto mb-1" />
                <p className="text-lg font-bold text-red-400">{currentJob.match}</p>
                <p className="text-xs text-slate-400">Match</p>
              </div>
              <div className="p-3 bg-slate-500/10 rounded-lg border border-slate-500/30 text-center">
                <Info className="w-5 h-5 text-slate-400 mx-auto mb-1" />
                <p className="text-lg font-bold text-slate-400">{currentJob.errors}</p>
                <p className="text-xs text-slate-400">Errors</p>
              </div>
            </div>

            {/* Download Results */}
            {currentJob.status === "completed" && (
              <div className="flex gap-3">
                <Button
                  onClick={handleDownloadResults}
                  className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download Results (CSV)
                </Button>
                <Button
                  variant="outline"
                  className="border-slate-700 text-slate-400 hover:text-white"
                  onClick={() => {
                    setCurrentJob(null);
                    setFile(null);
                  }}
                >
                  New Batch
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Instructions */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white text-sm">CSV Format Requirements</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <h4 className="font-medium text-white mb-2">Party Screening</h4>
              <code className="text-xs text-slate-400 block">
                name,country<br />
                Acme Trading,US<br />
                Global Corp,GB
              </code>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <h4 className="font-medium text-white mb-2">Vessel Screening</h4>
              <code className="text-xs text-slate-400 block">
                name,imo,flag_code<br />
                M/V STAR,9123456,PA<br />
                MT OCEAN,9876543,LR
              </code>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <h4 className="font-medium text-white mb-2">Goods Screening</h4>
              <code className="text-xs text-slate-400 block">
                description,hs_code,destination<br />
                Centrifuge,8421.19,IR<br />
                Electronics,8542.31,CN
              </code>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


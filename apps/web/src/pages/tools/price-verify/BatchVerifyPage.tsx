import { useState, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Upload, 
  FileText, 
  X, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle,
  Download,
  Loader2,
  Files,
  Trash2
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface BatchFile {
  id: string;
  file: File;
  status: "pending" | "processing" | "completed" | "error";
  result?: any;
  error?: string;
}

interface BatchSummary {
  total: number;
  passed: number;
  warnings: number;
  failed: number;
  tbmlFlags: number;
}

export default function BatchVerifyPage() {
  const { toast } = useToast();
  const [files, setFiles] = useState<BatchFile[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [summary, setSummary] = useState<BatchSummary | null>(null);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    const newFiles: BatchFile[] = selectedFiles.map((file, idx) => ({
      id: `${Date.now()}-${idx}`,
      file,
      status: "pending",
    }));
    setFiles(prev => [...prev, ...newFiles].slice(0, 20)); // Max 20 files
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    const newFiles: BatchFile[] = droppedFiles.map((file, idx) => ({
      id: `${Date.now()}-${idx}`,
      file,
      status: "pending",
    }));
    setFiles(prev => [...prev, ...newFiles].slice(0, 20));
  }, []);

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const clearAll = () => {
    setFiles([]);
    setSummary(null);
    setProgress(0);
  };

  const processFiles = async () => {
    if (files.length === 0) return;

    setIsProcessing(true);
    setProgress(0);
    setSummary(null);

    const results: BatchFile[] = [...files];
    let passed = 0, warnings = 0, failed = 0, tbmlFlags = 0;

    for (let i = 0; i < results.length; i++) {
      const file = results[i];
      results[i] = { ...file, status: "processing" };
      setFiles([...results]);

      try {
        const formData = new FormData();
        formData.append("file", file.file);
        formData.append("auto_verify", "true");

        const response = await fetch(`${API_BASE}/price-verify/extract`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error(await response.text());
        }

        const data = await response.json();
        results[i] = { ...file, status: "completed", result: data };

        // Count results
        if (data.summary) {
          passed += data.summary.passed || 0;
          warnings += data.summary.warnings || 0;
          failed += data.summary.failed || 0;
          tbmlFlags += data.summary.tbml_flags || 0;
        }
      } catch (err: any) {
        results[i] = { ...file, status: "error", error: err.message };
        failed++;
      }

      setFiles([...results]);
      setProgress(((i + 1) / results.length) * 100);
    }

    setSummary({
      total: results.length,
      passed,
      warnings,
      failed,
      tbmlFlags,
    });

    setIsProcessing(false);
    toast({
      title: "Batch Processing Complete",
      description: `Processed ${results.length} documents.`,
    });
  };

  const downloadReport = () => {
    // Generate CSV report
    const headers = ["File", "Status", "Items", "Passed", "Warnings", "Failed", "TBML Flags"];
    const rows = files.map(f => {
      if (f.status === "completed" && f.result?.summary) {
        const s = f.result.summary;
        return [f.file.name, "Completed", s.total_items, s.passed, s.warnings, s.failed, s.tbml_flags];
      }
      return [f.file.name, f.status, "-", "-", "-", "-", "-"];
    });

    const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `batch_verification_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Batch Verification</h1>
          <p className="text-muted-foreground">
            Upload multiple invoices or LCs for bulk price verification.
          </p>
        </div>
        {files.length > 0 && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={clearAll} disabled={isProcessing}>
              <Trash2 className="w-4 h-4 mr-2" />
              Clear All
            </Button>
            {summary && (
              <Button variant="outline" onClick={downloadReport}>
                <Download className="w-4 h-4 mr-2" />
                Download Report
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Upload Area */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Files className="w-5 h-5" />
            Upload Documents
          </CardTitle>
          <CardDescription>
            Drag & drop up to 20 documents for batch processing.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8 text-center hover:border-primary/50 transition-colors"
          >
            <Upload className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-lg font-medium mb-2">Drop files here or click to browse</p>
            <p className="text-sm text-muted-foreground mb-4">
              Supports PDF, JPG, PNG • Max 20 files • 20MB each
            </p>
            <input
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={handleFileSelect}
              className="hidden"
              id="batch-file-input"
            />
            <Button asChild variant="outline">
              <label htmlFor="batch-file-input" className="cursor-pointer">
                Select Files
              </label>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* File List */}
      {files.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Documents ({files.length})</CardTitle>
              {!isProcessing && !summary && (
                <Button onClick={processFiles}>
                  <Loader2 className="w-4 h-4 mr-2" />
                  Process All
                </Button>
              )}
            </div>
            {isProcessing && (
              <Progress value={progress} className="mt-2" />
            )}
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {files.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium text-sm">{f.file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {(f.file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {f.status === "pending" && (
                      <Badge variant="secondary">Pending</Badge>
                    )}
                    {f.status === "processing" && (
                      <Badge variant="default" className="animate-pulse">
                        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                        Processing
                      </Badge>
                    )}
                    {f.status === "completed" && (
                      <Badge variant="default" className="bg-green-600">
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        {f.result?.summary?.total_items || 0} items
                      </Badge>
                    )}
                    {f.status === "error" && (
                      <Badge variant="destructive">
                        <XCircle className="w-3 h-3 mr-1" />
                        Error
                      </Badge>
                    )}
                    {!isProcessing && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeFile(f.id)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary */}
      {summary && (
        <Card>
          <CardHeader>
            <CardTitle>Batch Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="text-center p-4 bg-muted rounded-lg">
                <p className="text-3xl font-bold">{summary.total}</p>
                <p className="text-sm text-muted-foreground">Documents</p>
              </div>
              <div className="text-center p-4 bg-green-500/10 rounded-lg">
                <p className="text-3xl font-bold text-green-600">{summary.passed}</p>
                <p className="text-sm text-muted-foreground">Passed</p>
              </div>
              <div className="text-center p-4 bg-yellow-500/10 rounded-lg">
                <p className="text-3xl font-bold text-yellow-600">{summary.warnings}</p>
                <p className="text-sm text-muted-foreground">Warnings</p>
              </div>
              <div className="text-center p-4 bg-red-500/10 rounded-lg">
                <p className="text-3xl font-bold text-red-600">{summary.failed}</p>
                <p className="text-sm text-muted-foreground">Failed</p>
              </div>
              <div className="text-center p-4 bg-purple-500/10 rounded-lg">
                <p className="text-3xl font-bold text-purple-600">{summary.tbmlFlags}</p>
                <p className="text-sm text-muted-foreground">TBML Flags</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}


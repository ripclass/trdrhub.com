import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { 
  FileText, 
  Upload, 
  X, 
  FileCheck, 
  AlertTriangle,
  ArrowLeft,
  Eye,
  Trash2,
  Plus,
  CheckCircle
} from "lucide-react";

interface UploadedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  status: "pending" | "uploading" | "completed" | "error";
  progress: number;
  preview?: string;
}

const documentTypes = [
  "Bill of Lading",
  "Commercial Invoice", 
  "Packing List",
  "Insurance Certificate",
  "Certificate of Origin",
  "Inspection Certificate",
  "Other"
];

export default function UploadLC() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [lcNumber, setLcNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const { toast } = useToast();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadedFile[] = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      name: file.name,
      size: file.size,
      type: file.type,
      status: "pending" as const,
      progress: 0
    }));

    setUploadedFiles(prev => [...prev, ...newFiles]);

    // Simulate file upload
    newFiles.forEach(file => {
      simulateUpload(file.id);
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxFiles: 10,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const simulateUpload = (fileId: string) => {
    setUploadedFiles(prev => 
      prev.map(file => 
        file.id === fileId ? { ...file, status: "uploading" as const } : file
      )
    );

    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 30;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        setUploadedFiles(prev => 
          prev.map(file => 
            file.id === fileId 
              ? { ...file, status: "completed" as const, progress: 100 }
              : file
          )
        );
      } else {
        setUploadedFiles(prev => 
          prev.map(file => 
            file.id === fileId ? { ...file, progress } : file
          )
        );
      }
    }, 200);
  };

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== fileId));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleProcessLC = async () => {
    if (uploadedFiles.length === 0) {
      toast({
        title: "No Files Selected",
        description: "Please upload at least one document to proceed.",
        variant: "destructive",
      });
      return;
    }

    if (!lcNumber.trim()) {
      toast({
        title: "LC Number Required",
        description: "Please enter the LC number before processing.",
        variant: "destructive",
      });
      return;
    }

    setIsProcessing(true);

    // Simulate processing
    try {
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      toast({
        title: "Processing Started",
        description: "Your LC documents are being validated. You'll be redirected to results.",
      });

      // Redirect to results page
      setTimeout(() => {
        window.location.href = `/results?lc=${encodeURIComponent(lcNumber)}`;
      }, 1500);
    } catch (error) {
      toast({
        title: "Processing Failed",
        description: "Something went wrong. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const completedFiles = uploadedFiles.filter(f => f.status === "completed");
  const isReadyToProcess = completedFiles.length > 0 && lcNumber.trim();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-gray-200">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <Button variant="outline" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="bg-gradient-primary p-2 rounded-lg">
                <Upload className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">Upload LC Documents</h1>
                <p className="text-sm text-muted-foreground">Upload and validate your Letter of Credit documents</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* LC Information */}
        <Card className="mb-8 shadow-soft border-0">
          <CardHeader>
            <CardTitle>LC Information</CardTitle>
            <CardDescription>
              Provide basic information about your Letter of Credit
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="lcNumber">LC Number *</Label>
                <Input
                  id="lcNumber"
                  placeholder="e.g., BD-2024-001"
                  value={lcNumber}
                  onChange={(e) => setLcNumber(e.target.value)}
                  className="mt-2"
                />
              </div>
              <div>
                <Label htmlFor="issueDate">Issue Date</Label>
                <Input
                  id="issueDate"
                  type="date"
                  className="mt-2"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="notes">Additional Notes (Optional)</Label>
              <Textarea
                id="notes"
                placeholder="Any special instructions or notes about this LC..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="mt-2"
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* File Upload Area */}
        <Card className="mb-8 shadow-soft border-0">
          <CardHeader>
            <CardTitle>Document Upload</CardTitle>
            <CardDescription>
              Upload your LC-related documents (PDF, JPG, PNG). Maximum 10 files, 10MB each.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                ${isDragActive 
                  ? "border-primary bg-primary/5" 
                  : "border-gray-200 hover:border-primary/50 hover:bg-secondary/20"
                }
              `}
            >
              <input {...getInputProps()} />
              <div className="flex flex-col items-center gap-4">
                <div className="bg-primary/10 p-4 rounded-full">
                  <Upload className="w-8 h-8 text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {isDragActive ? "Drop files here..." : "Upload Documents"}
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    Drag and drop your files here, or click to browse
                  </p>
                  <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
                    {documentTypes.map(type => (
                      <Badge key={type} variant="outline">{type}</Badge>
                    ))}
                  </div>
                </div>
                <Button variant="outline">
                  <Plus className="w-4 h-4 mr-2" />
                  Choose Files
                </Button>
              </div>
            </div>

            {/* Uploaded Files List */}
            {uploadedFiles.length > 0 && (
              <div className="mt-6 space-y-3">
                <h4 className="font-semibold text-foreground">Uploaded Files ({uploadedFiles.length})</h4>
                {uploadedFiles.map((file) => (
                  <div key={file.id} className="flex items-center gap-4 p-4 bg-secondary/20 rounded-lg border border-gray-200/50">
                    <div className="flex-shrink-0">
                      {file.status === "completed" ? (
                        <div className="bg-success/10 p-2 rounded-lg">
                          <FileCheck className="w-5 h-5 text-success" />
                        </div>
                      ) : file.status === "error" ? (
                        <div className="bg-destructive/10 p-2 rounded-lg">
                          <AlertTriangle className="w-5 h-5 text-destructive" />
                        </div>
                      ) : (
                        <div className="bg-primary/10 p-2 rounded-lg">
                          <FileText className="w-5 h-5 text-primary" />
                        </div>
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <h5 className="font-medium text-foreground truncate">{file.name}</h5>
                        <span className="text-sm text-muted-foreground">{formatFileSize(file.size)}</span>
                      </div>
                      
                      {file.status === "uploading" && (
                        <div className="space-y-2">
                          <Progress value={file.progress} className="h-1" />
                          <p className="text-xs text-muted-foreground">Uploading... {Math.round(file.progress)}%</p>
                        </div>
                      )}
                      
                      {file.status === "completed" && (
                        <div className="flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-success" />
                          <span className="text-xs text-success">Upload complete</span>
                        </div>
                      )}
                      
                      {file.status === "error" && (
                        <p className="text-xs text-destructive">Upload failed</p>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" disabled={file.status === "uploading"}>
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => removeFile(file.id)}
                        disabled={file.status === "uploading"}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Processing Section */}
        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle>Ready to Process</CardTitle>
            <CardDescription>
              Review your upload and start the LC validation process
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Summary */}
              <div className="bg-secondary/20 rounded-lg p-4 border border-gray-200/50">
                <h4 className="font-semibold text-foreground mb-3">Upload Summary</h4>
                <div className="grid md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">LC Number:</span>
                    <p className="font-medium">{lcNumber || "Not provided"}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Documents:</span>
                    <p className="font-medium">{completedFiles.length} files uploaded</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Total Size:</span>
                    <p className="font-medium">
                      {formatFileSize(completedFiles.reduce((acc, file) => acc + file.size, 0))}
                    </p>
                  </div>
                </div>
              </div>

              {/* Process Button */}
              <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  {isReadyToProcess ? (
                    <span className="text-success">✓ Ready to process your LC documents</span>
                  ) : (
                    <span>Please upload documents and provide LC number to continue</span>
                  )}
                </div>
                <div className="flex gap-3">
                  <Button variant="outline">
                    Save Draft
                  </Button>
                  <Button 
                    onClick={handleProcessLC}
                    disabled={!isReadyToProcess || isProcessing}
                    className="bg-gradient-primary hover:opacity-90"
                  >
                    {isProcessing ? "Processing..." : "Start Validation"}
                  </Button>
                </div>
              </div>

              {isProcessing && (
                <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full"></div>
                    <span className="font-medium text-primary">Processing your LC documents...</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    This may take up to 2-3 minutes. We're extracting data, checking compliance, and generating your report.
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
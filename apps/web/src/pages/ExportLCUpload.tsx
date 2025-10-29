import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useValidate } from "@/hooks/use-lcopilot";
import { useDrafts, type FileMeta, type FileData } from "@/hooks/use-drafts";
import { useVersions } from "@/hooks/use-versions";
import { RateLimitNotice } from "@/components/RateLimitNotice";
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
  documentType?: string; // Selected document type
}

const exportDocumentTypes = [
  { value: "lc", label: "Letter of Credit" },
  { value: "invoice", label: "Commercial Invoice" },
  { value: "packing_list", label: "Packing List" },
  { value: "bl", label: "Bill of Lading" },
  { value: "coo", label: "Certificate of Origin" },
  { value: "insurance", label: "Insurance Certificate" },
  { value: "other", label: "Other Trade Documents" }
];

export default function ExportLCUpload() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [lcNumber, setLcNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [showRateLimit, setShowRateLimit] = useState(false);
  const [currentDraftId, setCurrentDraftId] = useState<string | null>(null);
  const [isLoadingDraft, setIsLoadingDraft] = useState(false);
  const [issueDate, setIssueDate] = useState("");
  const [stagedFilesMeta, setStagedFilesMeta] = useState<FileMeta[]>([]);
  const [hasSessionFiles, setHasSessionFiles] = useState(false);
  const [versionInfo, setVersionInfo] = useState<{ exists: boolean; nextVersion: string; currentVersions: number } | null>(null);
  const [isCheckingLC, setIsCheckingLC] = useState(false);

  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { validate, isLoading: isValidating, clearError } = useValidate();
  const { saveDraft, loadDraft, removeDraft } = useDrafts();
  const { checkLCExists } = useVersions();

  // Load draft if draftId is provided in URL params
  useEffect(() => {
    const draftId = searchParams.get('draftId');
    if (draftId) {
      setIsLoadingDraft(true);
      setCurrentDraftId(draftId);

      try {
        const result = loadDraft(draftId);
        if (result) {
          const { draft, filesData } = result;

          // Populate form with draft data
          setLcNumber(draft.lcNumber || '');
          setIssueDate(draft.issueDate || '');
          setNotes(draft.notes || '');

          if (filesData.length > 0) {
            // Files available from session storage - restore them
            const restoredFiles: UploadedFile[] = filesData.map(fileData => ({
              id: fileData.id,
              file: new File([], fileData.name), // Placeholder file object
              name: fileData.name,
              size: fileData.size,
              type: fileData.type,
              status: fileData.status,
              progress: fileData.progress,
              documentType: fileData.documentType,
            }));

            setUploadedFiles(restoredFiles);
            setHasSessionFiles(true);

            toast({
              title: "Draft Loaded",
              description: `Resumed working on draft with ${filesData.length} files restored.`,
            });
          } else {
            // No files in session - show re-attach banner
            setStagedFilesMeta(draft.filesMeta || []);
            setHasSessionFiles(false);

            toast({
              title: "Draft Loaded",
              description: `Resumed working on draft. ${draft.filesMeta?.length || 0} files need to be re-attached.`,
            });
          }
        } else {
          toast({
            title: "Draft Not Found",
            description: "The requested draft could not be found.",
            variant: "destructive",
          });
        }
      } catch (error) {
        console.error('Failed to load draft:', error);
        toast({
          title: "Failed to Load Draft",
          description: "Could not load the saved draft. Please try again.",
          variant: "destructive",
        });
      } finally {
        setIsLoadingDraft(false);
      }
    }
  }, [searchParams, loadDraft, toast]);

  // Check if LC number exists when user enters it
  const handleLCNumberChange = async (value: string) => {
    setLcNumber(value);

    if (value.trim().length > 0) {
      setIsCheckingLC(true);
      try {
        const info = await checkLCExists(value.trim());
        setVersionInfo(info);
      } catch (error) {
        console.error('Failed to check LC:', error);
        setVersionInfo(null);
      } finally {
        setIsCheckingLC(false);
      }
    } else {
      setVersionInfo(null);
    }
  };

  const handleSaveDraft = () => {
    const completedFiles = uploadedFiles.filter(f => f.status === "completed");

    if (completedFiles.length === 0 && !lcNumber.trim() && !notes.trim()) {
      toast({
        title: "Nothing to Save",
        description: "Please upload some files or enter form data before saving a draft.",
        variant: "destructive",
      });
      return;
    }

    try {
      const filesMeta: FileMeta[] = completedFiles.map(file => ({
        name: file.name,
        size: file.size,
        type: file.type,
        tag: file.documentType,
      }));

      // Prepare files data for session storage (simplified)
      const filesData: FileData[] = completedFiles.map(file => ({
        id: file.id,
        name: file.name,
        size: file.size,
        type: file.type,
        documentType: file.documentType,
        status: file.status,
        progress: file.progress,
        // Note: Not storing actual file content for demo purposes
        // In production, you might want to store small files as base64
      }));

      const savedDraft = saveDraft({
        id: currentDraftId || undefined,
        lcNumber: lcNumber.trim() || undefined,
        issueDate: issueDate.trim() || undefined,
        notes: notes.trim() || undefined,
        filesMeta,
        filesData, // Save to session storage
      });

      setCurrentDraftId(savedDraft.id);

      toast({
        title: "Draft Saved",
        description: "Your progress has been saved. You can resume later from your dashboard.",
      });

      // Navigate to dashboard - user likely wants to work on other things
      navigate('/lcopilot/exporter-dashboard');
    } catch (error: any) {
      console.error('Failed to save draft:', error);
      toast({
        title: "Failed to Save Draft",
        description: error.message || "Could not save the draft. Please try again.",
        variant: "destructive",
      });
    }
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadedFile[] = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substring(2, 11),
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

  const updateFileDocumentType = (fileId: string, documentType: string) => {
    setUploadedFiles(prev =>
      prev.map(file =>
        file.id === fileId
          ? { ...file, documentType }
          : file
      )
    );
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handlePreviewFile = (file: UploadedFile) => {
    if (file.file && file.file.size > 0) {
      // Create a blob URL for the file
      const fileUrl = URL.createObjectURL(file.file);

      // Open in new tab for preview
      window.open(fileUrl, '_blank');

      // Clean up the object URL after a short delay
      setTimeout(() => {
        URL.revokeObjectURL(fileUrl);
      }, 1000);
    } else {
      toast({
        title: "Preview Unavailable",
        description: "This file cannot be previewed.",
        variant: "destructive",
      });
    }
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

    const completedFiles = uploadedFiles.filter(f => f.status === "completed");
    const files = completedFiles.map(f => f.file);

    // Create document tags mapping
    const documentTags: Record<string, string> = {};
    completedFiles.forEach(file => {
      documentTags[file.name] = file.documentType || 'other';
    });

    try {
      clearError();
      setShowRateLimit(false);

      toast({
        title: "Starting Document Validation",
        description: "Uploading documents and checking compliance...",
      });

      // For development/demo - create a mock jobId and navigate immediately
      // TODO: Replace with real API call when backend is ready
      const mockJobId = `job_${Date.now()}_${Math.random().toString(36).substring(2)}`;

      console.log('🔧 DEV MODE: Simulating validation with mock jobId:', mockJobId);
      console.log('📁 Files to validate:', files.map(f => f.name));
      console.log('🏷️  LC Number:', lcNumber.trim());
      console.log('📋 Document Tags:', documentTags);

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 2000));

      /*
      // Real API call - uncomment when backend is ready:
      const response = await validate({
        files,
        lcNumber: lcNumber.trim(),
        notes: notes.trim() || undefined,
        documentTags: documentTags,
      });
      */

      toast({
        title: "Validation In Progress",
        description: "Documents uploaded successfully. Redirecting to compliance results...",
      });

      // Remove draft from storage if we're working with a draft
      if (currentDraftId) {
        try {
          removeDraft(currentDraftId);
          console.log('✅ Draft removed after submission:', currentDraftId);
        } catch (error) {
          console.error('Failed to remove draft:', error);
        }
      }

      // Navigate to results page with jobId
      console.log('🚀 Navigating to results page with jobId:', mockJobId);
      setTimeout(() => {
        navigate(`/lcopilot/results/${mockJobId}`);
      }, 1500);

    } catch (error: any) {
      console.error('❌ Validation error:', error);
      if (error.type === 'rate_limit') {
        setShowRateLimit(true);
      } else {
        toast({
          title: "Validation Failed",
          description: error.message || "Something went wrong. Please try again.",
          variant: "destructive",
        });
      }
    }
  };

  const completedFiles = uploadedFiles.filter(f => f.status === "completed");
  const isReadyToProcess = completedFiles.length > 0 && lcNumber.trim() && !isValidating;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-gray-200">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link to="/lcopilot/exporter-dashboard">
              <Button variant="outline" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="bg-gradient-exporter p-2 rounded-lg">
                <Upload className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-bold text-foreground">Export LC & Trade Documents</h1>
                  {currentDraftId && (
                    <Badge variant="outline" className="text-xs">
                      Draft Mode
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  {currentDraftId
                    ? "Continue working on your saved draft"
                    : "Upload LC and trade documents to generate customs-ready pack"
                  }
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {isLoadingDraft && (
        <div className="container mx-auto px-4 py-8 max-w-4xl">
          <Card>
            <CardContent className="p-8 text-center">
              <div className="animate-spin w-8 h-8 border-2 border-exporter border-t-transparent rounded-full mx-auto mb-4"></div>
              <h3 className="text-lg font-semibold mb-2">Loading Draft...</h3>
              <p className="text-muted-foreground">Retrieving your saved progress.</p>
            </CardContent>
          </Card>
        </div>
      )}

      {!isLoadingDraft && (
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
                <div className="relative">
                  <Input
                    id="lcNumber"
                    placeholder="e.g., BD-2024-001"
                    value={lcNumber}
                    onChange={(e) => handleLCNumberChange(e.target.value)}
                    className="mt-2"
                  />
                  {isCheckingLC && (
                    <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                      <div className="animate-spin w-4 h-4 border-2 border-exporter border-t-transparent rounded-full"></div>
                    </div>
                  )}
                </div>
                {versionInfo?.exists && (
                  <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-md">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                      <div className="text-sm">
                        <p className="font-medium text-amber-800">
                          Amendment Detected
                        </p>
                        <p className="text-amber-700">
                          LC #{lcNumber} already exists with {versionInfo.currentVersions} version{versionInfo.currentVersions !== 1 ? 's' : ''}.
                          This upload will create <strong>{versionInfo.nextVersion}</strong>.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div>
                <Label htmlFor="issueDate">Issue Date</Label>
                <Input
                  id="issueDate"
                  type="date"
                  value={issueDate}
                  onChange={(e) => setIssueDate(e.target.value)}
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

        {/* Re-attach Files Banner - only show if no session files available */}
        {stagedFilesMeta.length > 0 && !hasSessionFiles && (
          <Card className="mb-6 border-blue-200 bg-blue-50">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="bg-blue-100 p-2 rounded-lg">
                  <FileText className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-blue-900 mb-2">Re-attach your files to continue</h4>
                  <p className="text-sm text-blue-700 mb-3">
                    Your files were saved in a previous session. Please re-attach the files listed below:
                  </p>
                  <div className="space-y-1">
                    {stagedFilesMeta.map((file, index) => (
                      <div key={index} className="text-sm text-blue-800 bg-blue-100 px-2 py-1 rounded inline-block mr-2 mb-1">
                        {file.name} ({(file.size / 1024 / 1024).toFixed(1)}MB)
                        {file.tag && <span className="ml-1 text-blue-600">• {exportDocumentTypes.find(t => t.value === file.tag)?.label || file.tag}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Session Files Restored Banner */}
        {hasSessionFiles && uploadedFiles.length > 0 && (
          <Card className="mb-6 border-green-200 bg-green-50">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="bg-green-100 p-2 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-green-900 mb-2">Files restored from draft</h4>
                  <p className="text-sm text-green-700">
                    Your uploaded files have been restored from your previous session. You can continue working or add more files.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* File Upload Area */}
        <Card className="mb-8 shadow-soft border-0">
          <CardHeader>
            <CardTitle>LC & Trade Documents Upload</CardTitle>
            <CardDescription>
              Upload LC and trade documents (Invoice, Packing List, BL, COO, etc.). Maximum 10 files, 10MB each.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                ${isDragActive 
                  ? "border-exporter bg-exporter/5" 
                  : "border-gray-200 hover:border-exporter/50 hover:bg-secondary/20"
                }
              `}
            >
              <input {...getInputProps()} />
              <div className="flex flex-col items-center gap-4">
                <div className="bg-exporter/10 p-4 rounded-full">
                  <Upload className="w-8 h-8 text-exporter" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {isDragActive ? "Drop files here..." : "Upload Documents"}
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    Drag and drop your files here, or click to browse
                  </p>
                  <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
                    {exportDocumentTypes.map(type => (
                      <Badge key={type.value} variant="outline">{type.label}</Badge>
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
                        <div className="bg-exporter/10 p-2 rounded-lg">
                          <FileText className="w-5 h-5 text-exporter" />
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
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <CheckCircle className="w-4 h-4 text-success" />
                            <span className="text-xs text-success">Upload complete</span>
                          </div>

                          {/* Document Type Selection */}
                          <div className="flex items-center gap-2">
                            <Label className="text-xs text-muted-foreground whitespace-nowrap">
                              Document Type:
                            </Label>
                            <Select
                              value={file.documentType || 'other'}
                              onValueChange={(value) => updateFileDocumentType(file.id, value)}
                            >
                              <SelectTrigger className="h-7 text-xs">
                                <SelectValue placeholder="Select type" />
                              </SelectTrigger>
                              <SelectContent>
                                {exportDocumentTypes.map((docType) => (
                                  <SelectItem key={docType.value} value={docType.value}>
                                    {docType.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      )}
                      
                      {file.status === "error" && (
                        <p className="text-xs text-destructive">Upload failed</p>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePreviewFile(file)}
                        disabled={file.status === "uploading"}
                        title="Preview file"
                      >
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

        {/* Validation Section */}
        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle>Document Validation</CardTitle>
            <CardDescription>
              Validate your LC and trade documents for compliance and completeness
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
                    <span className="text-success">✓ Ready to validate your export documents</span>
                  ) : (
                    <span>Please upload documents and provide LC number to continue</span>
                  )}
                </div>
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={handleSaveDraft}
                    disabled={isLoadingDraft}
                  >
                    {currentDraftId ? "Update Draft" : "Save Draft"}
                  </Button>
                  <Button
                    onClick={handleProcessLC}
                    disabled={!isReadyToProcess}
                    className="bg-gradient-exporter hover:opacity-90"
                  >
                    {isValidating ? (
                      <>
                        <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                        Validating Documents...
                      </>
                    ) : (
                      "Validate Documents"
                    )}
                  </Button>
                </div>
              </div>

              {isValidating && (
                <div className="bg-exporter/5 border border-exporter/20 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="animate-spin w-5 h-5 border-2 border-exporter border-t-transparent rounded-full"></div>
                    <span className="font-medium text-exporter">Validating your documents...</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Checking compliance, completeness, and regulatory requirements. This may take a few moments.
                  </p>
                </div>
              )}

              {showRateLimit && (
                <div className="mt-6">
                  <RateLimitNotice
                    onRetry={() => {
                      setShowRateLimit(false);
                      handleProcessLC();
                    }}
                    onCancel={() => setShowRateLimit(false)}
                  />
                </div>
              )}
            </div>
          </CardContent>
        </Card>
        </div>
      )}
    </div>
  );
}
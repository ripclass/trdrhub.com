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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useValidate, type ValidationError } from "@/hooks/use-lcopilot";
import { useDrafts, type DraftFile } from "@/hooks/use-drafts";
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
  CheckCircle,
  Shield,
  ClipboardCheck
} from "lucide-react";
import { QuotaLimitModal } from "@/components/billing/QuotaLimitModal";

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

const draftLCDocTypes = [
  { value: "lc", label: "Draft LC (PDF)" },
  { value: "swift", label: "SWIFT Message" },
  { value: "application", label: "LC Application Form" },
  { value: "proforma", label: "Proforma Invoice (PI)" },
  { value: "other", label: "Other Document" }
];

const supplierDocTypes = [
  { value: "invoice", label: "Commercial Invoice" },
  { value: "packing", label: "Packing List" },
  { value: "bill_of_lading", label: "Bill of Lading" },
  { value: "certificate_origin", label: "Certificate of Origin" },
  { value: "insurance", label: "Insurance Certificate" },
  { value: "other", label: "Other Trade Documents" }
];

export default function ImportLCUpload() {
  const [draftLCFiles, setDraftLCFiles] = useState<UploadedFile[]>([]);
  const [supplierFiles, setSupplierFiles] = useState<UploadedFile[]>([]);
  const [lcNumber, setLcNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState<"draft" | "supplier">("draft");
  const [currentDraftId, setCurrentDraftId] = useState<string | null>(null);
  const [isLoadingDraft, setIsLoadingDraft] = useState(false);

  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  const { validate, isLoading: isValidating } = useValidate();
  const { createDraft, getDraft, updateDraft, markDraftSubmitted, isLoading: isDraftLoading } = useDrafts();
  const navigate = useNavigate();
  const [quotaError, setQuotaError] = useState<ValidationError | null>(null);
  const [showQuotaModal, setShowQuotaModal] = useState(false);

  // Load draft if draft_id and type are provided in URL params
  useEffect(() => {
    const draftId = searchParams.get('draft_id');
    const draftType = searchParams.get('type');

    if (draftId && draftType) {
      setIsLoadingDraft(true);
      setCurrentDraftId(draftId);

      // Set the active tab based on draft type
      if (draftType === 'draft') {
        setActiveTab('draft');
      } else if (draftType === 'supplier') {
        setActiveTab('supplier');
      }

      getDraft(draftId)
        .then(draft => {
          // Populate form with draft data
          setLcNumber(draft.lc_number || '');
          setNotes(draft.notes || '');

          // Convert draft files to uploaded files format
          const draftFiles: UploadedFile[] = draft.uploaded_docs.map(draftFile => ({
            id: draftFile.id,
            file: draftFile.file || new File([], draftFile.name), // Create placeholder file
            name: draftFile.name,
            size: draftFile.size,
            type: draftFile.type,
            status: "completed" as const,
            progress: 100,
            documentType: draftFile.documentType,
          }));

          // Set files to the appropriate tab based on draft type
          if (draft.draft_type === 'importer_draft') {
            setDraftLCFiles(draftFiles);
          } else if (draft.draft_type === 'importer_supplier') {
            setSupplierFiles(draftFiles);
          }

          toast({
            title: "Draft Loaded",
            description: `Resumed working on ${draft.draft_type === 'importer_draft' ? 'Draft LC Risk' : 'Supplier Document'} draft with ${draft.uploaded_docs.length} files.`,
          });
        })
        .catch(error => {
          console.error('Failed to load draft:', error);
          toast({
            title: "Failed to Load Draft",
            description: "Could not load the saved draft. Please try again.",
            variant: "destructive",
          });
        })
        .finally(() => {
          setIsLoadingDraft(false);
        });
    }
  }, [searchParams, getDraft, toast]);

  const handleSaveDraft = async (draftType: 'draft' | 'supplier') => {
    const files = draftType === 'draft' ? draftLCFiles : supplierFiles;
    const completedFiles = files.filter(f => f.status === "completed");

    if (completedFiles.length === 0 && !lcNumber.trim()) {
      toast({
        title: "Nothing to Save",
        description: "Please upload some files or enter an LC number before saving a draft.",
        variant: "destructive",
      });
      return;
    }

    try {
      const draftFiles: DraftFile[] = completedFiles.map(file => ({
        id: file.id,
        name: file.name,
        size: file.size,
        type: file.type,
        documentType: file.documentType,
        file: file.file,
      }));

      const apiDraftType = draftType === 'draft' ? 'importer_draft' : 'importer_supplier';

      let savedDraft;
      if (currentDraftId) {
        // Update existing draft
        savedDraft = await updateDraft(currentDraftId, {
          lc_number: lcNumber.trim() || undefined,
          notes: notes.trim() || undefined,
          files: draftFiles,
        });
      } else {
        // Create new draft
        savedDraft = await createDraft({
          draft_type: apiDraftType,
          lc_number: lcNumber.trim() || undefined,
          notes: notes.trim() || undefined,
          files: draftFiles,
        });
        setCurrentDraftId(savedDraft.draft_id);
      }

      toast({
        title: "Draft Saved",
        description: `Your ${draftType === 'draft' ? 'Draft LC Risk' : 'Supplier Document'} progress has been saved. You can resume later from your dashboard.`,
      });

      // Navigate to dashboard - consistent with exporter flow
      navigate('/lcopilot/importer-dashboard');
    } catch (error: any) {
      console.error('Failed to save draft:', error);
      toast({
        title: "Failed to Save Draft",
        description: error.message || "Could not save the draft. Please try again.",
        variant: "destructive",
      });
    }
  };

  const createDropHandler = (fileType: "draft" | "supplier") => 
    useCallback((acceptedFiles: File[]) => {
      const newFiles: UploadedFile[] = acceptedFiles.map(file => ({
        id: Math.random().toString(36).substring(2, 11),
        file,
        name: file.name,
        size: file.size,
        type: file.type,
        status: "pending" as const,
        progress: 0
      }));

      if (fileType === "draft") {
        setDraftLCFiles(prev => [...prev, ...newFiles]);
      } else {
        setSupplierFiles(prev => [...prev, ...newFiles]);
      }

      // Simulate file upload
      newFiles.forEach(file => {
        simulateUpload(file.id, fileType);
      });
    }, []);

  const { getRootProps: getDraftRootProps, getInputProps: getDraftInputProps, isDragActive: isDraftDragActive } = useDropzone({
    onDrop: createDropHandler("draft"),
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxFiles: 5,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const { getRootProps: getSupplierRootProps, getInputProps: getSupplierInputProps, isDragActive: isSupplierDragActive } = useDropzone({
    onDrop: createDropHandler("supplier"),
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxFiles: 10,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const simulateUpload = (fileId: string, fileType: "draft" | "supplier") => {
    const setFiles = fileType === "draft" ? setDraftLCFiles : setSupplierFiles;
    
    setFiles(prev => 
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
        setFiles(prev => 
          prev.map(file => 
            file.id === fileId 
              ? { ...file, status: "completed" as const, progress: 100 }
              : file
          )
        );
      } else {
        setFiles(prev => 
          prev.map(file => 
            file.id === fileId ? { ...file, progress } : file
          )
        );
      }
    }, 200);
  };

  const removeFile = (fileId: string, fileType: "draft" | "supplier") => {
    if (fileType === "draft") {
      setDraftLCFiles(prev => prev.filter(file => file.id !== fileId));
    } else {
      setSupplierFiles(prev => prev.filter(file => file.id !== fileId));
    }
  };

  const updateFileDocumentType = (fileId: string, fileType: "draft" | "supplier", documentType: string) => {
    const setFiles = fileType === "draft" ? setDraftLCFiles : setSupplierFiles;
    setFiles(prev =>
      prev.map(file =>
        file.id === fileId ? { ...file, documentType } : file
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

  const handleProcessLC = async (processType: "draft" | "supplier") => {
    const files = processType === "draft" ? draftLCFiles : supplierFiles;
    const completedFiles = files.filter(f => f.status === "completed");

    if (completedFiles.length === 0) {
      toast({
        title: "No Files Selected",
        description: `Please upload at least one ${processType === "draft" ? "draft LC" : "supplier"} document to proceed.`,
        variant: "destructive",
      });
      return;
    }

    // Check if all completed files have document types selected
    const filesWithoutTypes = completedFiles.filter(f => !f.documentType);
    if (filesWithoutTypes.length > 0) {
      toast({
        title: "Document Types Required",
        description: `Please select document types for all uploaded files before processing.`,
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

    try {
      // Create document tags mapping
      const documentTags: Record<string, string> = {};
      completedFiles.forEach(file => {
        if (file.documentType) {
          documentTags[file.name] = file.documentType;
        }
      });

      // Determine workflow type based on process type
      const workflowType = processType === "draft" ? "draft-lc-risk" : "supplier-document-check";

      console.log("Starting validation request...");

      // Call validation API
      const response = await validate({
        files: completedFiles.map(f => f.file),
        lcNumber,
        notes,
        documentTags,
        userType: "importer",
        workflowType
      });

      const processTitle = processType === "draft" ? "LC Risk Analysis Started" : "Compliance Check Started";
      const processDescription = processType === "draft"
        ? "Your draft LC is being analyzed for risks and unfavorable terms."
        : "Your supplier documents are being checked against LC requirements.";

      toast({
        title: processTitle,
        description: processDescription,
      });

      // Navigate to unified results page with mode parameter
      navigate(`/import/results/${response.jobId}?mode=${processType}`);

    } catch (error: any) {
      console.error("Validation failed:", error);
      console.log("Error type:", error.type);
      console.log("Error code:", error.code);
      console.log("Error name:", error.name);
      console.log("Error details:", error);

      if (error.type === 'quota') {
        setQuotaError(error);
        setShowQuotaModal(true);
        return;
      }

      // Check for network errors (either our ValidationError type or raw Axios errors)
      const isNetworkError =
        error.type === 'network' ||
        error.type === 'server' ||
        error.code === 'ERR_NETWORK' ||
        error.name === 'AxiosError' ||
        !error.type;

      // For demo purposes: if API fails (likely due to backend not running),
      // create a mock job ID and redirect to results page with demo data
      if (isNetworkError) {
        console.log("API unavailable, redirecting to demo results...");

        const mockJobId = `demo-${processType}-${Date.now()}`;

        toast({
          title: "Demo Mode",
          description: "API unavailable - showing demo results with sample data.",
        });

        // Mark draft as submitted if we're working with a draft
        if (currentDraftId) {
          try {
            await markDraftSubmitted(currentDraftId);
            console.log('✅ Draft marked as submitted:', currentDraftId);
          } catch (error) {
            console.error('Failed to mark draft as submitted:', error);
          }
        }

        // Navigate to unified results page with mode parameter
        navigate(`/import/results/${mockJobId}?mode=${processType}`);
        return; // Exit early, don't show error
      }

      // Handle other specific error types
      if (error.type === 'rate_limit') {
        toast({
          title: "Rate Limit Exceeded",
          description: error.message || "Too many requests. Please try again later.",
          variant: "destructive",
        });
      } else if (error.type === 'validation') {
        toast({
          title: "Validation Failed",
          description: error.message || "Document validation failed. Please check your files.",
          variant: "destructive",
        });
      } else {
        // Fallback - also redirect to demo for any unhandled errors
        console.log("Unhandled error, falling back to demo mode...");

        const mockJobId = `demo-${processType}-${Date.now()}`;

        toast({
          title: "Demo Mode",
          description: "Processing unavailable - showing demo results with sample data.",
        });

        // Mark draft as submitted if we're working with a draft
        if (currentDraftId) {
          try {
            await markDraftSubmitted(currentDraftId);
            console.log('✅ Draft marked as submitted:', currentDraftId);
          } catch (error) {
            console.error('Failed to mark draft as submitted:', error);
          }
        }

        navigate(`/import/results/${mockJobId}?mode=${processType}`);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const renderFileUploadSection = (
    fileType: "draft" | "supplier",
    files: UploadedFile[],
    getRootProps: any,
    getInputProps: any,
    isDragActive: boolean,
    documentTypes: Array<{ value: string; label: string }>,
    title: string,
    description: string
  ) => {
    const completedFiles = files.filter(f => f.status === "completed");
    
    return (
      <div className="space-y-6">
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
            ${isDragActive 
              ? "border-importer bg-importer/5" 
              : "border-gray-200 hover:border-importer/50 hover:bg-secondary/20"
            }
          `}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-4">
            <div className="bg-importer/10 p-4 rounded-full">
              {fileType === "draft" ? (
                <Shield className="w-8 h-8 text-importer" />
              ) : (
                <ClipboardCheck className="w-8 h-8 text-importer" />
              )}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                {isDragActive ? "Drop files here..." : title}
              </h3>
              <p className="text-muted-foreground mb-4">
                {description}
              </p>
              <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
                {documentTypes.map(type => (
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

        {files.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-semibold text-foreground">Uploaded Files ({files.length})</h4>
            {files.map((file) => (
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
                    <div className="bg-importer/10 p-2 rounded-lg">
                      <FileText className="w-5 h-5 text-importer" />
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

                  {file.status === "completed" && (
                    <div className="mt-2">
                      <Label htmlFor={`doc-type-${file.id}`} className="text-xs text-muted-foreground">
                        Document Type
                      </Label>
                      <Select
                        value={file.documentType || ""}
                        onValueChange={(value) => updateFileDocumentType(file.id, fileType, value)}
                      >
                        <SelectTrigger className="mt-1 h-8 text-xs">
                          <SelectValue placeholder="Select document type" />
                        </SelectTrigger>
                        <SelectContent>
                          {documentTypes.map((docType) => (
                            <SelectItem key={docType.value} value={docType.value}>
                              {docType.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
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
                    onClick={() => removeFile(file.id, fileType)}
                    disabled={file.status === "uploading"}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle>
              {fileType === "draft" ? "Start LC Risk Analysis" : "Start Compliance Check"}
            </CardTitle>
            <CardDescription>
              {fileType === "draft" 
                ? "Analyze draft LC terms for risks and unfavorable clauses"
                : "Check supplier documents against LC requirements"
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div className="bg-secondary/20 rounded-lg p-4 border border-gray-200/50">
                <h4 className="font-semibold text-foreground mb-3">Summary</h4>
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

              <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  {completedFiles.length > 0 && lcNumber.trim() ? (
                    <span className="text-success">
                      ✓ Ready to {fileType === "draft" ? "analyze LC risks" : "check compliance"}
                    </span>
                  ) : (
                    <span>Please upload documents and provide LC number to continue</span>
                  )}
                </div>
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={() => handleSaveDraft(fileType)}
                    disabled={isDraftLoading || isLoadingDraft}
                  >
                    {isDraftLoading ? "Saving..." : (currentDraftId ? "Update Draft" : "Save Draft")}
                  </Button>
                  <Button
                    onClick={() => handleProcessLC(fileType)}
                    disabled={!(completedFiles.length > 0 && lcNumber.trim()) || isProcessing || isValidating}
                    className="bg-gradient-importer hover:opacity-90"
                  >
                    {(isProcessing || isValidating) ? "Processing..." : (fileType === "draft" ? "Analyze LC Risks" : "Check Compliance")}
                  </Button>
                </div>
              </div>

              {isProcessing && (
                <div className="bg-importer/5 border border-importer/20 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="animate-spin w-5 h-5 border-2 border-importer border-t-transparent rounded-full"></div>
                    <span className="font-medium text-importer">
                      {fileType === "draft" ? "Analyzing LC terms for risks..." : "Checking document compliance..."}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {fileType === "draft" 
                      ? "Reviewing LC clauses for potential risks, timeline issues, and unfavorable terms that may cause supplier rejections."
                      : "Validating supplier documents against LC requirements and checking for discrepancies."
                    }
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-gray-200">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link to="/lcopilot/importer-dashboard">
              <Button variant="outline" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="bg-gradient-importer p-2 rounded-lg">
                <Upload className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-bold text-foreground">Import LC Management</h1>
                  {currentDraftId && (
                    <Badge variant="outline" className="text-xs">
                      Draft Mode
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  {currentDraftId
                    ? "Continue working on your saved draft"
                    : "Analyze draft LC risks and check supplier document compliance"
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
              <div className="animate-spin w-8 h-8 border-2 border-importer border-t-transparent rounded-full mx-auto mb-4"></div>
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

        {/* Tabs for Different Workflows */}
        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle>Document Upload & Processing</CardTitle>
            <CardDescription>
              Choose your workflow: analyze draft LC for risks or check supplier documents for compliance
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "draft" | "supplier")}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="draft" className="flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  Draft LC Risk Analysis
                </TabsTrigger>
                <TabsTrigger value="supplier" className="flex items-center gap-2">
                  <ClipboardCheck className="w-4 h-4" />
                  Supplier Document Check
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="draft" className="mt-6">
                {renderFileUploadSection(
                  "draft",
                  draftLCFiles,
                  getDraftRootProps,
                  getDraftInputProps,
                  isDraftDragActive,
                  draftLCDocTypes,
                  "Upload Draft LC for Risk Analysis",
                  "Upload your bank's draft LC to identify risky clauses and potential supplier rejection points"
                )}
              </TabsContent>
              
              <TabsContent value="supplier" className="mt-6">
                {renderFileUploadSection(
                  "supplier",
                  supplierFiles,
                  getSupplierRootProps,
                  getSupplierInputProps,
                  isSupplierDragActive,
                  supplierDocTypes,
                  "Upload Supplier Documents for Compliance Check",
                  "Upload supplier's trade documents to verify compliance against your LC requirements"
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
        </div>
      )}

      <QuotaLimitModal
        open={showQuotaModal}
        onClose={() => setShowQuotaModal(false)}
        message={quotaError?.message ?? 'Your validation quota has been reached.'}
        quota={quotaError?.quota}
        nextActionUrl={quotaError?.nextActionUrl}
      />
    </div>
  );
}
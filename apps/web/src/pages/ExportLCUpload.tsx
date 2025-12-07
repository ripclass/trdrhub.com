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
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { useValidate } from "@/hooks/use-lcopilot";
import { useLCopilotV2 } from "@/hooks/use-lcopilot-v2";
import { useFeature } from "@/config/features-v2";
import { cn } from "@/lib/utils";
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

type ExportLCUploadProps = {
  embedded?: boolean;
  onComplete?: (payload: { jobId: string; lcNumber: string }) => void;
};

export default function ExportLCUpload({ embedded = false, onComplete }: ExportLCUploadProps = {}) {
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
  const [showDocTypeErrors, setShowDocTypeErrors] = useState(false);

  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialLcTypeParam = (searchParams.get('lcType') || '').toLowerCase();
  const initialLcTypeOverride: 'auto' | 'export' | 'import' =
    initialLcTypeParam === 'export' || initialLcTypeParam === 'import'
      ? (initialLcTypeParam as 'export' | 'import')
      : 'auto';
  const [lcTypeOverride, setLcTypeOverride] = useState<'auto' | 'export' | 'import'>(initialLcTypeOverride);
  const [useV2Pipeline, setUseV2Pipeline] = useState(false);
  
  // V1 validation hook
  const { validate, isLoading: isValidating, clearError } = useValidate();
  
  // V2 validation hook
  const { validate: validateV2, isLoading: isValidatingV2, results: v2Results } = useLCopilotV2();
  
  // Check if user has V2 access
  const hasV2Access = useFeature('USE_V2_API');
  
  const { saveDraft, loadDraft, removeDraft } = useDrafts();
  const { checkLCExists } = useVersions();
  
  // Combined loading state
  const isProcessing = isValidating || isValidatingV2;

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
              documentType: fileData.documentType || "other",
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

      // Navigate back to dashboard only when in standalone mode
      if (!embedded) {
        navigate('/lcopilot/exporter-dashboard');
      }
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
      progress: 0,
      documentType: "other",
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
    setUploadedFiles((prev) => {
      const updated = prev.map((file) =>
        file.id === fileId ? { ...file, documentType } : file
      );
      if (showDocTypeErrors) {
        const completed = updated.filter((file) => file.status === "completed");
        if (completed.length > 0 && completed.every((file) => !!file.documentType)) {
          setShowDocTypeErrors(false);
        }
      }
      return updated;
    });
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
    if (completedFiles.some(file => !file.documentType)) {
      setShowDocTypeErrors(true);
      toast({
        title: "Assign document types",
        description: "Please categorize each uploaded document (LC, Invoice, B/L, etc.) before processing.",
        variant: "destructive",
      });
      return;
    } else {
      setShowDocTypeErrors(false);
    }

    const files = completedFiles.map(f => f.file);

    // Create document tags mapping
    const documentTags: Record<string, string> = {};
    completedFiles.forEach(file => {
      documentTags[file.name] = file.documentType || 'supporting_document';
    });

    try {
      clearError();
      setShowRateLimit(false);

      toast({
        title: useV2Pipeline ? "Starting V2 Validation" : "Starting Document Validation",
        description: "Uploading documents and checking compliance...",
      });

      // Log validation params
      console.log('📁 Files to validate:', files.map(f => f.name));
      console.log('🏷️  LC Number:', lcNumber.trim());
      console.log('📋 Document Tags:', documentTags);
      console.log('⚙️  LC Type Override:', lcTypeOverride);
      console.log('🚀 Using V2 Pipeline:', useV2Pipeline);

      let jobId: string;
      
      if (useV2Pipeline && hasV2Access) {
        // Use V2 API
        console.log('🔬 Using V2 validation pipeline');
        const v2Response = await validateV2(files, {
          lcNumber: lcNumber.trim(),
          userType: 'exporter',
        });
        
        jobId = v2Response.sessionId;
        console.log('✅ V2 Validation complete, sessionId:', jobId);
        
        // Store V2 results AND mode marker in sessionStorage
        sessionStorage.setItem(`v2Results_${jobId}`, JSON.stringify(v2Response));
        sessionStorage.setItem(`v2Mode_${jobId}`, 'true');
        console.log('📦 V2 results stored in sessionStorage:', `v2Results_${jobId}`);
      } else {
        // Use V1 API
        const response = await validate({
          files,
          lcNumber: lcNumber.trim(),
          notes: notes.trim() || undefined,
          documentTags: documentTags,
          userType: "exporter",
          workflowType: "export-lc-upload",
          lcTypeOverride,
        });
        
        jobId = response.jobId || response.job_id;
      }
      
      console.log('✅ Validation started, jobId:', jobId);

      toast({
        title: "Validation Complete",
        description: embedded
          ? "Documents validated. Loading your compliance results..."
          : "Documents validated. Redirecting to compliance results...",
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

      if (embedded && onComplete) {
        // V2 mode is tracked via sessionStorage (v2Mode_${jobId})
        // So embedded mode doesn't need URL param manipulation
        setTimeout(() => {
          onComplete({ jobId, lcNumber: lcNumber.trim() });
        }, 800);
      } else {
        // Navigate with v2 flag if using V2 pipeline
        const v2Param = useV2Pipeline ? '&v2=true' : '';
        console.log('🚀 Navigating to results page with jobId:', jobId);
        setTimeout(() => {
          navigate(`/lcopilot/results/${jobId}?lc=${encodeURIComponent(lcNumber.trim())}${v2Param}`);
        }, 1500);
      }

    } catch (error: any) {
      const errorCode = error?.errorCode || error?.error_code || 'unknown';
      const errorLog = {
        type: error?.type,
        message: error?.message,
        statusCode: error?.statusCode,
        errorCode,
        quota: error?.quota,
        nextActionUrl: error?.nextActionUrl,
      };
      console.error('❌ [COMPONENT] Validation error caught:', JSON.stringify(errorLog, null, 2));
      console.error('❌ [COMPONENT] Full error object:', error);
      
      if (error.type === 'quota') {
        toast({
          title: 'Upgrade Required',
          description: error.message || 'Your validation quota has been reached. Please upgrade to continue.',
          variant: 'destructive',
        });
        return;
      }
      if (error.type === 'rate_limit') {
        setShowRateLimit(true);
      } else {
        // Include error code in the message if available for debugging
        const description = errorCode !== 'unknown' 
          ? `${error.message || 'Validation failed'} (${errorCode})`
          : error.message || "Something went wrong. Please try again.";
        toast({
          title: "Validation Failed",
          description,
          variant: "destructive",
        });
      }
    }
  };

  const completedFiles = uploadedFiles.filter(f => f.status === "completed");
  const isReadyToProcess = completedFiles.length > 0 && lcNumber.trim() && !isProcessing;

  const wrapperClass = embedded
    ? "mx-auto w-full max-w-4xl py-4"
    : "container mx-auto px-4 py-8 max-w-4xl";

  return (
    <div className={embedded ? "bg-transparent" : "bg-background"}>
      {/* Header */}
      {!embedded && (
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
      )}

      {isLoadingDraft && (
        <div className={embedded ? "mx-auto w-full max-w-4xl px-0 py-6" : "container mx-auto px-4 py-8 max-w-4xl"}>
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
        <div className={wrapperClass}>
        {/* LC Information */}
        <Card className="mb-8 shadow-soft border-0">
          <CardHeader>
            <CardTitle>LC Information</CardTitle>
            <CardDescription>
              Provide basic information about your Letter of Credit
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-3 gap-4">
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
              <div>
                <Label htmlFor="lcTypeOverride">LC Type Mode</Label>
                <Select
                  value={lcTypeOverride}
                  onValueChange={(value) =>
                    setLcTypeOverride(value as 'auto' | 'export' | 'import')
                  }
                >
                  <SelectTrigger className="mt-2" id="lcTypeOverride">
                    <SelectValue placeholder="Auto Detect" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto-detect (recommended)</SelectItem>
                    <SelectItem value="export">Force Export LC</SelectItem>
                    <SelectItem value="import">Force Import LC</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1">
                  Override when the detector misclassifies your LC. Auto mode keeps both importer and exporter checks aligned.
                </p>
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
                              value={file.documentType ?? "other"}
                              onValueChange={(value) => updateFileDocumentType(file.id, value)}
                            >
                              <SelectTrigger
                                className={cn(
                                  "h-7 text-xs",
                                  showDocTypeErrors &&
                                    !file.documentType &&
                                    "border-destructive focus-visible:ring-destructive"
                                )}
                              >
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
                            {showDocTypeErrors && !file.documentType && (
                              <p className="text-xs text-destructive">
                                Select the correct document category.
                              </p>
                            )}
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
                <div className="flex items-center gap-4">
                  {/* V2 Toggle - Only shown for users with V2 access */}
                  {hasV2Access && (
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-purple-500/10 to-blue-500/10 rounded-lg border border-purple-200">
                      <Switch
                        id="v2-toggle"
                        checked={useV2Pipeline}
                        onCheckedChange={setUseV2Pipeline}
                        className="data-[state=checked]:bg-purple-600"
                      />
                      <Label htmlFor="v2-toggle" className="text-sm font-medium cursor-pointer">
                        V2 Pipeline
                        <span className="ml-1.5 text-xs text-purple-600 font-normal">
                          (2,159 rules)
                        </span>
                      </Label>
                    </div>
                  )}
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
                      className={cn(
                        "hover:opacity-90",
                        useV2Pipeline 
                          ? "bg-gradient-to-r from-purple-600 to-blue-600" 
                          : "bg-gradient-exporter"
                      )}
                    >
                      {isProcessing ? (
                        <>
                          <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                          {useV2Pipeline ? 'V2 Validation...' : 'Validating...'}
                        </>
                      ) : (
                        useV2Pipeline ? "Validate (V2)" : "Validate Documents"
                      )}
                    </Button>
                  </div>
                </div>
              </div>

              {isProcessing && (
                <div className="bg-exporter/5 border border-exporter/20 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="animate-spin w-5 h-5 border-2 border-exporter border-t-transparent rounded-full"></div>
                    <span className="font-medium text-exporter">
                      {useV2Pipeline ? 'Running V2 validation with 2,159 rules...' : 'Validating your documents...'}
                    </span>
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
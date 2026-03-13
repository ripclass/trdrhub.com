import { useState, useCallback, useEffect, useMemo, type ChangeEvent } from "react";
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
import { cn } from "@/lib/utils";
import { useDrafts, type FileMeta, type FileData } from "@/hooks/use-drafts";
import { useVersions } from "@/hooks/use-versions";
import { RateLimitNotice } from "@/components/RateLimitNotice";
import { BlockedUploadModal } from "@/components/validation";
import { PreparationGuide } from "@/components/exporter/PreparationGuide";
// Shared document types - SINGLE SOURCE OF TRUTH
import { 
  DOCUMENT_TYPES, 
  DOCUMENT_TYPE_VALUES,
  DOCUMENT_CATEGORIES,
  normalizeDocumentType,
  getDocumentsByCategory,
  type DocumentTypeValue,
  type DocumentCategory,
} from "@shared/types";
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
  Lock,
  Sparkles
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
  manualDocumentType?: boolean;
  // Auto-detection fields
  detectedType?: string;
  detectedConfidence?: number;
  isTradeDocument?: boolean;
  relevanceWarning?: string;
}

interface LCIntakeState {
  status: "idle" | "uploading" | "resolved" | "invalid" | "ambiguous";
  file: File | null;
  message?: string;
  continuationAllowed?: boolean;
  isLc?: boolean;
  jobId?: string;
  lcSummary?: Record<string, any>;
  lcDetection?: {
    lc_type?: string;
    confidence?: number;
    reason?: string;
    is_draft?: boolean;
    source?: string;
  };
  requiredDocumentTypes?: string[];
  documentsRequired?: string[];
  specialConditions?: string[];
  detectedDocuments?: Array<{ type: string; filename?: string; document_type_resolution?: string }>;
  error?: {
    error_code?: string;
    title?: string;
    message?: string;
    detail?: string;
    action?: string;
    redirect_url?: string;
    help_text?: string;
  };
}

// Generate document type options from SHARED TYPES - SINGLE SOURCE OF TRUTH
// This ensures frontend and backend always use the same values
const exportDocumentTypes = Object.values(DOCUMENT_TYPES)
  .filter(info => info.value !== DOCUMENT_TYPE_VALUES.UNKNOWN)
  .map(info => ({
    value: info.value,
    label: info.label,
    shortLabel: info.shortLabel,
    category: info.category,
    emoji: info.emoji,
  }));

// Processing phases with estimated durations (based on typical timing data)
const PROCESSING_PHASES = [
  { id: 'upload', label: 'Uploading documents', duration: 2, icon: Upload },
  { id: 'ocr', label: 'Extracting text (OCR)', duration: 35, icon: FileText },
  { id: 'validation', label: 'Running compliance checks', duration: 5, icon: FileCheck },
  { id: 'sanctions', label: 'Screening parties', duration: 10, icon: AlertTriangle },
  { id: 'complete', label: 'Building results', duration: 3, icon: CheckCircle },
];

function ValidationProgressIndicator({ fileCount }: { fileCount: number }) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [startTime] = useState(() => Date.now());
  
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    }, 500);
    return () => clearInterval(interval);
  }, [startTime]);
  
  // Calculate which phase we're in based on elapsed time
  let accumulatedTime = 0;
  let currentPhaseIndex = 0;
  let phaseProgress = 0;
  
  for (let i = 0; i < PROCESSING_PHASES.length; i++) {
    const phase = PROCESSING_PHASES[i];
    // Scale OCR phase duration by file count
    const phaseDuration = phase.id === 'ocr' 
      ? phase.duration * Math.max(1, fileCount * 0.7) 
      : phase.duration;
    
    if (elapsedSeconds < accumulatedTime + phaseDuration) {
      currentPhaseIndex = i;
      phaseProgress = ((elapsedSeconds - accumulatedTime) / phaseDuration) * 100;
      break;
    }
    accumulatedTime += phaseDuration;
    currentPhaseIndex = i;
    phaseProgress = 100;
  }
  
  // Overall progress (capped at 95% to avoid false completion)
  const totalEstimated = PROCESSING_PHASES.reduce((sum, p) => 
    sum + (p.id === 'ocr' ? p.duration * Math.max(1, fileCount * 0.7) : p.duration), 0
  );
  const overallProgress = Math.min(95, (elapsedSeconds / totalEstimated) * 100);
  
  const currentPhase = PROCESSING_PHASES[currentPhaseIndex];
  const CurrentIcon = currentPhase.icon;
  
  return (
    <div className="bg-exporter/5 border border-exporter/20 rounded-lg p-4 space-y-4">
      {/* Current phase */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <div className="animate-spin w-5 h-5 border-2 border-exporter border-t-transparent rounded-full"></div>
          <CurrentIcon className="absolute inset-0 w-3 h-3 m-auto text-exporter/60" />
        </div>
        <div className="flex-1">
          <span className="font-medium text-exporter">
            {currentPhase.label}...
          </span>
          <span className="text-sm text-muted-foreground ml-2">
            ({elapsedSeconds}s)
          </span>
        </div>
      </div>
      
      {/* Overall progress bar */}
      <div className="space-y-2">
        <Progress value={overallProgress} className="h-2" />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Processing {fileCount} document{fileCount !== 1 ? 's' : ''}</span>
          <span>~{Math.max(0, Math.ceil(totalEstimated - elapsedSeconds))}s remaining</span>
        </div>
      </div>
      
      {/* Phase indicators */}
      <div className="flex gap-1">
        {PROCESSING_PHASES.map((phase, idx) => {
          const PhaseIcon = phase.icon;
          const isComplete = idx < currentPhaseIndex;
          const isCurrent = idx === currentPhaseIndex;
          
          return (
            <div 
              key={phase.id}
              className={cn(
                "flex-1 h-1 rounded-full transition-colors",
                isComplete ? "bg-exporter" : isCurrent ? "bg-exporter/50" : "bg-gray-200"
              )}
              title={phase.label}
            />
          );
        })}
      </div>
      
      <p className="text-xs text-muted-foreground">
        Analyzing LC terms, checking compliance with UCP600 & ISBP745, and screening parties.
      </p>
    </div>
  );
}

type ExportLCUploadProps = {
  embedded?: boolean;
  onComplete?: (payload: { jobId: string; lcNumber: string }) => void;
};

export default function ExportLCUpload({ embedded = false, onComplete }: ExportLCUploadProps = {}) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [lcIntake, setLcIntake] = useState<LCIntakeState>({ status: "idle", file: null });
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
  
  // Blocked upload modal state
  const [blockedModal, setBlockedModal] = useState<{
    open: boolean;
    blockReason?: string;
    error?: {
      error_code: string;
      title: string;
      message: string;
      detail?: string;
      action?: string;
      redirect_url?: string;
      help_text?: string;
    };
    detectedDocuments?: Array<{ type: string; filename?: string }>;
    lcDetection?: {
      lc_type?: string;
      confidence?: number;
      reason?: string;
      is_draft?: boolean;
    };
  }>({ open: false });

  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialLcTypeParam = (searchParams.get('lcType') || '').toLowerCase();
  const initialLcTypeOverride: 'auto' | 'export' | 'import' =
    initialLcTypeParam === 'export' || initialLcTypeParam === 'import'
      ? (initialLcTypeParam as 'export' | 'import')
      : 'auto';
  const [lcTypeOverride, setLcTypeOverride] = useState<'auto' | 'export' | 'import'>(initialLcTypeOverride);
  
  // Validation hook
  const { validate, isLoading: isValidating, clearError } = useValidate();
  const isLCResolved = lcIntake.status === "resolved" && !!lcIntake.continuationAllowed;
  
  const { saveDraft, loadDraft, removeDraft } = useDrafts();
  const { checkLCExists } = useVersions();
  
  // Loading state
  const isProcessing = isValidating;

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
            const restoredFiles: UploadedFile[] = filesData.map(fileData => {
              const detection = detectDocumentType(fileData.name);
              const restoredDocumentType = fileData.documentType || fileData.tag || detection.type;
              return {
                id: fileData.id,
                file: new File([], fileData.name), // Placeholder file object
                name: fileData.name,
                size: fileData.size,
                type: fileData.type,
                status: fileData.status,
                progress: fileData.progress,
                documentType: restoredDocumentType,
                manualDocumentType: !!fileData.manualDocumentType,
                detectedType: fileData.detectedType || detection.type,
                detectedConfidence: fileData.detectedConfidence ?? detection.confidence,
                isTradeDocument: fileData.isTradeDocument ?? detection.isTradeDoc,
                relevanceWarning: fileData.relevanceWarning ?? detection.warning,
              };
            });

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
        manualDocumentType: file.manualDocumentType,
        detectedType: file.detectedType,
        detectedConfidence: file.detectedConfidence,
        isTradeDocument: file.isTradeDocument,
        relevanceWarning: file.relevanceWarning,
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

  // Auto-detect document type from filename (fast, client-side)
  // Returns CANONICAL document type values from shared-types
  const detectDocumentType = (filename: string): { type: DocumentTypeValue; confidence: number; isTradeDoc: boolean; warning?: string } => {
    const name = filename.toLowerCase();
    
    // Define patterns for detection - returns CANONICAL values from DOCUMENT_TYPE_VALUES
    const patterns: Array<{ pattern: RegExp; type: DocumentTypeValue; confidence: number }> = [
      // LC patterns
      { pattern: /(^|[_\s])(lc|letter[_\s]?of[_\s]?credit|mt700|mt760|swift|documentary[_\s]?credit)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT, confidence: 0.9 },
      // Invoice patterns  
      { pattern: /(^|[_\s])(invoice|inv|commercial[_\s]?invoice)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.COMMERCIAL_INVOICE, confidence: 0.85 },
      { pattern: /(^|[_\s])(proforma)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.PROFORMA_INVOICE, confidence: 0.85 },
      // B/L patterns
      { pattern: /(^|[_\s])(b[\/.]?l|bill[_\s]?of[_\s]?lading|bol|lading)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.BILL_OF_LADING, confidence: 0.85 },
      { pattern: /(^|[_\s])(ocean[_\s]?bill|ocean[_\s]?bl)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.OCEAN_BILL_OF_LADING, confidence: 0.85 },
      { pattern: /(^|[_\s])(sea[_\s]?waybill|swb)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.SEA_WAYBILL, confidence: 0.85 },
      // Packing list
      { pattern: /(^|[_\s])(packing[_\s]?list|pack[_\s]?list|plist)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.PACKING_LIST, confidence: 0.85 },
      // Certificate of Origin
      { pattern: /(^|[_\s])(coo|certificate[_\s]?of[_\s]?origin|origin[_\s]?cert)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.CERTIFICATE_OF_ORIGIN, confidence: 0.85 },
      { pattern: /(^|[_\s])(form[_\s]?a|gsp)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.GSP_FORM_A, confidence: 0.85 },
      // Insurance
      { pattern: /(^|[_\s])(insurance[_\s]?cert|insurance|ins[_\s]?cert|marine[_\s]?insurance|cargo[_\s]?insurance)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.INSURANCE_CERTIFICATE, confidence: 0.85 },
      { pattern: /(^|[_\s])(insurance[_\s]?policy|policy)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.INSURANCE_POLICY, confidence: 0.85 },
      // Inspection certificates
      { pattern: /(^|[_\s])(inspection|insp[_\s]?cert|survey)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.INSPECTION_CERTIFICATE, confidence: 0.8 },
      { pattern: /(^|[_\s])(sgs)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.SGS_CERTIFICATE, confidence: 0.85 },
      { pattern: /(^|[_\s])(bureau[_\s]?veritas|bv)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.BUREAU_VERITAS_CERTIFICATE, confidence: 0.85 },
      { pattern: /(^|[_\s])(intertek)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.INTERTEK_CERTIFICATE, confidence: 0.85 },
      { pattern: /(^|[_\s])(psi|pre[_\s]?shipment)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.PRE_SHIPMENT_INSPECTION, confidence: 0.8 },
      // Weight/measurement
      { pattern: /(^|[_\s])(weight[_\s]?cert|weight|weighment)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.WEIGHT_CERTIFICATE, confidence: 0.75 },
      { pattern: /(^|[_\s])(measurement|dimension)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.MEASUREMENT_CERTIFICATE, confidence: 0.75 },
      // Quality/Analysis
      { pattern: /(^|[_\s])(quality[_\s]?cert|quality)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.QUALITY_CERTIFICATE, confidence: 0.75 },
      { pattern: /(^|[_\s])(analysis|chemical[_\s]?analysis)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.ANALYSIS_CERTIFICATE, confidence: 0.75 },
      { pattern: /(^|[_\s])(lab[_\s]?test|lab[_\s]?report|test[_\s]?report)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.LAB_TEST_REPORT, confidence: 0.75 },
      // Health certificates
      { pattern: /(^|[_\s])(fumigat|pest[_\s]?control)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.FUMIGATION_CERTIFICATE, confidence: 0.8 },
      { pattern: /(^|[_\s])(phyto|phytosanitary|plant[_\s]?health)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.PHYTOSANITARY_CERTIFICATE, confidence: 0.8 },
      { pattern: /(^|[_\s])(health[_\s]?cert|health)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.HEALTH_CERTIFICATE, confidence: 0.75 },
      { pattern: /(^|[_\s])(sanitary|sanit)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.SANITARY_CERTIFICATE, confidence: 0.75 },
      { pattern: /(^|[_\s])(vet|veterinary)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.VETERINARY_CERTIFICATE, confidence: 0.75 },
      { pattern: /(^|[_\s])(halal)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.HALAL_CERTIFICATE, confidence: 0.8 },
      { pattern: /(^|[_\s])(kosher)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.KOSHER_CERTIFICATE, confidence: 0.8 },
      { pattern: /(^|[_\s])(organic)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.ORGANIC_CERTIFICATE, confidence: 0.8 },
      // Financial documents
      { pattern: /(^|[_\s])(draft|bill[_\s]?of[_\s]?exchange|boe)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.DRAFT_BILL_OF_EXCHANGE, confidence: 0.8 },
      { pattern: /(^|[_\s])(beneficiary[_\s]?cert|benef)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.BENEFICIARY_CERTIFICATE, confidence: 0.8 },
      // Transport documents
      { pattern: /(^|[_\s])(awb|air[_\s]?waybill|airway)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.AIR_WAYBILL, confidence: 0.85 },
      { pattern: /(^|[_\s])(fcr|forwarder|freight[_\s]?receipt)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.FORWARDER_CERTIFICATE_OF_RECEIPT, confidence: 0.75 },
      { pattern: /(^|[_\s])(shipping[_\s]?cert|carrier[_\s]?cert)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.SHIPPING_COMPANY_CERTIFICATE, confidence: 0.75 },
      { pattern: /(^|[_\s])(cmr|road[_\s]?transport)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.ROAD_TRANSPORT_DOCUMENT, confidence: 0.8 },
      { pattern: /(^|[_\s])(rail|railway)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.RAILWAY_CONSIGNMENT_NOTE, confidence: 0.8 },
      // Customs documents
      { pattern: /(^|[_\s])(customs|declaration)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.CUSTOMS_DECLARATION, confidence: 0.75 },
      { pattern: /(^|[_\s])(export[_\s]?license)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.EXPORT_LICENSE, confidence: 0.8 },
      { pattern: /(^|[_\s])(import[_\s]?license)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.IMPORT_LICENSE, confidence: 0.8 },
      { pattern: /(^|[_\s])(eur[_\s]?1|eur\.1)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.EUR1_MOVEMENT_CERTIFICATE, confidence: 0.85 },
      { pattern: /(^|[_\s])(warehouse[_\s]?receipt)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.WAREHOUSE_RECEIPT, confidence: 0.8 },
      { pattern: /(^|[_\s])(manifest|cargo[_\s]?manifest)([_\s]|$|\.)/i, type: DOCUMENT_TYPE_VALUES.CARGO_MANIFEST, confidence: 0.75 },
    ];
    
    // Check for non-trade document indicators
    const nonTradePatterns = [
      /\b(brochure|catalog|presentation|company.?profile|resume|cv)\b/i,
      /\b(contract|agreement|mou|nda)\b/i, // contracts need review
      /\b(photo|image|picture|selfie)\b/i,
      /\b(screenshot|screen.?shot)\b/i,
    ];
    
    for (const pattern of nonTradePatterns) {
      if (pattern.test(name)) {
        return {
          type: DOCUMENT_TYPE_VALUES.OTHER,
          confidence: 0.3,
          isTradeDoc: false,
          warning: "This file doesn't appear to be a trade document. Please verify.",
        };
      }
    }
    
    // Find best match
    for (const { pattern, type, confidence } of patterns) {
      if (pattern.test(name)) {
        return { type, confidence, isTradeDoc: true };
      }
    }
    
    // No pattern matched - might be trade doc but unknown type
    return { type: DOCUMENT_TYPE_VALUES.OTHER, confidence: 0.5, isTradeDoc: true };
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadedFile[] = acceptedFiles.map(file => {
      // Auto-detect document type from filename
      const detection = detectDocumentType(file.name);
      
      return {
        id: Math.random().toString(36).substring(2, 11),
        file,
        name: file.name,
        size: file.size,
        type: file.type,
        status: "pending" as const,
        progress: 0,
        documentType: detection.type, // Auto-set from detection
        manualDocumentType: false,
        detectedType: detection.type,
        detectedConfidence: detection.confidence,
        isTradeDocument: detection.isTradeDoc,
        relevanceWarning: detection.warning,
      };
    });

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
        file.id === fileId ? { ...file, documentType, manualDocumentType: true } : file
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

  const handleLCIntakeFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] || null;
    if (!nextFile) return;

    setLcIntake({ status: "uploading", file: nextFile });

    try {
      const response = await validate({
        files: [nextFile],
        userType: "exporter",
        workflowType: "export-lc-intake",
        lcTypeOverride,
        intakeOnly: true,
        mode: "lc_intake",
      });

      if (response.status === "blocked" || response.status === "invalid") {
        setLcIntake({
          status: response.status === "blocked" ? "invalid" : response.status,
          file: nextFile,
          message: response.message,
          continuationAllowed: response.continuation_allowed,
          isLc: response.is_lc,
          lcSummary: response.lc_summary,
          lcDetection: response.lc_detection,
          requiredDocumentTypes: response.required_document_types || [],
          documentsRequired: response.documents_required || [],
          specialConditions: response.special_conditions || [],
          detectedDocuments: response.detected_documents || [],
          error: response.error,
        });
        return;
      }

      setLcIntake({
        status: response.status === "resolved" ? "resolved" : "ambiguous",
        file: nextFile,
        message: response.message,
        continuationAllowed: response.continuation_allowed,
        isLc: response.is_lc,
        jobId: response.jobId || response.job_id,
        lcSummary: response.lc_summary,
        lcDetection: response.lc_detection,
        requiredDocumentTypes: response.required_document_types || [],
        documentsRequired: response.documents_required || [],
        specialConditions: response.special_conditions || [],
        detectedDocuments: response.detected_documents || [],
      });

      if (response.lc_summary?.lc_number && !lcNumber.trim()) {
        setLcNumber(String(response.lc_summary.lc_number));
      }

      toast({
        title: response.continuation_allowed ? "LC Resolved" : "LC Needs Review",
        description: response.message || "LC intake completed.",
      });
    } catch (error: any) {
      console.error('LC intake failed:', error);
      setLcIntake({
        status: "invalid",
        file: nextFile,
        message: error?.message || "Could not process the LC file.",
      });
    } finally {
      event.target.value = '';
    }
  };

  const handleClearLCIntake = () => {
    setLcIntake({ status: "idle", file: null });
    setUploadedFiles([]);
  };

  const handleProcessLC = async () => {
    if (!isLCResolved) {
      toast({
        title: "Upload LC First",
        description: "Resolve the Letter of Credit before validating supporting documents.",
        variant: "destructive",
      });
      return;
    }

    if (uploadedFiles.length === 0) {
      toast({
        title: "No Files Selected",
        description: "Please upload at least one supporting document to proceed.",
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

    const files = lcIntake.file ? [lcIntake.file, ...completedFiles.map(f => f.file)] : completedFiles.map(f => f.file);

    const resolveFinalDocumentType = (file: UploadedFile): string => {
      const normalizedManual = normalizeDocumentType(file.documentType);
      const normalizedDetected = normalizeDocumentType(file.detectedType);

      if (file.manualDocumentType && normalizedManual && normalizedManual !== DOCUMENT_TYPE_VALUES.UNKNOWN) {
        return normalizedManual;
      }
      if (normalizedDetected && normalizedDetected !== DOCUMENT_TYPE_VALUES.UNKNOWN && normalizedDetected !== DOCUMENT_TYPE_VALUES.OTHER) {
        return normalizedDetected;
      }
      if (normalizedManual && normalizedManual !== DOCUMENT_TYPE_VALUES.UNKNOWN) {
        return normalizedManual;
      }
      return DOCUMENT_TYPE_VALUES.OTHER;
    };

    // Create document tags mapping
    const documentTags: Record<string, string> = {};
    if (lcIntake.file) {
      documentTags[lcIntake.file.name] = DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT;
    }
    completedFiles.forEach(file => {
      const finalDocumentType = resolveFinalDocumentType(file);
      documentTags[file.name] = finalDocumentType;
    });

    try {
      clearError();
      setShowRateLimit(false);

      toast({
        title: "Starting Document Validation",
        description: "Uploading documents and checking compliance...",
      });

      // Log validation params
      console.log('📁 Files to validate:', files.map(f => f.name));
      console.log('🏷️  LC Number:', lcNumber.trim());
      console.log('📋 Document Tags:', documentTags);
      console.log('🧭 Final Tag Resolution:', completedFiles.map(file => ({
        name: file.name,
        detectedType: file.detectedType,
        selectedType: file.documentType,
        manualDocumentType: file.manualDocumentType,
        finalTag: documentTags[file.name],
      })));
      console.log('⚙️  LC Type Override:', lcTypeOverride);

      // Validate using V1 API
      const response = await validate({
        files,
        lcNumber: lcNumber.trim(),
        notes: notes.trim() || undefined,
        documentTags: documentTags,
        userType: "exporter",
        workflowType: "export-lc-upload",
        lcTypeOverride,
      });
      
      // Check for blocked response (wrong LC type, no LC found, etc.)
      if (response.status === "blocked") {
        console.log('⚠️ Validation blocked:', response.block_reason);
        setBlockedModal({
          open: true,
          blockReason: response.block_reason,
          error: response.error,
          detectedDocuments: response.detected_documents,
          lcDetection: response.lc_detection,
        });
        return;
      }
      
      const jobId = response.jobId || response.job_id;
      
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
        setTimeout(() => {
          onComplete({ jobId, lcNumber: lcNumber.trim() });
        }, 800);
      } else {
        console.log('🚀 Navigating to results page with jobId:', jobId);
        setTimeout(() => {
          navigate(`/lcopilot/results/${jobId}?lc=${encodeURIComponent(lcNumber.trim())}`);
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
  const isReadyToProcess = isLCResolved && completedFiles.length > 0 && !!lcNumber.trim() && !isProcessing;

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

        {/* Preparation Guide - Static checklist before upload */}
        <div className="mb-6">
          <PreparationGuide />
        </div>

        {/* Step 1: LC Intake */}
        <Card className="mb-6 shadow-soft border-0">
          <CardHeader>
            <CardTitle>Step 1 — Upload Letter of Credit</CardTitle>
            <CardDescription>
              Start with the LC first. We’ll detect required supporting documents automatically and unlock the bulk uploader below.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="border-2 border-dashed rounded-lg p-6 text-center border-exporter/30 bg-exporter/5">
              <input
                id="lc-intake-upload"
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                className="hidden"
                onChange={handleLCIntakeFileChange}
              />
              <div className="flex flex-col items-center gap-3">
                <div className="bg-exporter/10 p-3 rounded-full">
                  <Sparkles className="w-7 h-7 text-exporter" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground mb-1">Upload LC first</h3>
                  <p className="text-sm text-muted-foreground">
                    We’ll check whether it is a real LC, identify flow, and extract required supporting documents.
                  </p>
                </div>
                <div className="flex gap-3">
                  <Button asChild variant="outline" disabled={lcIntake.status === "uploading" || isProcessing}>
                    <label htmlFor="lc-intake-upload" className="cursor-pointer">
                      <Plus className="w-4 h-4 mr-2" />
                      {lcIntake.file ? "Replace LC" : "Choose LC File"}
                    </label>
                  </Button>
                  {lcIntake.file && (
                    <Button variant="ghost" onClick={handleClearLCIntake}>
                      Clear
                    </Button>
                  )}
                </div>
              </div>
            </div>

            {lcIntake.file && (
              <div className="rounded-lg border border-gray-200 p-4 bg-secondary/10 space-y-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-medium text-foreground">{lcIntake.file.name}</p>
                    <p className="text-xs text-muted-foreground">{formatFileSize(lcIntake.file.size)}</p>
                  </div>
                  <Badge variant={isLCResolved ? "default" : lcIntake.status === "uploading" ? "outline" : "secondary"}>
                    {lcIntake.status === "uploading" ? "Checking LC..." : isLCResolved ? "LC Resolved" : lcIntake.status}
                  </Badge>
                </div>

                {(lcIntake.message || lcIntake.error?.message) && (
                  <div className={cn(
                    "rounded-md p-3 text-sm border",
                    isLCResolved ? "bg-green-50 border-green-200 text-green-800" : "bg-amber-50 border-amber-200 text-amber-800"
                  )}>
                    {lcIntake.error?.message || lcIntake.message}
                  </div>
                )}

                {lcIntake.lcDetection && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    <Badge variant="outline">Type: {lcIntake.lcDetection.lc_type || "unknown"}</Badge>
                    {typeof lcIntake.lcDetection.confidence === 'number' && (
                      <Badge variant="outline">Confidence: {Math.round(lcIntake.lcDetection.confidence * 100)}%</Badge>
                    )}
                    {lcIntake.lcDetection.is_draft && <Badge variant="outline">Draft LC</Badge>}
                  </div>
                )}

                {Object.keys(lcIntake.lcSummary || {}).length > 0 && (
                  <div className="grid md:grid-cols-3 gap-3 text-sm">
                    {Object.entries(lcIntake.lcSummary || {}).slice(0, 6).map(([key, value]) => (
                      <div key={key} className="rounded bg-background p-3 border border-gray-200/60">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">{key.replace(/_/g, ' ')}</p>
                        <p className="font-medium text-foreground break-words">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Step 1.5: Requirement summary / live checklist */}
        <Card className="mb-6 shadow-soft border-0">
          <CardHeader>
            <CardTitle>Required Documents</CardTitle>
            <CardDescription>
              {isLCResolved
                ? "These requirements were detected from the LC. Upload the remaining documents below in any order, any filename."
                : "Required documents will appear here after the LC is resolved."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!isLCResolved ? (
              <div className="flex items-center gap-3 rounded-lg border border-dashed border-gray-300 p-4 text-sm text-muted-foreground">
                <Lock className="w-4 h-4" />
                Upload and resolve the LC first to unlock the supporting-document checklist.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {(lcIntake.requiredDocumentTypes || []).length > 0 ? (
                    (lcIntake.requiredDocumentTypes || []).map((docType) => {
                      const label = exportDocumentTypes.find((t) => t.value === docType)?.label || docType;
                      const isFound = completedFiles.some((file) => normalizeDocumentType(file.documentType) === docType || normalizeDocumentType(file.detectedType) === docType);
                      return (
                        <Badge key={docType} variant={isFound ? "default" : "outline"}>
                          {label} {isFound ? "• Found" : "• Missing"}
                        </Badge>
                      );
                    })
                  ) : (
                    <p className="text-sm text-muted-foreground">No explicit supporting-document requirements were extracted yet.</p>
                  )}
                </div>
                {(lcIntake.specialConditions || []).length > 0 && (
                  <div className="rounded-lg border border-gray-200 p-4 bg-secondary/10">
                    <p className="text-sm font-medium text-foreground mb-2">Special Conditions</p>
                    <ul className="list-disc pl-5 space-y-1 text-sm text-muted-foreground">
                      {(lcIntake.specialConditions || []).slice(0, 4).map((item, index) => (
                        <li key={`${item}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Step 2: Supporting document bulk uploader */}
        <Card className="mb-8 shadow-soft border-0">
          <CardHeader>
            <CardTitle>Step 2 — Upload Supporting Documents</CardTitle>
            <CardDescription>
              Upload remaining documents in any order, any filename. We’ll match them against LC requirements.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              {...(isLCResolved ? getRootProps() : {})}
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
                isLCResolved
                  ? isDragActive
                    ? "border-exporter bg-exporter/5 cursor-pointer"
                    : "border-gray-200 hover:border-exporter/50 hover:bg-secondary/20 cursor-pointer"
                  : "border-gray-200 bg-muted/30 opacity-70 cursor-not-allowed"
              )}
            >
              {isLCResolved && <input {...getInputProps()} />}
              <div className="flex flex-col items-center gap-4">
                <div className={cn("p-4 rounded-full", isLCResolved ? "bg-exporter/10" : "bg-muted") }>
                  {isLCResolved ? <Upload className="w-8 h-8 text-exporter" /> : <Lock className="w-8 h-8 text-muted-foreground" />}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {isLCResolved ? (isDragActive ? "Drop supporting documents here..." : "Upload Supporting Documents") : "Supporting uploader locked"}
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    {isLCResolved
                      ? "Drag and drop your supporting files here, or click to browse"
                      : "Resolve the LC above to unlock supporting document upload."}
                  </p>
                  <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
                    {exportDocumentTypes.slice(0, 12).map(type => (
                      <Badge key={type.value} variant="outline">{type.label}</Badge>
                    ))}
                  </div>
                </div>
                <Button variant="outline" disabled={!isLCResolved}>
                  <Plus className="w-4 h-4 mr-2" />
                  Choose Files
                </Button>
              </div>
            </div>

            {/* Uploaded Files List */}
            {uploadedFiles.length > 0 && (
              <div className="mt-6 space-y-3">
                <h4 className="font-semibold text-foreground">Uploaded Supporting Files ({uploadedFiles.length})</h4>
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
                          <div className="flex items-center gap-2 flex-wrap">
                            <CheckCircle className="w-4 h-4 text-success" />
                            <span className="text-xs text-success">Upload complete</span>
                            {file.detectedType && file.detectedConfidence && file.detectedConfidence > 0.6 && (
                              <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                                Auto-detected: {exportDocumentTypes.find(d => d.value === file.detectedType)?.label || file.detectedType}
                                {file.detectedConfidence >= 0.8 && " ✓"}
                              </Badge>
                            )}
                          </div>

                          {file.relevanceWarning && (
                            <div className="flex items-start gap-2 p-2 rounded bg-amber-50 border border-amber-200">
                              <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                              <span className="text-xs text-amber-700">{file.relevanceWarning}</span>
                            </div>
                          )}

                          <div className="flex items-center gap-2 flex-wrap">
                            <Label className="text-xs text-muted-foreground whitespace-nowrap">
                              Document Type:
                            </Label>
                            <Select
                              value={file.documentType ?? "other"}
                              onValueChange={(value) => updateFileDocumentType(file.id, value)}
                            >
                              <SelectTrigger className={cn("h-7 text-xs w-48", showDocTypeErrors && !file.documentType && "border-destructive focus-visible:ring-destructive", file.relevanceWarning && "border-amber-300")}>
                                <SelectValue placeholder="Select type" />
                              </SelectTrigger>
                              <SelectContent className="max-h-80 overflow-y-auto">
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground bg-muted/50">Core Documents</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.CORE).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.emoji} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Transport Documents</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.TRANSPORT).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.emoji} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Inspection & Quality</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.INSPECTION).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.emoji} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Health & Agricultural</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.HEALTH).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.emoji} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Financial Documents</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.FINANCIAL).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.emoji} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Customs & Trade</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.CUSTOMS).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.emoji} {t.label}</SelectItem>
                                ))}
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 bg-muted/50">Other</div>
                                {exportDocumentTypes.filter(t => t.category === DOCUMENT_CATEGORIES.OTHER).map(t => (
                                  <SelectItem key={t.value} value={t.value}>{t.emoji} {t.label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            {showDocTypeErrors && !file.documentType && <p className="text-xs text-destructive">Select the correct document category.</p>}
                          </div>
                        </div>
                      )}
                      
                      {file.status === "error" && <p className="text-xs text-destructive">Upload failed</p>}
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={() => handlePreviewFile(file)} disabled={file.status === "uploading"} title="Preview file">
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => removeFile(file.id)} disabled={file.status === "uploading"}>
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
                      className="hover:opacity-90 bg-gradient-exporter"
                    >
                      {isProcessing ? (
                        <>
                          <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                          Validating...
                        </>
                      ) : (
                        "Validate Documents"
                      )}
                    </Button>
                  </div>
                </div>
              </div>

              {isProcessing && (
                <ValidationProgressIndicator fileCount={completedFiles.length} />
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
      
      {/* Blocked Upload Modal - Shows when LC type mismatch or no LC found */}
      <BlockedUploadModal
        open={blockedModal.open}
        onClose={() => setBlockedModal({ open: false })}
        blockReason={blockedModal.blockReason}
        error={blockedModal.error}
        detectedDocuments={blockedModal.detectedDocuments}
        lcDetection={blockedModal.lcDetection}
      />
    </div>
  );
}
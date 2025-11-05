import { useState, useCallback, useEffect, useMemo } from "react";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { useToast } from "@/hooks/use-toast";
import { useValidate } from "@/hooks/use-lcopilot";
import { useQuery } from "@tanstack/react-query";
import { bankApi, LCSetDetected } from "@/api/bank";
import { sanitizeText, sanitizeFileName } from "@/lib/sanitize";
import { MAX_FILE_SIZE, MAX_TOTAL_SIZE, MAX_ZIP_SIZE } from "@/lib/constants";
import { validateFilesContent } from "@/lib/file-validation";
import {
  Upload,
  FileText,
  X,
  AlertCircle,
  Clock,
  Check,
  ChevronsUpDown,
  Archive,
  Loader2,
} from "lucide-react";
import { format } from "date-fns";

// Inline cn function to avoid import/bundling issues
function cn(...classes: (string | undefined | null | boolean | Record<string, boolean>)[]): string {
  return classes
    .filter(Boolean)
    .map((cls) => {
      if (typeof cls === 'string') return cls;
      if (typeof cls === 'object' && cls !== null) {
        return Object.entries(cls)
          .filter(([_, val]) => val)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join(' ');
}

interface UploadedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  documentType?: string;
}

const documentTypes = [
  { value: "lc", label: "Letter of Credit" },
  { value: "invoice", label: "Commercial Invoice" },
  { value: "packing_list", label: "Packing List" },
  { value: "bl", label: "Bill of Lading" },
  { value: "coo", label: "Certificate of Origin" },
  { value: "insurance", label: "Insurance Certificate" },
  { value: "other", label: "Other Trade Documents" }
];

interface BulkLCUploadProps {
  onUploadSuccess?: () => void;
}

export function BulkLCUpload({ onUploadSuccess }: BulkLCUploadProps) {
  const [uploadMode, setUploadMode] = useState<"single" | "bulk">("single");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [clientName, setClientName] = useState("");
  const [lcNumber, setLcNumber] = useState("");
  const [dateReceived, setDateReceived] = useState("");
  const [notes, setNotes] = useState("");
  const [clientNameError, setClientNameError] = useState("");
  const [clientNameOpen, setClientNameOpen] = useState(false);
  
  // Bulk upload (ZIP) state
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [detectedLCSets, setDetectedLCSets] = useState<LCSetDetected[]>([]);
  const [bulkSessionId, setBulkSessionId] = useState<string | null>(null);
  const [isExtractingZip, setIsExtractingZip] = useState(false);
  const [duplicateCheck, setDuplicateCheck] = useState<{
    isDuplicate: boolean;
    duplicateCount: number;
    previousValidations: any[];
  } | null>(null);
  const [isCheckingDuplicate, setIsCheckingDuplicate] = useState(false);

  const { toast } = useToast();
  const { validate, isLoading: isValidating } = useValidate();

  // Debounced client name for API calls
  const [debouncedClientName, setDebouncedClientName] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedClientName(clientName);
    }, 300);
    return () => clearTimeout(timer);
  }, [clientName]);

  // Fetch client names for autocomplete
  const { data: clientsData } = useQuery({
    queryKey: ['bank-clients', debouncedClientName],
    queryFn: () => bankApi.getClients(debouncedClientName || undefined, 20),
    enabled: clientNameOpen && debouncedClientName.length > 0,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const clientSuggestions = useMemo(() => {
    if (!clientsData?.clients) return [] as string[];
    const sanitized = clientsData.clients
      .map((name) => sanitizeText(name).trim())
      .filter((name) => name.length > 0);
    // Remove duplicates while preserving order
    const unique: string[] = [];
    const seen = new Set<string>();
    for (const name of sanitized) {
      if (!seen.has(name)) {
        seen.add(name);
        unique.push(name);
      }
    }
    return unique;
  }, [clientsData]);

  // Check for duplicates when LC number and client name are provided
  const { data: duplicateData, refetch: checkDuplicate } = useQuery({
    queryKey: ['duplicate-check', clientName.trim(), lcNumber.trim()],
    queryFn: () => {
      if (!clientName.trim() || !lcNumber.trim()) {
        return null;
      }
      return bankApi.checkDuplicate(lcNumber.trim(), clientName.trim());
    },
    enabled: false, // Don't auto-fetch, we'll trigger manually
    staleTime: 30 * 1000,
  });

  // Check for duplicates when both fields are filled (with debounce)
  useEffect(() => {
    if (clientName.trim() && lcNumber.trim() && uploadMode === "single") {
      const timer = setTimeout(() => {
        setIsCheckingDuplicate(true);
        checkDuplicate().finally(() => setIsCheckingDuplicate(false));
      }, 500); // Debounce 500ms
      return () => clearTimeout(timer);
    } else {
      setDuplicateCheck(null);
    }
  }, [clientName, lcNumber, uploadMode, checkDuplicate]);

  // Update duplicate check state when data changes
  useEffect(() => {
    if (duplicateData) {
      setDuplicateCheck({
        isDuplicate: duplicateData.is_duplicate,
        duplicateCount: duplicateData.duplicate_count,
        previousValidations: duplicateData.previous_validations || [],
      });
    } else {
      setDuplicateCheck(null);
    }
  }, [duplicateData]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    // Validate file sizes first
    const oversizedFiles = acceptedFiles.filter(f => f.size > MAX_FILE_SIZE);
    if (oversizedFiles.length > 0) {
      toast({
        title: "File Too Large",
        description: `${oversizedFiles[0].name} exceeds 10MB limit`,
        variant: "destructive",
      });
      return;
    }

    // Check total size
    const totalSize = [...uploadedFiles, ...acceptedFiles].reduce((sum, f) => sum + f.size, 0);
    if (totalSize > MAX_TOTAL_SIZE) {
      toast({
        title: "Total Size Exceeded",
        description: `Total file size cannot exceed 50MB`,
        variant: "destructive",
      });
      return;
    }

    // Content-based validation (magic bytes)
    const validationResult = await validateFilesContent(acceptedFiles);
    if (!validationResult.valid) {
      const errorMessages = validationResult.errors.map(e => `${e.filename}: ${e.error}`).join('\n');
      toast({
        title: "Invalid File Content",
        description: errorMessages || "File content does not match declared type. Please upload valid PDF, JPEG, PNG, or TIFF files.",
        variant: "destructive",
      });
      return;
    }

    const newFiles: UploadedFile[] = acceptedFiles.map((file) => ({
      id: `${Date.now()}-${Math.random()}`,
      file,
      name: sanitizeFileName(file.name), // Sanitize file name
      size: file.size,
      type: file.type,
    }));
    setUploadedFiles((prev) => [...prev, ...newFiles]);
  }, [uploadedFiles, toast]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/*": [".png", ".jpg", ".jpeg"],
    },
    multiple: true,
  });

  const removeFile = (id: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const updateDocumentType = (fileId: string, docType: string) => {
    setUploadedFiles((prev) =>
      prev.map((f) =>
        f.id === fileId ? { ...f, documentType: docType } : f
      )
    );
  };

  // Handle ZIP file upload
  const handleZipUpload = async (file: File) => {
    if (file.size > MAX_ZIP_SIZE) {
      toast({
        title: "ZIP Too Large",
        description: `ZIP file exceeds ${MAX_ZIP_SIZE / (1024 * 1024)}MB limit`,
        variant: "destructive",
      });
      return;
    }

    setZipFile(file);
    setIsExtractingZip(true);

    try {
      const result = await bankApi.extractZipFile(file);
      setDetectedLCSets(result.lc_sets);
      setBulkSessionId(result.bulk_session_id);
      
      // Initialize metadata for each LC set
      const initialMetadata: Record<number, { client_name: string; lc_number: string; date_received: string }> = {};
      result.lc_sets.forEach((lcSet, index) => {
        initialMetadata[index] = {
          client_name: lcSet.client_name || '',
          lc_number: lcSet.lc_number || '',
          date_received: '',
        };
      });
      setLcSetMetadata(initialMetadata);

      toast({
        title: "ZIP Extracted",
        description: `Detected ${result.total_lc_sets} LC set(s) in ZIP file`,
      });
    } catch (error: any) {
      toast({
        title: "Extraction Failed",
        description: error.message || "Failed to extract ZIP file. Please try again.",
        variant: "destructive",
      });
      setZipFile(null);
    } finally {
      setIsExtractingZip(false);
    }
  };

  // Handle bulk submit (submit all detected LC sets)
  const handleBulkSubmit = async () => {
    if (!bulkSessionId || detectedLCSets.length === 0) {
      toast({
        title: "No LC Sets",
        description: "Please extract a ZIP file first",
        variant: "destructive",
      });
      return;
    }

    // Validate all LC sets have client names
    const missingClientNames = detectedLCSets.filter((_, index) => {
      const metadata = lcSetMetadata[index];
      return !metadata?.client_name?.trim();
    });

    if (missingClientNames.length > 0) {
      toast({
        title: "Missing Client Names",
        description: `Please provide client names for all LC sets`,
        variant: "destructive",
      });
      return;
    }

    try {
      setIsExtractingZip(true);

      // Prepare LC sets data for submission
      const lcSetsToSubmit = detectedLCSets.map((lcSet, index) => {
        const metadata = lcSetMetadata[index];
        return {
          client_name: sanitizeText(metadata.client_name.trim()),
          lc_number: metadata.lc_number ? sanitizeText(metadata.lc_number.trim()) : undefined,
          date_received: metadata.date_received || undefined,
          files: lcSet.files.map(f => ({
            filename: f.filename,
            s3_key: f.s3_key || '', // Include S3 key from extraction
            valid: f.valid,
          })),
        };
      });

      const result = await bankApi.submitBulkUpload({
        bulk_session_id: bulkSessionId,
        lc_sets: lcSetsToSubmit,
      });

      toast({
        title: "Bulk Upload Submitted",
        description: `Successfully queued ${result.jobs_created} LC set(s) for validation`,
      });

      // Reset state
      setZipFile(null);
      setDetectedLCSets([]);
      setLcSetMetadata({});
      setBulkSessionId(null);
      setUploadMode("single");

      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (error: any) {
      toast({
        title: "Bulk Upload Failed",
        description: error.message || "Failed to submit bulk upload. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsExtractingZip(false);
    }
  };

  const handleSubmit = async () => {
    // Validate required fields
    const sanitizedClientName = sanitizeText(clientName.trim());
    if (!sanitizedClientName) {
      setClientNameError("Client name is required");
      toast({
        title: "Validation Error",
        description: "Please enter the client name",
        variant: "destructive",
      });
      return;
    }

    if (uploadedFiles.length === 0) {
      toast({
        title: "No Files",
        description: "Please upload at least one document",
        variant: "destructive",
      });
      return;
    }

    // Validate file sizes before submission
    const oversizedFiles = uploadedFiles.filter(f => f.file.size > MAX_FILE_SIZE);
    if (oversizedFiles.length > 0) {
      toast({
        title: "File Too Large",
        description: "Please remove files larger than 10MB",
        variant: "destructive",
      });
      return;
    }

    // Check if all files have document types
    const filesWithoutTypes = uploadedFiles.filter((f) => !f.documentType);
    if (filesWithoutTypes.length > 0) {
      toast({
        title: "Document Types Required",
        description: "Please assign a document type to all files",
        variant: "destructive",
      });
      return;
    }

    try {
      // Create document tags mapping (sanitize file names)
      const documentTags: Record<string, string> = {};
      uploadedFiles.forEach((file) => {
        if (file.documentType) {
          documentTags[file.name] = file.documentType;
        }
      });

      // Sanitize inputs before sending
      const sanitizedLcNumber = lcNumber ? sanitizeText(lcNumber.trim()) : undefined;
      const sanitizedNotes = notes ? sanitizeText(notes.trim()) : undefined;

      // Check for duplicates before submitting (only warn, don't block)
      if (sanitizedLcNumber && sanitizedClientName) {
        try {
          const duplicateResult = await bankApi.checkDuplicate(sanitizedLcNumber, sanitizedClientName);
          if (duplicateResult.is_duplicate) {
            // Show warning but allow submission
            toast({
              title: "Duplicate LC Detected",
              description: `This LC has been validated ${duplicateResult.duplicate_count} time(s) before. You can still proceed with this upload.`,
              variant: "default",
            });
          }
        } catch (error) {
          // Don't block submission if duplicate check fails
          console.error("Failed to check for duplicates:", error);
        }
      }

      // Prepare validation request
      const response = await validate({
        files: uploadedFiles.map((f) => f.file),
        lcNumber: sanitizedLcNumber,
        notes: sanitizedNotes,
        documentTags,
        userType: "bank",
        workflowType: "bank-bulk-validation",
        metadata: {
          clientName: sanitizedClientName,
          dateReceived: dateReceived || undefined,
        },
      });

      // Job is now stored in backend via ValidationSession
      // No need to store in localStorage
      const jobId = response.jobId || response.job_id;

      toast({
        title: "Validation Started",
        description: `LC validation for ${sanitizedClientName} has been queued for processing.`,
      });

      // Reset form
      setUploadedFiles([]);
      setClientName("");
      setLcNumber("");
      setDateReceived("");
      setNotes("");
      setClientNameError("");

      // Switch to queue tab
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (error: any) {
      toast({
        title: "Validation Failed",
        description: error.message || "Failed to start validation. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Upload LC Documents</CardTitle>
          <CardDescription>
            Upload LC and supporting documents for validation. All fields marked with * are required.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Upload Mode Toggle */}
          <div className="flex items-center gap-4 border-b pb-4">
            <Label className="text-sm font-medium">Upload Mode:</Label>
            <div className="flex gap-2">
              <Button
                variant={uploadMode === "single" ? "default" : "outline"}
                size="sm"
                onClick={() => {
                  setUploadMode("single");
                  setZipFile(null);
                  setDetectedLCSets([]);
                  setLcSetMetadata({});
                  setBulkSessionId(null);
                }}
              >
                <Upload className="w-4 h-4 mr-2" />
                Single Upload
              </Button>
              <Button
                variant={uploadMode === "bulk" ? "default" : "outline"}
                size="sm"
                onClick={() => {
                  setUploadMode("bulk");
                  setUploadedFiles([]);
                  setClientName("");
                  setLcNumber("");
                  setDateReceived("");
                }}
              >
                <Archive className="w-4 h-4 mr-2" />
                Bulk Upload (ZIP)
              </Button>
            </div>
          </div>

          {uploadMode === "single" ? (
            <>
              {/* Single Upload Mode - Existing Code */}
              {/* Client Name - Required with Autocomplete */}
              <div className="space-y-2">
            <Label htmlFor="clientName">
              Client Name <span className="text-destructive">*</span>
            </Label>
            <Popover open={clientNameOpen} onOpenChange={setClientNameOpen}>
              <div className="relative">
                <Input
                  id="clientName"
                  value={clientName}
                  onChange={(e) => {
                    setClientName(e.target.value);
                    setClientNameError("");
                    setClientNameOpen(true);
                  }}
                  onFocus={() => setClientNameOpen(true)}
                  placeholder="Enter client/company name..."
                  className={cn(clientNameError ? "border-destructive" : "")}
                />
                <PopoverTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    onClick={(e) => {
                      e.preventDefault();
                      setClientNameOpen(!clientNameOpen);
                    }}
                  >
                    <ChevronsUpDown className="h-4 w-4 opacity-50" />
                  </Button>
                </PopoverTrigger>
              </div>
              <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
                <Command>
                  <CommandInput
                    placeholder="Search client name..."
                    value={clientName}
                    onValueChange={(value) => {
                      setClientName(value);
                      setClientNameError("");
                    }}
                  />
                  <CommandList>
                    <CommandEmpty>No client found. Type to add new client.</CommandEmpty>
                    <CommandGroup>
                      {clientSuggestions.map((client) => (
                        <CommandItem
                          key={client}
                          value={client}
                          onSelect={(currentValue) => {
                            setClientName(currentValue === clientName ? "" : currentValue);
                            setClientNameOpen(false);
                            setClientNameError("");
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              clientName === client ? "opacity-100" : "opacity-0"
                            )}
                          />
                          {client}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
            {clientNameError && (
              <p className="text-sm text-destructive flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                {clientNameError}
              </p>
            )}
          </div>

          {/* Duplicate Warning */}
          {duplicateCheck?.isDuplicate && (
            <Card className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium text-yellow-900 dark:text-yellow-100">
                      Duplicate LC Detected
                    </p>
                    <p className="text-sm text-yellow-800 dark:text-yellow-200 mt-1">
                      This LC ({sanitizeText(lcNumber)}) for {sanitizeText(clientName)} has been validated{" "}
                      {duplicateCheck.duplicateCount} time(s) before. You can still proceed with this upload.
                    </p>
                    {duplicateCheck.previousValidations.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs font-medium text-yellow-900 dark:text-yellow-100">
                          Previous Validations:
                        </p>
                        <div className="space-y-1 max-h-32 overflow-y-auto">
                          {duplicateCheck.previousValidations.slice(0, 3).map((prev: any) => (
                            <div
                              key={prev.id}
                              className="text-xs bg-white dark:bg-yellow-900 p-2 rounded border border-yellow-200 dark:border-yellow-800"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-medium">
                                  {prev.completed_at
                                    ? format(new Date(prev.completed_at), "MMM d, yyyy HH:mm")
                                    : "N/A"}
                                </span>
                                <Badge
                                  variant={
                                    prev.status === "compliant"
                                      ? "default"
                                      : prev.status === "discrepancies"
                                      ? "secondary"
                                      : "destructive"
                                  }
                                  className="text-xs"
                                >
                                  {prev.status === "compliant"
                                    ? "Compliant"
                                    : prev.status === "discrepancies"
                                    ? "Discrepancies"
                                    : "Failed"}
                                </Badge>
                              </div>
                              <div className="text-muted-foreground mt-1">
                                Score: {prev.compliance_score}% | Discrepancies: {prev.discrepancy_count}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* LC Number - Optional */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="lcNumber">LC Number (Optional)</Label>
              {isCheckingDuplicate && (
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              )}
            </div>
            <Input
              id="lcNumber"
              value={lcNumber}
              onChange={(e) => setLcNumber(e.target.value)}
              placeholder="e.g., BD-2024-001"
            />
          </div>

          {/* Date Received - Optional */}
          <div className="space-y-2">
            <Label htmlFor="dateReceived">Date Received (Optional)</Label>
            <Input
              id="dateReceived"
              type="date"
              value={dateReceived}
              onChange={(e) => setDateReceived(e.target.value)}
            />
          </div>

          {/* File Upload */}
          <div className="space-y-2">
            <Label>Documents <span className="text-destructive">*</span></Label>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-primary/50"
              }`}
            >
              <input {...getInputProps()} />
              <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-sm font-medium mb-1">
                {isDragActive ? "Drop files here" : "Drag & drop files or click to browse"}
              </p>
              <p className="text-xs text-muted-foreground">
                PDF, PNG, JPG (Max 10MB per file)
              </p>
            </div>

            {/* Uploaded Files List */}
            {uploadedFiles.length > 0 && (
              <div className="space-y-2 mt-4">
                {uploadedFiles.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center gap-3 p-3 border rounded-lg bg-card"
                  >
                    <FileText className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{sanitizeText(file.name)}</p>
                      <p className="text-xs text-muted-foreground">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    <Select
                      value={file.documentType || ""}
                      onValueChange={(value) => updateDocumentType(file.id, value)}
                    >
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        {documentTypes.map((type) => (
                          <SelectItem key={type.value} value={type.value}>
                            {type.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(file.id)}
                      className="text-destructive hover:text-destructive"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Notes - Optional */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes (Optional)</Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any additional notes or context..."
              rows={3}
            />
          </div>

          {/* Submit Button */}
          <Button
            onClick={handleSubmit}
            disabled={isValidating || uploadedFiles.length === 0 || !clientName.trim()}
            className="w-full"
            size="lg"
          >
            {isValidating ? (
              <>
                <Clock className="w-4 h-4 mr-2 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                Submit for Validation
              </>
            )}
          </Button>
            </>
          ) : (
            <>
              {/* Bulk Upload Mode - ZIP Upload */}
              <div className="space-y-6">
                {/* ZIP File Upload */}
                {!zipFile && !isExtractingZip && (
                  <div className="space-y-2">
                    <Label>ZIP File <span className="text-destructive">*</span></Label>
                    <div className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors hover:border-primary/50">
                      <input
                        type="file"
                        accept=".zip"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            handleZipUpload(file);
                          }
                        }}
                        className="hidden"
                        id="zip-upload"
                      />
                      <label htmlFor="zip-upload" className="cursor-pointer">
                        <Archive className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                        <p className="text-sm font-medium mb-1">
                          Click to upload ZIP file or drag & drop
                        </p>
                        <p className="text-xs text-muted-foreground">
                          ZIP file containing multiple LC document sets (Max {MAX_ZIP_SIZE / (1024 * 1024)}MB)
                        </p>
                      </label>
                    </div>
                  </div>
                )}

                {/* Extraction Progress */}
                {isExtractingZip && (
                  <div className="text-center py-8">
                    <Loader2 className="w-12 h-12 mx-auto mb-4 animate-spin text-primary" />
                    <p className="text-sm text-muted-foreground">Extracting ZIP file and detecting LC sets...</p>
                  </div>
                )}

                {/* Detected LC Sets */}
                {detectedLCSets.length > 0 && !isExtractingZip && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <Label className="text-base font-semibold">
                        Detected LC Sets ({detectedLCSets.length})
                      </Label>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setZipFile(null);
                          setDetectedLCSets([]);
                          setLcSetMetadata({});
                          setBulkSessionId(null);
                        }}
                      >
                        <X className="w-4 h-4 mr-2" />
                        Clear
                      </Button>
                    </div>

                    <div className="space-y-4">
                      {detectedLCSets.map((lcSet, index) => {
                        const metadata = lcSetMetadata[index] || {
                          client_name: '',
                          lc_number: '',
                          date_received: '',
                        };

                        return (
                          <Card key={index}>
                            <CardHeader>
                              <CardTitle className="text-base">
                                LC Set {index + 1}
                                <Badge variant="outline" className="ml-2">
                                  {lcSet.detection_method}
                                </Badge>
                              </CardTitle>
                              <CardDescription>
                                {lcSet.file_count} file(s) detected
                              </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              {/* Client Name */}
                              <div className="space-y-2">
                                <Label>
                                  Client Name <span className="text-destructive">*</span>
                                </Label>
                                <Input
                                  value={metadata.client_name}
                                  onChange={(e) => {
                                    setLcSetMetadata({
                                      ...lcSetMetadata,
                                      [index]: {
                                        ...metadata,
                                        client_name: e.target.value,
                                      },
                                    });
                                  }}
                                  placeholder="Enter client name..."
                                />
                              </div>

                              {/* LC Number */}
                              <div className="space-y-2">
                                <Label>LC Number</Label>
                                <Input
                                  value={metadata.lc_number}
                                  onChange={(e) => {
                                    setLcSetMetadata({
                                      ...lcSetMetadata,
                                      [index]: {
                                        ...metadata,
                                        lc_number: e.target.value,
                                      },
                                    });
                                  }}
                                  placeholder="Enter LC number..."
                                />
                              </div>

                              {/* Date Received */}
                              <div className="space-y-2">
                                <Label>Date Received</Label>
                                <Input
                                  type="date"
                                  value={metadata.date_received}
                                  onChange={(e) => {
                                    setLcSetMetadata({
                                      ...lcSetMetadata,
                                      [index]: {
                                        ...metadata,
                                        date_received: e.target.value,
                                      },
                                    });
                                  }}
                                />
                              </div>

                              {/* Files List */}
                              <div className="space-y-2">
                                <Label>Files ({lcSet.files.length})</Label>
                                <div className="space-y-1 max-h-32 overflow-y-auto">
                                  {lcSet.files.map((file, fileIndex) => (
                                    <div
                                      key={fileIndex}
                                      className="flex items-center gap-2 text-xs p-2 bg-muted rounded"
                                    >
                                      <FileText className="w-3 h-3 text-muted-foreground" />
                                      <span className="flex-1 truncate">{sanitizeText(file.filename)}</span>
                                      <span className="text-muted-foreground">
                                        {(file.size / 1024).toFixed(1)} KB
                                      </span>
                                      {file.valid ? (
                                        <Check className="w-3 h-3 text-green-600" />
                                      ) : (
                                        <AlertCircle className="w-3 h-3 text-red-600" />
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>

                    {/* Bulk Submit Button */}
                    <Button
                      onClick={handleBulkSubmit}
                      disabled={isExtractingZip || detectedLCSets.length === 0}
                      className="w-full"
                      size="lg"
                    >
                      {isExtractingZip ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <Upload className="w-4 h-4 mr-2" />
                          Submit {detectedLCSets.length} LC Set(s) for Validation
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

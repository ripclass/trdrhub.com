import { useState, useCallback } from "react";
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
import { bankApi } from "@/api/bank";
import { sanitizeText, sanitizeFileName } from "@/lib/sanitize";
import { MAX_FILE_SIZE, MAX_TOTAL_SIZE } from "@/lib/constants";
import {
  Upload,
  FileText,
  X,
  AlertCircle,
  Clock,
  Check,
  ChevronsUpDown,
} from "lucide-react";
import { cn } from "@/lib/utils";

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
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [clientName, setClientName] = useState("");
  const [lcNumber, setLcNumber] = useState("");
  const [dateReceived, setDateReceived] = useState("");
  const [notes, setNotes] = useState("");
  const [clientNameError, setClientNameError] = useState("");
  const [clientNameOpen, setClientNameOpen] = useState(false);

  const { toast } = useToast();
  const { validate, isLoading: isValidating } = useValidate();

  // Fetch client names for autocomplete
  const { data: clientsData } = useQuery({
    queryKey: ['bank-clients', clientName],
    queryFn: () => bankApi.getClients(clientName || undefined, 20),
    enabled: clientNameOpen || clientName.length > 0,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const clientSuggestions = clientsData?.clients || [];

  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Validate file sizes
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

          {/* LC Number - Optional */}
          <div className="space-y-2">
            <Label htmlFor="lcNumber">LC Number (Optional)</Label>
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
        </CardContent>
      </Card>
    </div>
  );
}

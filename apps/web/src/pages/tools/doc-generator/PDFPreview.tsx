/**
 * PDF Preview Component
 * 
 * Displays PDF preview in a modal or inline
 */

import { useState, useEffect } from "react";
import {
  FileText,
  Download,
  Loader2,
  X,
  ZoomIn,
  ZoomOut,
  ExternalLink,
  RefreshCw,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

const DOCUMENT_TYPES = [
  // Core Documents
  { value: "commercial_invoice", label: "Commercial Invoice" },
  { value: "packing_list", label: "Packing List" },
  { value: "certificate_of_origin", label: "Certificate of Origin" },
  // Shipping Documents
  { value: "bill_of_lading_draft", label: "Bill of Lading Draft" },
  { value: "shipping_instructions", label: "Shipping Instructions" },
  // Certificates
  { value: "weight_certificate", label: "Weight Certificate" },
  { value: "inspection_certificate", label: "Inspection Certificate" },
  { value: "beneficiary_certificate", label: "Beneficiary Certificate" },
  // Finance & Insurance
  { value: "bill_of_exchange", label: "Bill of Exchange" },
  { value: "insurance_certificate", label: "Insurance Certificate" },
];

interface PDFPreviewProps {
  docSetId: string;
  documentType?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  mode?: "modal" | "inline";
}

export function PDFPreview({
  docSetId,
  documentType: initialDocType,
  open,
  onOpenChange,
  mode = "modal",
}: PDFPreviewProps) {
  const { user } = useAuth();
  const [documentType, setDocumentType] = useState(initialDocType || "commercial_invoice");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [zoom, setZoom] = useState(100);

  useEffect(() => {
    if ((mode === "modal" && open) || mode === "inline") {
      loadPreview();
    }
  }, [open, documentType, docSetId]);

  const loadPreview = async () => {
    if (!docSetId) return;
    
    setLoading(true);
    setPdfUrl(null);
    
    try {
      // Generate URL for preview endpoint
      const previewUrl = `${API_BASE}/doc-generator/document-sets/${docSetId}/preview/${documentType}`;
      
      // Fetch PDF blob
      const response = await fetch(previewUrl, {
        headers: {
          Authorization: `Bearer ${user?.access_token || ""}`,
        },
      });
      
      if (!response.ok) throw new Error("Failed to load preview");
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);
    } catch (error) {
      console.error("Error loading preview:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!pdfUrl) return;
    
    const link = document.createElement("a");
    link.href = pdfUrl;
    link.download = `${documentType}_${docSetId.slice(0, 8)}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleOpenInNewTab = () => {
    if (pdfUrl) {
      window.open(pdfUrl, "_blank");
    }
  };

  const PreviewContent = () => (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="flex items-center justify-between p-3 border-b bg-muted/30">
        <div className="flex items-center gap-3">
          <Select value={documentType} onValueChange={setDocumentType}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select document" />
            </SelectTrigger>
            <SelectContent>
              {DOCUMENT_TYPES.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Button variant="ghost" size="icon" onClick={loadPreview}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center border rounded-md">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setZoom((z) => Math.max(50, z - 25))}
              disabled={zoom <= 50}
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="px-2 text-sm min-w-[60px] text-center">
              {zoom}%
            </span>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setZoom((z) => Math.min(200, z + 25))}
              disabled={zoom >= 200}
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>

          <Button variant="outline" size="sm" onClick={handleOpenInNewTab}>
            <ExternalLink className="h-4 w-4 mr-2" />
            Open
          </Button>
          
          <Button variant="outline" size="sm" onClick={handleDownload}>
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
        </div>
      </div>

      {/* PDF Viewer */}
      <div className="flex-1 bg-muted/20 overflow-auto">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">Loading preview...</p>
          </div>
        ) : pdfUrl ? (
          <div className="flex justify-center p-4">
            <iframe
              src={`${pdfUrl}#zoom=${zoom}`}
              className="bg-white shadow-lg border rounded"
              style={{
                width: `${(595 * zoom) / 100}px`,  // A4 width at 72 DPI
                height: `${(842 * zoom) / 100}px`, // A4 height at 72 DPI
                minHeight: "600px",
              }}
              title="PDF Preview"
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full">
            <FileText className="h-16 w-16 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No preview available</p>
            <Button variant="outline" className="mt-4" onClick={loadPreview}>
              Generate Preview
            </Button>
          </div>
        )}
      </div>
    </div>
  );

  // Modal mode
  if (mode === "modal") {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-5xl h-[80vh] p-0 flex flex-col">
          <DialogHeader className="px-4 py-3 border-b">
            <div className="flex items-center justify-between">
              <DialogTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Document Preview
              </DialogTitle>
              <Badge variant="outline">
                {DOCUMENT_TYPES.find((t) => t.value === documentType)?.label || documentType}
              </Badge>
            </div>
          </DialogHeader>
          <div className="flex-1 overflow-hidden">
            <PreviewContent />
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  // Inline mode
  return (
    <div className="border rounded-lg overflow-hidden h-[600px]">
      <PreviewContent />
    </div>
  );
}

export default PDFPreview;


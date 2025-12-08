import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, FileX, ArrowRight, Upload, HelpCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

/**
 * BlockedUploadModal - Shows clear error messages when document upload is blocked
 * 
 * Scenarios:
 * 1. WRONG_DASHBOARD - Import LC uploaded to Exporter dashboard (or vice versa)
 * 2. DRAFT_LC_ON_EXPORTER - Draft LC uploaded to Exporter dashboard
 * 3. NO_LC_FOUND - No Letter of Credit found in uploaded documents
 */

interface BlockedError {
  error_code: string
  title: string
  message: string
  detail?: string
  action?: string
  redirect_url?: string
  help_text?: string
}

interface DetectedDocument {
  type: string
  filename?: string
}

interface BlockedUploadModalProps {
  open: boolean
  onClose: () => void
  blockReason?: string
  error?: BlockedError
  detectedDocuments?: DetectedDocument[]
  lcDetection?: {
    lc_type?: string
    confidence?: number
    reason?: string
    is_draft?: boolean
  }
}

const ERROR_ICONS: Record<string, typeof AlertTriangle> = {
  'WRONG_DASHBOARD': ArrowRight,
  'DRAFT_LC_ON_EXPORTER': FileX,
  'NO_LC_FOUND': Upload,
}

const ERROR_COLORS: Record<string, string> = {
  'WRONG_DASHBOARD': 'text-amber-500',
  'DRAFT_LC_ON_EXPORTER': 'text-amber-500',
  'NO_LC_FOUND': 'text-blue-500',
}

export function BlockedUploadModal({
  open,
  onClose,
  blockReason,
  error,
  detectedDocuments,
  lcDetection,
}: BlockedUploadModalProps) {
  const navigate = useNavigate()

  const handleOpenChange = (value: boolean) => {
    if (!value) {
      onClose()
    }
  }

  const handleRedirect = () => {
    if (error?.redirect_url) {
      navigate(error.redirect_url)
      onClose()
    }
  }

  const errorCode = error?.error_code || blockReason || 'UNKNOWN'
  const IconComponent = ERROR_ICONS[errorCode] || AlertTriangle
  const iconColor = ERROR_COLORS[errorCode] || 'text-amber-500'

  // Format document types for display
  const formatDocType = (type: string): string => {
    const typeMap: Record<string, string> = {
      'commercial_invoice': 'Commercial Invoice',
      'bill_of_lading': 'Bill of Lading',
      'packing_list': 'Packing List',
      'certificate_of_origin': 'Certificate of Origin',
      'insurance_certificate': 'Insurance Certificate',
      'inspection_certificate': 'Inspection Certificate',
      'letter_of_credit': 'Letter of Credit',
      'swift_message': 'SWIFT Message',
      'supporting_document': 'Supporting Document',
    }
    return typeMap[type] || type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className={`p-2 rounded-full bg-muted ${iconColor}`}>
              <IconComponent className="h-5 w-5" />
            </div>
            <DialogTitle className="text-lg">
              {error?.title || 'Upload Blocked'}
            </DialogTitle>
          </div>
          <DialogDescription className="text-base">
            {error?.message || 'There was an issue with your uploaded documents.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Detection Details */}
          {error?.detail && (
            <div className="p-4 rounded-lg bg-muted/50 border">
              <div className="text-sm text-muted-foreground">
                {error.detail}
              </div>
            </div>
          )}

          {/* LC Detection Info */}
          {lcDetection && lcDetection.lc_type && (
            <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                <div className="text-sm">
                  <div className="font-medium text-amber-700 dark:text-amber-400">
                    Detected: {lcDetection.lc_type.toUpperCase()} LC
                    {lcDetection.confidence && (
                      <Badge variant="outline" className="ml-2 text-xs">
                        {Math.round(lcDetection.confidence * 100)}% confidence
                      </Badge>
                    )}
                  </div>
                  {lcDetection.reason && (
                    <div className="text-amber-600 dark:text-amber-300 mt-1">
                      {lcDetection.reason}
                    </div>
                  )}
                  {lcDetection.is_draft && (
                    <Badge variant="secondary" className="mt-2">Draft LC</Badge>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Detected Documents */}
          {detectedDocuments && detectedDocuments.length > 0 && (
            <div className="p-4 rounded-lg bg-muted">
              <div className="text-sm font-medium mb-2">Documents Detected:</div>
              <div className="space-y-1">
                {detectedDocuments.map((doc, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span className="w-2 h-2 rounded-full bg-green-500" />
                    <span>{formatDocType(doc.type)}</span>
                    {doc.filename && (
                      <span className="text-xs opacity-60">({doc.filename})</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Help Text */}
          {error?.help_text && (
            <div className="flex items-start gap-2 text-sm text-muted-foreground">
              <HelpCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{error.help_text}</span>
            </div>
          )}
        </div>

        <DialogFooter className="flex flex-col sm:flex-row gap-2 sm:gap-3">
          <Button 
            variant="outline" 
            onClick={onClose} 
            className="flex-1 sm:flex-none"
          >
            {errorCode === 'NO_LC_FOUND' ? 'Add More Documents' : 'Cancel'}
          </Button>
          
          {error?.redirect_url && (
            <Button 
              onClick={handleRedirect} 
              className="flex-1 sm:flex-none"
            >
              {error.action || 'Go to Correct Dashboard'}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default BlockedUploadModal

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface QuotaInfo {
  used: number
  limit: number | null
  remaining: number | null
  period_start?: string
}

interface QuotaLimitModalProps {
  open: boolean
  onClose: () => void
  message: string
  quota?: QuotaInfo | null
  nextActionUrl?: string | null
}

export function QuotaLimitModal({ open, onClose, message, quota, nextActionUrl }: QuotaLimitModalProps) {
  const handleOpenChange = (value: boolean) => {
    if (!value) {
      onClose()
    }
  }

  const quotaSummary = quota && quota.limit !== null
    ? `${quota.used.toLocaleString()} of ${quota.limit.toLocaleString()} checks used this period`
    : quota
    ? `${quota.used.toLocaleString()} checks used`
    : null

  const nextUrl = nextActionUrl || '/pricing'

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Usage Limit Reached</DialogTitle>
          <DialogDescription>
            {message}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {quotaSummary && (
            <div className="p-4 rounded-lg bg-muted">
              <Badge variant="secondary" className="mb-2">Current cycle</Badge>
              <div className="text-sm text-muted-foreground">{quotaSummary}</div>
              {quota?.remaining !== null && quota.remaining <= 0 && (
                <div className="text-sm text-destructive mt-2">No validations remaining in this cycle.</div>
              )}
            </div>
          )}

          <p className="text-sm text-muted-foreground">
            Upgrade your plan or purchase additional LC checks to continue validating documents.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row sm:justify-end sm:space-x-3 space-y-3 sm:space-y-0 pt-2">
          <Button variant="outline" onClick={onClose} className="flex-1 sm:flex-none">
            Close
          </Button>
          <Button asChild className="flex-1 sm:flex-none">
            <a href={nextUrl}>View upgrade options</a>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}


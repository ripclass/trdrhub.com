import { useState } from 'react'
import { Loader2, Send } from 'lucide-react'
import type { ProoflineRemediationAction, TradeCaseDocument } from '@shared/types'

import { Button } from '@/components/ui/button'
import { respondToRemediation } from '@/lib/proofline/api'

interface Props {
  caseId: string
  action: ProoflineRemediationAction
  documents: TradeCaseDocument[]
  onSaved: () => void
}

export function ProoflineRemediationResponse({ caseId, action, documents, onSaved }: Props) {
  const [response, setResponse] = useState(action.customer_response || '')
  const [documentId, setDocumentId] = useState(action.correction_document_id || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function save() {
    setSaving(true)
    setError(null)
    try {
      await respondToRemediation(caseId, action.id, {
        response: response.trim() || undefined,
        correction_document_id: documentId || undefined,
      })
      onSaved()
    } catch (caught) {
      const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || 'Your response could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-3 space-y-3 rounded-lg border border-amber-400/15 bg-[#00261C]/30 p-3">
      <div>
        <label htmlFor={`action-response-${action.id}`} className="mb-1 block text-xs font-medium text-[#EDF5F2]/65">Your response</label>
        <textarea id={`action-response-${action.id}`} value={response} onChange={(event) => setResponse(event.target.value)} rows={3} placeholder="Explain what was corrected or provide the requested information" className="w-full rounded-md border border-[#EDF5F2]/15 bg-[#00261C]/60 px-3 py-2 text-sm text-white outline-none placeholder:text-[#EDF5F2]/25 focus:border-[#B2F273]/60" />
      </div>
      <div>
        <label htmlFor={`action-document-${action.id}`} className="mb-1 block text-xs font-medium text-[#EDF5F2]/65">Corrected document (optional)</label>
        <select id={`action-document-${action.id}`} value={documentId} onChange={(event) => setDocumentId(event.target.value)} className="w-full rounded-md border border-[#EDF5F2]/15 bg-[#00261C] px-3 py-2 text-sm text-white">
          <option value="">No document selected</option>
          {documents.filter((document) => document.is_current).map((document) => <option key={document.id} value={document.id}>{document.filename} · v{document.version}</option>)}
        </select>
      </div>
      {error ? <p role="alert" className="text-xs text-red-200">{error}</p> : null}
      <Button size="sm" disabled={saving || (!response.trim() && !documentId)} onClick={() => void save()} className="border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]">
        {saving ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <Send className="mr-2 h-3.5 w-3.5" />}Save response
      </Button>
    </div>
  )
}

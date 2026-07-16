import { FormEvent, useMemo, useState } from 'react'
import { FileUp, Loader2 } from 'lucide-react'
import type { TradeCaseDocument } from '@shared/types'

import { Button } from '@/components/ui/button'
import { uploadTradeCaseDocument } from '@/lib/proofline/api'

const documentTypes = [
  ['purchase_order', 'Purchase order'], ['sales_contract', 'Sales contract'], ['letter_of_credit', 'Letter of credit'],
  ['lc_amendment', 'LC amendment'], ['commercial_invoice', 'Commercial invoice'], ['packing_list', 'Packing list'],
  ['bill_of_lading', 'Bill of lading / transport document'], ['certificate_of_origin', 'Certificate of origin'],
  ['inspection_certificate', 'Inspection certificate'], ['insurance_certificate', 'Insurance document'],
  ['proof_of_delivery', 'Proof of delivery'], ['buyer_requirements', 'Buyer requirements / vendor manual'],
  ['payment_undertaking', 'Payment undertaking'], ['credit_insurance', 'Trade-credit insurance'],
  ['supplier_credential', 'Supplier or facility credential'], ['product_evidence', 'Product or material evidence'],
  ['supporting_document', 'Other supporting document'],
]

export function ProoflineDocumentUpload({ caseId, documents, onSaved, onCancel }: { caseId: string; documents: TradeCaseDocument[]; onSaved: () => void; onCancel: () => void }) {
  const currentDocuments = documents.filter((item) => item.is_current)
  const [documentType, setDocumentType] = useState('commercial_invoice')
  const [supersedesId, setSupersedesId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const superseded = useMemo(() => currentDocuments.find((item) => item.id === supersedesId), [currentDocuments, supersedesId])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!file) { setError('Choose a PDF or image to upload.'); return }
    setSaving(true)
    setError(null)
    try {
      await uploadTradeCaseDocument(caseId, {
        file,
        logicalKey: superseded?.logical_key || `${documentType}-${Date.now()}`,
        documentType: superseded?.document_type || documentType,
        supersedesId: superseded?.id,
        correctionRound: superseded ? superseded.correction_round + 1 : 0,
      })
      onSaved()
    } catch (caught) {
      setError((caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'The document could not be processed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-xl border border-[#B2F273]/20 bg-[#00261C]/45 p-4">
      <div>
        <label htmlFor="supersedes" className="mb-1.5 block text-xs font-medium text-[#EDF5F2]/65">Upload purpose</label>
        <select id="supersedes" value={supersedesId} onChange={(event) => setSupersedesId(event.target.value)} className="h-10 w-full rounded-md border border-[#EDF5F2]/15 bg-[#00261C] px-3 text-sm text-white">
          <option value="">New document</option>
          {currentDocuments.map((item) => <option key={item.id} value={item.id}>Correction for {item.filename} (version {item.version})</option>)}
        </select>
      </div>
      {!superseded ? <div>
        <label htmlFor="document-type" className="mb-1.5 block text-xs font-medium text-[#EDF5F2]/65">Document type</label>
        <select id="document-type" value={documentType} onChange={(event) => setDocumentType(event.target.value)} className="h-10 w-full rounded-md border border-[#EDF5F2]/15 bg-[#00261C] px-3 text-sm text-white">
          {documentTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div> : null}
      <div>
        <label htmlFor="proofline-file" className="mb-1.5 block text-xs font-medium text-[#EDF5F2]/65">PDF or image</label>
        <input id="proofline-file" type="file" accept="application/pdf,image/jpeg,image/png,image/tiff" onChange={(event) => setFile(event.target.files?.[0] || null)} className="block w-full text-xs text-[#EDF5F2]/55 file:mr-3 file:rounded-md file:border-0 file:bg-[#EDF5F2]/10 file:px-3 file:py-2 file:text-white" />
        <p className="mt-2 text-[11px] leading-relaxed text-[#EDF5F2]/35">The file is content-validated, stored in the existing secure document store, extracted, and classified. Maximum 25 MB.</p>
      </div>
      {error ? <p role="alert" className="text-xs text-red-200">{error}</p> : null}
      <div className="flex gap-2">
        <Button type="button" onClick={onCancel} className="flex-1 border border-[#EDF5F2]/15 bg-transparent text-white hover:bg-[#EDF5F2]/5">Cancel</Button>
        <Button type="submit" disabled={saving} className="flex-1 border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]">{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileUp className="mr-2 h-4 w-4" />}Upload</Button>
      </div>
    </form>
  )
}

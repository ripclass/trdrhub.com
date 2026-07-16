import { FormEvent, useState } from 'react'
import { CheckCircle2, Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { reportTradeCaseOutcome } from '@/lib/proofline/api'

type Answer = '' | 'yes' | 'no'

const questions = [
  ['documents_accepted', 'Were the documents accepted?'],
  ['payment_delayed', 'Was payment delayed?'],
  ['bank_additional_discrepancies', 'Did the bank raise additional discrepancies?'],
  ['shipment_held', 'Was the shipment held?'],
] as const

export function ProoflineOutcomeFeedback({ caseId }: { caseId: string }) {
  const [answers, setAnswers] = useState<Record<(typeof questions)[number][0], Answer>>({
    documents_accepted: '', payment_delayed: '', bank_additional_discrepancies: '', shipment_held: '',
  })
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    const payload = Object.fromEntries(
      Object.entries(answers)
        .filter(([, value]) => value)
        .map(([key, value]) => [key, value === 'yes']),
    ) as Record<string, boolean>
    try {
      await reportTradeCaseOutcome(caseId, { ...payload, notes: notes.trim() || undefined })
      setSubmitted(true)
    } catch (caught) {
      setError((caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Outcome feedback could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  if (submitted) {
    return <div className="mt-4 flex items-start gap-2 rounded-lg border border-[#B2F273]/20 bg-[#B2F273]/5 p-3 text-xs text-[#B2F273]"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> Thank you. This customer-reported outcome will help improve future reviews.</div>
  }

  return (
    <form onSubmit={submit} className="mt-5 border-t border-[#EDF5F2]/10 pt-4">
      <p className="text-xs font-semibold text-[#EDF5F2]/70">Optional outcome feedback</p>
      <p className="mt-1 text-[11px] leading-relaxed text-[#EDF5F2]/35">Reported outcomes help improve Proofline and are not treated as verified ground truth.</p>
      <div className="mt-4 space-y-3">
        {questions.map(([key, label]) => <label key={key} className="block text-xs text-[#EDF5F2]/55">{label}<select aria-label={label} value={answers[key]} onChange={(event) => setAnswers((current) => ({ ...current, [key]: event.target.value as Answer }))} className="mt-1 h-9 w-full rounded-md border border-[#EDF5F2]/15 bg-[#00261C] px-2 text-xs text-white"><option value="">Prefer not to say</option><option value="yes">Yes</option><option value="no">No</option></select></label>)}
      </div>
      <textarea aria-label="Outcome notes" value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={5000} rows={3} placeholder="Optional context" className="mt-3 w-full rounded-md border border-[#EDF5F2]/15 bg-[#00261C] px-3 py-2 text-xs text-white placeholder:text-[#EDF5F2]/25" />
      {error ? <p role="alert" className="mt-2 text-xs text-red-200">{error}</p> : null}
      <Button type="submit" disabled={saving || (!notes.trim() && !Object.values(answers).some(Boolean))} className="mt-3 w-full border border-[#EDF5F2]/15 bg-[#EDF5F2]/5 text-white hover:bg-[#EDF5F2]/10">{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Share outcome</Button>
    </form>
  )
}

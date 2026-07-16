import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  Clock3,
  Download,
  FileUp,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Send,
  Users,
  Plus,
  Trash2,
} from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import type { ProoflineFinding, ProoflineQuote, TradeCaseDetail } from '@shared/types'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ProoflineDocumentUpload } from '@/components/proofline/ProoflineDocumentUpload'
import { ProoflinePartyForm } from '@/components/proofline/ProoflinePartyForm'
import { ProoflineRemediationResponse } from '@/components/proofline/ProoflineRemediationResponse'
import { ProoflineOutcomeFeedback } from '@/components/proofline/ProoflineOutcomeFeedback'
import { deleteTradeCaseParty, getProoflineQuote, getProoflineReport, getTradeCase, resubmitTradeCase, startProoflineCheckout, submitTradeCase, updateTradeCase } from '@/lib/proofline/api'
import {
  checkStateLabels,
  checkTone,
  decisionLabel,
  moduleLabels,
  paymentArrangementLabels,
  statusLabels,
  statusTone,
} from '@/lib/proofline/presentation'

const severityTone: Record<ProoflineFinding['severity'], string> = {
  critical: 'border-red-400/40 bg-red-500/10 text-red-200',
  high: 'border-orange-400/40 bg-orange-500/10 text-orange-200',
  medium: 'border-amber-400/40 bg-amber-500/10 text-amber-200',
  low: 'border-blue-400/40 bg-blue-500/10 text-blue-200',
  info: 'border-[#EDF5F2]/15 bg-[#EDF5F2]/5 text-[#EDF5F2]/65',
}

function FindingCard({ finding }: { finding: ProoflineFinding }) {
  return (
    <article className="rounded-xl border border-[#EDF5F2]/10 bg-[#00261C]/35 p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase ${severityTone[finding.severity]}`}>{finding.severity}</span>
        <span className="font-mono text-[11px] uppercase tracking-wide text-[#EDF5F2]/35">{moduleLabels[finding.source_module] || finding.source_module.replace(/_/g, ' ')}</span>
      </div>
      <h3 className="font-display text-lg font-bold text-white">{finding.title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-[#EDF5F2]/55">{finding.explanation}</p>
      <dl className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-lg border border-[#EDF5F2]/10 bg-[#00382E]/45 p-3">
          <dt className="mb-1 font-mono text-[10px] uppercase tracking-widest text-[#B2F273]">Expected</dt>
          <dd className="text-sm text-[#EDF5F2]/75">{finding.expected}</dd>
        </div>
        <div className="rounded-lg border border-[#EDF5F2]/10 bg-[#00382E]/45 p-3">
          <dt className="mb-1 font-mono text-[10px] uppercase tracking-widest text-amber-300">Found</dt>
          <dd className="text-sm text-[#EDF5F2]/75">{finding.observed}</dd>
        </div>
        <div className="rounded-lg border border-[#EDF5F2]/10 bg-[#00382E]/45 p-3">
          <dt className="mb-1 font-mono text-[10px] uppercase tracking-widest text-blue-300">Suggested fix</dt>
          <dd className="text-sm text-[#EDF5F2]/75">{finding.suggested_correction}</dd>
        </div>
      </dl>
    </article>
  )
}

export default function ProoflineCaseDetail() {
  const { caseId } = useParams<{ caseId: string }>()
  const [searchParams] = useSearchParams()
  const [tradeCase, setTradeCase] = useState<TradeCaseDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showPartyForm, setShowPartyForm] = useState(false)
  const [showDocumentUpload, setShowDocumentUpload] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [resubmitting, setResubmitting] = useState(false)
  const [quote, setQuote] = useState<ProoflineQuote | null>(null)
  const [paying, setPaying] = useState(false)
  const [downloadingReport, setDownloadingReport] = useState(false)
  const [presentationReference, setPresentationReference] = useState('')
  const [consentReference, setConsentReference] = useState('')
  const [credentialType, setCredentialType] = useState('')
  const [subjectReference, setSubjectReference] = useState('')
  const [savingEin, setSavingEin] = useState(false)

  async function load() {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      const loaded = await getTradeCase(caseId)
      setTradeCase(loaded)
      if (loaded.status === 'awaiting_payment') {
        setQuote(await getProoflineQuote(caseId))
      } else {
        setQuote(null)
      }
    } catch {
      setError('This trade case is unavailable or you do not have access to it.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [caseId])

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#00261C] text-[#EDF5F2]/55"><Loader2 className="mr-3 h-6 w-6 animate-spin text-[#B2F273]" /> Loading trade case…</div>
  }
  if (!tradeCase || error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#00261C] px-4 text-white">
        <div role="alert" className="max-w-lg rounded-xl border border-red-400/30 bg-red-500/10 p-6 text-center">
          <AlertTriangle className="mx-auto mb-3 h-7 w-7 text-red-300" /><p>{error}</p>
          <Button asChild className="mt-5 bg-white text-[#00261C] hover:bg-[#EDF5F2]"><Link to="/proofline/cases">Return to trade cases</Link></Button>
        </div>
      </div>
    )
  }

  const finalOrRecommended = tradeCase.final_decision || tradeCase.recommended_decision
  const openActions = tradeCase.actions.filter((action) => !['resolved', 'closed'].includes(action.status))

  async function removeParty(partyId: string) {
    if (!caseId) return
    await deleteTradeCaseParty(caseId, partyId)
    await load()
  }

  async function submitForReview() {
    if (!caseId) return
    setSubmitting(true)
    setActionError(null)
    try {
      setTradeCase(await submitTradeCase(caseId))
    } catch (caught) {
      const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setActionError(detail || 'The case could not be submitted. Confirm the parties and documents, then try again.')
    } finally {
      setSubmitting(false)
    }
  }

  async function requestFinalReview() {
    if (!caseId) return
    setResubmitting(true)
    setActionError(null)
    try {
      setTradeCase(await resubmitTradeCase(caseId))
    } catch (caught) {
      const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setActionError(detail || 'The corrections could not be submitted for final review.')
    } finally {
      setResubmitting(false)
    }
  }

  async function payForReview() {
    if (!caseId) return
    setPaying(true)
    setActionError(null)
    try {
      window.location.assign(await startProoflineCheckout(caseId))
    } catch (caught) {
      const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setActionError(detail || 'Secure checkout could not be started. Please try again.')
      setPaying(false)
    }
  }

  async function downloadReport() {
    if (!caseId) return
    setDownloadingReport(true)
    setActionError(null)
    try {
      const report = await getProoflineReport(caseId)
      window.location.assign(report.download_url)
    } catch (caught) {
      const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setActionError(detail || 'The clearance report could not be downloaded. Please try again.')
      setDownloadingReport(false)
    }
  }

  async function shareEinPresentation() {
    if (!caseId || !presentationReference.trim() || !consentReference.trim() || !credentialType.trim()) return
    setSavingEin(true)
    setActionError(null)
    const existing = Array.isArray(tradeCase.transaction_details.ein_presentations)
      ? tradeCase.transaction_details.ein_presentations
      : []
    try {
      const updated = await updateTradeCase(caseId, {
        transaction_details: {
          ...tradeCase.transaction_details,
          ein_requested: true,
          ein_presentations: [...existing, {
            presentation_reference: presentationReference.trim(),
            consent_reference: consentReference.trim(),
            credential_type: credentialType.trim(),
            subject_reference: subjectReference.trim() || undefined,
            requested_claims: ['credentialStatus', 'issuer', 'issuanceDate', 'expirationDate'],
          }],
        },
      })
      setTradeCase(updated)
      setPresentationReference('')
      setConsentReference('')
      setCredentialType('')
      setSubjectReference('')
    } catch (caught) {
      const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setActionError(detail || 'The EIN presentation reference could not be saved.')
    } finally {
      setSavingEin(false)
    }
  }

  const money = (cents: number, currency: string) => new Intl.NumberFormat(undefined, {
    style: 'currency', currency,
  }).format(cents / 100)

  return (
    <div className="min-h-screen bg-[#00261C] text-white">
      <header className="sticky top-0 z-30 border-b border-[#EDF5F2]/10 bg-[#00261C]/95 backdrop-blur">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-4">
            <Link to="/proofline/cases" aria-label="Back to trade cases" className="rounded-md p-2 text-[#EDF5F2]/50 hover:bg-[#EDF5F2]/5 hover:text-[#B2F273]"><ArrowLeft className="h-4 w-4" /></Link>
            <div className="min-w-0"><p className="font-mono text-[10px] text-[#B2F273]">{tradeCase.case_reference}</p><p className="truncate text-sm font-semibold">{tradeCase.title}</p></div>
          </div>
          <button onClick={() => void load()} className="inline-flex items-center gap-2 text-sm text-[#EDF5F2]/45 hover:text-[#B2F273]"><RefreshCw className="h-4 w-4" /> <span className="hidden sm:inline">Refresh</span></button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <section className="mb-6 rounded-2xl border border-[#B2F273]/20 bg-[#00382E]/55 p-6 sm:p-8">
            <div className="flex flex-col justify-between gap-7 lg:flex-row lg:items-start">
              <div>
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className={`rounded-full border px-2.5 py-1 text-xs ${statusTone(tradeCase.status)}`}>{statusLabels[tradeCase.status]}</span>
                  <span className="rounded-full border border-[#EDF5F2]/10 bg-[#00261C]/30 px-2.5 py-1 text-xs text-[#EDF5F2]/55">{paymentArrangementLabels[tradeCase.payment_arrangement]}</span>
                  {tradeCase.payment_status ? <span className="rounded-full border border-[#EDF5F2]/10 bg-[#00261C]/30 px-2.5 py-1 text-xs capitalize text-[#EDF5F2]/55">Payment {tradeCase.payment_status}</span> : null}
                </div>
                <h1 className="font-display text-3xl font-bold">{tradeCase.title}</h1>
                <p className="mt-3 text-sm text-[#EDF5F2]/45">{tradeCase.origin_country || 'Origin pending'} → {tradeCase.destination_country || 'Destination pending'}{tradeCase.amount && tradeCase.currency ? ` · ${tradeCase.currency} ${Number(tradeCase.amount).toLocaleString()}` : ''}</p>
              </div>
              <div className="min-w-[260px] space-y-3">
                {tradeCase.status === 'draft' ? (
                  <div className="rounded-xl border border-[#B2F273]/25 bg-[#B2F273]/5 p-5">
                    <p className="text-sm font-semibold">Ready for verified review?</p>
                    <p className="mt-2 text-xs leading-relaxed text-[#EDF5F2]/45">Add at least two parties and one current document. Proofline will route the applicable checks automatically.</p>
                    <Button onClick={() => void submitForReview()} disabled={submitting} className="mt-4 w-full border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]">
                      {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
                      Submit for review
                    </Button>
                  </div>
                ) : null}
                {tradeCase.status === 'awaiting_payment' && quote ? (
                  <div className="rounded-xl border border-[#B2F273]/30 bg-[#B2F273]/5 p-5">
                    <p className="text-sm font-semibold">{quote.package.name}</p>
                    <p className="mt-1 text-xs text-[#EDF5F2]/45">{quote.package.price_label}</p>
                    <dl className="mt-4 space-y-2 text-xs">
                      <div className="flex justify-between gap-3"><dt className="text-[#EDF5F2]/45">Case price</dt><dd>{money(quote.base_amount_cents, quote.currency)}</dd></div>
                      {quote.credit_amount_cents > 0 ? <div className="flex justify-between gap-3 text-[#B2F273]"><dt>LCopilot upgrade credit</dt><dd>âˆ’{money(quote.credit_amount_cents, quote.currency)}</dd></div> : null}
                      <div className="flex justify-between gap-3 border-t border-[#EDF5F2]/10 pt-2 font-semibold"><dt>Due now</dt><dd>{money(quote.amount_due_cents, quote.currency)}</dd></div>
                    </dl>
                    {quote.checkout_enabled && quote.package.self_service_enabled ? (
                      <Button onClick={() => void payForReview()} disabled={paying} className="mt-4 w-full border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]">
                        {paying ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BadgeCheck className="mr-2 h-4 w-4" />}Pay securely and start review
                      </Button>
                    ) : <p className="mt-4 text-xs leading-relaxed text-[#EDF5F2]/50">This service level is invoiced manually. Your case is saved; the TRDR Hub team will confirm scope and payment before review begins.</p>}
                  </div>
                ) : null}
                <div className="rounded-xl border border-[#EDF5F2]/10 bg-[#00261C]/35 p-5">
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#EDF5F2]/35">{tradeCase.final_decision ? 'Final decision' : 'Recommended decision'}</p>
                  <p className="mt-2 font-display text-xl font-bold text-[#B2F273]">{decisionLabel(finalOrRecommended)}</p>
                  <p className="mt-2 text-xs leading-relaxed text-[#EDF5F2]/40">A final paid-case decision is released only after internal reviewer approval.</p>
                </div>
              </div>
            </div>
            {actionError ? <div role="alert" className="mt-5 rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200">{actionError}</div> : null}
            {searchParams.get('checkout') === 'success' && tradeCase.status === 'awaiting_payment' ? <div className="mt-5 flex items-center gap-2 rounded-lg border border-blue-300/30 bg-blue-500/10 p-3 text-sm text-blue-100"><Loader2 className="h-4 w-4 animate-spin" /> Confirming payment with Stripe. Refreshing this case will show when review starts.</div> : null}
            {searchParams.get('checkout') === 'cancelled' ? <div className="mt-5 rounded-lg border border-amber-300/30 bg-amber-500/10 p-3 text-sm text-amber-100">Checkout was cancelled. Your trade case and documents are still saved.</div> : null}
          </section>

          <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
            <div className="space-y-6">
              <section className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-6">
                <div className="mb-5 flex items-center justify-between">
                  <div><p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#B2F273]">Applicable modules</p><h2 className="mt-1 font-display text-xl font-bold">Clearance checks</h2></div>
                  <ShieldCheck className="h-6 w-6 text-[#B2F273]" />
                </div>
                {tradeCase.checks.length ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {tradeCase.checks.map((check) => (
                      <div key={check.id} className="rounded-xl border border-[#EDF5F2]/10 bg-[#00261C]/30 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-sm font-semibold">{moduleLabels[check.module] || check.module.replace(/_/g, ' ')}</p>
                          <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] ${checkTone(check.state)}`}>{checkStateLabels[check.state]}</span>
                        </div>
                        <p className="mt-2 text-xs leading-relaxed text-[#EDF5F2]/45">{check.summary || check.applicability_reason}</p>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-[#EDF5F2]/40">Checks will appear after the required case information is submitted.</p>}
              </section>

              <section className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-6">
                <div className="mb-5 flex items-end justify-between gap-4">
                  <div><p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#B2F273]">Expected · Found · Suggested fix</p><h2 className="mt-1 font-display text-xl font-bold">Findings</h2></div>
                  <span className="text-sm text-[#EDF5F2]/40">{tradeCase.findings.length} total</span>
                </div>
                {tradeCase.findings.length ? <div className="space-y-4">{tradeCase.findings.map((finding) => <FindingCard key={finding.id} finding={finding} />)}</div> : (
                  <div className="rounded-xl border border-dashed border-[#EDF5F2]/15 p-8 text-center"><CheckCircle2 className="mx-auto mb-3 h-7 w-7 text-[#B2F273]" /><p className="text-sm text-[#EDF5F2]/50">No customer-visible findings yet.</p></div>
                )}
              </section>

              <section className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-6">
                <div className="mb-5 flex items-center justify-between gap-3"><h2 className="font-display text-xl font-bold">Documents and versions</h2><Button onClick={() => setShowDocumentUpload((value) => !value)} className="border border-[#EDF5F2]/15 bg-[#EDF5F2]/5 text-white hover:bg-[#EDF5F2]/10"><FileUp className="mr-2 h-4 w-4" /> Upload document</Button></div>
                {showDocumentUpload && caseId ? <div className="mb-5"><ProoflineDocumentUpload caseId={caseId} documents={tradeCase.documents} onCancel={() => setShowDocumentUpload(false)} onSaved={() => { setShowDocumentUpload(false); void load() }} /></div> : null}
                {tradeCase.documents.length ? <div className="space-y-3">{tradeCase.documents.map((document) => (
                  <div key={document.id} className="flex flex-col justify-between gap-3 rounded-xl border border-[#EDF5F2]/10 bg-[#00261C]/30 p-4 sm:flex-row sm:items-center">
                    <div><p className="text-sm font-semibold">{document.filename}</p><p className="mt-1 text-xs text-[#EDF5F2]/40">{document.document_type.replace(/_/g, ' ')} · Version {document.version}{document.correction_round ? ` · Correction round ${document.correction_round}` : ''}</p></div>
                    <span className={`self-start rounded-full border px-2 py-1 text-[10px] ${document.is_current ? 'border-[#B2F273]/30 bg-[#B2F273]/10 text-[#B2F273]' : 'border-[#EDF5F2]/10 text-[#EDF5F2]/35'}`}>{document.is_current ? 'Current' : 'Superseded'}</span>
                  </div>
                ))}</div> : <p className="text-sm text-[#EDF5F2]/40">No documents have been added.</p>}
              </section>
            </div>

            <aside className="space-y-5">
              <section className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-5">
                <div className="mb-4 flex items-center justify-between gap-2"><div className="flex items-center gap-2"><Users className="h-5 w-5 text-[#B2F273]" /><h2 className="font-display font-bold">Parties</h2></div><button onClick={() => setShowPartyForm((value) => !value)} className="rounded-md p-1.5 text-[#EDF5F2]/45 hover:bg-[#EDF5F2]/5 hover:text-[#B2F273]" aria-label="Add party"><Plus className="h-4 w-4" /></button></div>
                {showPartyForm && caseId ? <div className="mb-4"><ProoflinePartyForm caseId={caseId} onCancel={() => setShowPartyForm(false)} onSaved={() => { setShowPartyForm(false); void load() }} /></div> : null}
                {tradeCase.parties.length ? <ul className="space-y-3">{tradeCase.parties.map((party) => <li key={party.id} className="flex items-start justify-between gap-2 border-b border-[#EDF5F2]/10 pb-3 last:border-0 last:pb-0"><div><p className="text-sm font-medium">{party.name}</p><p className="mt-1 text-xs capitalize text-[#EDF5F2]/40">{party.role.replace(/_/g, ' ')}{party.country_code ? ` · ${party.country_code}` : ''}</p></div>{tradeCase.status === 'draft' || tradeCase.status === 'action_required' ? <button onClick={() => void removeParty(party.id)} aria-label={`Remove ${party.name}`} className="p-1 text-[#EDF5F2]/25 hover:text-red-300"><Trash2 className="h-3.5 w-3.5" /></button> : null}</li>)}</ul> : <p className="text-sm text-[#EDF5F2]/40">Add the buyer, seller and other parties.</p>}
              </section>

              <section className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-5">
                <div className="mb-4 flex items-center gap-2"><Clock3 className="h-5 w-5 text-[#B2F273]" /><h2 className="font-display font-bold">Required actions</h2></div>
                {openActions.length ? <ul className="space-y-3">{openActions.map((action) => <li key={action.id} className="rounded-lg border border-amber-400/20 bg-amber-500/5 p-3 text-sm text-[#EDF5F2]/65"><div className="flex items-start justify-between gap-2"><span>{action.requested_action}</span><span className="shrink-0 rounded-full border border-[#EDF5F2]/10 px-2 py-0.5 text-[10px] capitalize text-[#EDF5F2]/40">{action.status.replace(/_/g, ' ')}</span></div>{tradeCase.status === 'action_required' && caseId && !['resolved', 'submitted_for_review'].includes(action.status) ? <ProoflineRemediationResponse caseId={caseId} action={action} documents={tradeCase.documents} onSaved={() => void load()} /> : null}{action.customer_response ? <p className="mt-2 rounded bg-[#00261C]/35 p-2 text-xs text-[#EDF5F2]/45">Response: {action.customer_response}</p> : null}</li>)}</ul> : <p className="text-sm text-[#EDF5F2]/40">No open remediation actions.</p>}
                {tradeCase.status === 'action_required' && openActions.length > 0 && openActions.every((action) => ['customer_responded', 'resolved'].includes(action.status)) ? <Button onClick={() => void requestFinalReview()} disabled={resubmitting} className="mt-4 w-full border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]">{resubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BadgeCheck className="mr-2 h-4 w-4" />}Request final review</Button> : null}
              </section>

              <section className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-5">
                <div className="mb-3 flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-[#B2F273]" /><h2 className="font-display font-bold">Identity & credentials</h2></div>
                <p className="text-xs leading-relaxed text-[#EDF5F2]/40">Share consented EIN presentation references. Proofline stores verification results and disclosed claims, not wallet contents.</p>
                {Array.isArray(tradeCase.transaction_details.ein_presentations) && tradeCase.transaction_details.ein_presentations.length ? <p className="mt-3 rounded-lg border border-[#B2F273]/20 bg-[#B2F273]/5 p-2 text-xs text-[#B2F273]">{tradeCase.transaction_details.ein_presentations.length} presentation reference(s) ready for verification.</p> : null}
                {tradeCase.status === 'draft' ? <div className="mt-4 space-y-3">
                  <Input aria-label="EIN presentation reference" value={presentationReference} onChange={(event) => setPresentationReference(event.target.value)} placeholder="Presentation reference" className="border-[#EDF5F2]/15 bg-[#00261C] text-white placeholder:text-[#EDF5F2]/25" />
                  <Input aria-label="EIN consent reference" value={consentReference} onChange={(event) => setConsentReference(event.target.value)} placeholder="Consent reference" className="border-[#EDF5F2]/15 bg-[#00261C] text-white placeholder:text-[#EDF5F2]/25" />
                  <Input aria-label="EIN credential type" value={credentialType} onChange={(event) => setCredentialType(event.target.value)} placeholder="Credential type" className="border-[#EDF5F2]/15 bg-[#00261C] text-white placeholder:text-[#EDF5F2]/25" />
                  <Input aria-label="EIN subject reference" value={subjectReference} onChange={(event) => setSubjectReference(event.target.value)} placeholder="Organization or facility reference (optional)" className="border-[#EDF5F2]/15 bg-[#00261C] text-white placeholder:text-[#EDF5F2]/25" />
                  <Button onClick={() => void shareEinPresentation()} disabled={savingEin || !presentationReference.trim() || !consentReference.trim() || !credentialType.trim()} className="w-full border border-[#EDF5F2]/15 bg-[#EDF5F2]/5 text-white hover:bg-[#EDF5F2]/10">{savingEin ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Share presentation reference</Button>
                </div> : null}
              </section>

              <section className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-5">
                <div className="mb-4 flex items-center gap-2"><BadgeCheck className="h-5 w-5 text-[#B2F273]" /><h2 className="font-display font-bold">Clearance report</h2></div>
                {tradeCase.final_report_id ? <><Button onClick={() => void downloadReport()} disabled={downloadingReport} className="w-full border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]">{downloadingReport ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />} Download report</Button>{caseId ? <ProoflineOutcomeFeedback caseId={caseId} /> : null}</> : <p className="text-sm leading-relaxed text-[#EDF5F2]/40">The report becomes available after final analyst approval.</p>}
              </section>
            </aside>
          </div>

          <p className="mx-auto mt-8 max-w-4xl text-center text-[11px] leading-relaxed text-[#EDF5F2]/25">Proofline identifies preventable discrepancies, evidence gaps, regulatory issues and transaction risks based on submitted information. It is not a bank guarantee, customs decision, legal certification or guarantee of payment.</p>
        </div>
      </main>
    </div>
  )
}

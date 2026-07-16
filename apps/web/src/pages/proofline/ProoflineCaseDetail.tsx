import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  Clock3,
  Download,
  FileText,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import type { ProoflineFinding, TradeCaseDetail } from '@shared/types'

import { Button } from '@/components/ui/button'
import { getTradeCase } from '@/lib/proofline/api'
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
  const [tradeCase, setTradeCase] = useState<TradeCaseDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      setTradeCase(await getTradeCase(caseId))
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
                </div>
                <h1 className="font-display text-3xl font-bold">{tradeCase.title}</h1>
                <p className="mt-3 text-sm text-[#EDF5F2]/45">{tradeCase.origin_country || 'Origin pending'} → {tradeCase.destination_country || 'Destination pending'}{tradeCase.amount && tradeCase.currency ? ` · ${tradeCase.currency} ${Number(tradeCase.amount).toLocaleString()}` : ''}</p>
              </div>
              <div className="min-w-[260px] rounded-xl border border-[#EDF5F2]/10 bg-[#00261C]/35 p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#EDF5F2]/35">{tradeCase.final_decision ? 'Final decision' : 'Recommended decision'}</p>
                <p className="mt-2 font-display text-xl font-bold text-[#B2F273]">{decisionLabel(finalOrRecommended)}</p>
                <p className="mt-2 text-xs leading-relaxed text-[#EDF5F2]/40">A final paid-case decision is released only after internal reviewer approval.</p>
              </div>
            </div>
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
                <div className="mb-5 flex items-center justify-between"><h2 className="font-display text-xl font-bold">Documents and versions</h2><FileText className="h-6 w-6 text-[#B2F273]" /></div>
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
                <div className="mb-4 flex items-center gap-2"><Users className="h-5 w-5 text-[#B2F273]" /><h2 className="font-display font-bold">Parties</h2></div>
                {tradeCase.parties.length ? <ul className="space-y-3">{tradeCase.parties.map((party) => <li key={party.id} className="border-b border-[#EDF5F2]/10 pb-3 last:border-0 last:pb-0"><p className="text-sm font-medium">{party.name}</p><p className="mt-1 text-xs capitalize text-[#EDF5F2]/40">{party.role.replace(/_/g, ' ')}{party.country_code ? ` · ${party.country_code}` : ''}</p></li>)}</ul> : <p className="text-sm text-[#EDF5F2]/40">Add the buyer, seller and other parties.</p>}
              </section>

              <section className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-5">
                <div className="mb-4 flex items-center gap-2"><Clock3 className="h-5 w-5 text-[#B2F273]" /><h2 className="font-display font-bold">Required actions</h2></div>
                {openActions.length ? <ul className="space-y-3">{openActions.map((action) => <li key={action.id} className="rounded-lg border border-amber-400/20 bg-amber-500/5 p-3 text-sm text-[#EDF5F2]/65">{action.requested_action}</li>)}</ul> : <p className="text-sm text-[#EDF5F2]/40">No open remediation actions.</p>}
              </section>

              <section className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-5">
                <div className="mb-4 flex items-center gap-2"><BadgeCheck className="h-5 w-5 text-[#B2F273]" /><h2 className="font-display font-bold">Clearance report</h2></div>
                {tradeCase.final_report_id ? <Button className="w-full border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]"><Download className="mr-2 h-4 w-4" /> Download report</Button> : <p className="text-sm leading-relaxed text-[#EDF5F2]/40">The report becomes available after final analyst approval.</p>}
              </section>
            </aside>
          </div>

          <p className="mx-auto mt-8 max-w-4xl text-center text-[11px] leading-relaxed text-[#EDF5F2]/25">Proofline identifies preventable discrepancies, evidence gaps, regulatory issues and transaction risks based on submitted information. It is not a bank guarantee, customs decision, legal certification or guarantee of payment.</p>
        </div>
      </main>
    </div>
  )
}

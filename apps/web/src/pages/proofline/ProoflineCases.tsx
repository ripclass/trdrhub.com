import { useEffect, useState } from 'react'
import { ArrowRight, ClipboardCheck, FilePlus2, Loader2, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { TradeCaseSummary } from '@shared/types'

import { Button } from '@/components/ui/button'
import { listTradeCases } from '@/lib/proofline/api'
import { paymentArrangementLabels, statusLabels, statusTone } from '@/lib/proofline/presentation'

export default function ProoflineCases() {
  const [cases, setCases] = useState<TradeCaseSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const response = await listTradeCases()
      setCases(response.items)
    } catch {
      setError('Your trade cases could not be loaded. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  return (
    <div className="min-h-screen bg-[#00261C] text-white">
      <header className="border-b border-[#EDF5F2]/10 bg-[#00261C]/95">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/proofline" className="flex items-center gap-3">
            <img src="/logo-dark-v2.png" alt="TRDR Hub" className="h-8 w-auto" />
            <span className="border-l border-[#EDF5F2]/15 pl-3 font-display text-sm font-semibold text-[#EDF5F2]/70">Proofline</span>
          </Link>
          <Button asChild className="border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]">
            <Link to="/proofline/new"><FilePlus2 className="mr-2 h-4 w-4" /> Start a trade case</Link>
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-10 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
            <div>
              <p className="mb-2 font-mono text-xs uppercase tracking-[0.2em] text-[#B2F273]">Verified Trade Clearance</p>
              <h1 className="font-display text-3xl font-bold sm:text-4xl">Trade cases</h1>
              <p className="mt-2 text-sm text-[#EDF5F2]/50">Follow automated checks, analyst review, corrections and final reports.</p>
            </div>
            <button onClick={() => void load()} className="inline-flex items-center gap-2 self-start text-sm text-[#EDF5F2]/45 hover:text-[#B2F273]" disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
          </div>

          {loading ? (
            <div className="flex min-h-[320px] items-center justify-center rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/35">
              <Loader2 className="h-6 w-6 animate-spin text-[#B2F273]" /><span className="ml-3 text-sm text-[#EDF5F2]/50">Loading trade cases…</span>
            </div>
          ) : error ? (
            <div role="alert" className="rounded-xl border border-red-400/30 bg-red-500/10 p-5 text-red-100">
              <p>{error}</p>
              <Button onClick={() => void load()} className="mt-4 bg-red-100 text-red-950 hover:bg-white">Try again</Button>
            </div>
          ) : cases.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[#EDF5F2]/15 bg-[#00382E]/25 px-6 py-20 text-center">
              <ClipboardCheck className="mx-auto mb-5 h-10 w-10 text-[#B2F273]" />
              <h2 className="font-display text-xl font-bold">No trade cases yet</h2>
              <p className="mx-auto mt-2 max-w-md text-sm text-[#EDF5F2]/45">Create a case for an LC, open-account order or another payment arrangement.</p>
              <Button asChild className="mt-6 border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]"><Link to="/proofline/new">Start a trade case</Link></Button>
            </div>
          ) : (
            <div className="space-y-4">
              {cases.map((tradeCase) => {
                const findings = Object.values(tradeCase.finding_counts).reduce((sum, count) => sum + count, 0)
                return (
                  <article key={tradeCase.id} className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/45 p-6 transition-colors hover:border-[#B2F273]/30">
                    <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
                      <div className="min-w-0">
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <span className="font-mono text-xs text-[#B2F273]">{tradeCase.case_reference}</span>
                          <span className={`rounded-full border px-2.5 py-1 text-xs ${statusTone(tradeCase.status)}`}>{statusLabels[tradeCase.status]}</span>
                        </div>
                        <h2 className="truncate font-display text-xl font-bold">{tradeCase.title}</h2>
                        <p className="mt-2 text-sm text-[#EDF5F2]/45">{paymentArrangementLabels[tradeCase.payment_arrangement]} · {tradeCase.origin_country || '—'} → {tradeCase.destination_country || '—'}</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-[#EDF5F2]/55">
                        <span>{tradeCase.document_count} {tradeCase.document_count === 1 ? 'document' : 'documents'}</span>
                        <span>{findings} {findings === 1 ? 'finding' : 'findings'}</span>
                        {tradeCase.amount && tradeCase.currency ? <span className="font-mono text-[#EDF5F2]/70">{tradeCase.currency} {Number(tradeCase.amount).toLocaleString()}</span> : null}
                        <Button asChild className="border border-[#EDF5F2]/15 bg-[#EDF5F2]/5 text-white hover:bg-[#B2F273] hover:text-[#00261C]">
                          <Link to={`/proofline/cases/${tradeCase.id}`}>Open case <ArrowRight className="ml-2 h-4 w-4" /></Link>
                        </Button>
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

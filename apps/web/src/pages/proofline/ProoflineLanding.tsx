import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BadgeCheck,
  FileSearch,
  Landmark,
  ScanSearch,
  ShieldCheck,
  UserCheck,
} from 'lucide-react'

import { TRDRFooter } from '@/components/layout/trdr-footer'
import { TRDRHeader } from '@/components/layout/trdr-header'
import { Button } from '@/components/ui/button'

const scope = [
  {
    icon: FileSearch,
    title: 'Transaction and documents',
    body: 'Purchase orders, contracts, LCs, invoices, packing lists, transport evidence, certificates and amendments checked together.',
  },
  {
    icon: ScanSearch,
    title: 'Parties and requirements',
    body: 'Counterparties, sanctions results, buyer requirements and applicable CBAM or EUDR evidence brought into one case.',
  },
  {
    icon: BadgeCheck,
    title: 'Identity and evidence',
    body: 'Available organization, facility and credential evidence is verified through connected services without duplicating credential infrastructure.',
  },
  {
    icon: UserCheck,
    title: 'Analyst verification',
    body: 'Automated findings are reviewed by an internal analyst before a paid case receives its final customer-facing decision.',
  },
]

const workflow = [
  ['01', 'Build the trade case', 'Choose the payment arrangement, add the parties and upload the transaction documents.'],
  ['02', 'TRDRHub runs the applicable checks', 'LCopilot is invoked for an LC. Open-account and other cases follow their own evidence and payment-readiness routes.'],
  ['03', 'Resolve what could hold the trade up', 'Receive specific findings and requested corrections, then upload a new document version without losing the original.'],
  ['04', 'Receive the reviewed report', 'An analyst approves the final decision and the evidence trail behind it.'],
]

export default function ProoflineLanding() {
  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main>
        <section className="relative overflow-hidden border-b border-[#EDF5F2]/10 pb-20 pt-36 md:pt-44">
          <div className="absolute left-1/4 top-0 h-[520px] w-[520px] rounded-full bg-[#B2F273]/10 blur-[130px]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_35%,transparent_75%)]" />
          <div className="container relative z-10 mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[1.15fr_.85fr]">
              <div>
                <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/10 px-4 py-2">
                  <ShieldCheck className="h-4 w-4 text-[#B2F273]" />
                  <span className="text-sm font-medium text-[#B2F273]">Verified Trade Clearance</span>
                </div>
                <h1 className="mb-5 font-display text-5xl font-bold tracking-tight text-white sm:text-6xl">
                  Proofline
                </h1>
                <p className="mb-5 max-w-2xl text-xl leading-relaxed text-[#EDF5F2]/70">
                  Identify the document, compliance, identity, and evidence issues that could delay shipment,
                  presentation, or payment.
                </p>
                <p className="mb-8 max-w-2xl text-base leading-relaxed text-[#EDF5F2]/50">
                  One verified case for the parties, order, shipment, documents and payment route—whether the
                  transaction uses a letter of credit or open-account terms.
                </p>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button asChild size="lg" className="h-12 border-none bg-[#B2F273] px-7 font-bold text-[#00261C] hover:bg-[#a3e662]">
                    <Link to="/proofline/new">Start a trade case <ArrowRight className="ml-2 h-4 w-4" /></Link>
                  </Button>
                  <Button asChild size="lg" className="h-12 border border-[#EDF5F2]/15 bg-[#EDF5F2]/5 px-7 text-white hover:bg-[#EDF5F2]/10">
                    <Link to="/proofline/cases">View my cases</Link>
                  </Button>
                </div>
              </div>

              <div className="rounded-2xl border border-[#B2F273]/25 bg-[#00382E]/70 p-6 shadow-2xl shadow-black/20 backdrop-blur-sm sm:p-8">
                <p className="mb-5 font-mono text-xs uppercase tracking-[0.2em] text-[#B2F273]">A complete trade decision</p>
                <div className="space-y-3">
                  {['Payment arrangement and terms', 'Cross-document consistency', 'Party and sanctions checks', 'Applicable regulatory evidence', 'Buyer and credential requirements', 'Human analyst approval'].map((item) => (
                    <div key={item} className="flex items-center gap-3 rounded-lg border border-[#EDF5F2]/10 bg-[#00261C]/40 px-4 py-3">
                      <ShieldCheck className="h-4 w-4 shrink-0 text-[#B2F273]" />
                      <span className="text-sm text-[#EDF5F2]/75">{item}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-6 border-t border-[#EDF5F2]/10 pt-5">
                  <p className="font-display text-base font-semibold text-white">LCopilot checks the instrument. Proofline clears the trade.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-b border-[#EDF5F2]/10 py-20">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mx-auto mb-12 max-w-3xl text-center">
              <p className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-[#B2F273]">One case, applicable checks only</p>
              <h2 className="font-display text-3xl font-bold text-white sm:text-4xl">Readiness across the whole transaction</h2>
            </div>
            <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-2">
              {scope.map(({ icon: Icon, title, body }) => (
                <article key={title} className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/50 p-7">
                  <Icon className="mb-5 h-7 w-7 text-[#B2F273]" />
                  <h3 className="mb-2 font-display text-xl font-bold text-white">{title}</h3>
                  <p className="text-sm leading-relaxed text-[#EDF5F2]/55">{body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[.8fr_1.2fr]">
              <div>
                <Landmark className="mb-5 h-9 w-9 text-[#B2F273]" />
                <h2 className="mb-4 font-display text-3xl font-bold text-white">Built around how the trade gets paid</h2>
                <p className="text-base leading-relaxed text-[#EDF5F2]/55">
                  Letter of credit, open account, TT, documentary collection, supply-chain finance,
                  factoring, consignment and other arrangements each receive the right evidence route.
                </p>
              </div>
              <ol className="space-y-4">
                {workflow.map(([number, title, body]) => (
                  <li key={number} className="grid grid-cols-[auto_1fr] gap-4 rounded-xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-5">
                    <span className="font-mono text-sm font-bold text-[#B2F273]">{number}</span>
                    <div>
                      <h3 className="mb-1 font-display font-semibold text-white">{title}</h3>
                      <p className="text-sm leading-relaxed text-[#EDF5F2]/50">{body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section className="border-t border-[#EDF5F2]/10 bg-[#00382E]/50 py-20 text-center">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="mb-5 font-display text-3xl font-bold text-white">Find what could stop the trade before it does.</h2>
            <Button asChild size="lg" className="h-12 border-none bg-[#B2F273] px-8 font-bold text-[#00261C] hover:bg-[#a3e662]">
              <Link to="/proofline/new">Start a trade case <ArrowRight className="ml-2 h-4 w-4" /></Link>
            </Button>
            <p className="mx-auto mt-7 max-w-3xl text-xs leading-relaxed text-[#EDF5F2]/35">
              Proofline identifies preventable discrepancies, evidence gaps, regulatory issues and transaction risks based on the information submitted. It does not guarantee bank acceptance, customs clearance, shipment, payment, regulatory approval or financing approval.
            </p>
          </div>
        </section>
      </main>
      <TRDRFooter />
    </div>
  )
}

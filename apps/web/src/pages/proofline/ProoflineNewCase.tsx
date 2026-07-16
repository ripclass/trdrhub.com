import { FormEvent, useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, Check, FilePlus2, Loader2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import type { PaymentArrangement } from '@shared/types'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { createTradeCase } from '@/lib/proofline/api'

const paymentArrangements: Array<{
  value: PaymentArrangement
  label: string
  description: string
}> = [
  { value: 'letter_of_credit', label: 'Letter of credit', description: 'LCopilot reviews the instrument and feeds its structured findings into Proofline.' },
  { value: 'open_account', label: 'Open account / sales contract', description: 'Shipment and invoice are paid under agreed buyer terms without an LC.' },
  { value: 'advance_tt', label: 'Advance TT', description: 'The buyer pays by telegraphic transfer before shipment.' },
  { value: 'partial_advance_balance', label: 'Partial advance + balance', description: 'Part is paid in advance and the balance follows an agreed trigger.' },
  { value: 'documents_against_payment', label: 'Documents against payment', description: 'Documents are released through banks against payment.' },
  { value: 'documents_against_acceptance', label: 'Documents against acceptance', description: 'Documents are released against acceptance of a time draft.' },
  { value: 'buyer_led_supply_chain_finance', label: 'Buyer-led supply-chain finance', description: 'Approved invoices may be financed through the buyer programme.' },
  { value: 'factoring_receivables_finance', label: 'Factoring / receivables finance', description: 'Receivables are supported or purchased by a financier or insurer.' },
  { value: 'consignment', label: 'Consignment', description: 'Payment follows sale or use of consigned goods.' },
  { value: 'other', label: 'Other', description: 'Describe the arrangement so an analyst can route the evidence correctly.' },
]

const steps = ['Payment', 'Trade details', 'Parties', 'Products', 'Documents', 'Evidence', 'Service', 'Submit']

function PaymentRouteNote({ arrangement }: { arrangement: PaymentArrangement }) {
  if (arrangement === 'open_account') {
    return (
      <div className="rounded-xl border border-[#B2F273]/25 bg-[#B2F273]/5 p-4 text-sm leading-relaxed text-[#EDF5F2]/65">
        We will check the purchase order, sales contract, invoice approval conditions, shipment evidence,
        deductions, chargebacks and expected payment date. Add any payment undertaking, insurance, or
        receivables-finance evidence when you reach Documents.
      </div>
    )
  }
  if (arrangement === 'letter_of_credit') {
    return (
      <div className="rounded-xl border border-[#B2F273]/25 bg-[#B2F273]/5 p-4 text-sm leading-relaxed text-[#EDF5F2]/65">
        Proofline will invoke the existing LCopilot review and combine its cited LC findings with the rest of
        the transaction. Existing LCopilot work can be linked without copying the validation engine.
      </div>
    )
  }
  return (
    <div className="rounded-xl border border-[#EDF5F2]/10 bg-[#00382E]/40 p-4 text-sm leading-relaxed text-[#EDF5F2]/55">
      Proofline will request the payment evidence and trigger dates applicable to this arrangement.
    </div>
  )
}

export default function ProoflineNewCase() {
  const navigate = useNavigate()
  const [stage, setStage] = useState<1 | 2>(1)
  const [arrangement, setArrangement] = useState<PaymentArrangement>('letter_of_credit')
  const [title, setTitle] = useState('')
  const [originCountry, setOriginCountry] = useState('')
  const [destinationCountry, setDestinationCountry] = useState('')
  const [currency, setCurrency] = useState('USD')
  const [amount, setAmount] = useState('')
  const [paymentTerms, setPaymentTerms] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selected = useMemo(
    () => paymentArrangements.find((item) => item.value === arrangement),
    [arrangement],
  )

  async function saveDraft(event: FormEvent) {
    event.preventDefault()
    if (title.trim().length < 3) {
      setError('Give the trade case a short title so your team can find it later.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const tradeCase = await createTradeCase({
        title: title.trim(),
        payment_arrangement: arrangement,
        origin_country: originCountry.trim().toUpperCase() || undefined,
        destination_country: destinationCountry.trim().toUpperCase() || undefined,
        currency: currency.trim().toUpperCase() || undefined,
        amount: amount ? Number(amount) : undefined,
        payment_terms: paymentTerms.trim() || undefined,
      })
      navigate(`/proofline/cases/${tradeCase.id}`)
    } catch (caught) {
      const responseMessage = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(responseMessage || 'The draft could not be saved. Your entries are still here; please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#00261C] text-white">
      <header className="border-b border-[#EDF5F2]/10 bg-[#00261C]/95">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/proofline" className="flex items-center gap-3">
            <img src="/logo-dark-v2.png" alt="TRDR Hub" className="h-8 w-auto" />
            <span className="hidden border-l border-[#EDF5F2]/15 pl-3 font-display text-sm font-semibold text-[#EDF5F2]/70 sm:block">Proofline</span>
          </Link>
          <Link to="/proofline/cases" className="text-sm text-[#EDF5F2]/50 hover:text-[#B2F273]">Save and return later</Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-10 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="mb-10">
            <div className="mb-4 flex items-center gap-2 text-sm text-[#B2F273]">
              <FilePlus2 className="h-4 w-4" /> New trade case
            </div>
            <h1 className="font-display text-3xl font-bold sm:text-4xl">Build the case in small steps</h1>
            <p className="mt-3 max-w-2xl text-[#EDF5F2]/50">Start with how the transaction gets paid. Proofline uses that answer to request only the relevant documents and evidence.</p>
          </div>

          <ol aria-label="Trade case progress" className="mb-10 grid grid-cols-4 gap-2 md:grid-cols-8">
            {steps.map((item, index) => {
              const current = index === stage - 1
              const complete = index < stage - 1
              return (
                <li key={item} className="min-w-0">
                  <div className={`mb-2 h-1 rounded-full ${current || complete ? 'bg-[#B2F273]' : 'bg-[#EDF5F2]/10'}`} />
                  <span className={`text-[10px] font-mono uppercase tracking-wide ${current ? 'text-[#B2F273]' : 'text-[#EDF5F2]/35'}`}>{complete ? <Check className="inline h-3 w-3" /> : item}</span>
                </li>
              )
            })}
          </ol>

          {stage === 1 ? (
            <section className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/45 p-6 sm:p-8">
              <div className="mb-7">
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.2em] text-[#B2F273]">Step 1 of 8</p>
                <h2 className="font-display text-2xl font-bold">Payment arrangement</h2>
                <p className="mt-2 text-sm text-[#EDF5F2]/50">Choose the arrangement agreed with the buyer.</p>
              </div>

              <fieldset className="grid gap-3 md:grid-cols-2">
                <legend className="sr-only">Payment arrangement</legend>
                {paymentArrangements.map((item) => (
                  <label key={item.value} className={`flex cursor-pointer gap-3 rounded-xl border p-4 transition-colors ${arrangement === item.value ? 'border-[#B2F273]/70 bg-[#B2F273]/5' : 'border-[#EDF5F2]/10 bg-[#00261C]/30 hover:border-[#EDF5F2]/25'}`}>
                    <input type="radio" name="payment-arrangement" value={item.value} checked={arrangement === item.value} onChange={() => setArrangement(item.value)} className="mt-1 accent-[#B2F273]" aria-label={item.label} />
                    <span>
                      <span className="block text-sm font-semibold text-white">{item.label}</span>
                      <span className="mt-1 block text-xs leading-relaxed text-[#EDF5F2]/45">{item.description}</span>
                    </span>
                  </label>
                ))}
              </fieldset>
              <div className="mt-6"><PaymentRouteNote arrangement={arrangement} /></div>
              <div className="mt-7 flex justify-end">
                <Button onClick={() => setStage(2)} className="border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]">Continue to trade details <ArrowRight className="ml-2 h-4 w-4" /></Button>
              </div>
            </section>
          ) : (
            <form onSubmit={saveDraft} className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/45 p-6 sm:p-8">
              <div className="mb-7">
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.2em] text-[#B2F273]">Step 2 of 8</p>
                <h2 className="font-display text-2xl font-bold">Basic trade details</h2>
                <p className="mt-2 text-sm text-[#EDF5F2]/50">Create the draft now. Parties and documents are added on the case workspace.</p>
              </div>
              <div className="grid gap-5 md:grid-cols-2">
                <div className="md:col-span-2">
                  <label htmlFor="case-title" className="mb-2 block text-sm font-medium">Case title</label>
                  <Input id="case-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Buyer, order or shipment reference" className="border-[#EDF5F2]/15 bg-[#00261C]/60 text-white placeholder:text-[#EDF5F2]/25" required minLength={3} />
                </div>
                <div>
                  <label htmlFor="origin-country" className="mb-2 block text-sm font-medium">Export country code</label>
                  <Input id="origin-country" value={originCountry} onChange={(event) => setOriginCountry(event.target.value)} placeholder="BD" maxLength={2} className="border-[#EDF5F2]/15 bg-[#00261C]/60 text-white placeholder:text-[#EDF5F2]/25" />
                </div>
                <div>
                  <label htmlFor="destination-country" className="mb-2 block text-sm font-medium">Import country code</label>
                  <Input id="destination-country" value={destinationCountry} onChange={(event) => setDestinationCountry(event.target.value)} placeholder="US" maxLength={2} className="border-[#EDF5F2]/15 bg-[#00261C]/60 text-white placeholder:text-[#EDF5F2]/25" />
                </div>
                <div>
                  <label htmlFor="currency" className="mb-2 block text-sm font-medium">Currency</label>
                  <Input id="currency" value={currency} onChange={(event) => setCurrency(event.target.value)} maxLength={3} className="border-[#EDF5F2]/15 bg-[#00261C]/60 text-white" />
                </div>
                <div>
                  <label htmlFor="amount" className="mb-2 block text-sm font-medium">Transaction value</label>
                  <Input id="amount" type="number" min="0.01" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="Optional" className="border-[#EDF5F2]/15 bg-[#00261C]/60 text-white placeholder:text-[#EDF5F2]/25" />
                </div>
                <div className="md:col-span-2">
                  <label htmlFor="payment-terms" className="mb-2 block text-sm font-medium">Payment terms</label>
                  <textarea id="payment-terms" value={paymentTerms} onChange={(event) => setPaymentTerms(event.target.value)} placeholder={`Describe ${selected?.label.toLowerCase()} terms, triggers and tenor if known`} rows={4} className="w-full rounded-md border border-[#EDF5F2]/15 bg-[#00261C]/60 px-3 py-2 text-sm text-white outline-none placeholder:text-[#EDF5F2]/25 focus:border-[#B2F273]/60" />
                </div>
              </div>
              {error ? <div role="alert" className="mt-5 rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200">{error}</div> : null}
              <div className="mt-7 flex flex-col-reverse justify-between gap-3 sm:flex-row">
                <Button type="button" onClick={() => setStage(1)} className="border border-[#EDF5F2]/15 bg-transparent text-white hover:bg-[#EDF5F2]/5"><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
                <Button type="submit" disabled={saving} className="border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]">{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Save draft</Button>
              </div>
            </form>
          )}
        </div>
      </main>
    </div>
  )
}

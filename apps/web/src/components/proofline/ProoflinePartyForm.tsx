import { FormEvent, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { createTradeCaseParty } from '@/lib/proofline/api'

const roles = [
  ['buyer', 'Buyer'], ['seller', 'Seller'], ['exporter', 'Exporter'], ['importer', 'Importer'],
  ['issuing_bank', 'Issuing bank'], ['advising_bank', 'Advising bank'], ['confirming_bank', 'Confirming bank'],
  ['manufacturer', 'Manufacturer'], ['facility', 'Production facility'], ['freight_forwarder', 'Freight forwarder'],
  ['insurer', 'Insurer'], ['financier', 'Financier'], ['other', 'Other'],
]

export function ProoflinePartyForm({ caseId, onSaved, onCancel }: { caseId: string; onSaved: () => void; onCancel: () => void }) {
  const [role, setRole] = useState('buyer')
  const [name, setName] = useState('')
  const [countryCode, setCountryCode] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await createTradeCaseParty(caseId, {
        role,
        name: name.trim(),
        country_code: countryCode.trim().toUpperCase() || undefined,
      })
      onSaved()
    } catch (caught) {
      setError((caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'The party could not be added.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-xl border border-[#B2F273]/20 bg-[#00261C]/45 p-4">
      <div>
        <label htmlFor="party-role" className="mb-1.5 block text-xs font-medium text-[#EDF5F2]/65">Role</label>
        <select id="party-role" value={role} onChange={(event) => setRole(event.target.value)} className="h-10 w-full rounded-md border border-[#EDF5F2]/15 bg-[#00261C] px-3 text-sm text-white">
          {roles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="party-name" className="mb-1.5 block text-xs font-medium text-[#EDF5F2]/65">Legal or trading name</label>
        <Input id="party-name" value={name} onChange={(event) => setName(event.target.value)} required minLength={2} className="border-[#EDF5F2]/15 bg-[#00261C] text-white" />
      </div>
      <div>
        <label htmlFor="party-country" className="mb-1.5 block text-xs font-medium text-[#EDF5F2]/65">Country code</label>
        <Input id="party-country" value={countryCode} onChange={(event) => setCountryCode(event.target.value)} maxLength={2} placeholder="US" className="border-[#EDF5F2]/15 bg-[#00261C] text-white placeholder:text-[#EDF5F2]/25" />
      </div>
      {error ? <p role="alert" className="text-xs text-red-200">{error}</p> : null}
      <div className="flex gap-2">
        <Button type="button" onClick={onCancel} className="flex-1 border border-[#EDF5F2]/15 bg-transparent text-white hover:bg-[#EDF5F2]/5">Cancel</Button>
        <Button type="submit" disabled={saving} className="flex-1 border-none bg-[#B2F273] font-bold text-[#00261C] hover:bg-[#a3e662]">{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Add party</Button>
      </div>
    </form>
  )
}

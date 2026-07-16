import * as React from 'react'
import {
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  Clock3,
  FileText,
  Loader2,
  RefreshCw,
  ShieldCheck,
  UserCheck,
} from 'lucide-react'

import { api } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/components/ui/use-toast'

interface QueueItem {
  id: string
  case_reference: string
  title: string
  status: string
  payment_arrangement: string
  service_package_id: string | null
  recommended_decision: string | null
  reviewer_user_id: string | null
  customer_name: string
  customer_email: string | null
  finding_count: number
  submitted_at: string | null
  updated_at: string | null
}

interface Finding {
  id: string
  source_module: string
  category: string
  severity: string
  title: string
  explanation: string
  expected: string
  observed: string
  suggested_correction: string
  visibility: string
  status: string
}

interface ReviewDetail {
  case: QueueItem & {
    final_decision: string | null
    origin_country: string | null
    destination_country: string | null
    currency: string | null
    amount: string | null
    payment_terms: string | null
    correction_rounds_used: number
  }
  parties: Array<{ id: string; role: string; name: string; country_code: string | null }>
  documents: Array<{
    id: string
    document_id: string
    document_type: string
    filename: string
    version: number
    correction_round: number
    is_current: boolean
    ocr_confidence: number | null
    extracted_fields: Record<string, unknown>
    download_url: string | null
  }>
  checks: Array<{ id: string; module: string; state: string; summary: string | null; safe_error_message: string | null }>
  findings: Finding[]
  actions: Array<{ id: string; finding_id: string; requested_action: string; status: string; correction_round: number; customer_response: string | null }>
  decisions: Array<{ id: string; version: number; decision: string; decision_type: string; summary: string; reason: string; override_reason: string | null }>
  timeline: Array<{ id: string; event_type: string; actor_type: string; reason: string | null; occurred_at: string | null; details: Record<string, unknown> }>
}

const statusTone: Record<string, string> = {
  awaiting_analyst_review: 'border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300',
  action_required: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
  customer_resubmitted: 'border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300',
  final_review: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
}

function errorMessage(error: unknown): string {
  const typed = error as { response?: { data?: { detail?: string } }; message?: string }
  return typed.response?.data?.detail || typed.message || 'Request failed'
}

function elapsed(iso: string | null): string {
  if (!iso) return 'Not timestamped'
  const hours = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000))
  if (hours < 1) return 'Less than 1 hour'
  if (hours < 24) return `${hours}h waiting`
  return `${Math.floor(hours / 24)}d ${hours % 24}h waiting`
}

export function ProoflineReviewQueue() {
  const { toast } = useToast()
  const [items, setItems] = React.useState<QueueItem[]>([])
  const [selected, setSelected] = React.useState<string | null>(null)
  const [detail, setDetail] = React.useState<ReviewDetail | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [busy, setBusy] = React.useState(false)
  const [status, setStatus] = React.useState('all')
  const [customer, setCustomer] = React.useState('')
  const [servicePackage, setServicePackage] = React.useState('all')
  const [internalNote, setInternalNote] = React.useState('')
  const [correctionFinding, setCorrectionFinding] = React.useState<string | null>(null)
  const [correctionText, setCorrectionText] = React.useState('')
  const [decision, setDecision] = React.useState('CLEAR')
  const [decisionSummary, setDecisionSummary] = React.useState('')
  const [decisionReason, setDecisionReason] = React.useState('')
  const [overrideReason, setOverrideReason] = React.useState('')

  const loadList = React.useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.get<{ count: number; items: QueueItem[] }>('/api/admin/proofline', {
        params: {
          status: status === 'all' ? undefined : status,
          customer: customer.trim() || undefined,
          service_package: servicePackage === 'all' ? undefined : servicePackage,
        },
      })
      setItems(response.data.items)
    } catch (error) {
      toast({ title: 'Could not load Proofline queue', description: errorMessage(error), variant: 'destructive' })
    } finally {
      setLoading(false)
    }
  }, [customer, servicePackage, status, toast])

  const loadDetail = React.useCallback(async (caseId: string) => {
    setLoading(true)
    try {
      const response = await api.get<ReviewDetail>(`/api/admin/proofline/${caseId}`)
      setDetail(response.data)
    } catch (error) {
      toast({ title: 'Could not load trade case', description: errorMessage(error), variant: 'destructive' })
      setSelected(null)
    } finally {
      setLoading(false)
    }
  }, [toast])

  React.useEffect(() => { void loadList() }, [loadList])
  React.useEffect(() => { if (selected) void loadDetail(selected) }, [loadDetail, selected])

  async function mutate(request: () => Promise<unknown>, message: string) {
    if (!selected) return
    setBusy(true)
    try {
      await request()
      toast({ title: message })
      await loadDetail(selected)
      await loadList()
    } catch (error) {
      toast({ title: 'Action failed', description: errorMessage(error), variant: 'destructive' })
    } finally {
      setBusy(false)
    }
  }

  if (selected && detail) {
    const caseData = detail.case
    return (
      <div className="space-y-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div>
            <Button variant="ghost" className="mb-3 -ml-3" onClick={() => { setSelected(null); setDetail(null) }}><ArrowLeft className="mr-2 h-4 w-4" /> Back to queue</Button>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-muted-foreground">{caseData.case_reference}</span>
              <Badge variant="outline" className={statusTone[caseData.status]}>{caseData.status.replace(/_/g, ' ')}</Badge>
              <Badge variant="secondary">{caseData.payment_arrangement.replace(/_/g, ' ')}</Badge>
            </div>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">{caseData.title}</h1>
            <p className="mt-2 text-sm text-muted-foreground">{caseData.origin_country || 'Origin pending'} → {caseData.destination_country || 'Destination pending'} · Recommended {caseData.recommended_decision || 'pending'}</p>
          </div>
          <Button disabled={busy || Boolean(caseData.reviewer_user_id)} onClick={() => void mutate(() => api.post(`/api/admin/proofline/${selected}/claim`, { force: false }), 'Case claimed')}>
            <UserCheck className="mr-2 h-4 w-4" /> {caseData.reviewer_user_id ? 'Assigned' : 'Claim case'}
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <Card><CardContent className="pt-5"><p className="text-xs uppercase tracking-wide text-muted-foreground">Findings</p><p className="mt-1 text-2xl font-bold">{detail.findings.length}</p></CardContent></Card>
          <Card><CardContent className="pt-5"><p className="text-xs uppercase tracking-wide text-muted-foreground">Documents</p><p className="mt-1 text-2xl font-bold">{detail.documents.length}</p></CardContent></Card>
          <Card><CardContent className="pt-5"><p className="text-xs uppercase tracking-wide text-muted-foreground">Checks</p><p className="mt-1 text-2xl font-bold">{detail.checks.length}</p></CardContent></Card>
          <Card><CardContent className="pt-5"><p className="text-xs uppercase tracking-wide text-muted-foreground">Correction rounds</p><p className="mt-1 text-2xl font-bold">{caseData.correction_rounds_used}</p></CardContent></Card>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
          <div className="space-y-6">
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5" /> Applicable checks</CardTitle></CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-2">
                {detail.checks.map((check) => <div key={check.id} className="rounded-lg border p-3"><div className="flex items-start justify-between gap-2"><span className="font-medium capitalize">{check.module.replace(/_/g, ' ')}</span><Badge variant="outline">{check.state.replace(/_/g, ' ')}</Badge></div><p className="mt-2 text-xs text-muted-foreground">{check.safe_error_message || check.summary}</p></div>)}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Findings review</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {detail.findings.map((finding) => (
                  <article key={finding.id} className="rounded-xl border p-4">
                    <div className="flex flex-wrap items-center gap-2"><Badge>{finding.severity}</Badge><Badge variant="outline">{finding.source_module.replace(/_/g, ' ')}</Badge><Badge variant="secondary">{finding.visibility}</Badge><Badge variant="outline">{finding.status.replace(/_/g, ' ')}</Badge></div>
                    <h3 className="mt-3 font-semibold">{finding.title}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">{finding.explanation}</p>
                    <dl className="mt-4 grid gap-3 md:grid-cols-3">
                      <div className="rounded-lg bg-muted/40 p-3"><dt className="text-xs font-semibold uppercase text-muted-foreground">Expected</dt><dd className="mt-1 text-sm">{finding.expected}</dd></div>
                      <div className="rounded-lg bg-muted/40 p-3"><dt className="text-xs font-semibold uppercase text-muted-foreground">Observed</dt><dd className="mt-1 text-sm">{finding.observed}</dd></div>
                      <div className="rounded-lg bg-muted/40 p-3"><dt className="text-xs font-semibold uppercase text-muted-foreground">Suggested fix</dt><dd className="mt-1 text-sm">{finding.suggested_correction}</dd></div>
                    </dl>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" disabled={busy} onClick={() => void mutate(() => api.patch(`/api/admin/proofline/${selected}/findings/${finding.id}`, { status: 'false_positive', reviewer_decision: 'false_positive' }), 'Finding marked false positive')}>False positive</Button>
                      <Button size="sm" variant="outline" disabled={busy} onClick={() => void mutate(() => api.patch(`/api/admin/proofline/${selected}/findings/${finding.id}`, { status: 'resolved', reviewer_decision: 'resolved' }), 'Finding resolved')}>Resolve</Button>
                      <Button size="sm" variant="outline" disabled={busy} onClick={() => void mutate(() => api.patch(`/api/admin/proofline/${selected}/findings/${finding.id}`, { visibility: finding.visibility === 'customer' ? 'internal' : 'customer' }), 'Finding visibility updated')}>{finding.visibility === 'customer' ? 'Make internal' : 'Show customer'}</Button>
                      <Button size="sm" onClick={() => { setCorrectionFinding(finding.id); setCorrectionText(finding.suggested_correction) }}>Request correction</Button>
                    </div>
                    {correctionFinding === finding.id ? <div className="mt-4 rounded-lg border bg-muted/20 p-3"><Label htmlFor={`correction-${finding.id}`}>Customer action</Label><Textarea id={`correction-${finding.id}`} className="mt-2" value={correctionText} onChange={(event) => setCorrectionText(event.target.value)} /><div className="mt-2 flex gap-2"><Button size="sm" disabled={busy || !correctionText.trim()} onClick={() => void mutate(() => api.post(`/api/admin/proofline/${selected}/corrections`, { finding_id: finding.id, requested_action: correctionText.trim() }), 'Correction requested').then(() => { setCorrectionFinding(null); setCorrectionText('') })}>Send request</Button><Button size="sm" variant="ghost" onClick={() => setCorrectionFinding(null)}>Cancel</Button></div></div> : null}
                  </article>
                ))}
                {!detail.findings.length ? <p className="text-sm text-muted-foreground">No findings were generated. Confirm the source evidence before final approval.</p> : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><FileText className="h-5 w-5" /> Documents and extracted fields</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {detail.documents.map((document) => <details key={document.id} className="rounded-lg border p-3"><summary className="cursor-pointer text-sm font-medium">{document.filename} · v{document.version}{document.is_current ? ' · current' : ' · superseded'}</summary><div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground"><span>{document.document_type.replace(/_/g, ' ')}</span><span>OCR {document.ocr_confidence == null ? 'unavailable' : `${Math.round(document.ocr_confidence * 100)}%`}</span>{document.download_url ? <a className="font-medium text-primary underline" href={document.download_url} target="_blank" rel="noreferrer">Open original</a> : null}</div><pre className="mt-3 max-h-72 overflow-auto rounded bg-muted p-3 text-xs">{JSON.stringify(document.extracted_fields, null, 2)}</pre></details>)}
              </CardContent>
            </Card>
          </div>

          <aside className="space-y-5">
            <Card><CardHeader><CardTitle>Parties</CardTitle></CardHeader><CardContent className="space-y-3">{detail.parties.map((party) => <div key={party.id} className="border-b pb-3 last:border-0"><p className="text-sm font-medium">{party.name}</p><p className="text-xs capitalize text-muted-foreground">{party.role.replace(/_/g, ' ')}{party.country_code ? ` · ${party.country_code}` : ''}</p></div>)}</CardContent></Card>

            <Card><CardHeader><CardTitle>Internal note</CardTitle></CardHeader><CardContent><Textarea value={internalNote} onChange={(event) => setInternalNote(event.target.value)} placeholder="Reviewer-only reasoning; never shown to the customer" /><Button className="mt-3 w-full" variant="outline" disabled={busy || !internalNote.trim()} onClick={() => void mutate(() => api.post(`/api/admin/proofline/${selected}/notes`, { note: internalNote.trim() }), 'Internal note saved').then(() => setInternalNote(''))}>Save internal note</Button></CardContent></Card>

            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><BadgeCheck className="h-5 w-5" /> Approve final decision</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div><Label>Decision</Label><Select value={decision} onValueChange={setDecision}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="CLEAR">Clear</SelectItem><SelectItem value="CONDITIONAL_CLEARANCE">Conditional clearance</SelectItem><SelectItem value="ACTION_REQUIRED">Action required</SelectItem><SelectItem value="BLOCKED">Blocked</SelectItem><SelectItem value="UNABLE_TO_ASSESS">Unable to assess</SelectItem></SelectContent></Select></div>
                <div><Label>Customer summary</Label><Textarea className="mt-1" value={decisionSummary} onChange={(event) => setDecisionSummary(event.target.value)} /></div>
                <div><Label>Decision reason</Label><Textarea className="mt-1" value={decisionReason} onChange={(event) => setDecisionReason(event.target.value)} /></div>
                {caseData.recommended_decision && caseData.recommended_decision !== decision ? <div><Label>Override reason</Label><Textarea className="mt-1" value={overrideReason} onChange={(event) => setOverrideReason(event.target.value)} placeholder="Required because the final decision differs from the recommendation" /></div> : null}
                <Button className="w-full" disabled={busy || !decisionSummary.trim() || !decisionReason.trim() || Boolean(caseData.recommended_decision && caseData.recommended_decision !== decision && !overrideReason.trim())} onClick={() => void mutate(() => api.post(`/api/admin/proofline/${selected}/decisions`, { decision, summary: decisionSummary.trim(), reason: decisionReason.trim(), override_reason: overrideReason.trim() || undefined, idempotency_key: `reviewer-${selected}-${Date.now()}` }), 'Final decision approved')}>{busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}Approve final decision</Button>
              </CardContent>
            </Card>

            <Card><CardHeader><CardTitle className="flex items-center gap-2"><Clock3 className="h-5 w-5" /> Audit timeline</CardTitle></CardHeader><CardContent className="space-y-3">{detail.timeline.slice(0, 12).map((event) => <div key={event.id} className="border-l-2 pl-3"><p className="text-sm font-medium">{event.event_type.replace(/_/g, ' ')}</p><p className="text-xs text-muted-foreground">{event.reason}</p></div>)}</CardContent></Card>
          </aside>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div><p className="text-sm font-medium text-primary">Proofline · Verified Trade Clearance</p><h1 className="mt-1 text-3xl font-bold tracking-tight">Analyst queue</h1><p className="mt-2 text-muted-foreground">Verify automated findings, close evidence gaps, and approve customer-facing decisions.</p></div>
        <Button variant="outline" onClick={() => void loadList()}><RefreshCw className="mr-2 h-4 w-4" /> Refresh</Button>
      </div>
      <Card><CardContent className="grid gap-3 pt-6 md:grid-cols-3"><div><Label>Status</Label><Select value={status} onValueChange={setStatus}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All active cases</SelectItem><SelectItem value="awaiting_analyst_review">Awaiting analyst review</SelectItem><SelectItem value="action_required">Action required</SelectItem><SelectItem value="customer_resubmitted">Customer resubmitted</SelectItem><SelectItem value="final_review">Final review</SelectItem></SelectContent></Select></div><div><Label>Customer</Label><Input className="mt-1" value={customer} onChange={(event) => setCustomer(event.target.value)} placeholder="Company or email" /></div><div><Label>Service level</Label><Select value={servicePackage} onValueChange={setServicePackage}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All service levels</SelectItem><SelectItem value="proofline_standard">Standard</SelectItem><SelectItem value="proofline_managed">Managed clearance</SelectItem><SelectItem value="custom">Custom</SelectItem></SelectContent></Select></div></CardContent></Card>
      {loading ? <div className="flex justify-center py-16"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div> : items.length ? <div className="space-y-3">{items.map((item) => <button key={item.id} className="flex w-full flex-col justify-between gap-4 rounded-xl border bg-card p-5 text-left transition-colors hover:border-primary/40 md:flex-row md:items-center" onClick={() => setSelected(item.id)}><div><div className="flex flex-wrap items-center gap-2"><span className="font-mono text-xs text-muted-foreground">{item.case_reference}</span><Badge variant="outline" className={statusTone[item.status]}>{item.status.replace(/_/g, ' ')}</Badge>{item.reviewer_user_id ? <Badge variant="secondary">Assigned</Badge> : null}</div><h2 className="mt-2 text-lg font-semibold">{item.title}</h2><p className="mt-1 text-sm text-muted-foreground">{item.customer_name} · {item.payment_arrangement.replace(/_/g, ' ')}</p></div><div className="flex items-center gap-6"><div><p className="text-xs uppercase text-muted-foreground">Open findings</p><p className="text-xl font-bold">{item.finding_count}</p></div><div><p className="text-xs uppercase text-muted-foreground">Wait</p><p className="font-medium">{elapsed(item.updated_at)}</p></div></div></button>)}</div> : <Card><CardContent className="py-16 text-center"><ShieldCheck className="mx-auto h-8 w-8 text-muted-foreground" /><p className="mt-3 font-medium">No Proofline cases match these filters.</p></CardContent></Card>}
    </div>
  )
}

export default ProoflineReviewQueue

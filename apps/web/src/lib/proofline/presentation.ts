import type { PaymentArrangement, ProoflineCheckState, ProoflineDecision, TradeCaseStatus } from '@shared/types'

export const paymentArrangementLabels: Record<PaymentArrangement, string> = {
  letter_of_credit: 'Letter of credit',
  open_account: 'Open account / sales contract',
  advance_tt: 'Advance TT',
  partial_advance_balance: 'Partial advance + balance',
  documents_against_payment: 'Documents against payment',
  documents_against_acceptance: 'Documents against acceptance',
  buyer_led_supply_chain_finance: 'Buyer-led supply-chain finance',
  factoring_receivables_finance: 'Factoring / receivables finance',
  consignment: 'Consignment',
  other: 'Other',
}

export const statusLabels: Record<TradeCaseStatus, string> = {
  draft: 'Draft',
  awaiting_payment: 'Awaiting payment',
  submitted: 'Submitted',
  processing: 'Processing',
  automated_review_complete: 'Automated review complete',
  awaiting_analyst_review: 'Awaiting analyst review',
  action_required: 'Action required',
  customer_resubmitted: 'Corrections received',
  final_review: 'Final review',
  cleared: 'Cleared',
  conditionally_cleared: 'Conditionally cleared',
  blocked: 'Blocked',
  cancelled: 'Cancelled',
  closed: 'Closed',
}

export const checkStateLabels: Record<ProoflineCheckState, string> = {
  pending: 'Pending',
  running: 'Running',
  clear: 'Clear',
  issue_found: 'Issue found',
  evidence_incomplete: 'Evidence incomplete',
  not_applicable: 'Not applicable',
  unable_to_assess: 'Unable to assess',
  pending_review: 'Pending review',
}

export const moduleLabels: Record<string, string> = {
  lcopilot: 'LC review',
  open_account: 'Open-account readiness',
  advance_tt: 'Advance payment',
  partial_advance_balance: 'Partial advance and balance',
  documents_against_payment: 'Documents against payment',
  documents_against_acceptance: 'Documents against acceptance',
  buyer_led_supply_chain_finance: 'Supply-chain finance',
  factoring_receivables_finance: 'Receivables finance',
  consignment: 'Consignment terms',
  document_review: 'Cross-document review',
  sanctions: 'Sanctions',
  cbam: 'CBAM',
  eudr: 'EUDR',
  ein: 'Identity and credentials',
  rulhub: 'Applicable requirements',
  buyer_requirements: 'Buyer requirements',
}

export function decisionLabel(decision: ProoflineDecision | null): string {
  return decision ? decision.replace(/_/g, ' ') : 'PENDING REVIEW'
}

export function statusTone(status: TradeCaseStatus): string {
  if (status === 'cleared') return 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200'
  if (status === 'blocked') return 'border-red-400/30 bg-red-500/10 text-red-200'
  if (status === 'action_required' || status === 'conditionally_cleared') return 'border-amber-400/30 bg-amber-500/10 text-amber-200'
  return 'border-[#EDF5F2]/15 bg-[#EDF5F2]/5 text-[#EDF5F2]/65'
}

export function checkTone(state: ProoflineCheckState): string {
  if (state === 'clear') return 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200'
  if (state === 'issue_found') return 'border-red-400/30 bg-red-500/10 text-red-200'
  if (state === 'evidence_incomplete' || state === 'unable_to_assess') return 'border-amber-400/30 bg-amber-500/10 text-amber-200'
  return 'border-[#EDF5F2]/15 bg-[#EDF5F2]/5 text-[#EDF5F2]/55'
}

import type {
  PaymentArrangement,
  ProoflineQuote,
  ProoflineReportAccess,
  ProoflineServicePackage,
  TradeCaseDetail,
  TradeCaseDocument,
  TradeCaseParty,
  TradeCaseSummary,
} from '@shared/types'

import { api } from '@/api/client'

export interface TradeCaseCreateInput {
  title: string
  payment_arrangement: PaymentArrangement
  service_package_id?: string
  origin_country?: string
  destination_country?: string
  currency?: string
  amount?: number
  shipment_date?: string
  expected_payment_date?: string
  payment_terms?: string
  transaction_details?: Record<string, unknown>
}

export interface TradeCaseListResponse {
  items: TradeCaseSummary[]
  total: number
  offset: number
  limit: number
}

export async function createTradeCase(input: TradeCaseCreateInput): Promise<TradeCaseDetail> {
  const response = await api.post<TradeCaseDetail>('/api/proofline/cases', input)
  return response.data
}

export async function listTradeCases(offset = 0, limit = 50): Promise<TradeCaseListResponse> {
  const response = await api.get<TradeCaseListResponse>('/api/proofline/cases', {
    params: { limit, offset },
  })
  return response.data
}

export async function getTradeCase(caseId: string): Promise<TradeCaseDetail> {
  const response = await api.get<TradeCaseDetail>(`/api/proofline/cases/${caseId}`)
  return response.data
}

export async function listProoflinePackages(): Promise<ProoflineServicePackage[]> {
  const response = await api.get<ProoflineServicePackage[]>('/api/proofline/packages')
  return response.data
}

export async function getProoflineQuote(caseId: string): Promise<ProoflineQuote> {
  const response = await api.get<ProoflineQuote>(`/api/proofline/cases/${caseId}/quote`)
  return response.data
}

export async function getProoflineReport(caseId: string): Promise<ProoflineReportAccess> {
  const response = await api.get<ProoflineReportAccess>(`/api/proofline/cases/${caseId}/report`)
  return response.data
}

export async function startProoflineCheckout(caseId: string): Promise<string> {
  const response = await api.post<{ checkout_url: string }>(
    `/api/proofline/cases/${caseId}/checkout`,
  )
  return response.data.checkout_url
}

export async function upgradeLcopilotToProofline(sessionId: string): Promise<{
  case_id: string
  case_reference: string
  source_lcopilot_session_id: string
  created: boolean
}> {
  const response = await api.post<{
    case_id: string
    case_reference: string
    source_lcopilot_session_id: string
    created: boolean
  }>(`/api/proofline/upgrades/lcopilot/${sessionId}`)
  return response.data
}

export async function submitTradeCase(caseId: string): Promise<TradeCaseDetail> {
  const response = await api.post<TradeCaseDetail>(`/api/proofline/cases/${caseId}/submit`)
  return response.data
}

export async function respondToRemediation(
  caseId: string,
  actionId: string,
  input: { response?: string; correction_document_id?: string },
): Promise<TradeCaseDetail> {
  const response = await api.post<TradeCaseDetail>(
    `/api/proofline/cases/${caseId}/actions/${actionId}/respond`,
    input,
  )
  return response.data
}

export async function resubmitTradeCase(caseId: string): Promise<TradeCaseDetail> {
  const response = await api.post<TradeCaseDetail>(`/api/proofline/cases/${caseId}/resubmit`)
  return response.data
}

export async function updateTradeCase(
  caseId: string,
  input: Partial<TradeCaseCreateInput>,
): Promise<TradeCaseDetail> {
  const response = await api.patch<TradeCaseDetail>(`/api/proofline/cases/${caseId}`, input)
  return response.data
}

export async function createTradeCaseParty(
  caseId: string,
  input: { role: string; name: string; country_code?: string; identifiers?: Record<string, unknown> },
): Promise<TradeCaseParty> {
  const response = await api.post<TradeCaseParty>(`/api/proofline/cases/${caseId}/parties`, input)
  return response.data
}

export async function deleteTradeCaseParty(caseId: string, partyId: string): Promise<void> {
  await api.delete(`/api/proofline/cases/${caseId}/parties/${partyId}`)
}

export async function uploadTradeCaseDocument(
  caseId: string,
  input: {
    file: File
    logicalKey: string
    documentType?: string
    supersedesId?: string
    correctionRound?: number
  },
): Promise<TradeCaseDocument> {
  const body = new FormData()
  body.append('file', input.file)
  body.append('logical_key', input.logicalKey)
  if (input.documentType) body.append('document_type', input.documentType)
  if (input.supersedesId) body.append('supersedes_id', input.supersedesId)
  body.append('correction_round', String(input.correctionRound || 0))
  const response = await api.post<TradeCaseDocument>(
    `/api/proofline/cases/${caseId}/documents/upload`,
    body,
  )
  return response.data
}

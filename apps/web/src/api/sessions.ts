import axios from 'axios'
import { api } from './client'

export interface DocumentUploadUrl {
  document_type: 'letter_of_credit' | 'commercial_invoice' | 'bill_of_lading'
  upload_url: string
  s3_key: string
}

export interface ValidationSessionResponse {
  session_id: string
  status: 'created' | 'uploading' | 'processing' | 'completed' | 'failed'
  upload_urls: DocumentUploadUrl[]
  created_at: string
}

export interface DocumentInfo {
  id: string
  document_type: string
  original_filename: string
  file_size: number
  ocr_confidence?: number
  ocr_processed_at?: string
  extracted_fields?: Record<string, any>
}

export interface DiscrepancyInfo {
  id: string
  discrepancy_type: string
  severity: 'critical' | 'major' | 'minor'
  rule_name: string
  field_name?: string
  expected_value?: string
  actual_value?: string
  description: string
  source_document_types?: string[]
  created_at: string
}

export interface ValidationSession {
  id: string
  status: 'created' | 'uploading' | 'processing' | 'completed' | 'failed'
  ocr_provider?: string
  processing_started_at?: string
  processing_completed_at?: string
  extracted_data?: Record<string, any>
  validation_results?: Record<string, any>
  created_at: string
  updated_at: string
  documents: DocumentInfo[]
  discrepancies: DiscrepancyInfo[]
}

export interface CrossCheckField {
  field_name: string
  lc_value?: string
  invoice_value?: string
  bl_value?: string
  is_consistent: boolean
  discrepancies: string[]
}

export interface CrossCheckMatrix {
  session_id: string
  fields: CrossCheckField[]
  overall_consistency: boolean
  last_updated: string
}

export interface ReportInfo {
  id: string
  report_version: number
  total_discrepancies: number
  critical_discrepancies: number
  major_discrepancies: number
  minor_discrepancies: number
  generated_at: string
  file_size?: number
}

export interface ReportDownloadResponse {
  download_url: string
  expires_at: string
  report_info: ReportInfo
}

export const createValidationSession = async (): Promise<ValidationSessionResponse> => {
  const response = await api.post('/sessions', {})
  return response.data
}

export const getValidationSession = async (sessionId: string): Promise<ValidationSession> => {
  const response = await api.get(`/sessions/${sessionId}`)
  return response.data
}

export const getUserSessions = async (): Promise<ValidationSession[]> => {
  const response = await api.get('/sessions')
  return response.data
}

export const startSessionProcessing = async (sessionId: string): Promise<void> => {
  await api.post(`/sessions/${sessionId}/process`)
}

export const getReportDownloadUrl = async (sessionId: string): Promise<ReportDownloadResponse> => {
  const response = await api.get(`/sessions/${sessionId}/report`)
  return response.data
}

export const uploadToS3 = async (
  uploadUrl: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<void> => {
  await axios.put(uploadUrl, file, {
    headers: {
      'Content-Type': file.type,
    },
    onUploadProgress: (progressEvent: any) => {
      if (progressEvent.total && onProgress) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress(progress)
      }
    },
  })
}

export const uploadMultipleDocuments = async (
  uploadUrls: DocumentUploadUrl[],
  files: { [key: string]: File },
  onProgress?: (documentType: string, progress: number) => void
): Promise<void> => {
  const uploadPromises = uploadUrls.map(async (urlInfo) => {
    const file = files[urlInfo.document_type]
    if (file) {
      await uploadToS3(
        urlInfo.upload_url,
        file,
        (progress) => onProgress?.(urlInfo.document_type, progress)
      )
    }
  })
  
  await Promise.all(uploadPromises)
}

// Stub status API
export interface StubStatus {
  stub_mode_enabled: boolean
  current_scenario?: string
  scenario_info?: {
    name: string
    description: string
    tags: string[]
  }
  services: {
    ocr: string
    storage: string
  }
}

export const getStubStatus = async (): Promise<StubStatus> => {
  const response = await api.get('/health/info')
  const data = response.data

  // Transform the health/info response to match our StubStatus interface
  return {
    stub_mode_enabled: data.configuration?.use_stubs || false,
    current_scenario: data.configuration?.use_stubs ? 'development' : undefined,
    scenario_info: data.configuration?.use_stubs ? {
      name: 'Development Mode',
      description: 'Running with stub data for development',
      tags: ['development', 'stub']
    } : undefined,
    services: {
      ocr: data.configuration?.use_stubs ? 'stub' : 'live',
      storage: data.configuration?.use_stubs ? 'stub' : 'live'
    }
  }
}

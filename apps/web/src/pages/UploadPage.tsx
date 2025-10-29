import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, AlertCircle, CheckCircle } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { 
  createValidationSession, 
  uploadMultipleDocuments, 
  startSessionProcessing,
  DocumentUploadUrl 
} from '../api/sessions'

type DocumentType = 'letter_of_credit' | 'commercial_invoice' | 'bill_of_lading'

interface DocumentUploadState {
  file: File | null
  progress: number
  uploaded: boolean
}

export default function UploadPage() {
  const [documents, setDocuments] = useState<Record<DocumentType, DocumentUploadState>>({
    letter_of_credit: { file: null, progress: 0, uploaded: false },
    commercial_invoice: { file: null, progress: 0, uploaded: false },
    bill_of_lading: { file: null, progress: 0, uploaded: false }
  })
  const [isDragOver, setIsDragOver] = useState<DocumentType | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [uploadUrls, setUploadUrls] = useState<DocumentUploadUrl[]>([])
  const navigate = useNavigate()

  const createSessionMutation = useMutation({
    mutationFn: createValidationSession,
    onSuccess: (response) => {
      setSessionId(response.session_id)
      setUploadUrls(response.upload_urls)
      // Auto-start upload if files are ready
      const filesToUpload = Object.entries(documents).reduce((acc, [docType, state]) => {
        if (state.file) {
          acc[docType as DocumentType] = state.file
        }
        return acc
      }, {} as Record<string, File>)
      
      if (Object.keys(filesToUpload).length > 0) {
        uploadDocuments(response.upload_urls, filesToUpload)
      }
    },
  })

  const uploadDocuments = async (urls: DocumentUploadUrl[], files: Record<string, File>) => {
    try {
      await uploadMultipleDocuments(
        urls,
        files,
        (documentType: string, progress: number) => {
          setDocuments(prev => ({
            ...prev,
            [documentType]: {
              ...prev[documentType as DocumentType],
              progress
            }
          }))
        }
      )
      
      // Mark all uploaded documents as completed
      setDocuments(prev => {
        const updated = { ...prev }
        Object.keys(files).forEach(docType => {
          updated[docType as DocumentType] = {
            ...updated[docType as DocumentType],
            progress: 100,
            uploaded: true
          }
        })
        return updated
      })
      
      // Start processing
      if (sessionId) {
        await startSessionProcessing(sessionId)
        setTimeout(() => {
          navigate(`/review/${sessionId}`)
        }, 1000)
      }
    } catch (error) {
      console.error('Upload failed:', error)
    }
  }

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>, docType: DocumentType) => {
    e.preventDefault()
    setIsDragOver(null)
    
    const files = e.dataTransfer.files
    if (files.length > 0) {
      const selectedFile = files[0]
      if (selectedFile.type === 'application/pdf' || selectedFile.type.startsWith('image/')) {
        setDocuments(prev => ({
          ...prev,
          [docType]: { file: selectedFile, progress: 0, uploaded: false }
        }))
      }
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>, docType: DocumentType) => {
    e.preventDefault()
    setIsDragOver(docType)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(null)
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>, docType: DocumentType) => {
    const files = e.target.files
    if (files && files.length > 0) {
      setDocuments(prev => ({
        ...prev,
        [docType]: { file: files[0], progress: 0, uploaded: false }
      }))
    }
  }

  const handleUpload = () => {
    const hasFiles = Object.values(documents).some(doc => doc.file !== null)
    if (hasFiles) {
      createSessionMutation.mutate()
    }
  }

  const isUploading = createSessionMutation.isPending || Object.values(documents).some(doc => doc.progress > 0 && doc.progress < 100)
  const hasFiles = Object.values(documents).some(doc => doc.file !== null)
  const allRequiredUploaded = documents.letter_of_credit.file !== null // Only LC is required for basic validation

  return (
    <div className="container">
      <div className="nav-steps">
        <div className="nav-step active">1. Upload Documents</div>
        <div className="nav-step inactive">2. Review Results</div>
        <div className="nav-step inactive">3. Download Report</div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          Upload Documents for Validation
        </h2>
        <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
          Upload your trade documents (PDF or image format) for comprehensive LC validation
        </p>

        {/* Document Upload Sections */}
        {[
          { type: 'letter_of_credit' as DocumentType, label: 'Letter of Credit', required: true, color: '#3b82f6' },
          { type: 'commercial_invoice' as DocumentType, label: 'Commercial Invoice', required: false, color: '#10b981' },
          { type: 'bill_of_lading' as DocumentType, label: 'Bill of Lading', required: false, color: '#f59e0b' }
        ].map(({ type, label, required, color }) => {
          const docState = documents[type]
          const isDragOverThis = isDragOver === type
          
          return (
            <div key={type} style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: color }}>
                  {label}
                </h3>
                {required && (
                  <span style={{ 
                    marginLeft: '0.5rem', 
                    fontSize: '0.75rem', 
                    color: '#ef4444', 
                    fontWeight: '500'
                  }}>*Required</span>
                )}
                {docState.uploaded && (
                  <CheckCircle size={20} style={{ color: '#22c55e', marginLeft: '0.5rem' }} />
                )}
              </div>
              
              <div
                className={`upload-area ${isDragOverThis ? 'dragover' : ''} ${docState.file ? 'has-file' : ''}`}
                onDrop={(e) => handleDrop(e, type)}
                onDragOver={(e) => handleDragOver(e, type)}
                onDragLeave={handleDragLeave}
                onClick={() => document.getElementById(`file-input-${type}`)?.click()}
                style={{ 
                  borderColor: docState.uploaded ? '#22c55e' : color,
                  backgroundColor: docState.uploaded ? '#f0fdf4' : undefined
                }}
              >
                {docState.file ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                    <FileText size={20} style={{ color }} />
                    <span style={{ fontWeight: '500', fontSize: '0.9rem' }}>{docState.file.name}</span>
                    <span style={{ color: '#6b7280', fontSize: '0.8rem' }}>({(docState.file.size / 1024 / 1024).toFixed(2)} MB)</span>
                    {docState.progress > 0 && docState.progress < 100 && (
                      <span style={{ color, fontSize: '0.8rem' }}>({docState.progress}%)</span>
                    )}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center' }}>
                    <Upload size={32} style={{ color: '#9ca3af', margin: '0 auto 0.5rem' }} />
                    <p style={{ fontSize: '0.9rem', fontWeight: '500', marginBottom: '0.25rem' }}>
                      Drop {label.toLowerCase()} here or click to browse
                    </p>
                    <p style={{ color: '#6b7280', fontSize: '0.75rem' }}>
                      PDF, PNG, JPG up to 10MB
                    </p>
                  </div>
                )}
                
                {docState.progress > 0 && docState.progress < 100 && (
                  <div style={{ marginTop: '0.5rem', width: '100%' }}>
                    <div className="progress-bar" style={{ height: '4px' }}>
                      <div 
                        className="progress-bar-fill" 
                        style={{ width: `${docState.progress}%`, backgroundColor: color }}
                      />
                    </div>
                  </div>
                )}
              </div>
              
              <input
                id={`file-input-${type}`}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={(e) => handleFileSelect(e, type)}
                style={{ display: 'none' }}
              />
            </div>
          )
        })}

        {/* Upload Status */}
        {isUploading && (
          <div style={{ marginTop: '1.5rem', padding: '1rem', backgroundColor: '#f0f9ff', borderRadius: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <div className="spinner" style={{ width: '16px', height: '16px' }}></div>
              <span style={{ fontWeight: '500' }}>Processing documents...</span>
            </div>
            <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
              Uploading files and starting validation process
            </p>
          </div>
        )}

        {createSessionMutation.error && (
          <div style={{ 
            marginTop: '1rem', 
            padding: '1rem', 
            backgroundColor: '#fecaca', 
            border: '1px solid #ef4444', 
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <AlertCircle size={20} style={{ color: '#ef4444' }} />
            <span>Failed to create validation session. Please try again.</span>
          </div>
        )}

        <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center', gap: '1rem' }}>
          <button
            onClick={() => navigate('/')}
            className="btn btn-secondary"
            disabled={isUploading}
          >
            Back
          </button>
          <button
            onClick={handleUpload}
            className="btn btn-primary"
            disabled={!allRequiredUploaded || isUploading}
          >
            {isUploading ? 'Processing...' : 'Start Validation'}
          </button>
          
          {!allRequiredUploaded && (
            <p style={{ fontSize: '0.875rem', color: '#ef4444', marginTop: '0.5rem' }}>
              Please upload at least the Letter of Credit to continue
            </p>
          )}
          
          {hasFiles && !isUploading && (
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f8fafc', borderRadius: '6px' }}>
              <p style={{ fontSize: '0.875rem', color: '#374151', marginBottom: '0.5rem' }}>
                <strong>Tip:</strong> Upload multiple documents for comprehensive validation:
              </p>
              <ul style={{ fontSize: '0.8rem', color: '#6b7280', margin: 0, paddingLeft: '1rem' }}>
                <li>LC + Invoice: Verify amounts, dates, and party consistency</li>
                <li>LC + Invoice + B/L: Complete Fatal Four validation (Dates, Amounts, Parties, Ports)</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
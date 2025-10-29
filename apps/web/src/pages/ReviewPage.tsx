import { useParams, useNavigate } from 'react-router-dom'
import { AlertTriangle, CheckCircle, FileText } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getValidationSession } from '../api/sessions'
import DiscrepancyList from '../components/DiscrepancyList'


export default function ReviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()

  const { data: session, isLoading, error } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => getValidationSession(sessionId!),
    enabled: !!sessionId,
    refetchInterval: (data) => data?.status === 'processing' ? 2000 : false,
  })

  const isProcessing = session?.status === 'processing'
  const hasDiscrepancies = session?.discrepancies && session.discrepancies.length > 0

  if (isLoading) {
    return (
      <div className="container">
        <div className="card">
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div style={{ 
              width: '48px', 
              height: '48px', 
              border: '4px solid #e5e7eb', 
              borderTop: '4px solid #3b82f6', 
              borderRadius: '50%', 
              animation: 'spin 1s linear infinite',
              margin: '0 auto 1rem'
            }} />
            <p>Loading validation results...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container">
        <div className="card">
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <AlertTriangle size={48} style={{ color: '#ef4444', margin: '0 auto 1rem' }} />
            <p>Failed to load validation session</p>
            <button onClick={() => navigate('/')} className="btn btn-primary" style={{ marginTop: '1rem' }}>
              Back to Home
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="nav-steps">
        <div className="nav-step completed">1. Upload</div>
        <div className="nav-step active">2. Review</div>
        <div className="nav-step inactive">3. Report</div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          Validation Results
        </h2>
        <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
          Review the OCR extraction and Fatal Four validation results
        </p>

        {isProcessing ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div style={{ 
              width: '48px', 
              height: '48px', 
              border: '4px solid #e5e7eb', 
              borderTop: '4px solid #3b82f6', 
              borderRadius: '50%', 
              animation: 'spin 1s linear infinite',
              margin: '0 auto 1rem'
            }} />
            <p style={{ fontSize: '1.125rem', fontWeight: '500' }}>Processing document...</p>
            <p style={{ color: '#6b7280' }}>This may take a few moments</p>
          </div>
        ) : (
          <>
            <div style={{ 
              padding: '1rem', 
              backgroundColor: hasDiscrepancies ? '#fef3c7' : '#dcfce7', 
              border: `1px solid ${hasDiscrepancies ? '#f59e0b' : '#16a34a'}`, 
              borderRadius: '8px',
              marginBottom: '2rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              {hasDiscrepancies ? (
                <AlertTriangle size={24} style={{ color: '#f59e0b' }} />
              ) : (
                <CheckCircle size={24} style={{ color: '#16a34a' }} />
              )}
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.25rem' }}>
                  {hasDiscrepancies ? 'Discrepancies Found' : 'Validation Passed'}
                </h3>
                <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
                  {hasDiscrepancies 
                    ? `${session.discrepancies.length} discrepancy(ies) identified in Fatal Four elements`
                    : 'All Fatal Four elements passed validation'
                  }
                </p>
              </div>
            </div>

            {session?.documents && session.documents.length > 0 && (
              <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FileText size={20} />
                  OCR Extraction Results
                </h3>
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#f9fafb',
                  borderRadius: '8px',
                  fontSize: '0.875rem',
                  fontFamily: 'monospace',
                  whiteSpace: 'pre-wrap',
                  maxHeight: '200px',
                  overflowY: 'auto'
                }}>
                  {session.documents.map((doc, idx) => (
                    <div key={doc.id} style={{ marginBottom: idx < session.documents.length - 1 ? '1rem' : 0 }}>
                      <strong>{doc.document_type}:</strong><br />
                      {doc.extracted_fields ? JSON.stringify(doc.extracted_fields, null, 2) : 'No data extracted'}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <DiscrepancyList discrepancies={session?.discrepancies || []} />
          </>
        )}

        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
          <button
            onClick={() => navigate('/upload')}
            className="btn btn-secondary"
            disabled={isProcessing}
          >
            Upload Another
          </button>
          <button
            onClick={() => navigate(`/report/${sessionId}`)}
            className="btn btn-primary"
            disabled={isProcessing}
          >
            Generate Report
          </button>
        </div>
      </div>
    </div>
  )
}
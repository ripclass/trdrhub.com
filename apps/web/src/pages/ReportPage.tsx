import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, FileText, CheckCircle, AlertTriangle, Calendar } from 'lucide-react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getValidationSession, getReportDownloadUrl } from '../api/sessions'

export default function ReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()

  const { data: session, isLoading } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => getValidationSession(sessionId!),
    enabled: !!sessionId,
  })

  const downloadMutation = useMutation({
    mutationFn: () => getReportDownloadUrl(sessionId!),
    onSuccess: (data) => {
      window.open(data.download_url, '_blank')
    },
  })

  const handleDownload = () => {
    downloadMutation.mutate()
  }

  const handleNewValidation = () => {
    navigate('/upload')
  }

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
            <p>Loading report...</p>
          </div>
        </div>
      </div>
    )
  }

  const hasDiscrepancies = session?.discrepancies && session.discrepancies.length > 0

  return (
    <div className="container">
      <div className="nav-steps">
        <div className="nav-step completed">1. Upload</div>
        <div className="nav-step completed">2. Review</div>
        <div className="nav-step active">3. Report</div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          Validation Report
        </h2>
        <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
          Download your comprehensive LC validation report
        </p>

        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '1rem', 
          marginBottom: '2rem' 
        }}>
          <div style={{ 
            padding: '1.5rem', 
            backgroundColor: '#f9fafb', 
            borderRadius: '8px', 
            textAlign: 'center' 
          }}>
            <FileText size={32} style={{ color: '#3b82f6', margin: '0 auto 0.5rem' }} />
            <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '0.25rem' }}>Document</h3>
            <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
              {session?.documents?.[0]?.original_filename || 'LC Document'}
            </p>
          </div>

          <div style={{ 
            padding: '1.5rem', 
            backgroundColor: '#f9fafb', 
            borderRadius: '8px', 
            textAlign: 'center' 
          }}>
            <Calendar size={32} style={{ color: '#6b7280', margin: '0 auto 0.5rem' }} />
            <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '0.25rem' }}>Processed</h3>
            <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
              {session?.created_at ? new Date(session.created_at).toLocaleDateString() : 'Today'}
            </p>
          </div>

          <div style={{ 
            padding: '1.5rem', 
            backgroundColor: hasDiscrepancies ? '#fef3c7' : '#dcfce7', 
            borderRadius: '8px', 
            textAlign: 'center' 
          }}>
            {hasDiscrepancies ? (
              <AlertTriangle size={32} style={{ color: '#f59e0b', margin: '0 auto 0.5rem' }} />
            ) : (
              <CheckCircle size={32} style={{ color: '#16a34a', margin: '0 auto 0.5rem' }} />
            )}
            <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '0.25rem' }}>Status</h3>
            <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
              {hasDiscrepancies ? `${session.discrepancies.length} Issue(s)` : 'All Clear'}
            </p>
          </div>
        </div>

        {hasDiscrepancies && (
          <div style={{ 
            padding: '1.5rem', 
            backgroundColor: '#fef3c7', 
            border: '1px solid #f59e0b', 
            borderRadius: '8px',
            marginBottom: '2rem'
          }}>
            <h3 style={{ 
              fontSize: '1.125rem', 
              fontWeight: '600', 
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <AlertTriangle size={20} style={{ color: '#f59e0b' }} />
              Summary of Issues
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
              {['dates', 'amounts', 'parties', 'ports'].map(category => {
                const count = session.discrepancies.filter(d => d.discrepancy_type === category).length
                return (
                  <div key={category} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: count > 0 ? '#f59e0b' : '#6b7280' }}>
                      {count}
                    </div>
                    <div style={{ fontSize: '0.875rem', textTransform: 'capitalize', color: '#6b7280' }}>
                      {category}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        <div style={{ 
          textAlign: 'center', 
          padding: '2rem', 
          backgroundColor: '#f9fafb', 
          borderRadius: '8px',
          marginBottom: '2rem'
        }}>
          <Download size={48} style={{ color: '#3b82f6', margin: '0 auto 1rem' }} />
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            PDF Validation Report
          </h3>
          <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
            Comprehensive report including OCR results, validation findings, and recommendations
          </p>
          <button
            onClick={handleDownload}
            disabled={downloadMutation.isPending}
            className="btn btn-primary"
            style={{ fontSize: '1.125rem' }}
          >
            {downloadMutation.isPending ? (
              <>
                <div style={{ 
                  width: '16px', 
                  height: '16px', 
                  border: '2px solid #ffffff', 
                  borderTop: '2px solid transparent', 
                  borderRadius: '50%', 
                  animation: 'spin 1s linear infinite' 
                }} />
                Generating...
              </>
            ) : (
              <>
                <Download size={20} />
                Download PDF Report
              </>
            )}
          </button>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
          <button
            onClick={() => navigate(`/review/${sessionId}`)}
            className="btn btn-secondary"
          >
            Back to Review
          </button>
          <button
            onClick={handleNewValidation}
            className="btn btn-primary"
          >
            New Validation
          </button>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
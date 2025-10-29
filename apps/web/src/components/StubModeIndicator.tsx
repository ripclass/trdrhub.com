import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Settings, TestTube } from 'lucide-react'
import { getStubStatus, StubStatus } from '../api/sessions'

export default function StubModeIndicator() {
  const { data: stubStatus } = useQuery<StubStatus>({
    queryKey: ['stub-status'],
    queryFn: getStubStatus,
    refetchInterval: 30000, // Check every 30 seconds
    retry: false // Don't retry on failures (API might not support this endpoint)
  })

  // Don't show indicator if stub mode is disabled or query failed
  if (!stubStatus?.stub_mode_enabled) {
    return null
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      backgroundColor: '#f59e0b',
      color: 'white',
      padding: '8px 12px',
      borderRadius: '20px',
      fontSize: '0.8rem',
      fontWeight: '500',
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
      zIndex: 1000,
      border: '2px solid #fbbf24'
    }}>
      <TestTube size={14} />
      <span>Stub Mode: {stubStatus.current_scenario?.replace('.json', '') || 'Active'}</span>
      {stubStatus.scenario_info && (
        <div style={{
          position: 'absolute',
          bottom: '100%',
          right: '0',
          marginBottom: '8px',
          backgroundColor: '#1f2937',
          color: 'white',
          padding: '8px 12px',
          borderRadius: '8px',
          fontSize: '0.75rem',
          minWidth: '200px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
          opacity: 0,
          pointerEvents: 'none',
          transform: 'translateY(10px)',
          transition: 'all 0.2s ease-in-out'
        }}
        className="stub-tooltip"
        >
          <div style={{ fontWeight: '600', marginBottom: '4px' }}>
            {stubStatus.scenario_info.name}
          </div>
          <div style={{ marginBottom: '6px' }}>
            {stubStatus.scenario_info.description}
          </div>
          <div style={{ 
            display: 'flex', 
            gap: '4px', 
            flexWrap: 'wrap'
          }}>
            {stubStatus.scenario_info.tags?.map(tag => (
              <span key={tag} style={{
                backgroundColor: '#374151',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '0.65rem'
              }}>
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}
      <style jsx>{`
        .stub-tooltip-parent:hover .stub-tooltip {
          opacity: 1;
          pointer-events: auto;
          transform: translateY(0);
        }
      `}</style>
    </div>
  )
}
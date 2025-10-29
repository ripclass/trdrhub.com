import { useState } from 'react'
import {
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  Calendar,
  DollarSign,
  Users,
  MapPin,
  Filter,
  ChevronDown
} from 'lucide-react'
import { DiscrepancyInfo } from '../api/sessions'

interface DiscrepancyListProps {
  discrepancies: DiscrepancyInfo[]
  className?: string
}

type SeverityFilter = 'all' | 'critical' | 'major' | 'minor'

const DISCREPANCY_ICONS = {
  date: Calendar,
  amount: DollarSign,
  party: Users,
  port: MapPin,
  default: AlertTriangle,
}

const SEVERITY_CONFIG = {
  critical: {
    icon: AlertTriangle,
    color: '#ef4444',
    bgColor: '#fecaca',
    borderColor: '#ef4444',
    badgeColor: '#dc2626',
    label: 'Critical'
  },
  major: {
    icon: AlertCircle,
    color: '#f59e0b',
    bgColor: '#fef3c7',
    borderColor: '#f59e0b',
    badgeColor: '#d97706',
    label: 'Major'
  },
  minor: {
    icon: CheckCircle,
    color: '#10b981',
    bgColor: '#d1fae5',
    borderColor: '#10b981',
    badgeColor: '#059669',
    label: 'Minor'
  }
}

const getDiscrepancyIcon = (discrepancyType: string) => {
  const type = discrepancyType.toLowerCase()
  if (type.includes('date')) return DISCREPANCY_ICONS.date
  if (type.includes('amount')) return DISCREPANCY_ICONS.amount
  if (type.includes('party') || type.includes('parties')) return DISCREPANCY_ICONS.party
  if (type.includes('port')) return DISCREPANCY_ICONS.port
  return DISCREPANCY_ICONS.default
}

const getDocumentTypeBadgeColor = (docType: string) => {
  const type = docType.toLowerCase()
  if (type.includes('letter') || type.includes('credit')) return '#3b82f6'
  if (type.includes('invoice')) return '#8b5cf6'
  if (type.includes('bill') || type.includes('lading')) return '#06b6d4'
  return '#6b7280'
}

const formatDocumentType = (docType: string) => {
  return docType
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export default function DiscrepancyList({ discrepancies, className = '' }: DiscrepancyListProps) {
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [isFilterOpen, setIsFilterOpen] = useState(false)

  // Filter discrepancies based on severity
  const filteredDiscrepancies = severityFilter === 'all'
    ? discrepancies
    : discrepancies.filter(d => d.severity === severityFilter)

  // Count discrepancies by severity
  const severityCounts = discrepancies.reduce((acc, d) => {
    acc[d.severity] = (acc[d.severity] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const totalCount = discrepancies.length
  const criticalCount = severityCounts.critical || 0
  const majorCount = severityCounts.major || 0
  const minorCount = severityCounts.minor || 0

  if (totalCount === 0) {
    return (
      <div className={`discrepancy-list-container ${className}`}>
        <div className="no-discrepancies">
          <CheckCircle size={48} style={{ color: '#10b981', margin: '0 auto 1rem' }} />
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            No Discrepancies Found
          </h3>
          <p style={{ color: '#6b7280' }}>
            All Fatal Four elements passed validation successfully.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`discrepancy-list-container ${className}`}>
      {/* Summary Header */}
      <div className="discrepancy-summary">
        <div className="summary-header">
          <h3>
            <AlertTriangle size={20} style={{ color: '#ef4444' }} />
            {totalCount} Discrepanc{totalCount === 1 ? 'y' : 'ies'} Found
          </h3>
          <div className="severity-badges">
            {criticalCount > 0 && (
              <span className="severity-badge critical">
                {criticalCount} Critical
              </span>
            )}
            {majorCount > 0 && (
              <span className="severity-badge major">
                {majorCount} Major
              </span>
            )}
            {minorCount > 0 && (
              <span className="severity-badge minor">
                {minorCount} Minor
              </span>
            )}
          </div>
        </div>

        {/* Filter Controls */}
        <div className="filter-controls">
          <div className="filter-dropdown" style={{ position: 'relative' }}>
            <button
              className="filter-button"
              onClick={() => setIsFilterOpen(!isFilterOpen)}
            >
              <Filter size={16} />
              Filter by Severity
              <ChevronDown size={16} style={{
                transform: isFilterOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 0.2s ease'
              }} />
            </button>

            {isFilterOpen && (
              <div className="filter-menu">
                <button
                  className={`filter-option ${severityFilter === 'all' ? 'active' : ''}`}
                  onClick={() => {
                    setSeverityFilter('all')
                    setIsFilterOpen(false)
                  }}
                >
                  All Severities ({totalCount})
                </button>
                <button
                  className={`filter-option ${severityFilter === 'critical' ? 'active' : ''}`}
                  onClick={() => {
                    setSeverityFilter('critical')
                    setIsFilterOpen(false)
                  }}
                  disabled={criticalCount === 0}
                >
                  Critical ({criticalCount})
                </button>
                <button
                  className={`filter-option ${severityFilter === 'major' ? 'active' : ''}`}
                  onClick={() => {
                    setSeverityFilter('major')
                    setIsFilterOpen(false)
                  }}
                  disabled={majorCount === 0}
                >
                  Major ({majorCount})
                </button>
                <button
                  className={`filter-option ${severityFilter === 'minor' ? 'active' : ''}`}
                  onClick={() => {
                    setSeverityFilter('minor')
                    setIsFilterOpen(false)
                  }}
                  disabled={minorCount === 0}
                >
                  Minor ({minorCount})
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Discrepancy List */}
      <div className="discrepancy-list">
        {filteredDiscrepancies.length === 0 ? (
          <div className="no-filtered-results">
            <p style={{ textAlign: 'center', color: '#6b7280', padding: '2rem' }}>
              No {severityFilter} discrepancies found.
            </p>
          </div>
        ) : (
          filteredDiscrepancies.map((discrepancy, index) => {
            const severityConfig = SEVERITY_CONFIG[discrepancy.severity]
            const Icon = getDiscrepancyIcon(discrepancy.discrepancy_type)

            return (
              <div
                key={discrepancy.id || index}
                className="discrepancy-card"
                style={{
                  backgroundColor: severityConfig.bgColor,
                  borderColor: severityConfig.borderColor,
                }}
              >
                <div className="discrepancy-header">
                  <div className="discrepancy-icon-title">
                    <Icon
                      size={20}
                      style={{ color: severityConfig.color }}
                    />
                    <h4 className="discrepancy-title">
                      {discrepancy.rule_name}
                    </h4>
                  </div>
                  <span
                    className="severity-badge"
                    style={{
                      backgroundColor: severityConfig.badgeColor,
                      color: 'white'
                    }}
                  >
                    {severityConfig.label}
                  </span>
                </div>

                <div className="discrepancy-content">
                  <p className="discrepancy-description">
                    {discrepancy.description}
                  </p>

                  {/* Expected vs Actual Values */}
                  {discrepancy.expected_value && discrepancy.actual_value && (
                    <div className="value-comparison">
                      <div className="value-row">
                        <span className="value-label">Expected:</span>
                        <span className="value-text expected">{discrepancy.expected_value}</span>
                      </div>
                      <div className="value-row">
                        <span className="value-label">Found:</span>
                        <span className="value-text actual">{discrepancy.actual_value}</span>
                      </div>
                    </div>
                  )}

                  {/* Field Name */}
                  {discrepancy.field_name && (
                    <div className="field-info">
                      <span className="field-label">Field:</span>
                      <span className="field-value">{discrepancy.field_name}</span>
                    </div>
                  )}
                </div>

                {/* Document Type Badges */}
                {discrepancy.source_document_types && discrepancy.source_document_types.length > 0 && (
                  <div className="document-badges">
                    <span className="badges-label">Source Documents:</span>
                    <div className="badges-list">
                      {discrepancy.source_document_types.map((docType, idx) => (
                        <span
                          key={idx}
                          className="document-badge"
                          style={{
                            backgroundColor: getDocumentTypeBadgeColor(docType),
                            color: 'white'
                          }}
                        >
                          {formatDocumentType(docType)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
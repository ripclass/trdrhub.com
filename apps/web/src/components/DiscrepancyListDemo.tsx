import DiscrepancyList from './DiscrepancyList'
import { DiscrepancyInfo } from '../api/sessions'

// Sample discrepancy data for testing different scenarios
const sampleDiscrepancies: DiscrepancyInfo[] = [
  {
    id: '1',
    discrepancy_type: 'amount_mismatch',
    severity: 'critical',
    rule_name: 'Amount Consistency Check',
    field_name: 'invoice_amount',
    expected_value: 'USD 25,000.00',
    actual_value: 'USD 35,000.00',
    description: 'Invoice amount exceeds the Letter of Credit limit by USD 10,000.00. This violates the maximum allowable amount and could result in payment rejection.',
    source_document_types: ['letter_of_credit', 'commercial_invoice'],
    created_at: '2024-01-15T10:30:00Z'
  },
  {
    id: '2',
    discrepancy_type: 'date_mismatch',
    severity: 'major',
    rule_name: 'Shipment Date Validation',
    field_name: 'shipment_date',
    expected_value: 'Before 2024-02-20',
    actual_value: '2024-02-25',
    description: 'Bill of Lading date is after the Letter of Credit expiry date. Shipment occurred 5 days late.',
    source_document_types: ['letter_of_credit', 'bill_of_lading'],
    created_at: '2024-01-15T10:31:00Z'
  },
  {
    id: '3',
    discrepancy_type: 'party_mismatch',
    severity: 'major',
    rule_name: 'Beneficiary Consistency',
    field_name: 'beneficiary',
    expected_value: 'ABC Trading Company Ltd',
    actual_value: 'ABC Trading Co',
    description: 'Beneficiary name in the commercial invoice does not exactly match the name specified in the Letter of Credit.',
    source_document_types: ['letter_of_credit', 'commercial_invoice'],
    created_at: '2024-01-15T10:32:00Z'
  },
  {
    id: '4',
    discrepancy_type: 'port_mismatch',
    severity: 'minor',
    rule_name: 'Port of Discharge Check',
    field_name: 'port_of_discharge',
    expected_value: 'Chennai Port',
    actual_value: 'Chattogram Port',
    description: 'Port of discharge in Bill of Lading differs from the Letter of Credit specification.',
    source_document_types: ['letter_of_credit', 'bill_of_lading'],
    created_at: '2024-01-15T10:33:00Z'
  },
  {
    id: '5',
    discrepancy_type: 'missing_field',
    severity: 'critical',
    rule_name: 'Required Field Validation',
    field_name: 'lc_number',
    description: 'Letter of Credit number is missing from the commercial invoice. This is a mandatory field for trade finance compliance.',
    source_document_types: ['commercial_invoice'],
    created_at: '2024-01-15T10:34:00Z'
  }
]

// Component for testing the DiscrepancyList
export default function DiscrepancyListDemo() {
  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '2rem', textAlign: 'center' }}>
        Discrepancy List Component Demo
      </h1>

      <div style={{ background: 'white', borderRadius: '12px', padding: '2rem', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem' }}>
          Sample Discrepancies
        </h2>
        <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
          This demo shows the DiscrepancyList component with various types of discrepancies across different severity levels.
        </p>

        <DiscrepancyList discrepancies={sampleDiscrepancies} />
      </div>

      <div style={{ background: 'white', borderRadius: '12px', padding: '2rem', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)', marginTop: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem' }}>
          No Discrepancies Scenario
        </h2>
        <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
          This shows how the component displays when no discrepancies are found.
        </p>

        <DiscrepancyList discrepancies={[]} />
      </div>

      <div style={{ background: 'white', borderRadius: '12px', padding: '2rem', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)', marginTop: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem' }}>
          Critical Only Scenario
        </h2>
        <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
          This shows only critical discrepancies for testing the severity filter.
        </p>

        <DiscrepancyList discrepancies={sampleDiscrepancies.filter(d => d.severity === 'critical')} />
      </div>
    </div>
  )
}
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import ProoflineLanding from '../ProoflineLanding'

vi.mock('@/components/layout/trdr-header', () => ({
  TRDRHeader: () => <header>TRDR Hub</header>,
}))
vi.mock('@/components/layout/trdr-footer', () => ({
  TRDRFooter: () => <footer>TRDR Hub footer</footer>,
}))

describe('Proofline landing page', () => {
  it('uses the approved product language and a real case CTA', () => {
    render(<MemoryRouter><ProoflineLanding /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: 'Proofline' })).toBeInTheDocument()
    expect(screen.getByText('Verified Trade Clearance')).toBeInTheDocument()
    expect(screen.getByText(/identify the document, compliance, identity, and evidence issues/i)).toBeInTheDocument()
    expect(screen.getByText('LCopilot checks the instrument. Proofline clears the trade.')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /start a trade case/i })).toHaveLength(2)
    for (const link of screen.getAllByRole('link', { name: /start a trade case/i })) {
      expect(link).toHaveAttribute('href', '/proofline/new')
    }
    expect(screen.getByText(/does not guarantee bank acceptance, customs clearance, shipment, payment/i)).toBeInTheDocument()
  })
})

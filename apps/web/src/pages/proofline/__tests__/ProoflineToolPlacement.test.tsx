import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import ToolsPage from '@/pages/ToolsPage'
import { ToolsSection } from '@/components/sections/tools-section'

vi.mock('@/components/layout/trdr-header', () => ({ TRDRHeader: () => null }))
vi.mock('@/components/layout/trdr-footer', () => ({ TRDRFooter: () => null }))

describe('Proofline tool placement', () => {
  it('appears in the Tools index as a live TRDRHub tool', () => {
    render(<MemoryRouter><ToolsPage /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: 'Five things. Done properly.' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Proofline' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /start a trade case/i })).toHaveAttribute('href', '/proofline')
  })

  it('appears in the homepage tools section', () => {
    render(<MemoryRouter><ToolsSection /></MemoryRouter>)

    expect(screen.getByRole('link', { name: /proofline/i })).toHaveAttribute('href', '/proofline')
  })
})

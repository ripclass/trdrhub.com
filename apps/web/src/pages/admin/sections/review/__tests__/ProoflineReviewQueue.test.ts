import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('Proofline analyst workspace', () => {
  it('uses the real admin API and exposes the required review actions', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/pages/admin/sections/review/ProoflineReviewQueue.tsx'),
      'utf8',
    )

    expect(source).toContain('/api/admin/proofline')
    expect(source).toContain('Claim case')
    expect(source).toContain('Request correction')
    expect(source).toContain('Internal note')
    expect(source).toContain('Approve final decision')
    expect(source).toContain('Expected')
    expect(source).toContain('Observed')
  })
})


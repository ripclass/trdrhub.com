import { afterEach, describe, expect, it, vi } from 'vitest'

import { isProoflineEnabled } from '../featureFlags'

describe('Proofline release flag', () => {
  afterEach(() => vi.unstubAllEnvs())

  it('is available by default and supports a deployment kill switch', () => {
    expect(isProoflineEnabled()).toBe(true)
    vi.stubEnv('VITE_PROOFLINE_ENABLED', 'false')
    expect(isProoflineEnabled()).toBe(false)
  })
})

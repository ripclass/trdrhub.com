import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('shared api contract order', () => {
  it('defines WorkflowStageInfoSchema before FactResolutionV1Schema', () => {
    const source = readFileSync(
      resolve(process.cwd(), '..', '..', 'packages', 'shared-types', 'src', 'api.ts'),
      'utf-8',
    )

    const workflowIndex = source.indexOf('export const WorkflowStageInfoSchema')
    const factResolutionIndex = source.indexOf('export const FactResolutionV1Schema')

    expect(workflowIndex).toBeGreaterThanOrEqual(0)
    expect(factResolutionIndex).toBeGreaterThanOrEqual(0)
    expect(workflowIndex).toBeLessThan(factResolutionIndex)
  })
})

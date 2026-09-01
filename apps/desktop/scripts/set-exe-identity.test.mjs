import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import { loadDistributionIdentity } from './set-exe-identity.mjs'

describe('Windows executable identity', () => {
  it('comes from downstream distribution metadata', () => {
    const distribution = loadDistributionIdentity(resolve(import.meta.dirname, '..'))

    expect(distribution.id).toBe('hermes-agent-windows')
    expect(distribution.display_name).toBe('Hermes Agent Windows Workstation Edition')
    expect(distribution.version).toBe('0.21.0')
    expect(distribution.windowsVersion).toBe('0.21.0.0')
  })
})

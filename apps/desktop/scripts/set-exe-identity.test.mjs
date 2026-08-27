import assert from 'node:assert/strict'
import test from 'node:test'
import { resolve } from 'node:path'

import { loadDistributionIdentity } from './set-exe-identity.mjs'

test('Windows executable identity comes from downstream distribution metadata', () => {
  const distribution = loadDistributionIdentity(resolve(import.meta.dirname, '..'))

  assert.equal(distribution.id, 'hermes-agent-windows')
  assert.equal(distribution.display_name, 'Hermes Agent Windows Workstation Edition')
  assert.equal(distribution.version, '0.20.5-win.1')
  assert.equal(distribution.windowsVersion, '0.20.5.1')
})

import assert from 'node:assert/strict'
import path from 'node:path'

import { test } from 'vitest'

import { distributionInstallArgs, distributionRawUrl, loadDistributionMetadata } from './distribution'

test('distribution metadata controls Desktop repository authority', () => {
  const metadataPath = path.resolve(process.cwd(), '../../downstream/distribution.json')
  const distribution = loadDistributionMetadata(metadataPath)

  assert.equal(distribution.id, 'hermes-agent-windows')
  assert.equal(distribution.repository.slug, 'zapabob/hermes-agent-windows')
  assert.equal(distribution.update.allow_upstream_sync, false)
})

test('Desktop bootstrap URLs and install args target the downstream repository', () => {
  const url = distributionRawUrl('a'.repeat(40), 'install.ps1')
  const args = distributionInstallArgs()

  assert.equal(
    url,
    `https://raw.githubusercontent.com/zapabob/hermes-agent-windows/${'a'.repeat(40)}/scripts/install.ps1`
  )
  assert.deepEqual(args, [
    '-RepositoryUrlHttps',
    'https://github.com/zapabob/hermes-agent-windows.git',
    '-RepositoryUrlSsh',
    'git@github.com:zapabob/hermes-agent-windows.git',
    '-RepositoryArchiveBase',
    'https://github.com/zapabob/hermes-agent-windows/archive'
  ])
  assert.equal(url.includes('NousResearch'), false)
  assert.equal(
    distributionRawUrl('preview/windows', 'install.ps1'),
    'https://raw.githubusercontent.com/zapabob/hermes-agent-windows/preview/windows/scripts/install.ps1'
  )
})

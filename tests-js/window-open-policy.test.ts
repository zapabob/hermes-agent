import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { describe, test } from 'vitest'

import { createWindowOpenHandler, describeDeniedUrl } from '../apps/desktop/electron/window-open-policy'

const mainSource = readFileSync(new URL('../apps/desktop/electron/main.ts', import.meta.url), 'utf8')

function hasLegacyOpenExternalSideEffect(source: string): boolean {
  return /setWindowOpenHandler\(\s*details\s*=>\s*{\s*openExternalUrl\(details\.url\)/.test(source)
}

describe('window-open policy', () => {
  test('denies every scheme and reports only the sanitized origin', () => {
    const seen: string[] = []
    const handler = createWindowOpenHandler(origin => seen.push(origin))

    const urls = [
      'https://attacker.test/steal?token=SECRET#frag',
      'http://attacker.test:8080/x',
      'https://x.com/hermes/status/123',
      'https://www.youtube.com/watch?v=explicit-click-only',
      'file:///etc/passwd',
      'javascript:alert(1)',
      'custom-proto://payload',
      ''
    ]

    for (const url of urls) {
      assert.deepEqual(handler({ url }), { action: 'deny' })
    }

    assert.equal(seen.length, urls.length)
    assert.equal(seen[0], 'https://attacker.test')
    assert.equal(seen[1], 'http://attacker.test:8080')
    assert.equal(seen[2], 'https://x.com')
    assert.equal(seen[3], 'https://www.youtube.com')
    assert.equal(describeDeniedUrl(''), '<unparseable>')
    assert.ok(seen.every(origin => !origin.includes('SECRET') && !origin.includes('/steal')))
  })

  test('a throwing observer still yields an explicit deny', () => {
    const handler = createWindowOpenHandler(() => {
      throw new Error('logging blew up')
    })

    assert.deepEqual(handler({ url: 'https://attacker.test/x' }), { action: 'deny' })
  })

  test('main wires the shared policy instead of reopening before deny', () => {
    const vulnerableWiring = `
      win.webContents.setWindowOpenHandler(details => {
        openExternalUrl(details.url)
        return { action: 'deny' }
      })
    `

    assert.equal(hasLegacyOpenExternalSideEffect(vulnerableWiring), true)
    assert.equal(hasLegacyOpenExternalSideEffect(mainSource), false)
    assert.match(mainSource, /setWindowOpenHandler\(\s*createWindowOpenHandler\(/)
  })
})

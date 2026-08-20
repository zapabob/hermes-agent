import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it, vi } from 'vitest'

import { ACCENT_LOCALES } from './i18n'
import { copyAccentColor } from './plugin'

const directory = dirname(fileURLToPath(import.meta.url))
const source = readFileSync(join(directory, 'picker.tsx'), 'utf8')
const pluginSource = readFileSync(join(directory, 'plugin.tsx'), 'utf8')

describe('accent picker design and interaction contracts', () => {
  it('uses SDK controls, localized copy, and tokenized selection chrome', () => {
    expect(source).not.toMatch(/<input\b|<button\b|\btitle=/)
    expect(source).not.toMatch(/border-white|shadow-\[/)
    expect(source).toContain('usePluginI18n')
    expect(source).toContain('<Input')
    expect(source).toContain('<Button')
    expect(source).toContain('pointercancel')
  })

  it('ships the same accent-picker message shape in every supported locale', () => {
    const required = ['reset', 'triggerLabel', 'swatches', 'readout', 'contrast', 'mode', 'picked', 'copyLabel']

    for (const locale of ['en', 'ja', 'zh', 'zh-hant'] as const) {
      const messages = ACCENT_LOCALES[locale]
      expect(messages).toBeDefined()

      for (const key of required) {
        expect(messages).toHaveProperty(key)
      }
    }
  })

  it('keeps the authoring plugin opt-in and registers its scoped locales', () => {
    expect(pluginSource).toContain('defaultEnabled: false')
    expect(pluginSource).toContain('ctx.i18n.register(ACCENT_LOCALES)')
  })

  it('uses the attributed OS clipboard door and reports unavailable writes', async () => {
    const writeClipboard = vi.fn(async (color: string) => color === '#123456')
    const os = { writeClipboard }

    await expect(copyAccentColor(os, '#123456')).resolves.toBe(true)
    await expect(copyAccentColor(os, '#abcdef')).resolves.toBe(false)
    await expect(copyAccentColor(os, null)).resolves.toBe(false)
    expect(writeClipboard).toHaveBeenCalledTimes(2)
    expect(writeClipboard).toHaveBeenNthCalledWith(1, '#123456')
  })

  it('contains clipboard bridge rejection and reports it as unavailable', async () => {
    const writeClipboard = vi.fn(async () => {
      throw new Error('bridge unavailable')
    })

    await expect(copyAccentColor({ writeClipboard }, '#123456')).resolves.toBe(false)
    expect(writeClipboard).toHaveBeenCalledWith('#123456')
  })
})

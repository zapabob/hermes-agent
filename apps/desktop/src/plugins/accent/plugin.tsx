/**
 * Accent — pick the theme's accent color and watch the whole app retint live.
 *
 * The COLOR MATH is not here. `themes/retint.ts` owns re-seeding a palette from
 * one color, and it works on any theme with any accent; this plugin is only the
 * control surface for it. That split is deliberate: the retint is core behavior
 * that Appearance settings and ⌘K should be able to drive too, while the
 * statusbar picker is an authoring tool most users never need.
 *
 * Ships OFF (`defaultEnabled: false`): it inventories in Settings ▸ Plugins and
 * registers nothing until the switch is flipped. With it off, `$accentOverride`
 * stays null and `retintTheme` is never called — themes paint exactly as
 * authored.
 */

import type { HermesPlugin, PaletteContribution, PluginOs } from '@hermes/plugin-sdk'
import { $accentOverride, PALETTE_AREA, setAccentOverride, STATUSBAR_AREAS } from '@hermes/plugin-sdk'

import { ACCENT_LOCALES } from './i18n'
import { AccentPickerTrigger } from './picker'
import { $paintedAccent, setPaintedAccent } from './state'

export async function copyAccentColor(os: Pick<PluginOs, 'writeClipboard'>, color: null | string): Promise<boolean> {
  const candidate = color?.trim()

  if (!candidate) {
    return false
  }

  try {
    return await os.writeClipboard(candidate)
  } catch {
    return false
  }
}

const plugin: HermesPlugin = {
  id: 'accent',
  name: 'Accent Picker',
  description:
    'Pick the theme accent from an OKLCH color picker in the status bar; the palette re-derives live. Authoring tool — the color is not persisted.',
  defaultEnabled: false,
  register(ctx) {
    ctx.i18n.register(ACCENT_LOCALES)
    // The override is a scratch value, not a setting. Dropping it on unregister
    // means disabling the plugin (or reloading) returns every surface to the
    // authored theme instead of stranding a color with no control to clear it.
    ctx.onDispose(() => {
      setAccentOverride(null)
      setPaintedAccent(null)
    })

    ctx.registerMany([
      {
        id: 'picker',
        area: STATUSBAR_AREAS.right,
        order: 90,
        render: () => <AccentPickerTrigger />
      },
      {
        id: 'reset',
        area: PALETTE_AREA,
        data: {
          id: 'accent.reset',
          label: `${ctx.i18n.t('triggerLabel')}: ${ctx.i18n.t('reset')}`,
          keywords: ['accent', 'color', 'theme', 'reset', 'default'],
          run: () => setAccentOverride(null)
        } satisfies PaletteContribution
      },
      {
        id: 'copy',
        area: PALETTE_AREA,
        data: {
          id: 'accent.copy',
          label: `${ctx.i18n.t('triggerLabel')}: ${ctx.i18n.t('copyLabel')}`,
          keywords: ['accent', 'color', 'hex', 'copy', 'clipboard'],
          run: () => {
            void copyAccentColor(ctx.os, $accentOverride.get() ?? $paintedAccent.get())
          }
        } satisfies PaletteContribution
      }
    ])
  }
}

export default plugin

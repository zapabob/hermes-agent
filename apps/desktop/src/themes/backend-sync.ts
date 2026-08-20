/**
 * Live skin sync from the Hermes backend.
 *
 * The backend resolves the active skin (built-in or `$HERMES_HOME/skins/*.yaml`)
 * and announces it on `gateway.ready` / `skin.changed`, and answers `config.get
 * skin` with the same payload. `ingestBackendSkin` folds that into the desktop:
 *
 *   1. Registers the converted theme in `$backendThemes` so it appears wherever a
 *      built-in does — Appearance, Cmd-K, `/skin` — with no per-surface wiring
 *      (`listAllThemes` merges this store). A skin sharing a built-in name keeps
 *      the hand-tuned built-in palette while contributing wallpaper metadata.
 *   2. When asked to apply (an explicit change), requests the switch via
 *      `$pendingSkinApply`, which the ThemeProvider drains through `setTheme`.
 *
 * `gateway.ready` seeds the baseline WITHOUT applying, so a fresh connect never
 * stomps the user's persisted desktop theme; only a genuine name change (Hermes
 * authoring/activating a skin from a prompt, or `/skin` elsewhere) repaints.
 */

import { registryBackendScopeKey } from '@hermes/shared'
import type { HermesSkin } from '@hermes/shared/skin'
import { atom } from 'nanostores'

import { $connection } from '@/store/session'

import { BUILTIN_THEMES } from './presets'
import { skinToDesktopTheme } from './skin'
import type { DesktopTheme, DesktopThemeSource } from './types'

/** Skins pushed by each backend, keyed first by its connection/profile scope. */
const $backendThemesByScope = atom<Record<string, Record<string, DesktopTheme>>>({})

/** Active-scope view consumed by the theme registry. Kept as a writable atom
 * for compatibility with existing theme tests and plugin integrations. */
export const $backendThemes = atom<Record<string, DesktopTheme>>({})

function activeScopeKey(): string {
  const connection = $connection.get()

  return registryBackendScopeKey(connection?.connectionId ?? null, connection?.profile ?? null)
}

function publishActiveScope(scoped = $backendThemesByScope.get()): void {
  $backendThemes.set(scoped[activeScopeKey()] ?? {})
}

$connection.subscribe(() => publishActiveScope())

/** One-shot skin name the ThemeProvider should switch to (it clears this). */
export const $pendingSkinApply = atom<string | null>(null)

// Last skin name synced from the backend + whether it was ever APPLIED (vs
// merely seeded at connect). Once applied, only a name change applies again —
// no re-apply on repeat events, no snap-back after a manual desktop switch.
// A `skin.changed` matching a seed-only baseline still applies: the seed
// records without painting, so if the activation event was missed (backend
// restart / disconnected), an explicit re-affirm must repaint, not no-op.
const lastSyncedByScope = new Map<string, { applied: boolean; name: string }>()

function sourceFor(source?: DesktopThemeSource): DesktopThemeSource {
  if (source) {
    return Object.freeze({
      connectionId: source.connectionId ?? null,
      profile: source.profile.trim() || 'default'
    })
  }

  const connection = $connection.get()

  return Object.freeze({
    connectionId: connection?.connectionId ?? null,
    profile: connection?.profile?.trim() || 'default'
  })
}

/** Test-only: reset the module's apply guard + registry between cases. */
export function __resetBackendSkinSync(): void {
  lastSyncedByScope.clear()
  $backendThemesByScope.set({})
  $backendThemes.set({})
  $pendingSkinApply.set(null)
}

/**
 * Fold a resolved skin into the desktop. `apply: false` (connect-time seed) only
 * records the baseline; `apply: true` (runtime change / poll) repaints on a name
 * change. Built-in names keep the desktop's own palette while still accepting
 * wallpaper, fit, position, and overlay from the canonical backend skin.
 */
export function ingestBackendSkin(
  skin: HermesSkin | undefined | null,
  { apply, scope }: { apply: boolean; scope?: DesktopThemeSource }
): void {
  const name = (skin && typeof skin === 'object' ? (skin.name ?? '') : '').trim()

  if (!name) {
    return
  }

  const source = sourceFor(scope)
  const scopeKey = registryBackendScopeKey(source.connectionId, source.profile)

  // `default` is "no opinion" on the PALETTE — the desktop keeps its own default
  // (nous), so we never register a converted theme under `default`. It is still a
  // valid apply TARGET though: a runtime switch back to `default` must repaint the
  // desktop to its own default (setTheme normalizes `default` → nous). So we only
  // skip the registry step here and let it flow through the apply logic below.
  // Built-in names (mono/slate/…) already have a hand-tuned desktop palette.
  // Preserve it, but do not discard wallpaper metadata carried by the skin —
  // Backdrop owns that presentation layer independently from the colour tokens.
  if (name !== 'default') {
    const converted = skinToDesktopTheme(skin as HermesSkin)

    if (!converted) {
      return
    }

    const scoped = $backendThemesByScope.get()
    const current = scoped[scopeKey] ?? {}
    const builtin = BUILTIN_THEMES[name]

    const theme = builtin
      ? converted.backgroundImage
        ? {
            ...builtin,
            backgroundImage: converted.backgroundImage,
            backgroundImageFit: converted.backgroundImageFit,
            backgroundImagePosition: converted.backgroundImagePosition,
            backgroundOverlay: converted.backgroundOverlay,
            backgroundImageSource: source
          }
        : null
      : converted.backgroundImage
        ? { ...converted, backgroundImageSource: source }
        : converted

    if (!theme && current[name]) {
      const { [name]: _removed, ...rest } = current
      const next = { ...scoped, [scopeKey]: rest }
      $backendThemesByScope.set(next)

      if (scopeKey === activeScopeKey()) {
        publishActiveScope(next)
      }
    } else if (theme && JSON.stringify(current[name]) !== JSON.stringify(theme)) {
      const next = { ...scoped, [scopeKey]: { ...current, [name]: theme } }
      $backendThemesByScope.set(next)

      if (scopeKey === activeScopeKey()) {
        publishActiveScope(next)
      }
    }
  }

  const lastSynced = lastSyncedByScope.get(scopeKey)

  if (!apply) {
    // Connect-time seed: record without painting. A reconnect re-seed keeps an
    // earlier real apply's flag so repeat events can't override a manual switch.
    if (lastSynced?.name !== name || !lastSynced?.applied) {
      lastSyncedByScope.set(scopeKey, { applied: false, name })
    }

    return
  }

  if (name !== lastSynced?.name || !lastSynced?.applied) {
    lastSyncedByScope.set(scopeKey, { applied: true, name })
    $pendingSkinApply.set(name)
  }
}

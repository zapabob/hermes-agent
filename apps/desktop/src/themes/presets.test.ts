import { describe, expect, it } from 'vitest'

import { BUILTIN_THEME_LIST, BUILTIN_THEMES, DEFAULT_TYPOGRAPHY, EMOJI_FALLBACK, nousTheme, psycheTheme } from './presets'

// #40364: none of the UI text/mono fonts carry emoji glyphs, so every font
// stack must end with a color-emoji fallback or emoji render as tofu on
// platforms whose default font lacks them (e.g. Linux).
describe('theme typography emoji fallback (#40364)', () => {
  const stacks: Array<[string, string]> = [
    ['DEFAULT_TYPOGRAPHY.fontSans', DEFAULT_TYPOGRAPHY.fontSans],
    ['DEFAULT_TYPOGRAPHY.fontMono', DEFAULT_TYPOGRAPHY.fontMono],
    // A theme may override only fontMono (fontSans then falls back to the
    // default, which already carries the emoji stack), so skip undefined.
    ...BUILTIN_THEME_LIST.flatMap(theme =>
      (
        [
          [`${theme.name}.fontSans`, theme.typography?.fontSans],
          [`${theme.name}.fontMono`, theme.typography?.fontMono]
        ] as Array<[string, string | undefined]>
      ).filter((entry): entry is [string, string] => typeof entry[1] === 'string')
    )
  ]

  it.each(stacks)('%s includes a color-emoji font', (_label, stack) => {
    expect(stack).toMatch(/Apple Color Emoji|Segoe UI Emoji|Noto Color Emoji|(^|,\s*)emoji\b/)
  })

  it('EMOJI_FALLBACK lists the major platform emoji fonts', () => {
    expect(EMOJI_FALLBACK).toContain('Apple Color Emoji')
    expect(EMOJI_FALLBACK).toContain('Segoe UI Emoji')
    expect(EMOJI_FALLBACK).toContain('Noto Color Emoji')
  })
})

describe('built-in theme registry', () => {
  it('keeps official palettes and fork-specific skins available together', () => {
    expect(BUILTIN_THEMES.github?.label).toBe('GitHub')
    expect(BUILTIN_THEMES.catppuccin?.label).toBe('Catppuccin')
    expect(BUILTIN_THEMES.hakua?.label).toBe('Hakua')
    expect(BUILTIN_THEMES['twilight-hakua']?.backgroundImageFit).toBe('cover')
  })

  it('preserves the pre-upstream Psyche palette as a separate identity', () => {
    expect(BUILTIN_THEMES.psyche).toBe(psycheTheme)
    expect(psycheTheme.colors.background).not.toBe(nousTheme.colors.background)
    expect(psycheTheme.darkColors?.background).toBe('#0d2f86')
    expect(psycheTheme.darkColors?.foreground).toBe('#ffe6cb')
  })
})

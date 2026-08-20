import { atom } from '@hermes/plugin-sdk'

/** The rendered theme accent, kept current by the statusbar contribution. */
export const $paintedAccent = atom<string | null>(null)

export function setPaintedAccent(color: string | null): void {
  $paintedAccent.set(color)
}

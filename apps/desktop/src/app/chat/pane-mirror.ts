/**
 * Mirror a reactive list of "tiles" into layout-tree pane contributions:
 * register a pane per tile, refresh its title in place, and dispose panes whose
 * tile is gone. This is the shared bookkeeping — a keyed registry, a wanted-set
 * diff, a one-time pane closer — behind BOTH session tiles and route (page)
 * tiles; each supplies only what differs (key, title, render, close, edge).
 */

import type { ReadableAtom } from 'nanostores'
import type { ReactElement, ReactNode, PointerEvent as ReactPointerEvent } from 'react'

import type { DoubleTapContext } from '@/components/pane-shell/tree/renderer/drag-session'
import { registerPaneCloser, removeTreePane, treePanesWithPrefix } from '@/components/pane-shell/tree/store'
import { registry } from '@/contrib/registry'
import type { TileDock } from '@/store/session-states'

export interface PaneMirror<T> {
  /** Reactive source list. */
  source: ReadableAtom<T[]>
  /** Extra atoms whose changes should re-sync (e.g. titles living elsewhere). */
  also?: ReadableAtom<unknown>[]
  /** Stable key + pane-id seed for a tile. */
  key: (tile: T) => string
  /** Pane-id namespace — the id is `${prefix}:${key}`. */
  prefix: string
  /** Dock on adoption (default right; `center` = stack into anchor's zone). */
  dir?: (tile: T) => TileDock | undefined
  /** Pane to dock against (default `workspace`) — a drop's target zone. */
  anchor?: (tile: T) => string | undefined
  /** Center docks: the strip slot (stack before this pane id). */
  before?: (tile: T) => null | string | undefined
  minWidth: string
  title: (key: string) => string
  /** Custom lead NODE for the tile's tab (rendered before the label). A live,
   *  self-subscribing component (e.g. a session's status dot) so the strip needn't
   *  re-sync on status/color change — only `title` drives re-registration. */
  tabLead?: (key: string) => ReactNode
  /** Custom label NODE for the tile's tab, self-subscribing for the same reason
   *  as `tabLead` — a name that moves faster than re-registration (see
   *  PaneChrome.tabTitle). Falls back to `title`. */
  tabTitle?: (key: string) => ReactNode
  render: (key: string) => ReactNode
  /** Wrap the tile's TAB (domain context menu — session verbs). */
  tabWrap?: (key: string, tab: ReactElement) => ReactNode
  /** Override the tile's TAB drag (session drop language: stack/split/link).
   *  Returns whether it took the drag (see PaneChrome.tabDrag). */
  tabDrag?: (
    key: string,
    event: ReactPointerEvent<HTMLElement>,
    onTap: () => void,
    double?: DoubleTapContext
  ) => boolean
  /** Wired as the pane's closer (tab Close). */
  close: (key: string) => void
}

/** Build a `watch*` fn: syncs once, then re-syncs on every source/also change.
 *  Module-level state lives in the returned closure, so call it once per app. */
export function paneMirror<T>(cfg: PaneMirror<T>): () => void {
  const registered = new Map<string, { dispose: () => void; title: string; dockKey: string }>()
  const paneId = (key: string) => `${cfg.prefix}:${key}`

  const sync = () => {
    const tiles = cfg.source.get()
    const wanted = new Set(tiles.map(cfg.key))

    for (const tile of tiles) {
      const key = cfg.key(tile)
      const title = cfg.title(key)
      const dock = {
        before: cfg.before?.(tile),
        pane: cfg.anchor?.(tile) ?? 'workspace',
        pos: cfg.dir?.(tile) ?? 'right'
      }
      const dockKey = JSON.stringify(dock)
      const current = registered.get(key)

      // A tile's anchor can depend on its siblings. When an earlier tile closes,
      // a surviving tile must be re-adopted against its new anchor; keeping the
      // old contribution would leave its pane pointed at the removed tile.
      if (current && current.title === title && current.dockKey === dockKey) {
        continue
      }

      // Re-registration replaces the contribution, but the layout tree still
      // contains the old placement. Remove it first so the normal contributor
      // adoption pass inserts it using the fresh dock hint.
      if (current) {
        removeTreePane(paneId(key))
        current.dispose()
      }

      const dispose = registry.register({
        id: paneId(key),
        area: 'panes',
        title,
        data: {
          tabLead: cfg.tabLead ? () => cfg.tabLead!(key) : undefined,
          tabTitle: cfg.tabTitle ? () => cfg.tabTitle!(key) : undefined,
          dock,
          minWidth: cfg.minWidth,
          // Every mirrored tile is a full workspace surface docked beside main —
          // and closeable, which is what keeps its tab when it lands in a zone of
          // its own (see lone-header.ts).
          placement: 'main',
          tabDrag: cfg.tabDrag
            ? (event: ReactPointerEvent<HTMLElement>, onTap: () => void, double?: DoubleTapContext) =>
                cfg.tabDrag!(key, event, onTap, double)
            : undefined, // returns boolean (handled) — see PaneChrome.tabDrag
          tabWrap: cfg.tabWrap ? (tab: ReactElement) => cfg.tabWrap!(key, tab) : undefined
        },
        render: () => cfg.render(key)
      })

      registered.set(key, { dispose, title, dockKey })

      if (!current) {
        registerPaneCloser(paneId(key), () => cfg.close(key))
      }
    }

    for (const [key, entry] of registered) {
      if (!wanted.has(key)) {
        entry.dispose()
        registered.delete(key)
        removeTreePane(paneId(key))
      }
    }

    // Prune tree panes the SHARED tree persisted for a tile we never registered
    // this session and that isn't wanted now — a profile switch reloads with the
    // other profile's tile panes still stacked in. (`registered` is empty after a
    // reload, so the loop above can't catch these.)
    for (const id of treePanesWithPrefix(`${cfg.prefix}:`)) {
      if (!wanted.has(id.slice(cfg.prefix.length + 1))) {
        removeTreePane(id)
      }
    }
  }

  return () => {
    sync()
    cfg.source.listen(sync)
    cfg.also?.forEach(atom => atom.listen(sync))
  }
}

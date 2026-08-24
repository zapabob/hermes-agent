/**
 * PREVIEW TILES — every open preview (a file, a URL, an artifact) rendered as a
 * layout-tree pane, the preview analog of session and route tiles.
 *
 * The rail used to bring its OWN tab strip: a second bar beside the zone's own,
 * at a different height, with its own close menu and its own label casing. It
 * predated the layout tree. Now `$previewTabs` mirrors into pane contributions
 * through the same `paneMirror` the other tiles use, so a preview tab IS a zone
 * tab — same strip, same drag/stack/split, same ⌘W, same right-click verbs, and
 * one bar instead of two.
 */

import { findGroup } from '@/components/pane-shell/tree/model'
import { $activeTreeGroup, $layoutTree, revealTreePane } from '@/components/pane-shell/tree/store'
import { FileTypeIcon } from '@/components/ui/file-type-icon'
import { ToolIcon } from '@/components/ui/tool-icon'
import { $rightRailActiveTabId, type RightRailTabId, selectRightRailTab } from '@/store/layout'
import { $previewTabs, closeRightRailTab, type PreviewTarget } from '@/store/preview'

import { paneMirror } from './pane-mirror'
import { PreviewTilePane } from './right-rail/preview'
import { forgetPreviewConsole } from './right-rail/preview-console-store'

/** The target behind a tile id, or null once its tab is gone. */
function targetFor(tabId: string): PreviewTarget | null {
  return $previewTabs.get().find(tab => tab.id === tabId)?.target ?? null
}

/** Tab title. A URL is a BROWSER — the tab names the surface, not the page, so
 *  it doesn't rename itself on every navigation. A file names the file; an
 *  artifact is titled rather than located, so its label is the whole name. */
function previewTitle(tabId: string): string {
  const target = targetFor(tabId)

  if (!target) {
    return 'Preview'
  }

  if (target.kind === 'url') {
    return 'Browser'
  }

  if (target.kind === 'artifact') {
    return target.label || 'Preview'
  }

  const value = target.label || target.path || target.source || target.url
  const tail = value.split(/[\\/]/).filter(Boolean).at(-1)

  return tail || value || 'Preview'
}

/** The tab's lead glyph — the same file/tool icon family the file tree and code
 *  fences resolve through, so a `.tsx` peek and its sidebar row agree. */
function PreviewTabLead({ tabId }: { tabId: string }) {
  const target = targetFor(tabId)

  if (!target) {
    return null
  }

  if (target.kind === 'artifact') {
    return <ToolIcon className="opacity-70" name="sparkle" size="0.6875rem" />
  }

  if (target.kind === 'url') {
    return <ToolIcon className="opacity-70" name="globe" size="0.6875rem" />
  }

  return <FileTypeIcon className="opacity-70" path={target.path || target.url} size="0.6875rem" />
}

const PREVIEW_TILE_PREFIX = 'preview-tile'

const previewPaneId = (tabId: string) => `${PREVIEW_TILE_PREFIX}:${tabId}`

function previewAnchor(tab: { id: string; target: PreviewTarget }): string | undefined {
  if (tab.target.kind === 'url') {
    const firstBrowser = $previewTabs.get().find(candidate => candidate.target.kind === 'url')

    return firstBrowser && firstBrowser.id !== tab.id ? previewPaneId(firstBrowser.id) : 'workspace'
  }

  const firstStacked = $previewTabs.get().find(candidate => candidate.target.kind !== 'url')

  return firstStacked && firstStacked.id !== tab.id ? previewPaneId(firstStacked.id) : undefined
}

/** Keep pane contributions mirroring `$previewTabs`, keep the store's selection
 *  and the tree's active pane agreeing, and front a tile when its tab is
 *  selected. Call once from the root. */
export function watchPreviewTiles(): void {
  watchPreviewTileMirror()

  // The reveal analog of session tiles (session-states calls revealTreePane on
  // open): `openPreview` selects the tab, and the TREE must front its pane —
  // un-minimize, un-hide, activate in its zone. Both stores, because re-opening
  // the already-active tab changes only `$previewTabs` (fresh tab object), while
  // switching tabs changes only the active id.
  const reveal = () => {
    const tabs = $previewTabs.get()

    for (const tab of tabs) {
      if (tab.target.kind === 'url') {
        revealTreePane(`${PREVIEW_TILE_PREFIX}:${tab.id}`)
      }
    }

    const tabId = $rightRailActiveTabId.get()

    if (tabId && targetFor(tabId)) {
      revealTreePane(`${PREVIEW_TILE_PREFIX}:${tabId}`)
    }
  }

  $rightRailActiveTabId.listen(reveal)
  $previewTabs.listen(reveal)
  reveal()

  // And the reverse: clicking a preview TAB activates its pane in the TREE
  // only, so the store's selection must follow or `$previewTarget` (⌘L quote
  // labels, the titlebar's has-preview state) keeps reporting the previous
  // tab. Same derivation `$focusedStoredSessionId` uses: the interacted zone's
  // active pane names the tab. Converges with `reveal` — re-selecting the id
  // the tree already fronts is a no-op in both directions.
  const follow = () => {
    const tree = $layoutTree.get()
    const groupId = $activeTreeGroup.get()
    const active = groupId && tree ? findGroup(tree, groupId)?.active : undefined

    if (!active?.startsWith(`${PREVIEW_TILE_PREFIX}:`)) {
      return
    }

    const tabId = active.slice(PREVIEW_TILE_PREFIX.length + 1) as RightRailTabId

    if (targetFor(tabId) && $rightRailActiveTabId.get() !== tabId) {
      selectRightRailTab(tabId)
    }
  }

  $layoutTree.listen(follow)
  $activeTreeGroup.listen(follow)
}

const watchPreviewTileMirror = paneMirror<{ id: string; target: PreviewTarget }>({
  source: $previewTabs,
  // Unscoped on purpose. `$previewTabs` is one global Browser/file surface —
  // clicking a link in a bot chat must open the same pane Sessions already
  // shows. Scoping this to `sessions` filtered the pane out of Bot Mode, so
  // `openPreview` ran and the click looked like a no-op.
  key: tab => tab.id,
  prefix: PREVIEW_TILE_PREFIX,
  dir: tab => (tab.target.kind !== 'url' && previewAnchor(tab) ? 'center' : 'right'),
  anchor: previewAnchor,
  minWidth: '22rem',
  title: previewTitle,
  tabLead: tabId => <PreviewTabLead tabId={tabId} />,
  render: tabId => <PreviewTilePane tabId={tabId} />,
  close: tabId => {
    forgetPreviewConsole(tabId)
    closeRightRailTab(tabId)
  }
})

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

import { useStore } from '@nanostores/react'

import { findGroup } from '@/components/pane-shell/tree/model'
import { $activeTreeGroup, $layoutTree, revealTreePane } from '@/components/pane-shell/tree/store'
import { type MenuKit, renderActionItem } from '@/components/ui/actions-menu'
import { FileTypeIcon } from '@/components/ui/file-type-icon'
import { ToolIcon } from '@/components/ui/tool-icon'
import { translateNow } from '@/i18n'
import { openExternalLink } from '@/lib/external-link'
import { $rightRailActiveTabId, type RightRailTabId, selectRightRailTab } from '@/store/layout'
import {
  $browserPages,
  $dockedPreviewTabs,
  $previewTabs,
  adoptPersistedBrowserTab,
  type BrowserPage,
  closeRightRailTab,
  forgetBrowserPage,
  markBrowserTabPopped,
  newBrowserTab,
  popOutBrowserTab,
  type PreviewTarget
} from '@/store/preview'
import { canOpenBrowserWindow } from '@/store/windows'

import { paneMirror } from './pane-mirror'
import { PreviewTilePane } from './right-rail/preview'
import { forgetPreviewConsole } from './right-rail/preview-console-store'

/** The target behind a tile id, or null once its tab is gone. */
function targetFor(tabId: string): PreviewTarget | null {
  return $previewTabs.get().find(tab => tab.id === tabId)?.target ?? null
}

/** Schemes that are not a page the user's default browser can usefully open
 *  (blank vessel, Chromium internals, injected documents). */
const NON_EXTERNAL_URL = /^(about|blob|chrome|data|devtools|javascript):/i

/** The URL a Browser tab should hand to the OS browser — the page it is
 *  showing now, else the address it was opened with. Null when there isn't
 *  one (`about:blank`, a half-typed address, a file/artifact tab). */
export function browserTabExternalUrl(tabId: string): null | string {
  const target = targetFor(tabId)

  if (target?.kind !== 'url') {
    return null
  }

  const url = $browserPages.get()[tabId]?.url || target.url

  return url && !NON_EXTERNAL_URL.test(url) ? url : null
}

function browserTabMenuPrefix(tabId: string) {
  if (targetFor(tabId)?.kind !== 'url') {
    return undefined
  }

  return (kit: MenuKit) => (
    <>
      {canOpenBrowserWindow()
        ? renderActionItem(kit, {
            icon: 'empty-window',
            key: 'pop-out',
            label: translateNow('preview.popOut'),
            onSelect: () => popOutBrowserTab(tabId)
          })
        : null}
      {renderActionItem(kit, {
        disabled: !browserTabExternalUrl(tabId),
        icon: 'link-external',
        key: 'open-external',
        label: translateNow('preview.openInExternal'),
        onSelect: () => openExternalLink(browserTabExternalUrl(tabId) ?? '')
      })}
    </>
  )
}

/** Tab title. A URL tab is titled by the CONTRIBUTION as the surface — see
 *  `BrowserTabLabel` for the live page name the strip actually renders — so
 *  navigating doesn't re-register the pane on every hop. A file names the
 *  file; an artifact is titled rather than located, so its label is the whole
 *  name. */
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

/**
 * What to call a Browser tab. Its page title, else the host it is on, else
 * the surface — the ladder every browser walks, and the reason more than one
 * Browser is usable at all: three tabs reading "Browser" name nothing.
 *
 * A page that never set a title reports its own address as one, which is a
 * worse label than the host it came from, so an address-shaped title falls
 * through.
 */
export function browserTabLabel(target: PreviewTarget, page?: BrowserPage): string {
  const url = page?.url || target.url
  const title = page?.title.trim()

  if (title && title !== url) {
    return title
  }

  try {
    return new URL(url).hostname.replace(/^www\./, '') || 'Browser'
  } catch {
    // `about:blank` and half-typed addresses have no host to fall back to.
    return 'Browser'
  }
}

/** Live tab label for a Browser: it renames itself as the page navigates,
 *  without the contribution re-registering (see PaneChrome.tabTitle). */
function BrowserTabLabel({ tabId }: { tabId: string }) {
  const pages = useStore($browserPages)
  const target = targetFor(tabId)

  return target ? browserTabLabel(target, pages[tabId]) : null
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

  const firstPreview = $dockedPreviewTabs.get().find(candidate => candidate.target.kind !== 'url')

  return firstPreview && firstPreview.id !== tab.id ? previewPaneId(firstPreview.id) : undefined
}

/** Keep pane contributions mirroring `$previewTabs`, keep the store's selection
 *  and the tree's active pane agreeing, and front a tile when its tab is
 *  selected. Call once from the root. */
export function watchPreviewTiles(): void {
  watchPreviewTileMirror()

  window.hermesDesktop?.onBrowserPopoutClosed?.(tabId => {
    adoptPersistedBrowserTab(tabId)
    markBrowserTabPopped(tabId, false)
  })

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
  source: $dockedPreviewTabs,
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
  tabTitle: tabId => (targetFor(tabId)?.kind === 'url' ? <BrowserTabLabel tabId={tabId} /> : undefined),
  // A Browser is a vessel, so there can be more of it — a file peek is one of
  // a kind and leaves the strip's "+" to whatever else the zone holds.
  newTab: tabId => (targetFor(tabId)?.kind === 'url' ? newBrowserTab : undefined),
  tabMenuPrefix: browserTabMenuPrefix,
  render: tabId => <PreviewTilePane tabId={tabId} />,
  close: tabId => {
    forgetBrowserPage(tabId)
    forgetPreviewConsole(tabId)
    closeRightRailTab(tabId)
  }
})

import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest'

import { group } from '@/components/pane-shell/tree/model'
import { $activeTreeGroup, $layoutTree, closeTreePane, watchContributedPanes } from '@/components/pane-shell/tree/store'
import { registry } from '@/contrib/registry'
import { $previewTabs, closeRightRailTab, newBrowserTab, openPreview, type PreviewTarget } from '@/store/preview'

import { watchPreviewTiles } from './preview-tile'
import { previewConsoleState } from './right-rail/preview-console-store'

const workspaceGroupId = 'preview-test-workspace'
const workspacePaneId = 'workspace'

function urlTarget(url: string): PreviewTarget {
  return { kind: 'url', label: url, source: url, url }
}

function paneDock(paneId: string) {
  const pane = registry.getArea('panes').find(candidate => candidate.id === paneId)
  const data = pane?.data as { dock?: { pane?: string; pos?: string } } | undefined

  return data?.dock
}

function expectDock(paneId: string, anchor: string) {
  const dock = paneDock(paneId)

  expect(dock?.pane).toBe(anchor)
  expect(dock?.pos).toBe('right')
}

describe('preview tiles', () => {
  let disposeWorkspace: (() => void) | undefined

  beforeAll(() => {
    disposeWorkspace = registry.register({
      area: 'panes',
      data: { placement: 'main', uncloseable: true },
      id: workspacePaneId,
      render: () => null,
      title: workspacePaneId
    })
    $layoutTree.set(group([workspacePaneId], { active: workspacePaneId, id: workspaceGroupId }))
    $activeTreeGroup.set(workspaceGroupId)
    watchContributedPanes()
    watchPreviewTiles()
  })

  beforeEach(() => {
    // Reset both stores and the tree so each scenario observes only the tabs it
    // opens. The mirror's reactive source listener removes the old tile panes.
    $layoutTree.set(group([workspacePaneId], { active: workspacePaneId, id: workspaceGroupId }))
    $activeTreeGroup.set(workspaceGroupId)
    $previewTabs.set([])
    closeRightRailTab('url:browser')
  })

  afterAll(() => {
    $previewTabs.set([])
    disposeWorkspace?.()
  })

  it('places two URL previews workspace -> first -> second, and keeps the anchor after close/reopen', () => {
    const first = 'https://first.example.test'
    const second = 'https://second.example.test'

    openPreview(urlTarget(first), 'explicit-link')
    newBrowserTab()
    openPreview(urlTarget(second), 'explicit-link')

    const tabs = $previewTabs.get()
    expect(tabs.map(tab => tab.target.url)).toEqual([first, second])

    const firstId = tabs[0].id
    const secondId = tabs[1].id
    expectDock(`preview-tile:${firstId}`, 'workspace')
    expectDock(`preview-tile:${secondId}`, `preview-tile:${firstId}`)

    const originalConsole = previewConsoleState(firstId)
    closeTreePane(`preview-tile:${firstId}`)

    expect($previewTabs.get().map(tab => tab.target.url)).toEqual([second])
    expect(previewConsoleState(firstId)).not.toBe(originalConsole)
    expectDock(`preview-tile:${$previewTabs.get()[0].id}`, 'workspace')

    newBrowserTab()
    openPreview(urlTarget(first), 'explicit-link')
    const reopened = $previewTabs.get()
    const reopenedFirstId = reopened[1].id

    expect(reopened.map(tab => tab.target.url)).toEqual([second, first])
    expectDock(`preview-tile:${reopened[0].id}`, 'workspace')
    expectDock(`preview-tile:${reopenedFirstId}`, `preview-tile:${reopened[0].id}`)
  })
})

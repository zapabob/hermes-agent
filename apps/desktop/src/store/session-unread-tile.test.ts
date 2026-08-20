import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { group, split } from '@/components/pane-shell/tree/model'
import * as tree from '@/components/pane-shell/tree/store'
import { registry } from '@/contrib/registry'
import { createClientSessionState } from '@/lib/chat-runtime'

import * as session from './session'
import * as states from './session-states'

// The completed-unread dot is keyed on the FOCUSED session, not the selected
// one. A tile is never $selectedStoredSessionId, so keying either half on the
// selection left a tiled session's dot green with no way to clear it.

describe('completed-unread dot follows the focused session', () => {
  const disposers: (() => void)[] = []

  beforeEach(() => {
    for (const id of ['workspace', 'session-tile:tiled']) {
      disposers.push(
        registry.register({
          area: 'panes',
          data: id === 'workspace' ? { placement: 'main', uncloseable: true } : { placement: 'main' },
          id,
          render: () => null,
          title: id
        })
      )
    }

    tree.$layoutTree.set(null)
    tree.$activeTreeGroup.set(null)
    tree.$hoveredTreeGroup.set(null)
    states.clearAllSessionStates()
    session.$unreadFinishedSessionIds.set([])
    session.$selectedStoredSessionId.set('primary')
  })

  afterEach(() => {
    states.clearAllSessionStates()
    session.$unreadFinishedSessionIds.set([])
    session.$selectedStoredSessionId.set(null)
    tree.$layoutTree.set(null)
    tree.$activeTreeGroup.set(null)
    tree.$hoveredTreeGroup.set(null)
    disposers.splice(0).forEach(dispose => dispose())
  })

  function setup() {
    // The workspace holds the primary chat, a second zone holds the tile.
    tree.declareDefaultTree(
      split('row', [
        group(['workspace'], { active: 'workspace', id: 'grp-main' }),
        group(['session-tile:tiled'], { active: 'session-tile:tiled', id: 'grp-tile' })
      ])
    )

    const finishTurn = (storedSessionId: string) => {
      const working = { ...createClientSessionState(null), busy: true, storedSessionId }
      states.publishSessionState(`rt-${storedSessionId}`, working)
      states.publishSessionState(`rt-${storedSessionId}`, { ...working, busy: false })
    }

    return { finishTurn }
  }

  it('clears the dot when an already-open tile is fronted', () => {
    const { finishTurn } = setup()

    tree.noteActiveTreeGroup('grp-main')
    finishTurn('tiled')
    expect(session.$unreadFinishedSessionIds.get()).toEqual(['tiled'])

    // Fronting the tile is what a tab click does. Before the fix nothing on
    // this path cleared the marker, so the dot stayed green.
    tree.noteActiveTreeGroup('grp-tile')
    expect(session.$unreadFinishedSessionIds.get()).toEqual([])
  })

  it('never marks a tile that finishes while it is the focused one', () => {
    const { finishTurn } = setup()

    tree.noteActiveTreeGroup('grp-tile')
    finishTurn('tiled')

    expect(session.$unreadFinishedSessionIds.get()).toEqual([])
  })

  it('marks the primary session when a tile has focus', () => {
    const { finishTurn } = setup()

    tree.noteActiveTreeGroup('grp-tile')
    finishTurn('primary')

    expect(session.$unreadFinishedSessionIds.get()).toEqual(['primary'])
  })
})

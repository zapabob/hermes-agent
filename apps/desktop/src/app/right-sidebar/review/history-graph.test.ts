import { describe, expect, it } from 'vitest'

import type { HermesGitCommit } from '@/global'

import { buildCommitGraph } from './history-graph'

function commit(sha: string, parents: string[] = []): HermesGitCommit {
  return {
    author: 'Hermes Test',
    authoredAt: '2026-08-10T12:00:00+00:00',
    parents,
    sha,
    shortSha: sha.slice(0, 7),
    subject: `commit ${sha}`
  }
}

describe('buildCommitGraph', () => {
  it('is empty for an empty window', () => {
    expect(buildCommitGraph([])).toEqual([])
  })

  it('keeps a linear chain in one lane', () => {
    const a = commit('aaaa', ['bbbb'])
    const b = commit('bbbb', ['cccc'])
    const c = commit('cccc', ['dddd'])
    const d = commit('dddd')

    const rows = buildCommitGraph([a, b, c, d])

    expect(rows.map(row => row.lane)).toEqual([0, 0, 0, 0])
    expect(rows.map(row => row.through)).toEqual([[0], [0], [0], []])
    expect(rows.every(row => row.branchIn.length === 0)).toBe(true)
  })

  it('opens a second lane for a merge parent and connects it with a stub', () => {
    const merge = commit('aaaa', ['bbbb', 'cccc'])
    const b = commit('bbbb', ['dddd'])
    const c = commit('cccc', ['dddd'])
    const d = commit('dddd')

    const rows = buildCommitGraph([merge, b, c, d])

    // The merge row sits in the first-parent lane, the second parent branches
    // in from lane 1, and the two chains rejoin on the shared ancestor.
    expect(rows.map(row => row.lane)).toEqual([0, 0, 1, 0])
    expect(rows.map(row => row.through)).toEqual([[0, 1], [0, 1], [0], []])
    expect(rows.map(row => row.branchIn)).toEqual([[1], [], [], []])
  })

  it('ends the chain when a parent is outside the window', () => {
    const rows = buildCommitGraph([commit('aaaa', ['beyond-the-window'])])

    expect(rows.map(row => row.lane)).toEqual([0])
    expect(rows.map(row => row.through)).toEqual([[]])
  })

  it('does not double-claim a parent shared by two visible commits', () => {
    const a = commit('aaaa', ['dddd'])
    const c = commit('cccc', ['dddd'])
    const d = commit('dddd')

    const rows = buildCommitGraph([a, c, d])

    // A claims lane 0 down to d; c opens lane 1 with no line of its own.
    expect(rows.map(row => row.lane)).toEqual([0, 1, 0])
    expect(rows.map(row => row.through)).toEqual([[0], [0], []])
    expect(rows.every(row => row.branchIn.length === 0)).toBe(true)
  })

  it('is deterministic for the same window', () => {
    const commits = [commit('aaaa', ['bbbb', 'cccc']), commit('bbbb', ['dddd']), commit('cccc', ['dddd']), commit('dddd')]

    expect(buildCommitGraph(commits)).toEqual(buildCommitGraph(commits))
  })
})
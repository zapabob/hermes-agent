import type { HermesGitCommit } from '@/global'

// One rendered row of the commit graph: the lane the commit dot sits in, the
// lanes whose vertical edges pass through the row, and the lanes this row
// connects to with a horizontal stub (merge second parents and shared
// ancestors). Lanes are compacted left to right and never reused, so the
// widest row's gutter is (maxLane + 1) lanes wide.
export interface CommitGraphRow {
  branchIn: number[]
  lane: number
  through: number[]
}

// Assign lanes to a newest-first commit list (the `git log` window the history
// pane shows). A commit continues the lane of its first visible parent; a
// later visible parent branches in from a fresh lane. Parents outside the
// window just end the chain. The result is deterministic and bounded by the
// visible list, so the pane renders a graph without any extra IPC.
export function buildCommitGraph(commits: readonly HermesGitCommit[]): CommitGraphRow[] {
  const rows: CommitGraphRow[] = commits.map(() => ({ branchIn: [], lane: 0, through: [] }))
  const visible = new Set(commits.map(commit => commit.sha))
  const indexOf = new Map(commits.map((commit, index) => [commit.sha, index]))
  // Lane a commit is expected at (claimed by the chain above it); consumed
  // when the commit's own row is drawn.
  const pendingLane = new Map<string, number>()
  // Lane → row of the commit the lane's vertical edge still runs down to.
  const laneTarget = new Map<number, number>()
  const assigned = new Set<number>()

  const nextLane = (): number => {
    let lane = 0

    while (assigned.has(lane)) {
      lane += 1
    }

    assigned.add(lane)

    return lane
  }

  commits.forEach((commit, i) => {
    const lane = pendingLane.get(commit.sha) ?? nextLane()
    const parents = commit.parents.filter(parent => visible.has(parent))

    pendingLane.delete(commit.sha)
    laneTarget.delete(lane)

    parents.forEach((parent, index) => {
      if (pendingLane.has(parent)) {
        return
      }

      const parentLane = index === 0 ? lane : nextLane()

      if (index > 0) {
        rows[i].branchIn.push(parentLane)
      }

      pendingLane.set(parent, parentLane)
      laneTarget.set(parentLane, indexOf.get(parent)!)
    })

    rows[i].lane = lane
    rows[i].through = [...laneTarget.entries()]
      .filter(([, target]) => target > i)
      .map(([openLane]) => openLane)
      .sort((a, b) => a - b)
  })

  return rows
}
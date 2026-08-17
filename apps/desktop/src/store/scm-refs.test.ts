import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { HermesGitBranch, HermesGitStash, HermesGitTag } from '@/global'

import { $reviewOpen, $reviewScopeCwd } from './review'
import {
  $scmBranches,
  $scmBranchesLoading,
  $scmBusy,
  $scmStashes,
  $scmStashesLoading,
  $scmTags,
  $scmTagsLoading,
  refreshScmRefs,
  scmBranchCreate,
  scmBranchDelete,
  scmBranchRename,
  scmFetch,
  scmPull,
  scmStashApply,
  scmStashCreate,
  scmStashDrop,
  scmTagCreate,
  scmTagDelete
} from './scm-refs'
import { $currentCwd } from './session'

// refreshRepoStatus is a fire-and-forget side effect of mutations; stub it so
// it doesn't try to hit the (absent) probe and log.
vi.mock('./coding-status', () => ({ refreshRepoStatus: vi.fn(), repoStatusForCwd: () => ({ get: () => null }) }))

const tag = (over: Partial<HermesGitTag> = {}): HermesGitTag => ({
  name: 'v1.0',
  sha: '1234567890abcdef1234567890abcdef12345678',
  shortSha: '1234567',
  date: '2026-08-10T12:00:00+00:00',
  subject: 'release',
  ...over
})

const stash = (over: Partial<HermesGitStash> = {}): HermesGitStash => ({
  index: 0,
  id: 'stash@{0}',
  sha: '1234567890abcdef1234567890abcdef12345678',
  shortSha: '1234567',
  date: '2026-08-10T12:00:00+00:00',
  message: 'On main: wip',
  ...over
})

const branch = (over: Partial<HermesGitBranch> = {}): HermesGitBranch => ({
  name: 'feature',
  checkedOut: false,
  isDefault: false,
  isRemote: false,
  worktreePath: null,
  ...over
})

type GitStub = Record<string, ReturnType<typeof vi.fn>>

// Install a git bridge on window.hermesDesktop. Any op not supplied defaults
// to a resolved no-op so a test only declares what it exercises.
function stubGit(over: GitStub = {}) {
  const git: GitStub = {
    tagList: vi.fn(async () => []),
    stashList: vi.fn(async () => []),
    branchList: vi.fn(async () => []),
    branchCreate: vi.fn(async () => ({ ok: true })),
    branchRename: vi.fn(async () => ({ ok: true })),
    branchDelete: vi.fn(async () => ({ ok: true })),
    tagCreate: vi.fn(async () => ({ ok: true })),
    tagDelete: vi.fn(async () => ({ ok: true })),
    stashCreate: vi.fn(async () => ({ ok: true })),
    stashApply: vi.fn(async () => ({ ok: true })),
    stashDrop: vi.fn(async () => ({ ok: true })),
    fetch: vi.fn(async () => ({ ok: true })),
    pull: vi.fn(async () => ({ ok: true })),
    ...over
  }

  ;(window as unknown as { hermesDesktop?: unknown }).hermesDesktop = {
    git,
    openExternal: vi.fn()
  }

  return git
}

beforeEach(() => {
  $reviewOpen.set(false)
  $reviewScopeCwd.set(null)
  $currentCwd.set('/repo')
  $scmBranches.set([])
  $scmBranchesLoading.set(false)
  $scmTags.set([])
  $scmTagsLoading.set(false)
  $scmStashes.set([])
  $scmStashesLoading.set(false)
  $scmBusy.set(null)
})

afterEach(() => {
  delete (window as unknown as { hermesDesktop?: unknown }).hermesDesktop
})

describe('refreshScmRefs', () => {
  it('is a no-op that clears state when the pane is closed', async () => {
    const git = stubGit()
    $scmTags.set([tag()])
    $scmStashes.set([stash()])
    $scmBranches.set([branch()])

    await refreshScmRefs()

    expect(git.tagList).not.toHaveBeenCalled()
    expect(git.stashList).not.toHaveBeenCalled()
    expect(git.branchList).not.toHaveBeenCalled()
    expect($scmTags.get()).toEqual([])
    expect($scmStashes.get()).toEqual([])
    expect($scmBranches.get()).toEqual([])
    expect($scmTagsLoading.get()).toBe(false)
  })

  it('clears state when there is no bridge/cwd', async () => {
    delete (window as unknown as { hermesDesktop?: unknown }).hermesDesktop
    $reviewOpen.set(true)
    $scmTagsLoading.set(true)

    await refreshScmRefs()

    expect($scmTags.get()).toEqual([])
    expect($scmTagsLoading.get()).toBe(false)
  })

  it('populates branches, tags and stashes from the bridge', async () => {
    stubGit({
      tagList: vi.fn(async () => [tag({ name: 'v2.0' })]),
      stashList: vi.fn(async () => [stash({ index: 1 })]),
      branchList: vi.fn(async () => [branch({ name: 'main', checkedOut: true })])
    })
    $reviewOpen.set(true)

    await refreshScmRefs()

    expect($scmTags.get().map(t => t.name)).toEqual(['v2.0'])
    expect($scmStashes.get().map(s => s.index)).toEqual([1])
    expect($scmBranches.get().map(b => b.name)).toEqual(['main'])
    expect($scmTagsLoading.get()).toBe(false)
  })

  it('clears lists but keeps loading off when the bridge throws', async () => {
    stubGit({
      tagList: vi.fn(async () => {
        throw new Error('git failed')
      })
    })
    $reviewOpen.set(true)
    $scmTags.set([tag()])

    await refreshScmRefs()

    expect($scmTags.get()).toEqual([])
    expect($scmTagsLoading.get()).toBe(false)
  })
})

describe('mutations', () => {
  it('scmTagCreate forwards name and target, then re-syncs', async () => {
    const git = stubGit()
    $reviewOpen.set(true)

    await scmTagCreate('v1.0', 'abc123')

    expect(git.tagCreate).toHaveBeenCalledWith('/repo', 'v1.0', 'abc123')
    expect(git.tagList).toHaveBeenCalledWith('/repo')
  })

  it('scmTagCreate is a no-op when the bridge lacks the op', async () => {
    const git = stubGit()
    delete git.tagCreate

    await expect(scmTagCreate('v1.0')).resolves.toBeUndefined()
  })

  it('scmTagDelete forwards the name', async () => {
    const git = stubGit()
    $reviewOpen.set(true)

    await scmTagDelete('v1.0')

    expect(git.tagDelete).toHaveBeenCalledWith('/repo', 'v1.0')
  })

  it('scmBranchCreate forwards base', async () => {
    const git = stubGit()
    $reviewOpen.set(true)

    await scmBranchCreate('feature', 'main')

    expect(git.branchCreate).toHaveBeenCalledWith('/repo', 'feature', 'main')
  })

  it('scmBranchRename forwards newName', async () => {
    const git = stubGit()
    $reviewOpen.set(true)

    await scmBranchRename('feature', 'feature2')

    expect(git.branchRename).toHaveBeenCalledWith('/repo', 'feature', 'feature2')
  })

  it('scmBranchDelete forwards force', async () => {
    const git = stubGit()
    $reviewOpen.set(true)

    await scmBranchDelete('feature', true)

    expect(git.branchDelete).toHaveBeenCalledWith('/repo', 'feature', true)
  })

  it('scmStashCreate forwards message and includeUntracked', async () => {
    const git = stubGit()
    $reviewOpen.set(true)

    await scmStashCreate('wip', true)

    expect(git.stashCreate).toHaveBeenCalledWith('/repo', 'wip', true)
  })

  it('scmStashApply forwards the index', async () => {
    const git = stubGit()
    $reviewOpen.set(true)

    await scmStashApply(1)

    expect(git.stashApply).toHaveBeenCalledWith('/repo', 1)
  })

  it('scmStashDrop forwards the index', async () => {
    const git = stubGit()
    $reviewOpen.set(true)

    await scmStashDrop(0)

    expect(git.stashDrop).toHaveBeenCalledWith('/repo', 0)
  })

  it('scmFetch forwards the remote', async () => {
    const git = stubGit()
    $reviewOpen.set(true)

    await scmFetch('origin')

    expect(git.fetch).toHaveBeenCalledWith('/repo', 'origin')
  })

  it('scmPull forwards rebase', async () => {
    const git = stubGit()
    $reviewOpen.set(true)

    await scmPull(true)

    expect(git.pull).toHaveBeenCalledWith('/repo', true)
  })

  it('toggles the busy flag around the op', async () => {
    const git = stubGit()
    const seen: (null | string)[] = []
    const unsub = $scmBusy.subscribe(v => seen.push(v))

    await scmTagCreate('v1.0')

    expect(seen).toContain('tag')
    expect($scmBusy.get()).toBeNull()
    unsub()
  })
})

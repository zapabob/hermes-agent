import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test } from 'vitest'

import {
  branchCreate,
  branchDelete,
  branchRename,
  gitFetch,
  gitPull,
  listStashes,
  listTags,
  parseStashes,
  parseTags,
  stashApply,
  stashCreate,
  stashDrop,
  tagCreate,
  tagDelete
} from './git-ref-ops'

const tempDirs: string[] = []

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function rmRetry(dir: string) {
  // Windows can hold a temp dir handle open briefly after the last git
  // subprocess exits; retry instead of failing the whole test file on it.
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      fs.rmSync(dir, { force: true, recursive: true })

      return
    } catch {
      if (attempt === 3) {
        throw new Error(`Failed to remove temp dir: ${dir}`)
      }

      await sleep(150)
    }
  }
}

afterEach(async () => {
  for (const dir of tempDirs.splice(0)) {
    await rmRetry(dir)
  }
})

// A repo with one committed tracked file. Stash tests modify it.
function makeRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-desktop-git-ref-'))

  tempDirs.push(dir)
  execFileSync('git', ['init', '-q', '-b', 'main'], { cwd: dir })
  execFileSync('git', ['config', 'user.email', 'hermes-test@example.com'], { cwd: dir })
  execFileSync('git', ['config', 'user.name', 'Hermes Test'], { cwd: dir })
  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'one\n')
  execFileSync('git', ['add', 'tracked.txt'], { cwd: dir })
  execFileSync('git', ['commit', '-qm', 'initial'], { cwd: dir })

  return dir
}

// A pair of repos: a "remote" with `main` plus a clone of it. Used for
// fetch/pull tests. The caller must remove them.
function seedRemoteAndClone(label) {
  const remoteDir = fs.mkdtempSync(path.join(os.tmpdir(), `hermes-${label}-remote-`))
  const cloneDir = fs.mkdtempSync(path.join(os.tmpdir(), `hermes-${label}-clone-`))

  tempDirs.push(remoteDir, cloneDir)
  execFileSync('git', ['init', '-q', '-b', 'main', remoteDir])
  execFileSync('git', [
    '-C',
    remoteDir,
    '-c',
    'user.email=hermes@localhost',
    '-c',
    'user.name=Hermes',
    'commit',
    '--allow-empty',
    '-m',
    'root'
  ])
  execFileSync('git', ['clone', '-q', remoteDir, cloneDir])

  return { cloneDir, remoteDir }
}

function remoteHead(remoteDir) {
  return execFileSync('git', ['-C', remoteDir, 'rev-parse', 'HEAD']).toString().trim()
}

test('parseTags: parses lightweight and annotated tag rows', () => {
  const rows = parseTags(
    [
      `v1${String.fromCharCode(31)}aaabbbcccdddeeefff000111222333444555666${String.fromCharCode(31)}${String.fromCharCode(31)}2026-08-18T03:00:00+09:00${String.fromCharCode(31)}release one`,
      `v2${String.fromCharCode(31)}${String.fromCharCode(31)}7777777777777777777777777777777777777777${String.fromCharCode(31)}2026-08-18T03:01:00+09:00${String.fromCharCode(31)}`
    ].join('\n')
  )

  // Annotated: the peeled commit sha wins over the tag-object sha.
  assert.equal(rows.length, 2)
  assert.equal(rows[0].name, 'v1')
  assert.equal(rows[0].sha, 'aaabbbcccdddeeefff000111222333444555666')
  assert.equal(rows[0].shortSha, 'aaabbbc')
  assert.equal(rows[0].subject, 'release one')
  // Lightweight: no peeled sha, so the commit sha is used.
  assert.equal(rows[1].sha, '7777777777777777777777777777777777777777')
  assert.equal(rows[1].subject, '')
})

test('parseStashes: parses stash list rows into indexes and messages', () => {
  const rows = parseStashes(
    [
      `stash@{0}${String.fromCharCode(31)}1111111111111111111111111111111111111111${String.fromCharCode(31)}2026-08-18T03:00:00+09:00${String.fromCharCode(31)}On main: wip fixture`,
      `stash@{1}${String.fromCharCode(31)}2222222222222222222222222222222222222222${String.fromCharCode(31)}2026-08-18T03:01:00+09:00${String.fromCharCode(31)}On main: older`
    ].join('\n')
  )

  assert.equal(rows.length, 2)
  assert.equal(rows[0].index, 0)
  assert.equal(rows[0].id, 'stash@{0}')
  assert.equal(rows[0].sha, '1111111111111111111111111111111111111111')
  assert.equal(rows[0].message, 'On main: wip fixture')
  assert.equal(rows[1].index, 1)
})

test('listTags: empty on a fresh repo and on a non-repo path', async () => {
  const dir = makeRepo()

  assert.deepEqual(await listTags(dir, 'git'), [])

  const nonRepo = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-nonrepo-tags-'))

  tempDirs.push(nonRepo)
  assert.deepEqual(await listTags(nonRepo, 'git'), [])
})

test('listStashes: empty when nothing is stashed', async () => {
  assert.deepEqual(await listStashes(makeRepo(), 'git'), [])
})

test('tagCreate: creates a lightweight tag at HEAD and lists it', async () => {
  const dir = makeRepo()

  await tagCreate(dir, 'v1.0', null, 'git')

  const tags = await listTags(dir, 'git')

  assert.equal(tags.length, 1)
  assert.equal(tags[0].name, 'v1.0')
  assert.equal(tags[0].sha, execFileSync('git', ['-C', dir, 'rev-parse', 'HEAD']).toString().trim())
})

test('tagCreate: tags a specified target and rejects invalid names', async () => {
  const dir = makeRepo()

  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'two\n')
  execFileSync('git', ['add', 'tracked.txt'], { cwd: dir })
  execFileSync('git', ['commit', '-qm', 'second'], { cwd: dir })

  await tagCreate(dir, 'v-old', 'HEAD~1', 'git')

  const tags = await listTags(dir, 'git')

  assert.equal(tags.length, 1)
  assert.equal(tags[0].sha, execFileSync('git', ['-C', dir, 'rev-parse', 'HEAD~1']).toString().trim())

  await assert.rejects(tagCreate(dir, 'bad..name', null, 'git'))
  await assert.rejects(tagCreate(dir, 'has space', null, 'git'))
})

test('tagDelete: removes a tag', async () => {
  const dir = makeRepo()

  await tagCreate(dir, 'v1.0', null, 'git')
  await tagDelete(dir, 'v1.0', 'git')

  assert.deepEqual(await listTags(dir, 'git'), [])
})

test('branchCreate: creates a branch at HEAD', async () => {
  const dir = makeRepo()

  await branchCreate(dir, 'feature/one', null, 'git')

  const created = execFileSync('git', ['-C', dir, 'rev-parse', 'feature/one']).toString().trim()

  assert.equal(created, execFileSync('git', ['-C', dir, 'rev-parse', 'HEAD']).toString().trim())
})

test('branchCreate: base param branches off a specified commit', async () => {
  const dir = makeRepo()

  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'two\n')
  execFileSync('git', ['add', 'tracked.txt'], { cwd: dir })
  execFileSync('git', ['commit', '-qm', 'second'], { cwd: dir })

  await branchCreate(dir, 'from-base', 'HEAD~1', 'git')

  assert.equal(
    execFileSync('git', ['-C', dir, 'rev-parse', 'from-base']).toString().trim(),
    execFileSync('git', ['-C', dir, 'rev-parse', 'HEAD~1']).toString().trim()
  )
})

test('branchCreate: rejects invalid branch names', async () => {
  const dir = makeRepo()

  await assert.rejects(branchCreate(dir, '-leading-dash', null, 'git'))
  await assert.rejects(branchCreate(dir, 'bad..name', null, 'git'))
  await assert.rejects(branchCreate(dir, '', null, 'git'))
})

test('branchRename: renames a branch', async () => {
  const dir = makeRepo()

  await branchCreate(dir, 'old-name', null, 'git')
  await branchRename(dir, 'old-name', 'new-name', 'git')

  assert.equal(
    execFileSync('git', ['-C', dir, 'rev-parse', 'new-name']).toString().trim(),
    execFileSync('git', ['-C', dir, 'rev-parse', 'HEAD']).toString().trim()
  )
  assert.throws(() => execFileSync('git', ['-C', dir, 'rev-parse', '--verify', 'old-name'], { stdio: 'ignore' }))
})

test('branchRename: rejects a rename to an invalid name', async () => {
  const dir = makeRepo()

  await assert.rejects(branchRename(dir, 'main', 'bad..name', 'git'))
})

test('branchDelete: deletes a merged branch', async () => {
  const dir = makeRepo()

  await branchCreate(dir, 'merged', null, 'git')
  await branchDelete(dir, 'merged', false, 'git')

  assert.throws(() => execFileSync('git', ['-C', dir, 'rev-parse', '--verify', 'merged'], { stdio: 'ignore' }))
})

test('branchDelete: refuses the checked-out branch', async () => {
  const dir = makeRepo()

  await assert.rejects(branchDelete(dir, 'main', false, 'git'))
})

test('branchDelete: force-deletes an unmerged branch', async () => {
  const dir = makeRepo()

  await branchCreate(dir, 'unmerged', null, 'git')
  execFileSync('git', ['-C', dir, 'switch', 'unmerged'], { cwd: dir })
  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'two\n')
  execFileSync('git', ['add', 'tracked.txt'], { cwd: dir })
  execFileSync('git', ['commit', '-qm', 'unmerged work'], { cwd: dir })
  execFileSync('git', ['-C', dir, 'switch', 'main'], { cwd: dir })

  // `-d` refuses an unmerged branch; `-D` goes through.
  await assert.rejects(branchDelete(dir, 'unmerged', false, 'git'))
  await branchDelete(dir, 'unmerged', true, 'git')
  assert.throws(() => execFileSync('git', ['-C', dir, 'rev-parse', '--verify', 'unmerged'], { stdio: 'ignore' }))
})

test('stashCreate: stashes working-tree changes and leaves the tree clean', async () => {
  const dir = makeRepo()

  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'two\n')
  await stashCreate(dir, 'wip fixture', false, 'git')

  // git's autocrlf normalizes the checkout to CRLF on Windows; compare the
  // line endings stripped.
  assert.equal(fs.readFileSync(path.join(dir, 'tracked.txt'), 'utf8').replace(/\r\n/g, '\n'), 'one\n')

  const stashes = await listStashes(dir, 'git')

  assert.equal(stashes.length, 1)
  assert.equal(stashes[0].index, 0)
  assert.match(stashes[0].message, /wip fixture/)
})

test('stashCreate: includeUntracked sweeps new files too', async () => {
  const dir = makeRepo()

  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'two\n')
  fs.writeFileSync(path.join(dir, 'new.txt'), 'brand new\n')
  await stashCreate(dir, 'with untracked', true, 'git')

  assert.equal(fs.existsSync(path.join(dir, 'new.txt')), false)
  assert.equal((await listStashes(dir, 'git')).length, 1)
})

test('stashApply: restores the stashed changes', async () => {
  const dir = makeRepo()

  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'two\n')
  await stashCreate(dir, 'wip fixture', false, 'git')
  await stashApply(dir, 0, 'git')

  assert.equal(fs.readFileSync(path.join(dir, 'tracked.txt'), 'utf8').replace(/\r\n/g, '\n'), 'two\n')
})

test('stashDrop: removes a stash', async () => {
  const dir = makeRepo()

  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'two\n')
  await stashCreate(dir, 'first', false, 'git')
  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'three\n')
  await stashCreate(dir, 'second', false, 'git')

  assert.equal((await listStashes(dir, 'git')).length, 2)

  await stashDrop(dir, 0, 'git')

  // Stashes are LIFO: dropping 0 removes the newest ("second"), leaving the
  // older "first" stash behind.
  const stashes = await listStashes(dir, 'git')

  assert.equal(stashes.length, 1)
  assert.match(stashes[0].message, /first/)
})

test('stashApply: rejects a bad index and an empty stash', async () => {
  const dir = makeRepo()

  await assert.rejects(stashApply(dir, -1, 'git'))
  await assert.rejects(stashApply(dir, 0, 'git'))
})

test('gitFetch: fetches new commits from the remote', async () => {
  const { cloneDir, remoteDir } = seedRemoteAndClone('fetch')

  try {
    execFileSync('git', [
      '-C',
      remoteDir,
      '-c',
      'user.email=hermes@localhost',
      '-c',
      'user.name=Hermes',
      'commit',
      '--allow-empty',
      '-m',
      'remote work'
    ])

    await gitFetch(cloneDir, 'origin', 'git')

    assert.equal(
      execFileSync('git', ['-C', cloneDir, 'rev-parse', 'origin/main']).toString().trim(),
      remoteHead(remoteDir)
    )
  } finally {
    fs.rmSync(cloneDir, { recursive: true, force: true })
    fs.rmSync(remoteDir, { recursive: true, force: true })
  }
}, 30_000)

test('gitPull: fast-forwards the local branch', async () => {
  const { cloneDir, remoteDir } = seedRemoteAndClone('pull')

  try {
    execFileSync('git', [
      '-C',
      remoteDir,
      '-c',
      'user.email=hermes@localhost',
      '-c',
      'user.name=Hermes',
      'commit',
      '--allow-empty',
      '-m',
      'remote work'
    ])

    await gitPull(cloneDir, false, 'git')

    assert.equal(execFileSync('git', ['-C', cloneDir, 'rev-parse', 'HEAD']).toString().trim(), remoteHead(remoteDir))
  } finally {
    fs.rmSync(cloneDir, { recursive: true, force: true })
    fs.rmSync(remoteDir, { recursive: true, force: true })
  }
}, 30_000)

test('gitPull: rejects when no upstream is configured', async () => {
  const dir = makeRepo()

  await assert.rejects(gitPull(dir, false, 'git'))
})
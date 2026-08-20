import assert from 'node:assert/strict'
import fs from 'node:fs'

import { test } from 'vitest'

const source = fs.readFileSync(new URL('./git-ipc.ts', import.meta.url), 'utf8')
const preload = fs.readFileSync(new URL('./preload.ts', import.meta.url), 'utf8')

const scmChannels = [
  'hermes:git:tagList',
  'hermes:git:stashList',
  'hermes:git:branchCreate',
  'hermes:git:branchRename',
  'hermes:git:branchDelete',
  'hermes:git:tagCreate',
  'hermes:git:tagDelete',
  'hermes:git:stashCreate',
  'hermes:git:stashApply',
  'hermes:git:stashDrop',
  'hermes:git:fetch',
  'hermes:git:pull',
  'hermes:git:review:history',
  'hermes:git:review:historyDiff'
] as const

test('native SCM Git IPC handlers and preload channels stay connected', () => {
  for (const channel of scmChannels) {
    assert.match(
      source,
      new RegExp(`ipcMain\\.handle\\('${channel.replaceAll(':', '\\:')}'`),
      `${channel} must be registered`
    )
    assert.match(
      preload,
      new RegExp(
        `hermes:git:${channel.includes('review:') ? channel.slice('hermes:git:'.length) : channel.slice('hermes:git:'.length)}`
      ),
      `${channel} must be exposed by preload`
    )
  }
})

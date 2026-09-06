import assert from 'node:assert/strict'

import { test } from 'vitest'

import { stopBackendChild, stopBackendTreesForUpdate } from './backend-child'
import { hiddenWindowsChildOptions } from './windows-child-options'

test('hiddenWindowsChildOptions adds windowsHide:true on Windows when unset', () => {
  assert.deepEqual(hiddenWindowsChildOptions({}, true), { windowsHide: true })
})

test('hiddenWindowsChildOptions preserves an existing windowsHide:false on Windows', () => {
  assert.deepEqual(hiddenWindowsChildOptions({ windowsHide: false }, true), { windowsHide: false })
})

test('hiddenWindowsChildOptions preserves an existing windowsHide:true on Windows', () => {
  assert.deepEqual(hiddenWindowsChildOptions({ windowsHide: true }, true), { windowsHide: true })
})

test('hiddenWindowsChildOptions leaves options unchanged off Windows', () => {
  assert.deepEqual(hiddenWindowsChildOptions({}, false), {})
  assert.deepEqual(hiddenWindowsChildOptions({ stdio: 'ignore' }, false), { stdio: 'ignore' })
})

test('hiddenWindowsChildOptions merges windowsHide alongside other options on Windows', () => {
  assert.deepEqual(hiddenWindowsChildOptions({ encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }, true), {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore'],
    windowsHide: true
  })
})

test('hiddenWindowsChildOptions defaults isWindows from process.platform when omitted', () => {
  const result = hiddenWindowsChildOptions({})
  const expectedHide = process.platform === 'win32'

  assert.equal(Boolean(result.windowsHide), expectedHide)
})

function makeChild(overrides: Partial<{ pid: number | null; killed: boolean }> = {}) {
  const calls: string[] = []

  return {
    calls,
    child: {
      kill: (signal: string) => {
        calls.push(signal)
      },
      killed: overrides.killed ?? false,
      pid: 'pid' in overrides ? overrides.pid : 1234
    }
  }
}

test('stopBackendChild uses the retained ChildProcess handle on Windows', () => {
  const { child, calls } = makeChild({ pid: 4242 })

  stopBackendChild(child, { isWindows: true })

  assert.deepEqual(calls, ['SIGTERM'])
})

test('stopBackendChild group-SIGTERMs on POSIX (negative pgid) when the child has a pid', () => {
  const { child, calls } = makeChild({ pid: 4242 })
  const groupKills: Array<[number, string]> = []

  stopBackendChild(child, {
    isWindows: false,
    killGroup: (pgid, signal) => groupKills.push([pgid, signal])
  })

  assert.deepEqual(groupKills, [[-4242, 'SIGTERM']], 'must signal the whole process group')
  assert.deepEqual(calls, [], 'direct child.kill must not run when the group send succeeds')
})

test('stopBackendChild falls back to direct SIGTERM on POSIX when the group send throws', () => {
  const { child, calls } = makeChild({ pid: 4242 })

  stopBackendChild(child, {
    isWindows: false,
    killGroup: () => {
      throw new Error('ESRCH: no such process group')
    }
  })

  assert.deepEqual(calls, ['SIGTERM'], 'must fall back to signalling the direct child')
})

test('stopBackendChild uses the retained handle on Windows without a numeric pid', () => {
  const { child, calls } = makeChild({ pid: null })

  stopBackendChild(child, { isWindows: true })

  assert.deepEqual(calls, ['SIGTERM'])
})

test('stopBackendChild is a no-op for an already-killed child', () => {
  const { child, calls } = makeChild({ killed: true })

  stopBackendChild(child, { isWindows: true })

  assert.deepEqual(calls, [])
})

test('stopBackendChild is a no-op for a null/undefined child', () => {
  assert.doesNotThrow(() => {
    stopBackendChild(null, { isWindows: true })
    stopBackendChild(undefined, { isWindows: true })
  })
})

test('stopBackendChild swallows errors thrown by the kill strategy', () => {
  const child = {
    kill: () => {
      throw new Error('ESRCH: no such process')
    },
    killed: false,
    pid: 99
  }

  assert.doesNotThrow(() => {
    stopBackendChild(child, {
      isWindows: false
    })
  })
})

test('Windows update stops captured roots through retained handles', () => {
  const primary = makeChild({ pid: 101 })
  const pooled = makeChild({ pid: 202 })
  const events: string[] = []

  stopBackendTreesForUpdate(primary.child, {
    stopAllPoolBackends: () => {
      events.push('pool-stop')
      pooled.child.kill('SIGTERM')
    }
  })

  assert.deepEqual(events, ['pool-stop'])
  assert.deepEqual(primary.calls, ['SIGTERM'])
  assert.deepEqual(pooled.calls, ['SIGTERM'])
})

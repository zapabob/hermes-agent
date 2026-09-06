import { describe, expect, it, vi } from 'vitest'

import { installPersonalSessionRequestGuard, type GuardableSession } from './personal-session-request-guard'

type Listener = Parameters<GuardableSession['webRequest']['onBeforeRequest']>[0]

function harness() {
  let listener: Listener | undefined
  const onBeforeRequest = vi.fn((next: Listener) => {
    listener = next
  })
  const target = { webRequest: { onBeforeRequest } }

  installPersonalSessionRequestGuard(target)

  return {
    decide(url: string, resourceType: string) {
      const callback = vi.fn()
      listener?.({ url, resourceType }, callback)

      return callback
    },
    onBeforeRequest,
    target
  }
}

describe('installPersonalSessionRequestGuard', () => {
  it.each(['mainFrame', 'subFrame', 'xmlhttprequest', 'script', 'image', 'serviceWorker'])(
    'cancels X and YouTube %s requests before transport',
    resourceType => {
      const { decide } = harness()

      expect(decide('https://accounts.youtube.com/session', resourceType)).toHaveBeenCalledWith({ cancel: true })
      expect(decide('https://api.x.com/redirect-target', resourceType)).toHaveBeenCalledWith({ cancel: true })
    }
  )

  it('cancels WebSocket handshakes for personal-session hosts', () => {
    const { decide } = harness()

    expect(decide('wss://stream.x.com/socket', 'webSocket')).toHaveBeenCalledWith({ cancel: true })
    expect(decide('ws://music.youtube.com/socket', 'webSocket')).toHaveBeenCalledWith({ cancel: true })
  })

  it('allows unrelated destinations and rejects a redirected personal destination on its next request', () => {
    const { decide } = harness()

    expect(decide('https://example.com/start', 'mainFrame')).toHaveBeenCalledWith({ cancel: false })
    expect(decide('https://youtu.be/redirected', 'mainFrame')).toHaveBeenCalledWith({ cancel: true })
  })

  it('installs only once per session', () => {
    const { onBeforeRequest, target } = harness()

    installPersonalSessionRequestGuard(target)

    expect(onBeforeRequest).toHaveBeenCalledTimes(1)
  })
})

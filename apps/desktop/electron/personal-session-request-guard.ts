import { isPersonalSessionTransportUrl } from '../../shared/src/personal-session-url'

interface RequestDetails {
  resourceType?: string
  url: string
}

interface RequestDecision {
  cancel: boolean
}

interface GuardableWebRequest {
  onBeforeRequest(
    listener: (details: RequestDetails, callback: (decision: RequestDecision) => void) => void
  ): void
}

export interface GuardableSession {
  webRequest: GuardableWebRequest
}

const guardedSessions = new WeakSet<object>()

/**
 * Keep personal-session services out of every app-owned request path. This is
 * deliberately transport-level: top-level navigation events do not observe
 * subframes, scripts, images, fetch/XHR, service workers, or redirect targets.
 */
export function installPersonalSessionRequestGuard(target: GuardableSession): void {
  if (guardedSessions.has(target)) {
    return
  }

  target.webRequest.onBeforeRequest((details, callback) => {
    callback({ cancel: isPersonalSessionTransportUrl(details.url) })
  })
  guardedSessions.add(target)
}

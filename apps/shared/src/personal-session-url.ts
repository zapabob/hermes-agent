const PERSONAL_SESSION_HOSTS = new Set(['twitter.com', 'x.com', 'youtu.be', 'youtube.com'])
const PERSONAL_NAVIGATION_PROTOCOLS = new Set(['http:', 'https:'])
const PERSONAL_TRANSPORT_PROTOCOLS = new Set(['http:', 'https:', 'ws:', 'wss:'])

function hasPersonalSessionHost(raw: string, protocols: ReadonlySet<string>): boolean {
  try {
    const url = new URL(raw)

    if (!protocols.has(url.protocol)) {
      return false
    }

    const hostname = url.hostname.toLowerCase().replace(/\.$/, '')

    return [...PERSONAL_SESSION_HOSTS].some(host => hostname === host || hostname.endsWith(`.${host}`))
  } catch {
    return false
  }
}

/**
 * These services must use the operator's existing OS-browser session. Hermes
 * may present the link, but must not preview, embed, title-fetch, or automate
 * the destination in an app-owned browser surface.
 */
export function isPersonalSessionUrl(raw: string | null | undefined): boolean {
  if (!raw) {
    return false
  }

  return hasPersonalSessionHost(raw, PERSONAL_NAVIGATION_PROTOCOLS)
}

/** Match every Chromium network scheme that can carry an app-owned session. */
export function isPersonalSessionTransportUrl(raw: string | null | undefined): boolean {
  if (!raw) {
    return false
  }

  return hasPersonalSessionHost(raw, PERSONAL_TRANSPORT_PROTOCOLS)
}

const STARTUP_URL_RULES = [
  {
    env: 'HERMES_DESKTOP_STARTUP_X_URL',
    hosts: new Set(['twitter.com', 'x.com'])
  },
  {
    env: 'HERMES_DESKTOP_STARTUP_YOUTUBE_URL',
    hosts: new Set(['youtu.be', 'youtube.com'])
  }
] as const

function matchesHost(hostname: string, allowed: ReadonlySet<string>): boolean {
  const normalized = hostname.toLowerCase().replace(/\.$/, '')

  return [...allowed].some(host => normalized === host || normalized.endsWith(`.${host}`))
}

/**
 * Read optional, operator-owned startup URLs without shipping an account or
 * destination in the public build. Invalid or cross-service values are
 * ignored; the caller opens returned URLs through the OS default browser.
 */
export function configuredStartupExternalUrls(env: NodeJS.ProcessEnv): string[] {
  const urls: string[] = []

  for (const rule of STARTUP_URL_RULES) {
    const raw = String(env[rule.env] || '').trim()

    if (!raw) {
      continue
    }

    try {
      const parsed = new URL(raw)

      if (!['http:', 'https:'].includes(parsed.protocol) || !matchesHost(parsed.hostname, rule.hosts)) {
        continue
      }

      urls.push(parsed.href)
    } catch {
      // A malformed optional value must never delay Desktop startup.
    }
  }

  return [...new Set(urls)]
}

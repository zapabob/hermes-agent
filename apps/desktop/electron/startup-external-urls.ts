import fs from 'node:fs'
import path from 'node:path'

import { parse } from 'yaml'

const PROFILE_NAME_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/

const STARTUP_URL_RULES = [
  {
    key: 'x',
    hosts: new Set(['twitter.com', 'x.com'])
  },
  {
    key: 'youtube',
    hosts: new Set(['youtu.be', 'youtube.com'])
  }
] as const

function matchesHost(hostname: string, allowed: ReadonlySet<string>): boolean {
  const normalized = hostname.toLowerCase().replace(/\.$/, '')

  return [...allowed].some(host => normalized === host || normalized.endsWith(`.${host}`))
}

/**
 * Read optional, operator-owned startup URLs from profile-scoped config.yaml
 * without shipping an account or destination in the public build. Invalid or
 * cross-service values are ignored; the caller opens returned URLs through
 * the OS default browser.
 */
export function configuredStartupExternalUrls(config: unknown): string[] {
  if (!config || typeof config !== 'object') {
    return []
  }

  const desktop = (config as Record<string, unknown>).desktop

  if (!desktop || typeof desktop !== 'object') {
    return []
  }

  const configured = (desktop as Record<string, unknown>).startup_external_urls

  if (!configured || typeof configured !== 'object') {
    return []
  }

  const urls: string[] = []

  for (const rule of STARTUP_URL_RULES) {
    const value = (configured as Record<string, unknown>)[rule.key]
    const raw = typeof value === 'string' ? value.trim() : ''

    if (!raw) {
      continue
    }

    try {
      const parsed = new URL(raw)

      if (
        parsed.protocol !== 'https:' ||
        parsed.username ||
        parsed.password ||
        !matchesHost(parsed.hostname, rule.hosts)
      ) {
        continue
      }

      urls.push(parsed.href)
    } catch {
      // A malformed optional value must never delay Desktop startup.
    }
  }

  return [...new Set(urls)]
}

export function configuredStartupExternalUrlsFromYaml(rawConfig: string): string[] {
  try {
    return configuredStartupExternalUrls(parse(rawConfig))
  } catch {
    return []
  }
}

export function startupExternalUrlsConfigPath(hermesHome: string, activeProfile: string | null): string {
  let profile = String(activeProfile || '').trim()

  // Match the backend's profile authority: an explicit Desktop choice wins;
  // only an unset choice follows the CLI's sticky active_profile file.
  if (!profile) {
    try {
      const stickyProfile = fs.readFileSync(path.join(hermesHome, 'active_profile'), 'utf8').trim()

      if (stickyProfile === 'default' || PROFILE_NAME_RE.test(stickyProfile)) {
        profile = stickyProfile
      }
    } catch {
      // Missing or unreadable sticky state means the root/default profile.
    }
  }

  if (profile !== 'default' && !PROFILE_NAME_RE.test(profile)) {
    profile = 'default'
  }

  const profileHome = profile && profile !== 'default' ? path.join(hermesHome, 'profiles', profile) : hermesHome

  return path.join(profileHome, 'config.yaml')
}

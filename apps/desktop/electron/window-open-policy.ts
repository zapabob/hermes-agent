export interface WindowOpenRequestLike {
  url: string
}

export interface WindowOpenDecision {
  action: 'deny'
}

export function describeDeniedUrl(url: string): string {
  try {
    const parsed = new URL(url)

    return parsed.origin === 'null' ? parsed.protocol : parsed.origin
  } catch {
    return '<unparseable>'
  }
}

export function createWindowOpenHandler(
  onDenied?: (origin: string) => void
): (details: WindowOpenRequestLike) => WindowOpenDecision {
  return details => {
    try {
      onDenied?.(describeDeniedUrl(details.url))
    } catch {
      // A logging failure must never weaken the deny decision.
    }

    return { action: 'deny' }
  }
}

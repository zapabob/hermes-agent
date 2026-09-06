import { describe, expect, it } from 'vitest'

import { resolveDeepLinkAction } from './deeplink-routes'

describe('resolveDeepLinkAction', () => {
  it('routes unified plugin install deeplinks', () => {
    expect(
      resolveDeepLinkAction({
        kind: 'plugin',
        name: 'install',
        params: { repo: 'owner/repo', enable: '0', force: '1' }
      })
    ).toEqual({
      type: 'plugin-install',
      repo: 'owner/repo',
      enable: false,
      force: true,
      legacyHint: null
    })
  })

  it('routes legacy plugin-agent alias', () => {
    expect(
      resolveDeepLinkAction({
        kind: 'plugin-agent',
        name: '',
        params: { repo: 'owner/repo' }
      })
    ).toMatchObject({ type: 'plugin-install', legacyHint: 'agent' })
  })

  it('routes blueprint composer inserts', () => {
    expect(
      resolveDeepLinkAction({
        kind: 'blueprint',
        name: 'morning-brief',
        params: { time: '08:00' }
      })
    ).toEqual({
      type: 'composer-blueprint',
      name: 'morning-brief',
      params: { time: '08:00' }
    })
  })

  it('routes open/browser into the in-app Browser pane', () => {
    expect(
      resolveDeepLinkAction({
        kind: 'open',
        name: 'browser',
        params: { url: 'https://example.com/' }
      })
    ).toEqual({ type: 'open-browser', url: 'https://example.com/' })
  })

  it('consumes invalid open/browser urls without falling through', () => {
    expect(
      resolveDeepLinkAction({
        kind: 'open',
        name: 'browser',
        params: { url: 'file:///C:/Secrets.txt' }
      })
    ).toEqual({ type: 'handled' })
  })
})

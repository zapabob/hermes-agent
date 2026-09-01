import { beforeEach, describe, expect, it, vi } from 'vitest'

import { dismissNotification, notify } from '@/store/notifications'

// The store wires itself to gateway/profile atoms and the REST layer at import
// time paths; mock the seams (same shape as updates.test.ts) so this test only
// exercises the pure transition state machine.
vi.mock('@/hermes', () => ({
  getHermesConfigRecord: vi.fn(),
  testMcpServer: vi.fn()
}))

vi.mock('@/i18n', () => ({
  translateNow: (key: string) => key
}))

vi.mock('@/store/notifications', () => ({
  dismissNotification: vi.fn(),
  notify: vi.fn()
}))

vi.mock('@/store/profile', () => ({
  $activeGatewayProfile: { get: () => 'default', listen: () => () => {} },
  normalizeProfileKey: (name: string | null | undefined) => (name ?? '').trim() || 'default'
}))

vi.mock('@/store/session', () => ({
  $gatewayState: { get: () => 'closed', subscribe: () => () => {} }
}))

const { MCP_HEALTH_STATUS_STORAGE_KEY, recordMcpHealthResult, shouldNotifyOnTransition } = await import('./mcp-health')

type Status = 'error' | 'needs-auth' | 'ok'

describe('shouldNotifyOnTransition', () => {
  // The full previous × next decision table: notify only on a TRANSITION into
  // a bad state. Rechecks of an already-bad server stay quiet; ok never nudges.
  it.each<[previous: Status | null, next: Status, notify: boolean]>([
    // First observation of the session (previous unknown).
    [null, 'ok', false],
    [null, 'needs-auth', true],
    [null, 'error', true],
    // Healthy server stays healthy / breaks.
    ['ok', 'ok', false],
    ['ok', 'needs-auth', true],
    ['ok', 'error', true],
    // Already-broken server: rechecks must NOT re-notify…
    ['needs-auth', 'needs-auth', false],
    ['error', 'error', false],
    // …but flipping from one bad state to the other is a new transition.
    ['needs-auth', 'error', true],
    ['error', 'needs-auth', true],
    // Recovery is silent.
    ['needs-auth', 'ok', false],
    ['error', 'ok', false]
  ])('previous=%s next=%s → notify=%s', (previous, next, expected) => {
    expect(shouldNotifyOnTransition(previous, next)).toBe(expected)
  })
})

describe('recordMcpHealthResult', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.mocked(dismissNotification).mockClear()
    vi.mocked(notify).mockClear()
  })

  it('does not repeat an unchanged warning after an app restart', () => {
    window.localStorage.setItem(
      MCP_HEALTH_STATUS_STORAGE_KEY,
      JSON.stringify({ 'default::stripe-persisted': 'needs-auth' })
    )

    recordMcpHealthResult('default', 'stripe-persisted', 'needs-auth')

    expect(notify).not.toHaveBeenCalled()
  })

  it('dismisses a warning on recovery and notifies if authentication later expires again', () => {
    window.localStorage.setItem(
      MCP_HEALTH_STATUS_STORAGE_KEY,
      JSON.stringify({ 'default::stripe-recovery': 'needs-auth' })
    )

    recordMcpHealthResult('default', 'stripe-recovery', 'ok')

    expect(dismissNotification).toHaveBeenCalledWith('mcp-health-default::stripe-recovery')

    recordMcpHealthResult('default', 'stripe-recovery', 'needs-auth')

    expect(notify).toHaveBeenCalledTimes(1)
  })
})

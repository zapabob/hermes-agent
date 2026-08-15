import { afterEach, describe, expect, it, vi } from 'vitest'

import { gatewayScope, setPrimaryGateway } from './gateway'
import { $mcpSetupRequests, setMcpSetupRequest, skipMcpSetupRequest } from './mcp-setup'

afterEach(() => {
  $mcpSetupRequests.set({})
  setPrimaryGateway(null)
  vi.clearAllMocks()
})

describe('skipMcpSetupRequest', () => {
  it('declines through the exact source gateway', async () => {
    const request = vi.fn().mockResolvedValue({ ok: true })
    setPrimaryGateway({ connectionState: 'open', request } as never, 'source-profile', 'connection-a')
    setMcpSetupRequest({
      action: 'install',
      reason: 'needed for this task',
      requestId: 'mcp-1',
      scope: gatewayScope('connection-a', 'source-profile'),
      server: 'example',
      sessionId: 'session-1'
    })

    await expect(skipMcpSetupRequest('session-1')).resolves.toBe(true)
    expect(request).toHaveBeenCalledWith('mcp.setup.respond', {
      request_id: 'mcp-1',
      result: JSON.stringify({ server: 'example', status: 'declined' })
    })
  })

  it('does not fall back to a newly active different gateway', async () => {
    const sourceRequest = vi.fn().mockResolvedValue({ ok: true })
    const otherRequest = vi.fn().mockResolvedValue({ ok: true })
    setPrimaryGateway({ connectionState: 'open', request: sourceRequest } as never, 'source-profile', 'connection-a')
    setMcpSetupRequest({
      action: 'enable',
      reason: 'needed for this task',
      requestId: 'mcp-1',
      scope: gatewayScope('connection-a', 'source-profile'),
      server: 'example',
      sessionId: 'session-1'
    })
    setPrimaryGateway({ connectionState: 'open', request: otherRequest } as never, 'other-profile', 'connection-b')

    await expect(skipMcpSetupRequest('session-1')).resolves.toBe(true)
    expect(sourceRequest).not.toHaveBeenCalled()
    expect(otherRequest).not.toHaveBeenCalled()
  })
})

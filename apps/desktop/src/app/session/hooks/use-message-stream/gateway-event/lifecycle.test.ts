import { beforeEach, describe, expect, it } from 'vitest'

import { gatewayScope } from '@/store/gateway'
import { $pendingSkinApply, __resetBackendSkinSync } from '@/themes/backend-sync'
import { skinPref } from '@/themes/context'

import { handleLifecycleEvent } from './lifecycle'
import type { GatewayEventContext } from './types'

const skin = {
  background_image: 'C:/Users/example/.hermes/skins/twilight.png',
  colors: { background: '#101020', ui_accent: '#ff33aa' },
  name: 'twilight-hakua'
}

function readyContext(active: boolean): GatewayEventContext {
  return {
    deps: { activeGatewayProfile: 'default' },
    event: { profile: 'default', type: 'gateway.ready' },
    fromActiveSource: () => active,
    payload: { skin },
    sourceScope: gatewayScope('desktop', 'default')
  } as GatewayEventContext
}

describe('gateway.ready skin adoption', () => {
  beforeEach(() => {
    window.localStorage.clear()
    __resetBackendSkinSync()
  })

  it('applies the configured backend wallpaper on a fresh Desktop profile', () => {
    expect(handleLifecycleEvent(readyContext(true))).toBe(true)
    expect($pendingSkinApply.get()).toBe('twilight-hakua')
  })

  it('preserves a stored Desktop appearance on reconnect', () => {
    skinPref.assign('default', 'ember')

    expect(handleLifecycleEvent(readyContext(true))).toBe(true)
    expect($pendingSkinApply.get()).toBeNull()
  })

  it('does not repaint from an inactive gateway source', () => {
    expect(handleLifecycleEvent(readyContext(false))).toBe(true)
    expect($pendingSkinApply.get()).toBeNull()
  })
})

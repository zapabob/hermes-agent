import assert from 'node:assert/strict'
import path from 'node:path'

import { test } from 'vitest'

import { configuredStartupExternalUrlsFromYaml, startupExternalUrlsConfigPath } from './startup-external-urls'

test('public build opens no personal service when profile settings are absent', () => {
  assert.deepEqual(configuredStartupExternalUrlsFromYaml('desktop: {}'), [])
})

test('configured X and YouTube URLs are returned for the OS default browser', () => {
  assert.deepEqual(
    configuredStartupExternalUrlsFromYaml(`
desktop:
  startup_external_urls:
    x: https://x.com/home
    youtube: https://www.youtube.com/feed/subscriptions
`),
    ['https://x.com/home', 'https://www.youtube.com/feed/subscriptions']
  )
})

test('startup settings reject malformed, executable, and cross-service values', () => {
  assert.deepEqual(
    configuredStartupExternalUrlsFromYaml(`
desktop:
  startup_external_urls:
    x: javascript:alert(1)
    youtube: https://x.com/not-youtube
`),
    []
  )
})

test('startup settings reject plaintext transport and URL credentials', () => {
  assert.deepEqual(
    configuredStartupExternalUrlsFromYaml(`
desktop:
  startup_external_urls:
    x: http://x.com/home
    youtube: https://owner:secret@youtube.com/feed/subscriptions
`),
    []
  )
})

test('service subdomains and trailing-dot hosts remain valid', () => {
  assert.deepEqual(
    configuredStartupExternalUrlsFromYaml(`
desktop:
  startup_external_urls:
    x: https://mobile.twitter.com./home
    youtube: https://music.youtube.com./
`),
    ['https://mobile.twitter.com./home', 'https://music.youtube.com./']
  )
})

test('malformed YAML fails closed without delaying Desktop startup', () => {
  assert.deepEqual(configuredStartupExternalUrlsFromYaml('desktop: [not closed'), [])
})

test('config path follows the active Desktop profile', () => {
  const hermesHome = path.join('home', 'owner', '.hermes')

  assert.equal(startupExternalUrlsConfigPath(hermesHome, null), path.join(hermesHome, 'config.yaml'))
  assert.equal(startupExternalUrlsConfigPath(hermesHome, 'default'), path.join(hermesHome, 'config.yaml'))
  assert.equal(
    startupExternalUrlsConfigPath(hermesHome, 'work'),
    path.join(hermesHome, 'profiles', 'work', 'config.yaml')
  )
})

import assert from 'node:assert/strict'

import { test } from 'vitest'

import { configuredStartupExternalUrls } from './startup-external-urls'

test('public build opens no personal service when startup variables are absent', () => {
  assert.deepEqual(configuredStartupExternalUrls({}), [])
})

test('configured X and YouTube URLs are returned for the OS default browser', () => {
  assert.deepEqual(
    configuredStartupExternalUrls({
      HERMES_DESKTOP_STARTUP_X_URL: 'https://x.com/home',
      HERMES_DESKTOP_STARTUP_YOUTUBE_URL: 'https://www.youtube.com/feed/subscriptions'
    }),
    ['https://x.com/home', 'https://www.youtube.com/feed/subscriptions']
  )
})

test('startup variables reject malformed, executable, and cross-service values', () => {
  assert.deepEqual(
    configuredStartupExternalUrls({
      HERMES_DESKTOP_STARTUP_X_URL: 'javascript:alert(1)',
      HERMES_DESKTOP_STARTUP_YOUTUBE_URL: 'https://x.com/not-youtube'
    }),
    []
  )
})

test('service subdomains and trailing-dot hosts remain valid', () => {
  assert.deepEqual(
    configuredStartupExternalUrls({
      HERMES_DESKTOP_STARTUP_X_URL: 'https://mobile.twitter.com./home',
      HERMES_DESKTOP_STARTUP_YOUTUBE_URL: 'https://music.youtube.com./'
    }),
    ['https://mobile.twitter.com./home', 'https://music.youtube.com./']
  )
})

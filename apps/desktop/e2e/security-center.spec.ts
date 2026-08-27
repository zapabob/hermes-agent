import * as path from 'node:path'

import type { MockBackendFixture } from './fixtures'
import { setupMockBackend, waitForAppReady } from './fixtures'
import { collectErrorBanners, expect, test } from './test'

let fixture: MockBackendFixture | null = null

test.beforeAll(async () => {
  fixture = await setupMockBackend()
  await waitForAppReady(fixture, 120_000)
})

test.afterAll(async () => {
  await fixture?.cleanup()
})

test('renders exact local scanner evidence without overstating protection', async () => {
  const page = fixture!.page
  await expect(page.getByRole('button', { name: 'Gateway ready' })).toBeVisible({ timeout: 120_000 })
  await page.getByRole('button', { name: 'Security Center' }).click()
  const heading = page.getByRole('heading', { name: 'Security Center', level: 1 })
  await expect(heading).toBeVisible()
  await expect(page.getByText('Needs attention').first()).toBeVisible()
  await expect(page.getByText('scanner_unavailable')).toBeVisible()
  await expect(page.getByText('windows_dpapi')).toBeVisible()
  await expect(page.getByText('Active feed status')).toBeVisible()
  const summary = page.getByRole('heading', { name: 'Security summary' })
  await expect(summary).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Encrypted quarantine' })).toBeVisible()
  expect(await collectErrorBanners(page)).toEqual([])
  await heading.locator('xpath=ancestor::section[1]').screenshot({
    path: path.resolve(import.meta.dirname, '..', '..', '..', '.tmp', 'security-center-manual-qa.png')
  })
})

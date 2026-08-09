import { execFileSync } from 'node:child_process'
import * as fs from 'node:fs'
import * as path from 'node:path'

import {
  buildAppEnv,
  createSandbox,
  launchDesktop,
  type MockBackendFixture,
  waitForAppReady,
  writeEnvFile,
  writeMockProviderConfig
} from './fixtures'
import { startMockServer } from './mock-server'
import { expect, test } from './test'
import { expectVisualSnapshot } from './visual-snapshot'

function createHistoryRepo(root: string): string {
  const repo = path.join(root, 'history-repo')

  fs.mkdirSync(repo, { recursive: true })
  execFileSync('git', ['init', '--initial-branch=main'], { cwd: repo })
  execFileSync('git', ['config', 'user.email', 'e2e@example.com'], { cwd: repo })
  execFileSync('git', ['config', 'user.name', 'Hermes E2E'], { cwd: repo })
  fs.writeFileSync(path.join(repo, 'history.txt'), 'first\n', 'utf8')
  execFileSync('git', ['add', 'history.txt'], { cwd: repo })
  execFileSync('git', ['commit', '-m', 'initial history'], { cwd: repo })
  fs.writeFileSync(path.join(repo, 'history.txt'), 'first\nsecond\n', 'utf8')
  execFileSync('git', ['add', 'history.txt'], { cwd: repo })
  execFileSync('git', ['commit', '-m', 'add second history line'], { cwd: repo })

  return repo
}

function configureRepoCwd(hermesHome: string, mockUrl: string, repo: string): void {
  writeMockProviderConfig(hermesHome, mockUrl)
  fs.appendFileSync(path.join(hermesHome, 'config.yaml'), `\nterminal:\n  cwd: ${repo}\n`, 'utf8')
  writeEnvFile(hermesHome)
}

let fixture: MockBackendFixture | null = null

test.beforeAll(async () => {
  const sandbox = createSandbox('git-history')
  const repo = createHistoryRepo(sandbox.root)
  const mock = await startMockServer()

  configureRepoCwd(sandbox.hermesHome, mock.url, repo)

  const { app, page } = await launchDesktop(buildAppEnv(sandbox))
  fixture = {
    app,
    page,
    mock,
    mockUrl: mock.url,
    sandbox,
    cleanup: async () => {
      await app.close().catch(() => undefined)
      await mock.close()
      sandbox.cleanup()
    }
  }

  await waitForAppReady(fixture, 120_000)

  const composer = page.locator('[contenteditable="true"]').first()
  await composer.click()
  await composer.type('open a repository-backed history session', { delay: 2 })
  await page.keyboard.press('Enter')
  await page.waitForFunction(
    prompt => (document.querySelector('[data-slot="aui_thread-viewport"]')?.textContent ?? '').includes(prompt),
    'open a repository-backed history session',
    { timeout: 15_000 }
  )
  await expect(page.locator('.coding-status-bar')).toContainText('main')
})

test.afterAll(async () => {
  await fixture?.cleanup()
  fixture = null
})

test('review history lists commits, opens a selected diff, and renders for visual review', async () => {
  const page = fixture!.page

  await page.keyboard.press('Control+g')
  await expect(page.getByRole('button', { name: 'History' })).toBeVisible()
  await page.getByRole('button', { name: 'History' }).click()
  await expect(page.getByText('add second history line')).toBeVisible({ timeout: 15_000 })

  await page.getByRole('button', { name: /add second history line/i }).click()
  await expect(page.locator('[data-slot="file-diff-panel"]')).toContainText('second')
  await expectVisualSnapshot(page, { app: fixture!.app, name: 'review-history-selected-commit' })
})

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import type { HermesGitCommit } from '@/global'
import { I18nProvider } from '@/i18n'
import {
  $reviewHistory,
  $reviewHistoryDiff,
  $reviewHistoryDiffLoading,
  $reviewHistoryLoading,
  $reviewSelectedCommit
} from '@/store/review'

import { ReviewHistory } from './history'

const commit: HermesGitCommit = {
  author: 'Hermes Test',
  authoredAt: '2026-08-10T12:00:00+00:00',
  parents: ['0123456789abcdef0123456789abcdef01234567'],
  sha: '1234567890abcdef1234567890abcdef12345678',
  shortSha: '1234567',
  subject: 'add history view'
}

function renderHistory() {
  return render(
    <I18nProvider configClient={null} initialLocale="en">
      <ReviewHistory />
    </I18nProvider>
  )
}

describe('ReviewHistory', () => {
  beforeEach(() => {
    $reviewHistory.set([])
    $reviewHistoryDiff.set(null)
    $reviewHistoryDiffLoading.set(false)
    $reviewHistoryLoading.set(false)
    $reviewSelectedCommit.set(null)
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the history empty state', () => {
    renderHistory()

    expect(screen.getByText('No commits')).toBeTruthy()
  })

  it('renders compact commit metadata and selects a commit on click', () => {
    $reviewHistory.set([commit])
    renderHistory()

    const row = screen.getByRole('button', { name: /add history view/i })
    expect(row.textContent).toContain('1234567')
    expect(row.textContent).toContain('Hermes Test')

    fireEvent.click(row)

    expect($reviewSelectedCommit.get()).toBe(commit.sha)
    expect(row.getAttribute('aria-current')).toBe('true')
  })

  it('renders the selected commit diff pane and supports closing it', () => {
    $reviewHistory.set([commit])
    $reviewSelectedCommit.set(commit.sha)
    $reviewHistoryDiff.set('diff --git a/history.txt b/history.txt\n+second')
    renderHistory()

    expect(screen.getAllByText('add history view').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))

    expect($reviewSelectedCommit.get()).toBeNull()
  })
})

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { I18nProvider } from '@/i18n'
import { $reviewFiles, $reviewLoading, $reviewOpen } from '@/store/review'

import { ReviewPane } from './index'

describe('ReviewPane', () => {
  beforeEach(() => {
    $reviewOpen.set(true)
    $reviewFiles.set([])
    $reviewLoading.set(false)
  })

  afterEach(() => {
    cleanup()
  })

  it('renders without crashing when empty', () => {
    render(
      <I18nProvider configClient={null} initialLocale="en">
        <ReviewPane />
      </I18nProvider>
    )

    expect(screen.getByText('No diffs')).toBeTruthy()
  })

  it('renders loading skeleton without crashing', () => {
    $reviewLoading.set(true)
    render(
      <I18nProvider configClient={null} initialLocale="en">
        <ReviewPane />
      </I18nProvider>
    )
  })
})

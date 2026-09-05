/** One interpretation of browser.use_real_profile shared by settings and the
 * first-open Browser consent surface. */
export function readUseRealProfile(record: Record<string, unknown> | undefined): boolean {
  const browser = record?.browser

  return Boolean(
    browser &&
    typeof browser === 'object' &&
    !Array.isArray(browser) &&
    (browser as Record<string, unknown>).use_real_profile === true
  )
}

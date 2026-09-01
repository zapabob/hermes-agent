import { storedString, storedStringRecord } from '@/lib/storage'

export const SKIN_KEY = 'hermes-desktop-theme-v2'
export const MODE_KEY = 'hermes-desktop-mode-v1'
export const PROFILE_SKINS_KEY = 'hermes-desktop-profile-themes-v1'
export const PROFILE_MODES_KEY = 'hermes-desktop-profile-modes-v1'
export const LAST_PROFILE_KEY = 'hermes-desktop-active-profile-v1'

export function hasStoredSkinPreference(profile: string): boolean {
  if (profile === 'default') {
    return storedString(SKIN_KEY) !== null
  }

  const profileSkins = storedStringRecord(PROFILE_SKINS_KEY)

  return Object.prototype.hasOwnProperty.call(profileSkins, profile) || storedString(SKIN_KEY) !== null
}

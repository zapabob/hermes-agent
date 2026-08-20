import { type PluginLocaleBundles } from '@hermes/plugin-sdk'

export const ACCENT_LOCALES: PluginLocaleBundles = {
  en: {
    reset: 'Reset',
    triggerLabel: 'Accent color',
    swatches: {
      nousLight: 'Nous blue (light seed)',
      nousDark: 'Nous blue (dark seed)',
      psyche: 'Psyche blue',
      githubBlue: 'GitHub blue',
      githubGreen: 'GitHub green',
      githubPurple: 'GitHub purple',
      githubPink: 'GitHub pink',
      githubOrange: 'GitHub orange'
    },
    readout: (h: string, l: string, c: string) => `H${h} L${l} C${c}`,
    contrast: (mode: string, ratio: string) => `${mode} ${ratio}:1`,
    mode: { light: 'light', dark: 'dark' },
    picked: (override: string, painted: string) => `Picked ${override} → ${painted} for contrast`,
    copyLabel: 'Copy accent color'
  },
  ja: {
    reset: 'リセット',
    triggerLabel: 'アクセント色',
    swatches: {
      nousLight: 'Nous ブルー（ライト）',
      nousDark: 'Nous ブルー（ダーク）',
      psyche: 'Psyche ブルー',
      githubBlue: 'GitHub ブルー',
      githubGreen: 'GitHub グリーン',
      githubPurple: 'GitHub パープル',
      githubPink: 'GitHub ピンク',
      githubOrange: 'GitHub オレンジ'
    },
    readout: (h: string, l: string, c: string) => `H${h} L${l} C${c}`,
    contrast: (mode: string, ratio: string) => `${mode} ${ratio}:1`,
    mode: { light: 'ライト', dark: 'ダーク' },
    picked: (override: string, painted: string) => `選択色 ${override} → コントラスト調整後 ${painted}`,
    copyLabel: 'アクセント色をコピー'
  },
  zh: {
    reset: '重置',
    triggerLabel: '强调色',
    swatches: {
      nousLight: 'Nous 蓝（浅色种子）',
      nousDark: 'Nous 蓝（深色种子）',
      psyche: 'Psyche 蓝',
      githubBlue: 'GitHub 蓝',
      githubGreen: 'GitHub 绿',
      githubPurple: 'GitHub 紫',
      githubPink: 'GitHub 粉',
      githubOrange: 'GitHub 橙'
    },
    readout: (h: string, l: string, c: string) => `H${h} L${l} C${c}`,
    contrast: (mode: string, ratio: string) => `${mode} ${ratio}:1`,
    mode: { light: '浅色', dark: '深色' },
    picked: (override: string, painted: string) => `所选 ${override} → 对比度调整后 ${painted}`,
    copyLabel: '复制强调色'
  },
  'zh-hant': {
    reset: '重設',
    triggerLabel: '強調色',
    swatches: {
      nousLight: 'Nous 藍（淺色種子）',
      nousDark: 'Nous 藍（深色種子）',
      psyche: 'Psyche 藍',
      githubBlue: 'GitHub 藍',
      githubGreen: 'GitHub 綠',
      githubPurple: 'GitHub 紫',
      githubPink: 'GitHub 粉',
      githubOrange: 'GitHub 橙'
    },
    readout: (h: string, l: string, c: string) => `H${h} L${l} C${c}`,
    contrast: (mode: string, ratio: string) => `${mode} ${ratio}:1`,
    mode: { light: '淺色', dark: '深色' },
    picked: (override: string, painted: string) => `所選 ${override} → 對比度調整後 ${painted}`,
    copyLabel: '複製強調色'
  }
}

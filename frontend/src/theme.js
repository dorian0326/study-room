import { reactive } from 'vue'

const KEY = 'studyroom_theme'
const THEMES = ['dark', 'light']

/** 当前主题。未手动选择时跟随系统，手动切换后写入 localStorage。 */
export const theme = reactive({ name: 'light', followSystem: true })

let media = null

function systemTheme() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function apply(name) {
  theme.name = THEMES.includes(name) ? name : 'light'
  document.documentElement.dataset.theme = theme.name
  document.documentElement.style.colorScheme = theme.name
}

function onSystemChange() {
  if (theme.followSystem) apply(systemTheme())
}

/** 读取已保存的主题，在挂载前调用以避免闪烁。无记录时跟随系统。 */
export function initTheme() {
  let saved = null
  try {
    saved = localStorage.getItem(KEY)
  } catch {
    saved = null
  }
  if (THEMES.includes(saved)) {
    theme.followSystem = false
    apply(saved)
  } else {
    theme.followSystem = true
    apply(systemTheme())
  }
  media = window.matchMedia?.('(prefers-color-scheme: dark)')
  media?.addEventListener?.('change', onSystemChange)
}

/** 在深色与浅色之间切换并保存，之后不再跟随系统。 */
export function toggleTheme() {
  theme.followSystem = false
  apply(theme.name === 'dark' ? 'light' : 'dark')
  try {
    localStorage.setItem(KEY, theme.name)
  } catch {
    /* 隐私模式下忽略 */
  }
}

import { reactive } from 'vue'

const KEY = 'studyroom_theme'
const THEMES = ['dark', 'light']

/** 当前主题（默认深色），持久化到 localStorage，并写入 <html data-theme>。 */
export const theme = reactive({ name: 'dark' })

function apply(name) {
  theme.name = THEMES.includes(name) ? name : 'dark'
  document.documentElement.dataset.theme = theme.name
  document.documentElement.style.colorScheme = theme.name
}

/** 读取已保存的主题，在挂载前调用以避免闪烁。 */
export function initTheme() {
  let saved = null
  try {
    saved = localStorage.getItem(KEY)
  } catch {
    saved = null
  }
  apply(saved || 'dark')
}

/** 在深色与浅色之间切换并保存。 */
export function toggleTheme() {
  apply(theme.name === 'dark' ? 'light' : 'dark')
  try {
    localStorage.setItem(KEY, theme.name)
  } catch {
    /* 隐私模式下忽略 */
  }
}

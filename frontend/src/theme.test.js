import { beforeEach, describe, expect, it } from 'vitest'

import { initTheme, theme, toggleTheme } from './theme.js'

function mockSystem(dark) {
  window.matchMedia = () => ({
    matches: dark,
    addEventListener() {},
  })
}

beforeEach(() => {
  localStorage.clear()
  theme.name = 'light'
  theme.followSystem = true
  document.documentElement.dataset.theme = ''
  document.documentElement.style.colorScheme = ''
})

describe('theme', () => {
  it('uses a saved choice instead of the system theme', () => {
    localStorage.setItem('studyroom_theme', 'dark')
    mockSystem(false)
    initTheme()
    expect(theme.followSystem).toBe(false)
    expect(theme.name).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('follows the system when nothing valid is saved', () => {
    localStorage.setItem('studyroom_theme', 'blue')
    mockSystem(true)
    initTheme()
    expect(theme.followSystem).toBe(true)
    expect(theme.name).toBe('dark')
    expect(document.documentElement.style.colorScheme).toBe('dark')
  })

  it('toggle stores the choice and stops following the system', () => {
    mockSystem(false)
    initTheme()
    toggleTheme()
    expect(theme.name).toBe('dark')
    expect(theme.followSystem).toBe(false)
    expect(localStorage.getItem('studyroom_theme')).toBe('dark')
    toggleTheme()
    expect(theme.name).toBe('light')
  })
})

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./api/client.js', () => ({
  api: vi.fn(),
  getToken: vi.fn(),
  setToken: vi.fn(),
}))

import { api, getToken, setToken } from './api/client.js'
import { auth, can, hasRole, loadMe, login, logout } from './auth.js'

const user = { roles: ['user'], permissions: ['room:read', 'reservation:own'] }

beforeEach(() => {
  auth.user = null
  auth.loaded = false
  vi.clearAllMocks()
})

describe('auth session', () => {
  it('stays logged out when there is no token', async () => {
    getToken.mockReturnValue(null)
    await expect(loadMe()).resolves.toBeNull()
    expect(auth.loaded).toBe(true)
    expect(api).not.toHaveBeenCalled()
    expect(hasRole('user')).toBe(false)
    expect(can('room:read')).toBe(false)
  })

  it('drops a token that the server no longer accepts', async () => {
    getToken.mockReturnValue('expired')
    api.mockRejectedValue(new Error('unauthorized'))
    await loadMe()
    expect(setToken).toHaveBeenCalledWith(null)
    expect(auth.user).toBeNull()
    expect(auth.loaded).toBe(true)
  })

  it('stores the user returned by login', async () => {
    api.mockResolvedValue({ access_token: 'tok', user })
    await login('20260001', 'Demo1234')
    expect(api).toHaveBeenCalledWith('/auth/login', {
      method: 'POST',
      body: { student_no: '20260001', password: 'Demo1234' },
    })
    expect(setToken).toHaveBeenCalledWith('tok')
    expect(hasRole('user')).toBe(true)
    expect(hasRole('admin')).toBe(false)
    expect(can('reservation:own')).toBe(true)
    expect(can('user:manage')).toBe(false)
  })

  it('clears the session even when logout fails', async () => {
    auth.user = user
    api.mockRejectedValue(new Error('offline'))
    await expect(logout()).rejects.toThrow('offline')
    expect(auth.user).toBeNull()
    expect(setToken).toHaveBeenCalledWith(null)
  })
})

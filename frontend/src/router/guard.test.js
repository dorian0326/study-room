import { describe, expect, it, vi } from 'vitest'

import { authorizeNavigation } from './guard.js'

function authState(user) {
  return { loaded: true, user }
}

describe('authorizeNavigation', () => {
  it('sends an anonymous visitor to login and keeps the target', async () => {
    const loadMe = vi.fn()
    const result = await authorizeNavigation(
      { fullPath: '/workflows', meta: { auth: true } },
      authState(null),
      loadMe,
    )
    expect(result).toEqual({ path: '/login', query: { next: '/workflows' } })
    expect(loadMe).not.toHaveBeenCalled()
  })

  it('loads the session once before deciding', async () => {
    const auth = { loaded: false, user: null }
    const loadMe = vi.fn(async () => {
      auth.loaded = true
      auth.user = { permissions: ['room:read'] }
    })
    const result = await authorizeNavigation({ fullPath: '/', meta: { auth: true } }, auth, loadMe)
    expect(loadMe).toHaveBeenCalledOnce()
    expect(result).toBe(true)
  })

  it('blocks a page the signed-in user cannot access', async () => {
    const user = { permissions: ['room:read'] }
    const missing = await authorizeNavigation(
      { fullPath: '/admin/users', meta: { auth: true, perm: 'user:manage' } },
      authState(user),
      vi.fn(),
    )
    expect(missing).toBe('/')
    const neither = await authorizeNavigation(
      {
        fullPath: '/admin/logs',
        meta: { auth: true, anyPerm: ['audit_log:read', 'system_log:read'] },
      },
      authState(user),
      vi.fn(),
    )
    expect(neither).toBe('/')
  })

  it('allows a page when any required permission matches', async () => {
    const user = { permissions: ['system_log:read'] }
    const result = await authorizeNavigation(
      {
        fullPath: '/admin/ops',
        meta: { auth: true, anyPerm: ['system:backup', 'system_log:read'] },
      },
      authState(user),
      vi.fn(),
    )
    expect(result).toBe(true)
  })

  it('leaves public pages open', async () => {
    const result = await authorizeNavigation(
      { fullPath: '/login', meta: {} },
      authState(null),
      vi.fn(),
    )
    expect(result).toBe(true)
  })
})

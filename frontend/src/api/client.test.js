import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, getToken, setToken } from './client.js'

function mockFetch(response) {
  const fetchMock = vi.fn().mockResolvedValue(response)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('token storage', () => {
  it('writes and clears the session token', () => {
    setToken('abc')
    expect(getToken()).toBe('abc')
    setToken('')
    expect(getToken()).toBeNull()
  })
})

describe('api', () => {
  it('sends the bearer token and returns JSON', async () => {
    setToken('abc')
    const fetchMock = mockFetch({
      status: 200,
      ok: true,
      json: async () => ({ ok: true }),
    })
    await expect(api('/auth/me')).resolves.toEqual({ ok: true })
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/auth/me')
    expect(options.headers.Authorization).toBe('Bearer abc')
  })

  it('returns null for an empty response', async () => {
    mockFetch({ status: 204, ok: true, json: async () => ({}) })
    await expect(api('/auth/logout', { method: 'POST' })).resolves.toBeNull()
  })

  it('surfaces a string error from the backend', async () => {
    mockFetch({
      status: 401,
      ok: false,
      json: async () => ({ detail: '学号或密码错误' }),
    })
    await expect(api('/auth/login', { method: 'POST', body: { student_no: '1' } })).rejects.toThrow(
      '学号或密码错误',
    )
  })

  it('joins field validation messages', async () => {
    mockFetch({
      status: 422,
      ok: false,
      json: async () => ({ detail: [{ msg: '太短' }, { message: '缺数字' }] }),
    })
    await expect(api('/auth/register', { method: 'POST', body: {} })).rejects.toThrow(
      '太短；缺数字',
    )
  })

  it('uses an object message and keeps the status code', async () => {
    mockFetch({
      status: 409,
      ok: false,
      json: async () => ({ detail: { message: '座位已被占用' } }),
    })
    const error = await api('/reservations', { method: 'POST', body: { seat_id: 1 } }).catch(
      (err) => err,
    )
    expect(error).toMatchObject({
      message: '座位已被占用',
      status: 409,
      detail: { message: '座位已被占用' },
    })
  })

  it('explains a conflict that has no detail', async () => {
    mockFetch({ status: 409, ok: false, json: async () => ({}) })
    await expect(api('/reservations')).rejects.toThrow('资源冲突，请刷新后重试')
  })

  it('names the HTTP status when the body cannot be read', async () => {
    mockFetch({
      status: 500,
      ok: false,
      json: async () => {
        throw new Error('not json')
      },
    })
    await expect(api('/health')).rejects.toThrow('请求失败（HTTP 500）')
  })
})

import { reactive } from 'vue'
import { api, getToken, setToken } from './api/client.js'

export const auth = reactive({ user: null, loaded: false })

export async function loadMe() {
  if (getToken()) {
    try {
      auth.user = await api('/auth/me')
    } catch {
      setToken(null)
      auth.user = null
    }
  }
  auth.loaded = true
  return auth.user
}

export async function login(studentNo, password) {
  const data = await api('/auth/login', {
    method: 'POST',
    body: { student_no: studentNo, password },
  })
  setToken(data.access_token)
  auth.user = data.user
}

export async function logout() {
  try {
    await api('/auth/logout', { method: 'POST' })
  } finally {
    setToken(null)
    auth.user = null
  }
}

export function hasRole(...roles) {
  return !!auth.user && auth.user.roles.some((r) => roles.includes(r))
}

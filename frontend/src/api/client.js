const TOKEN_KEY = 'studyroom_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** 调用后端 /api；失败时抛出带后端提示信息的 Error。 */
export async function api(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const resp = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (resp.status === 204) return null
  const data = await resp.json().catch(() => null)
  if (!resp.ok) {
    const d = data?.detail
    const msg = typeof d === 'string' ? d : (d?.message ?? (Array.isArray(d) ? '输入不合法' : null))
    const err = new Error(msg ?? `请求失败（HTTP ${resp.status}）`)
    err.status = resp.status
    throw err
  }
  return data
}

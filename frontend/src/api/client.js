const TOKEN_KEY = 'studyroom_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** 把 FastAPI detail 转成可读中文。 */
function detailMessage(detail, status) {
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    return detail.message || detail.msg || JSON.stringify(detail)
  }
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => item.msg || item.message || (typeof item === 'string' ? item : '输入不合法'))
      .join('；')
  }
  if (status === 409) return '资源冲突，请刷新后重试'
  return null
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
    const msg = detailMessage(data?.detail, resp.status)
    const err = new Error(msg ?? `请求失败（HTTP ${resp.status}）`)
    err.status = resp.status
    err.detail = data?.detail
    throw err
  }
  return data
}

export async function fetchHealth() {
  const resp = await fetch('/api/health')
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

/** 验证页面所需的登录状态和权限码。未登录去登录页，缺权限回首页。 */
export async function authorizeNavigation(to, auth, loadMe) {
  if (!auth.loaded) await loadMe()
  if (to.meta.auth && !auth.user) return { path: '/login', query: { next: to.fullPath } }
  if (to.meta.perm && !auth.user.permissions.includes(to.meta.perm)) return '/'
  if (to.meta.anyPerm) {
    const ok = to.meta.anyPerm.some((p) => auth.user.permissions.includes(p))
    if (!ok) return '/'
  }
  return true
}

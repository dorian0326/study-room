import { createRouter, createWebHistory } from 'vue-router'
import { auth, loadMe } from '../auth.js'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import ChangePasswordView from '../views/ChangePasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
import AdminUsersView from '../views/AdminUsersView.vue'
import AdminConfigView from '../views/AdminConfigView.vue'

export const routes = [
  { path: '/', component: HomeView, meta: { auth: true } },
  { path: '/login', component: LoginView },
  { path: '/register', component: RegisterView },
  { path: '/reset-password', component: ResetPasswordView },
  { path: '/change-password', component: ChangePasswordView, meta: { auth: true } },
  { path: '/admin/config', component: AdminConfigView, meta: { auth: true, perm: 'room:manage' } },
  { path: '/admin/users', component: AdminUsersView, meta: { auth: true, perm: 'user:manage' } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  if (!auth.loaded) await loadMe()
  if (to.meta.auth && !auth.user) return { path: '/login', query: { next: to.fullPath } }
  // meta.perm：需要对应权限码（#7）
  if (to.meta.perm && !auth.user.permissions.includes(to.meta.perm)) return '/'
  return true
})

export default router

import { createRouter, createWebHistory } from 'vue-router'
import { auth, loadMe } from '../auth.js'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import ChangePasswordView from '../views/ChangePasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'

export const routes = [
  { path: '/', component: HomeView, meta: { auth: true } },
  { path: '/login', component: LoginView },
  { path: '/register', component: RegisterView },
  { path: '/reset-password', component: ResetPasswordView },
  { path: '/change-password', component: ChangePasswordView, meta: { auth: true } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  if (!auth.loaded) await loadMe()
  if (to.meta.auth && !auth.user) return { path: '/login', query: { next: to.fullPath } }
  // meta.roles：仅允许列出的角色访问（#7）
  if (to.meta.roles && !auth.user.roles.some((r) => to.meta.roles.includes(r))) return '/'
  return true
})

export default router

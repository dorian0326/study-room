import { createRouter, createWebHistory } from 'vue-router'
import { auth, loadMe } from '../auth.js'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import ChangePasswordView from '../views/ChangePasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
import AdminUsersView from '../views/AdminUsersView.vue'
import AdminConfigView from '../views/AdminConfigView.vue'
import WorkflowsView from '../views/WorkflowsView.vue'
import NotificationsView from '../views/NotificationsView.vue'
import ViolationsView from '../views/ViolationsView.vue'
import AdminSeatsView from '../views/AdminSeatsView.vue'
import AdminReportsView from '../views/AdminReportsView.vue'
import AdminAppealsView from '../views/AdminAppealsView.vue'
import CheckInView from '../views/CheckInView.vue'
import AdminLogsView from '../views/AdminLogsView.vue'
import AdminOpsView from '../views/AdminOpsView.vue'
import AdminGateView from '../views/AdminGateView.vue'
import NotFoundView from '../views/NotFoundView.vue'

export const routes = [
  { path: '/', component: HomeView, meta: { auth: true } },
  { path: '/workflows', component: WorkflowsView, meta: { auth: true } },
  { path: '/check-in', component: CheckInView, meta: { auth: true } },
  { path: '/violations', component: ViolationsView, meta: { auth: true } },
  { path: '/notifications', component: NotificationsView, meta: { auth: true } },
  { path: '/admin/seats', component: AdminSeatsView, meta: { auth: true, perm: 'room:manage' } },
  { path: '/admin/reports', component: AdminReportsView, meta: { auth: true, perm: 'stats:read' } },
  {
    path: '/admin/appeals',
    component: AdminAppealsView,
    meta: { auth: true, perm: 'appeal:manage' },
  },
  {
    path: '/admin/logs',
    component: AdminLogsView,
    meta: { auth: true, anyPerm: ['audit_log:read', 'system_log:read'] },
  },
  {
    path: '/admin/ops',
    component: AdminOpsView,
    meta: { auth: true, anyPerm: ['system:backup', 'system_log:read'] },
  },
  {
    path: '/admin/gate',
    component: AdminGateView,
    meta: { auth: true, perm: 'entry_exit:read' },
  },
  { path: '/login', component: LoginView },
  { path: '/register', component: RegisterView },
  { path: '/reset-password', component: ResetPasswordView },
  { path: '/change-password', component: ChangePasswordView, meta: { auth: true } },
  { path: '/admin/config', component: AdminConfigView, meta: { auth: true, perm: 'room:manage' } },
  { path: '/admin/users', component: AdminUsersView, meta: { auth: true, perm: 'user:manage' } },
  { path: '/:pathMatch(.*)*', component: NotFoundView, meta: { auth: true } },
]

const router = createRouter({ history: createWebHistory(), routes })

/** 验证页面所需的登录状态和权限码。 */
async function authorizeNavigation(to) {
  if (!auth.loaded) await loadMe()
  if (to.meta.auth && !auth.user) return { path: '/login', query: { next: to.fullPath } }
  if (to.meta.perm && !auth.user.permissions.includes(to.meta.perm)) return '/'
  if (to.meta.anyPerm) {
    const ok = to.meta.anyPerm.some((p) => auth.user.permissions.includes(p))
    if (!ok) return '/'
  }
  return true
}

router.beforeEach(authorizeNavigation)

export default router

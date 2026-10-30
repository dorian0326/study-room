<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth, can, logout } from './auth.js'

const router = useRouter()
const route = useRoute()
const openMenu = ref('')

const mainLinks = [
  { to: '/', label: '首页' },
  { to: '/workflows', label: '预约' },
  { to: '/check-in', label: '签到' },
  { to: '/violations', label: '违规' },
  { to: '/notifications', label: '通知' },
]

const adminLinks = computed(() =>
  [
    { to: '/admin/config', label: '自习室配置', show: can('room:manage') },
    { to: '/admin/seats', label: '座位管理', show: can('room:manage') },
    { to: '/admin/users', label: '用户管理', show: can('user:manage') },
    { to: '/admin/reports', label: '统计报表', show: can('stats:read') },
    { to: '/admin/appeals', label: '申诉处理', show: can('appeal:manage') },
    {
      to: '/admin/logs',
      label: '系统日志',
      show: can('audit_log:read') || can('system_log:read'),
    },
    {
      to: '/admin/ops',
      label: '备份监控',
      show: can('system:backup') || can('system_log:read'),
    },
    { to: '/admin/gate', label: '出入馆记录', show: can('entry_exit:read') },
  ].filter((link) => link.show),
)

const adminActive = computed(() => route.path.startsWith('/admin'))
const initial = computed(() => (auth.user?.name || '?').slice(0, 1))

watch(
  () => route.fullPath,
  () => {
    openMenu.value = ''
  },
)

function toggle(name) {
  openMenu.value = openMenu.value === name ? '' : name
}

/** 注销当前账号并返回登录页。 */
async function onLogout() {
  openMenu.value = ''
  await logout()
  router.push('/login')
}

const ROLE_LABELS = { user: '学生', admin: '管理员', ops: '运维' }
const roleText = computed(() => (auth.user?.roles || []).map((r) => ROLE_LABELS[r] || r).join('、'))
</script>

<template>
  <header class="topbar">
    <div class="topbar-inner">
      <RouterLink to="/" class="brand">
        <span class="logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor">
            <path d="M4 19V6a2 2 0 0 1 2-2h12v15" stroke-width="2" stroke-linejoin="round" />
            <path d="M4 19a2 2 0 0 1 2-2h12v3H6a2 2 0 0 1-2-1Z" stroke-width="2" />
            <path d="M9 8h6M9 11h4" stroke-width="2" stroke-linecap="round" />
          </svg>
        </span>
        <span class="brand-text">
          <strong>智慧自习室</strong>
          <small>Study Room</small>
        </span>
      </RouterLink>

      <nav v-if="auth.user" class="links" aria-label="主导航">
        <RouterLink v-for="link in mainLinks" :key="link.to" :to="link.to" class="nav-link">
          {{ link.label }}
        </RouterLink>
        <div v-if="adminLinks.length" class="menu" @mouseleave="openMenu = ''">
          <button
            type="button"
            class="nav-link menu-trigger"
            :class="{ active: adminActive }"
            :aria-expanded="openMenu === 'admin'"
            @click="toggle('admin')"
          >
            管理后台 <span class="caret">▾</span>
          </button>
          <div v-if="openMenu === 'admin'" class="dropdown">
            <RouterLink v-for="link in adminLinks" :key="link.to" :to="link.to">
              {{ link.label }}
            </RouterLink>
          </div>
        </div>
      </nav>

      <div class="account">
        <div v-if="auth.user" class="menu" @mouseleave="openMenu = ''">
          <button
            type="button"
            class="user-trigger"
            :aria-expanded="openMenu === 'user'"
            @click="toggle('user')"
          >
            <span class="avatar">{{ initial }}</span>
            <span class="who">{{ auth.user.name }}</span>
            <span class="caret">▾</span>
          </button>
          <div v-if="openMenu === 'user'" class="dropdown right">
            <div class="dropdown-head">
              <strong>{{ auth.user.name }}</strong>
              <small>{{ auth.user.student_no }} · {{ roleText }}</small>
            </div>
            <RouterLink to="/change-password">修改密码</RouterLink>
            <button type="button" class="logout" @click="onLogout">退出登录</button>
          </div>
        </div>
        <template v-else>
          <RouterLink to="/login" class="nav-link">登录</RouterLink>
          <RouterLink to="/register" class="nav-link">注册</RouterLink>
        </template>
      </div>
    </div>
  </header>
  <main class="app-main"><RouterView /></main>
  <footer class="app-footer">智慧自习室管理系统 · 软件工程课程设计</footer>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  background: rgba(255, 255, 255, 0.62);
  -webkit-backdrop-filter: saturate(180%) blur(24px);
  backdrop-filter: saturate(180%) blur(24px);
  border-bottom: 0.5px solid rgba(60, 60, 67, 0.14);
  box-shadow: 0 1px 12px rgba(15, 40, 90, 0.05);
}
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .topbar {
    background: rgba(255, 255, 255, 0.96);
  }
}
.topbar-inner {
  max-width: 1200px;
  margin: 0 auto;
  height: 56px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text);
  white-space: nowrap;
  flex: none;
}
.brand:hover {
  text-decoration: none;
}
.logo {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  color: #fff;
  background: linear-gradient(145deg, #5ac8fa, #007aff 70%);
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
}
.brand-text {
  display: grid;
  line-height: 1.15;
}
.brand-text strong {
  font-size: 1rem;
}
.brand-text small {
  color: var(--muted);
  font-size: 0.7rem;
  letter-spacing: 0.04em;
}
.links {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border-radius: 999px;
  background: rgba(120, 120, 128, 0.08);
  min-width: 0;
  white-space: nowrap;
}
.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 30px;
  padding: 0 14px;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: var(--muted);
  font-weight: 500;
  white-space: nowrap;
}
.nav-link:hover,
button.nav-link:hover:not(:disabled) {
  text-decoration: none;
  color: var(--text);
  background: rgba(255, 255, 255, 0.6);
}
.nav-link {
  transition:
    background 0.18s,
    color 0.18s;
}
.nav-link.router-link-exact-active,
.nav-link.active,
.nav-link.active:hover:not(:disabled) {
  color: #fff;
  background: #007aff;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}
.caret {
  font-size: 0.7rem;
  opacity: 0.7;
}
.menu {
  position: relative;
}
.dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 180px;
  padding: 6px;
  margin-top: 6px;
  background: rgba(255, 255, 255, 0.72);
  -webkit-backdrop-filter: blur(28px) saturate(180%);
  backdrop-filter: blur(28px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 14px;
  animation: pop 0.16s ease-out;
  box-shadow: var(--shadow-lg);
  display: grid;
  gap: 2px;
  z-index: 50;
}
.dropdown.right {
  left: auto;
  right: 0;
  min-width: 220px;
}
.dropdown a,
.dropdown .logout {
  display: flex;
  justify-content: flex-start;
  height: 34px;
  align-items: center;
  padding: 0 10px;
  border-radius: 8px;
  color: var(--text);
  border: none;
  background: transparent;
  font-weight: 400;
}
.menu::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 100%;
  height: 8px;
}
@keyframes pop {
  from {
    opacity: 0;
    transform: translateY(-4px) scale(0.98);
  }
}
.dropdown a:hover,
.dropdown .logout:hover:not(:disabled) {
  text-decoration: none;
  background: rgba(0, 122, 255, 0.1);
}
.dropdown a.router-link-active {
  color: #fff;
  background: #007aff;
}
.dropdown .logout {
  color: var(--danger);
}
.dropdown-head {
  display: grid;
  padding: 6px 10px 10px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--line);
}
.dropdown-head small {
  color: var(--muted);
}
.account {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  flex: none;
}
.user-trigger {
  height: 40px;
  padding: 0 10px 0 4px;
  border-color: transparent;
  background: transparent;
  border-radius: 999px;
  color: var(--text);
}
.avatar {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(145deg, #5ac8fa, #007aff);
  color: #fff;
  font-weight: 600;
}
.who {
  max-width: 8em;
  overflow: hidden;
  text-overflow: ellipsis;
}
.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 28px 24px 40px;
}
.app-footer {
  text-align: center;
  color: #8e8e93;
  font-size: 0.8rem;
  padding: 0 0 24px;
}
@media (max-width: 1060px) {
  .brand-text small,
  .who {
    display: none;
  }
  .topbar-inner {
    gap: 12px;
    padding: 0 16px;
  }
  .nav-link {
    padding: 0 9px;
  }
}
</style>

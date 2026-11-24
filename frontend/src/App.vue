<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from './api/client.js'
import { auth, can, logout } from './auth.js'
import { theme, toggleTheme } from './theme.js'
import XIcon from './components/XIcon.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'
import logoUrl from './assets/nailong/nailong-logo.png'
import coverUrl from './assets/nailong/cover.jpg'
import sillyUrl from './assets/nailong/nailong-silly.webp'

const BRAND = '奶龙自习室'
const router = useRouter()
const route = useRoute()
const menuOpen = ref(false)
const menuRef = ref(null)
const menuTopRef = ref(null)
const adminOpen = ref(false)
const unreadCount = ref(0)

const mainLinks = [
  { to: '/', label: '首页', icon: 'home' },
  { to: '/workflows', label: '预约', icon: 'calendar' },
  { to: '/check-in', label: '签到', icon: 'qr' },
  { to: '/violations', label: '违规', icon: 'alert' },
  { to: '/notifications', label: '通知', icon: 'bell' },
]

const adminLinks = computed(() =>
  [
    { to: '/admin/config', label: '自习室配置', icon: 'building', show: can('room:manage') },
    { to: '/admin/seats', label: '座位管理', icon: 'seat', show: can('room:manage') },
    { to: '/admin/users', label: '用户管理', icon: 'users', show: can('user:manage') },
    { to: '/admin/reports', label: '统计报表', icon: 'chart', show: can('stats:read') },
    { to: '/admin/appeals', label: '申诉处理', icon: 'gavel', show: can('appeal:manage') },
    {
      to: '/admin/logs',
      label: '系统日志',
      icon: 'logs',
      show: can('audit_log:read') || can('system_log:read'),
    },
    {
      to: '/admin/ops',
      label: '备份监控',
      icon: 'server',
      show: can('system:backup') || can('system_log:read'),
    },
    { to: '/admin/gate', label: '出入馆记录', icon: 'door', show: can('entry_exit:read') },
  ].filter((link) => link.show),
)

const allLinks = computed(() => [...mainLinks, ...adminLinks.value])
const TITLES = {
  '/login': '登录',
  '/register': '注册',
  '/reset-password': '重置密码',
  '/change-password': '修改密码',
}
const pageTitle = computed(() => {
  const hit = allLinks.value.find((l) => l.to === route.path)
  return hit ? hit.label : TITLES[route.path] || '页面未找到'
})
const isAuthPage = computed(() => ['/login', '/register', '/reset-password'].includes(route.path))
const showShell = computed(() => !!auth.user && !isAuthPage.value)
const wide = computed(
  () => route.path.startsWith('/admin') || ['/workflows', '/'].includes(route.path),
)
const initial = computed(() => (auth.user?.name || '?').slice(0, 1))

/** 页面切换时同步浏览器标题，并收起账号菜单。 */
watch(
  () => [route.fullPath, pageTitle.value],
  () => {
    menuOpen.value = false
    adminOpen.value = false
    document.title = route.path === '/' ? BRAND : `${pageTitle.value} / ${BRAND}`
    if (auth.user) loadUnread()
  },
  { immediate: true },
)

function isActive(to) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

function inMenus(target) {
  return Boolean(menuRef.value?.contains(target) || menuTopRef.value?.contains(target))
}

function onDocClick(e) {
  if (menuOpen.value && !inMenus(e.target)) menuOpen.value = false
}
function onKey(e) {
  if (e.key === 'Escape') {
    menuOpen.value = false
    adminOpen.value = false
  }
}

/** 用已有通知接口取未读条数，只为入口小红点，不改后端。 */
async function loadUnread() {
  if (!auth.user) {
    unreadCount.value = 0
    return
  }
  try {
    const rows = await api('/notifications?unread_only=true&limit=50')
    unreadCount.value = Array.isArray(rows) ? rows.length : 0
  } catch {
    /* 角标失败不影响主界面 */
  }
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
  window.addEventListener('studyroom:notifications-changed', loadUnread)
  loadUnread()
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
  window.removeEventListener('studyroom:notifications-changed', loadUnread)
})

/** 注销当前账号并返回登录页。 */
async function onLogout() {
  menuOpen.value = false
  await logout()
  router.push('/login')
}

const ROLE_LABELS = { user: '学生', admin: '管理员', ops: '运维' }
const roleText = computed(() => (auth.user?.roles || []).map((r) => ROLE_LABELS[r] || r).join('、'))
</script>

<template>
  <div v-if="!auth.loaded" class="nl-loading splash" role="status">
    <img :src="sillyUrl" alt="" />
    <span>奶龙正在加载…</span>
  </div>
  <!-- 登录 / 注册 / 重置：左侧奶龙封面 + 右侧表单 -->
  <div v-else-if="isAuthPage || !auth.user" class="auth-layout">
    <aside class="auth-cover" aria-hidden="true">
      <img :src="coverUrl" alt="" />
      <div class="auth-cover-text">
        <img :src="logoUrl" alt="" class="auth-cover-logo" />
        <strong>{{ BRAND }}</strong>
        <span>约座、签到，安心自习</span>
      </div>
    </aside>
    <main class="auth-side">
      <div class="auth-brand">
        <img :src="logoUrl" alt="" />
        <span>{{ BRAND }}</span>
      </div>
      <RouterView />
      <button type="button" class="ghost small theme-btn" @click="toggleTheme">
        <XIcon :name="theme.name === 'dark' ? 'sun' : 'moon'" :size="16" />
        {{ theme.name === 'dark' ? '浅色模式' : '深色模式' }}
      </button>
    </main>
  </div>

  <div v-else-if="showShell" class="shell" :class="{ wide }">
    <header class="rail" aria-label="主导航">
      <RouterLink to="/" class="rail-logo" :title="BRAND">
        <img :src="logoUrl" alt="" />
        <span class="rail-label brand-name">{{ BRAND }}</span>
      </RouterLink>
      <nav class="rail-nav">
        <RouterLink
          v-for="link in mainLinks"
          :key="link.to"
          :to="link.to"
          class="rail-item"
          :class="{ active: isActive(link.to) }"
          :aria-current="isActive(link.to) ? 'page' : undefined"
        >
          <span class="rail-pill">
            <span class="nav-icon">
              <XIcon :name="link.icon" :bold="isActive(link.to)" />
              <i
                v-if="link.to === '/notifications' && unreadCount"
                class="nav-dot"
                aria-label="有未读通知"
              />
            </span>
            <span class="rail-label">{{ link.label }}</span>
          </span>
        </RouterLink>
        <template v-if="adminLinks.length">
          <div class="rail-sep"><span class="rail-label">管理后台</span></div>
          <RouterLink
            v-for="link in adminLinks"
            :key="link.to"
            :to="link.to"
            class="rail-item"
            :class="{ active: isActive(link.to) }"
            :aria-current="isActive(link.to) ? 'page' : undefined"
          >
            <span class="rail-pill">
              <XIcon :name="link.icon" :bold="isActive(link.to)" />
              <span class="rail-label">{{ link.label }}</span>
            </span>
          </RouterLink>
        </template>
      </nav>
      <RouterLink to="/workflows" class="rail-cta">
        <span class="rail-label">预约座位</span>
        <XIcon name="calendar" :size="22" class="rail-cta-icon" />
      </RouterLink>

      <div ref="menuRef" class="account">
        <div v-if="menuOpen" class="account-menu" role="menu">
          <div class="menu-head">
            <strong>{{ auth.user.name }}</strong>
            <small>{{ auth.user.student_no }}（{{ roleText }}）</small>
          </div>
          <button type="button" role="menuitem" class="menu-item" @click="toggleTheme">
            <XIcon :name="theme.name === 'dark' ? 'sun' : 'moon'" :size="20" />
            {{ theme.name === 'dark' ? '切换到浅色模式' : '切换到深色模式' }}
          </button>
          <RouterLink to="/change-password" role="menuitem" class="menu-item">
            <XIcon name="key" :size="20" /> 修改密码
          </RouterLink>
          <button type="button" role="menuitem" class="menu-item danger-item" @click="onLogout">
            <XIcon name="logout" :size="20" /> 退出 @{{ auth.user.student_no }}
          </button>
        </div>
        <button
          type="button"
          class="account-chip"
          :aria-expanded="menuOpen"
          aria-haspopup="menu"
          @click.stop="menuOpen = !menuOpen"
        >
          <span class="avatar">{{ initial }}</span>
          <span class="rail-label who">
            <strong>{{ auth.user.name }}</strong>
            <small>@{{ auth.user.student_no }}</small>
          </span>
          <span class="rail-label more"><XIcon name="more" :size="18" /></span>
        </button>
      </div>
    </header>

    <div class="column">
      <div class="topbar">
        <h1>{{ pageTitle }}</h1>
        <span class="topbar-sub">{{ BRAND }}</span>
        <div ref="menuTopRef" class="account topbar-account">
          <div v-if="menuOpen" class="account-menu" role="menu">
            <div class="menu-head">
              <strong>{{ auth.user.name }}</strong>
              <small>{{ auth.user.student_no }}（{{ roleText }}）</small>
            </div>
            <button type="button" role="menuitem" class="menu-item" @click="toggleTheme">
              <XIcon :name="theme.name === 'dark' ? 'sun' : 'moon'" :size="20" />
              {{ theme.name === 'dark' ? '切换到浅色模式' : '切换到深色模式' }}
            </button>
            <RouterLink to="/change-password" role="menuitem" class="menu-item">
              <XIcon name="key" :size="20" /> 修改密码
            </RouterLink>
            <button type="button" role="menuitem" class="menu-item danger-item" @click="onLogout">
              <XIcon name="logout" :size="20" /> 退出 @{{ auth.user.student_no }}
            </button>
          </div>
          <button
            type="button"
            class="account-chip"
            :aria-expanded="menuOpen"
            aria-haspopup="menu"
            aria-label="账号菜单"
            @click.stop="menuOpen = !menuOpen"
          >
            <span class="avatar">{{ initial }}</span>
          </button>
        </div>
      </div>
      <main class="app-main"><RouterView /></main>
      <footer class="app-footer">{{ BRAND }}，软件工程课程设计</footer>
    </div>

    <!-- 移动端底部标签栏 -->
    <nav class="tabbar" aria-label="底部导航">
      <RouterLink
        v-for="link in mainLinks"
        :key="link.to"
        :to="link.to"
        class="tabbar-item"
        :class="{ active: isActive(link.to) }"
        :aria-current="isActive(link.to) ? 'page' : undefined"
      >
        <span class="nav-icon">
          <XIcon :name="link.icon" :size="22" :bold="isActive(link.to)" />
          <i
            v-if="link.to === '/notifications' && unreadCount"
            class="nav-dot"
            aria-label="有未读通知"
          />
        </span>
        <span class="tab-label">{{ link.label }}</span>
      </RouterLink>
      <button
        v-if="adminLinks.length"
        type="button"
        class="tabbar-item"
        :class="{ active: adminOpen || route.path.startsWith('/admin') }"
        aria-haspopup="dialog"
        :aria-expanded="adminOpen"
        @click="adminOpen = !adminOpen"
      >
        <XIcon name="building" :size="22" :bold="route.path.startsWith('/admin')" />
        <span class="tab-label">管理</span>
      </button>
    </nav>
    <div
      v-if="adminOpen && adminLinks.length"
      class="admin-sheet-mask"
      @click.self="adminOpen = false"
    >
      <div class="admin-sheet" role="dialog" aria-label="管理后台">
        <h3>管理后台</h3>
        <RouterLink
          v-for="link in adminLinks"
          :key="link.to"
          :to="link.to"
          class="admin-sheet-item"
          :class="{ active: isActive(link.to) }"
          @click="adminOpen = false"
        >
          <XIcon :name="link.icon" :size="20" :bold="isActive(link.to)" />
          {{ link.label }}
        </RouterLink>
      </div>
    </div>
  </div>
  <ConfirmDialog />
</template>

<style scoped>
/* ---------- 认证页 ---------- */
.splash {
  min-height: 100vh;
  align-content: center;
}
.auth-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(380px, 1fr);
}
.auth-cover {
  position: relative;
  overflow: hidden;
  background: #1c1710;
}
.auth-cover > img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.auth-cover::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 50%, rgba(28, 23, 16, 0.78));
}
.auth-cover-text {
  position: absolute;
  left: 32px;
  bottom: 28px;
  z-index: 1;
  display: grid;
  gap: 2px;
  color: #fff8f1;
}
.auth-cover-logo {
  width: 44px;
  margin-bottom: 6px;
}
.auth-cover-text strong {
  font-family: var(--font-display);
  font-size: 1.9rem;
  font-weight: 700;
}
.auth-cover-text span {
  color: rgba(255, 248, 241, 0.86);
}
.auth-side {
  position: relative;
  display: grid;
  align-content: center;
  padding: 32px 40px;
  background: var(--bg);
}
.auth-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-self: start;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.15rem;
  margin-bottom: 8px;
}
.auth-brand img {
  width: 40px;
}
.auth-side :deep(.auth-wrap) {
  min-height: 0;
  place-items: stretch;
  padding: 0;
}
.theme-btn {
  position: absolute;
  top: 16px;
  right: 16px;
}

/* ---------- 应用外壳：左侧圆角服务台，右侧书桌工作区 ---------- */
.shell {
  display: grid;
  grid-template-columns: var(--rail-w) minmax(0, 1fr);
  max-width: calc(var(--rail-w) + 1120px);
  margin: 0 auto;
  min-height: 100vh;
  padding: 16px 20px 16px 12px;
  gap: 12px;
}
.rail {
  position: sticky;
  top: 16px;
  height: calc(100vh - 32px);
  display: flex;
  flex-direction: column;
  padding: 12px;
  overflow-y: auto;
  scrollbar-width: none;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: 24px;
}
.rail-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  margin: 0 0 8px;
  border-radius: 16px;
  color: var(--text);
  width: 100%;
}
.rail-logo:hover {
  text-decoration: none;
  background: var(--bg-hover-strong);
}
.rail-logo img {
  width: 36px;
  height: 36px;
  object-fit: contain;
}
.brand-name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.15rem;
  color: var(--nl-yellow-text);
}
.rail-nav {
  display: grid;
  gap: 2px;
}
.rail-item {
  display: flex;
  color: var(--text);
  padding: 0;
  border-radius: 14px;
}
.rail-item:hover {
  text-decoration: none;
}
.rail-pill {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 0.98rem;
  transition: background 0.15s;
}
.rail-item:hover .rail-pill {
  background: var(--bg-hover-strong);
}
.rail-item:focus-visible {
  outline: none;
}
.rail-item:focus-visible .rail-pill {
  box-shadow: 0 0 0 2px var(--brand);
}
.rail-item.active .rail-pill {
  font-weight: 700;
  background: var(--brand-soft);
  color: var(--text);
}
.rail-item.active .x-icon {
  color: var(--nl-yellow-text);
}
.rail-sep {
  margin: 10px 8px 4px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 700;
}
.rail-nav .rail-sep ~ .rail-item .rail-pill {
  font-size: 0.92rem;
  padding-top: 8px;
  padding-bottom: 8px;
}
.rail-cta {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 44px;
  margin: 14px 0;
  width: 100%;
  border-radius: 14px;
  background: var(--brand);
  color: var(--brand-ink);
  font-weight: 700;
  font-size: 1rem;
}
.rail-cta:hover {
  text-decoration: none;
  background: var(--brand-hover);
}
.rail-cta-icon {
  display: none;
}
.account {
  margin-top: auto;
  position: relative;
}
.account-chip {
  width: 100%;
  height: auto;
  justify-content: flex-start;
  gap: 10px;
  padding: 8px 10px;
  border: none;
  border-radius: 14px;
  background: transparent;
  font-weight: 400;
  text-align: left;
}
.account-chip:hover:not(:disabled) {
  background: var(--bg-hover-strong);
}
.avatar {
  flex: none;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--nl-yellow);
  color: var(--brand-ink);
  font-weight: 700;
}
.who {
  display: grid;
  min-width: 0;
  line-height: 1.25;
}
.who strong,
.who small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.who small {
  color: var(--muted);
  font-size: 0.86rem;
}
.more {
  margin-left: auto;
  display: flex;
}
.account-menu {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  width: 290px;
  padding: 12px 0;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow-lg);
  z-index: 60;
  display: grid;
}
.menu-head {
  display: grid;
  padding: 4px 16px 12px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--line);
}
.menu-head small {
  color: var(--muted);
}
.menu-item {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  height: 44px;
  padding: 0 16px;
  border: none;
  border-radius: 0;
  background: transparent;
  color: var(--text);
  font-weight: 700;
  font-size: 0.95rem;
}
.menu-item:hover,
button.menu-item:hover:not(:disabled) {
  text-decoration: none;
  background: var(--bg-hover-strong);
}
.danger-item {
  color: var(--danger);
}

.column {
  min-width: 0;
  max-width: none;
  border: none;
  min-height: calc(100vh - 32px);
  display: flex;
  flex-direction: column;
}
.shell.wide .column {
  max-width: none;
}
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 8px 0 4px;
  background: var(--header-bg);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  border-bottom: none;
}
.topbar h1 {
  font-size: 1.4rem;
  font-weight: 700;
}
.topbar-sub {
  color: var(--muted);
  font-size: 0.85rem;
}
.topbar-account {
  display: none;
  margin-left: auto;
  position: relative;
}
.topbar-account .account-chip {
  width: auto;
  height: auto;
  padding: 2px;
  border: none;
  background: transparent;
}
.topbar-account .avatar {
  width: 32px;
  height: 32px;
  font-size: 0.9rem;
}
.topbar-account .account-menu {
  bottom: auto;
  top: calc(100% + 8px);
  left: auto;
  right: 0;
}
.app-main {
  flex: 1;
  padding: 8px 8px 24px;
  min-width: 0;
}
.app-footer {
  text-align: left;
  color: var(--muted);
  font-size: 0.8rem;
  padding: 8px 8px 16px;
  border-top: none;
}
.tabbar {
  display: none;
}

/* 中屏：仅图标的收起导航栏 */
@media (max-width: 1260px) {
  .shell {
    grid-template-columns: var(--rail-w-sm) minmax(0, 1fr);
    padding: 12px;
  }
  .rail {
    align-items: center;
    padding: 10px 8px;
  }
  .rail-label,
  .rail-sep {
    display: none;
  }
  .rail-logo {
    width: auto;
    padding: 8px;
  }
  .rail-pill {
    padding: 12px;
    gap: 0;
  }
  .rail-cta {
    width: 48px;
    height: 48px;
  }
  .rail-cta-icon {
    display: block;
  }
  .account-chip {
    width: auto;
    padding: 8px;
    border-radius: 14px;
  }
  .account-menu {
    left: 0;
  }
}
/* 小屏：底部标签栏 */
@media (max-width: 700px) {
  .shell {
    grid-template-columns: minmax(0, 1fr);
    padding: 0;
    gap: 0;
  }
  .rail {
    display: none;
  }
  .column {
    border: none;
    min-height: 100vh;
    padding-bottom: calc(56px + env(safe-area-inset-bottom, 0px));
  }
  .topbar {
    padding: 0 16px;
    height: 56px;
  }
  .topbar-sub {
    display: none;
  }
  .topbar-account {
    display: block;
  }
  .app-main {
    padding: 12px 16px 24px;
  }
  .tabbar {
    display: flex;
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    height: auto;
    min-height: 56px;
    padding: 4px 2px env(safe-area-inset-bottom, 0px);
    justify-content: space-around;
    align-items: stretch;
    background: var(--header-bg);
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter: blur(12px);
    border-top: 1px solid var(--line);
    z-index: 30;
  }
  .tabbar-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    min-width: 0;
    padding: 6px 2px;
    border: none;
    border-radius: 0;
    background: transparent;
    color: var(--muted);
    font-weight: 500;
    height: auto;
  }
  .tabbar-item:hover:not(:disabled) {
    background: transparent;
    color: var(--text);
  }
  .tabbar-item.active {
    color: var(--nl-yellow-text);
    font-weight: 700;
  }
  .tab-label {
    font-size: 0.68rem;
    line-height: 1.2;
    white-space: nowrap;
  }
  .admin-sheet-mask {
    position: fixed;
    inset: 0;
    background: var(--mask);
    z-index: 35;
    display: flex;
    align-items: flex-end;
  }
  .admin-sheet {
    width: 100%;
    background: var(--bg-elevated);
    border-radius: 20px 20px 0 0;
    padding: 16px 16px calc(16px + env(safe-area-inset-bottom, 0px));
    display: grid;
    gap: 4px;
  }
  .admin-sheet h3 {
    font-size: 1.1rem;
    padding: 4px 8px 12px;
  }
  .admin-sheet-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 8px;
    border-radius: 12px;
    color: var(--text);
    font-weight: 700;
  }
  .admin-sheet-item:hover {
    text-decoration: none;
    background: var(--bg-hover-strong);
  }
  .admin-sheet-item.active {
    background: var(--brand-soft);
    color: var(--text);
  }
}
@media (max-width: 900px) {
  .auth-layout {
    grid-template-columns: 1fr;
  }
  .auth-cover {
    height: 220px;
  }
  .auth-side {
    padding: 24px 20px 40px;
  }
}
</style>

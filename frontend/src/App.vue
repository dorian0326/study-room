<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth, can, logout } from './auth.js'
import { theme, toggleTheme } from './theme.js'
import XIcon from './components/XIcon.vue'
import logoUrl from './assets/nailong/nailong-logo.png'
import coverUrl from './assets/nailong/cover.jpg'
import sillyUrl from './assets/nailong/nailong-silly.webp'

const BRAND = '奶龙自习室'
const router = useRouter()
const route = useRoute()
const menuOpen = ref(false)
const menuRef = ref(null)

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
    document.title = route.path === '/' ? BRAND : `${pageTitle.value} / ${BRAND}`
  },
  { immediate: true },
)

function isActive(to) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

function onDocClick(e) {
  if (menuOpen.value && menuRef.value && !menuRef.value.contains(e.target)) menuOpen.value = false
}
function onKey(e) {
  if (e.key === 'Escape') menuOpen.value = false
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
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
        <span>约座 · 签到 · 专注，每一天</span>
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
            <XIcon :name="link.icon" :bold="isActive(link.to)" />
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
            <small>{{ auth.user.student_no }} · {{ roleText }}</small>
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
      </div>
      <main class="app-main"><RouterView /></main>
      <footer class="app-footer">{{ BRAND }} · 软件工程课程设计</footer>
    </div>

    <!-- 移动端底部标签栏 -->
    <nav class="tabbar" aria-label="底部导航">
      <RouterLink
        v-for="link in mainLinks"
        :key="link.to"
        :to="link.to"
        :class="{ active: isActive(link.to) }"
        :aria-label="link.label"
      >
        <XIcon :name="link.icon" :bold="isActive(link.to)" />
      </RouterLink>
    </nav>
  </div>
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
  background: #1a1408;
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
  background: linear-gradient(180deg, transparent 55%, rgba(0, 0, 0, 0.72));
}
.auth-cover-text {
  position: absolute;
  left: 32px;
  bottom: 28px;
  z-index: 1;
  display: grid;
  gap: 2px;
  color: #fff;
}
.auth-cover-logo {
  width: 44px;
  margin-bottom: 6px;
}
.auth-cover-text strong {
  font-size: 1.9rem;
  font-weight: 800;
}
.auth-cover-text span {
  color: rgba(255, 255, 255, 0.82);
}
.auth-side {
  position: relative;
  display: grid;
  align-content: center;
  padding: 32px;
}
.auth-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-self: center;
  font-weight: 800;
  font-size: 1.1rem;
}
.auth-brand img {
  width: 40px;
}
.auth-side :deep(.auth-wrap) {
  min-height: 0;
}
.theme-btn {
  position: absolute;
  top: 16px;
  right: 16px;
}

/* ---------- 应用外壳 ---------- */
.shell {
  display: grid;
  grid-template-columns: var(--rail-w) minmax(0, 1fr);
  max-width: calc(var(--rail-w) + 1000px);
  margin: 0 auto;
  min-height: 100vh;
}
.rail {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 4px 12px 12px;
  overflow-y: auto;
  scrollbar-width: none;
}
.rail-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  margin: 4px 0;
  border-radius: 9999px;
  color: var(--text);
  width: fit-content;
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
  font-weight: 800;
  font-size: 1.15rem;
  color: var(--nl-yellow-text);
}
.rail-nav {
  display: grid;
  gap: 0;
}
.rail-item {
  display: flex;
  color: var(--text);
  padding: 2px 0;
}
.rail-item:hover {
  text-decoration: none;
}
.rail-pill {
  display: inline-flex;
  align-items: center;
  gap: 18px;
  padding: 10px 22px 10px 12px;
  border-radius: 9999px;
  font-size: 1.15rem;
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
  font-weight: 800;
}
.rail-item.active .x-icon {
  color: var(--text);
}
.rail-sep {
  margin: 10px 12px 4px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 700;
}
.rail-nav .rail-sep ~ .rail-item .rail-pill {
  font-size: 1rem;
  padding-top: 8px;
  padding-bottom: 8px;
}
.rail-cta {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 52px;
  margin: 14px 0;
  width: 90%;
  border-radius: 9999px;
  background: var(--brand);
  color: #fff;
  font-weight: 800;
  font-size: 1.05rem;
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
  padding: 10px 12px;
  border: none;
  background: transparent;
  font-weight: 400;
  text-align: left;
}
.avatar {
  flex: none;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--nl-yellow);
  color: #2b1d00;
  font-weight: 800;
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
  font-size: 0.9rem;
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
  background: var(--bg);
  border-radius: 16px;
  box-shadow:
    0 0 15px rgba(255, 255, 255, 0.12),
    0 0 3px 1px rgba(255, 255, 255, 0.08);
  z-index: 60;
  display: grid;
}
[data-theme='light'] .account-menu {
  box-shadow:
    rgba(101, 119, 134, 0.2) 0 0 15px,
    rgba(101, 119, 134, 0.15) 0 0 3px 1px;
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
  max-width: var(--main-max);
  border-left: 1px solid var(--line);
  border-right: 1px solid var(--line);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.shell.wide .column {
  max-width: 1000px;
}
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: baseline;
  gap: 10px;
  height: 53px;
  padding: 0 16px;
  align-items: center;
  background: var(--header-bg);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--line);
}
.topbar h1 {
  font-size: 1.25rem;
  font-weight: 800;
}
.topbar-sub {
  color: var(--muted);
  font-size: 0.85rem;
}
.app-main {
  flex: 1;
  padding: 16px;
  min-width: 0;
}
.app-footer {
  text-align: center;
  color: var(--muted);
  font-size: 0.8rem;
  padding: 16px 0 24px;
  border-top: 1px solid var(--line);
}
.tabbar {
  display: none;
}

/* 中屏：仅图标的收起导航栏 */
@media (max-width: 1260px) {
  .shell {
    grid-template-columns: var(--rail-w-sm) minmax(0, 1fr);
  }
  .rail {
    align-items: center;
    padding: 4px 4px 12px;
  }
  .rail-label,
  .rail-sep {
    display: none;
  }
  .rail-pill {
    padding: 12px;
    gap: 0;
  }
  .rail-cta {
    width: 52px;
  }
  .rail-cta-icon {
    display: block;
  }
  .account-chip {
    width: auto;
    padding: 8px;
    border-radius: 9999px;
  }
  .account-menu {
    left: 0;
  }
}
/* 小屏：底部标签栏 */
@media (max-width: 700px) {
  .shell {
    grid-template-columns: minmax(0, 1fr);
  }
  .rail {
    display: none;
  }
  .column {
    border: none;
    padding-bottom: 56px;
  }
  .tabbar {
    display: flex;
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    height: 54px;
    justify-content: space-around;
    align-items: center;
    background: var(--header-bg);
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter: blur(12px);
    border-top: 1px solid var(--line);
    z-index: 30;
  }
  .tabbar a {
    color: var(--text);
    padding: 8px 14px;
  }
}
@media (max-width: 900px) {
  .auth-layout {
    grid-template-columns: 1fr;
  }
  .auth-cover {
    height: 220px;
  }
}
</style>

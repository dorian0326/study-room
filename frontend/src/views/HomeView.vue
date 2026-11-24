<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client.js'
import { auth, can } from '../auth.js'
import StatusBadge from '../components/StatusBadge.vue'
import XIcon from '../components/XIcon.vue'
import NlLoading from '../components/NlLoading.vue'
import EmptyState from '../components/EmptyState.vue'
import helloUrl from '../assets/nailong/nailong-hello.webp'

const health = ref(null)
const error = ref('')
const mine = ref([])
const rooms = ref([])
const overviewLoaded = ref(false)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 11) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
const openRooms = computed(() => rooms.value.filter((r) => r.status === 'open').length)
const isAdmin = computed(() => can('room:manage') || can('user:manage'))

function fmt(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', {
    hour12: false,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function today() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/** 加载首页展示的 API 健康状态摘要。 */
async function loadHealth() {
  // 健康检查失败只展示在首页，不阻止用户继续使用其他业务页面。
  try {
    health.value = await api('/health')
  } catch (cause) {
    error.value = String(cause)
  }
}

/** 概览数据失败时静默降级，首页仍可用。 */
async function loadOverview() {
  try {
    mine.value = await api('/reservations?scope=current')
  } catch {
    mine.value = []
  }
  try {
    rooms.value = await api(`/rooms?date=${today()}`)
  } catch {
    rooms.value = []
  } finally {
    overviewLoaded.value = true
  }
}

onMounted(() => {
  loadHealth()
  loadOverview()
})

const ROLE_LABELS = { user: '学生', admin: '管理员', ops: '运维' }
const roleText = computed(() => (auth.user?.roles || []).map((r) => ROLE_LABELS[r] || r).join('、'))
</script>

<template>
  <div class="home">
    <div class="feed">
      <section class="hero">
        <img :src="helloUrl" alt="奶龙挥手打招呼" class="nl-art hero-art" />
        <div class="hero-body">
          <p class="eyebrow">{{ greeting }}</p>
          <h2>{{ auth.user?.name }}，今天也来专注学习吧</h2>
          <p class="hero-sub">
            角色：{{ roleText }} · 浏览自习室与座位、创建 / 改约 / 取消预约，用桌上二维码签到。
          </p>
          <div class="row hero-actions">
            <RouterLink to="/workflows" class="btn-link primary">预约座位</RouterLink>
            <RouterLink to="/check-in" class="btn-link">扫码签到</RouterLink>
          </div>
        </div>
      </section>

      <div class="feed-head">
        <h3>我的预约</h3>
        <RouterLink to="/workflows">查看全部</RouterLink>
      </div>
      <NlLoading v-if="!overviewLoaded" />
      <ul v-else-if="mine.length" class="res-list">
        <li v-for="row in mine.slice(0, 5)" :key="row.id">
          <span class="res-icon"><XIcon name="seat" :size="20" /></span>
          <div class="res-main">
            <strong>{{ row.room_name }} · {{ row.seat_code }}</strong>
            <small class="hint">{{ fmt(row.start_time) }} – {{ fmt(row.end_time) }}</small>
          </div>
          <StatusBadge :status="row.status" />
        </li>
      </ul>
      <EmptyState
        v-else
        class="feed-empty"
        title="暂无进行中的预约"
        action-to="/workflows"
        action-text="去预约一个座位"
      />

      <div class="feed-head">
        <h3>快捷入口</h3>
      </div>
      <nav class="quick">
        <RouterLink to="/workflows"><XIcon name="calendar" :size="22" />预约自习室</RouterLink>
        <RouterLink to="/check-in"><XIcon name="qr" :size="22" />扫码签到</RouterLink>
        <RouterLink to="/violations"><XIcon name="alert" :size="22" />违规记录</RouterLink>
        <RouterLink to="/notifications"><XIcon name="bell" :size="22" />消息通知</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/config"
          ><XIcon name="building" :size="22" />自习室配置</RouterLink
        >
        <RouterLink v-if="can('user:manage')" to="/admin/users"
          ><XIcon name="users" :size="22" />用户管理</RouterLink
        >
      </nav>
    </div>

    <aside class="side">
      <section class="side-card">
        <h3>系统状态</h3>
        <div class="side-row">
          <template v-if="health">
            <strong class="ok">● 运行正常</strong>
            <small class="hint"
              >{{ health.status }} · {{ health.database }} · {{ health.timezone }}</small
            >
          </template>
          <template v-else-if="error">
            <strong class="error">● 后端不可用</strong>
            <small class="hint">{{ error }}</small>
          </template>
          <strong v-else class="hint">检测中…</strong>
        </div>
      </section>
      <section class="side-card">
        <h3>今日概览</h3>
        <div class="side-row">
          <small class="hint">进行中的预约</small>
          <strong class="big">{{ overviewLoaded ? mine.length : '…' }}</strong>
        </div>
        <div class="side-row">
          <small class="hint">今日开放自习室</small>
          <strong class="big"
            >{{ overviewLoaded ? openRooms : '…'
            }}<small v-if="overviewLoaded" class="hint"> / {{ rooms.length }}</small></strong
          >
        </div>
        <div class="side-row">
          <small class="hint">当前角色</small>
          <strong>{{ roleText }}</strong>
        </div>
      </section>
    </aside>
  </div>
</template>

<style scoped>
.home {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 24px;
  align-items: start;
}
.hero {
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 16px 20px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background:
    radial-gradient(120% 140% at 0% 0%, var(--nl-yellow-soft), transparent 60%), var(--bg);
}
.hero-art {
  width: 96px;
  flex: none;
}
.hero-body {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.eyebrow {
  color: var(--nl-yellow-text);
  font-weight: 700;
}
.hero h2 {
  font-size: 1.3rem;
}
.hero-sub {
  color: var(--muted);
}
.hero-actions {
  margin-top: 6px;
}
.btn-link {
  display: inline-flex;
  align-items: center;
  height: 36px;
  padding: 0 18px;
  border-radius: 9999px;
  border: 1px solid var(--line);
  color: var(--text);
  font-weight: 700;
}
.btn-link:hover {
  text-decoration: none;
  background: var(--bg-hover-strong);
}
.btn-link.primary {
  background: var(--pill-bg);
  color: var(--pill-text);
  border-color: transparent;
}
.btn-link.primary:hover {
  background: var(--pill-hover);
}
.feed-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px 0 0;
  padding: 12px 4px;
  border-bottom: 1px solid var(--line);
}
.feed-head h3 {
  font-size: 1.2rem;
  font-weight: 800;
}
.res-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.res-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--line);
  transition: background 0.15s;
}
.res-list li:hover {
  background: var(--bg-hover);
}
.res-icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--brand-soft);
  color: var(--brand);
  flex: none;
}
.res-main {
  display: grid;
  flex: 1;
  min-width: 0;
}
.feed-empty {
  margin-top: 12px;
}
.quick {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
}
.quick a {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 8px;
  color: var(--text);
  font-weight: 700;
  border-bottom: 1px solid var(--line);
}
.quick a:hover {
  text-decoration: none;
  background: var(--bg-hover);
}
.side {
  position: sticky;
  top: 69px;
  display: grid;
  gap: 16px;
}
.side-card {
  border-radius: 16px;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  overflow: hidden;
}
.side-card h3 {
  padding: 12px 16px;
  font-size: 1.2rem;
  font-weight: 800;
}
.side-row {
  display: grid;
  gap: 2px;
  padding: 10px 16px;
  border-top: 1px solid var(--line);
}
.side-row:hover {
  background: var(--bg-hover);
}
.big {
  font-size: 1.4rem;
  font-weight: 800;
}
@media (max-width: 1000px) {
  .home {
    grid-template-columns: minmax(0, 1fr);
  }
  .side {
    position: static;
  }
}
</style>

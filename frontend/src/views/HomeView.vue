<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client.js'
import { auth, can } from '../auth.js'
import StatusBadge from '../components/StatusBadge.vue'

const health = ref(null)
const error = ref('')
const mine = ref([])
const rooms = ref([])

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
  }
}

onMounted(() => {
  loadHealth()
  loadOverview()
})
</script>

<template>
  <section class="hero">
    <div>
      <p class="eyebrow">{{ greeting }}</p>
      <h2>{{ auth.user?.name }}，今天也来专注学习吧</h2>
      <p class="hero-sub">
        角色：{{ auth.user?.roles.join('、') }} ·
        可浏览自习室与座位、创建/改约/取消预约，并用桌上二维码签到。
      </p>
      <div class="row hero-actions">
        <RouterLink to="/workflows" class="btn-link primary">预约座位</RouterLink>
        <RouterLink to="/check-in" class="btn-link">扫码签到</RouterLink>
      </div>
    </div>
    <div class="status-card">
      <span class="hint">系统状态</span>
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

  <section class="metrics">
    <article>
      <span>进行中的预约</span>
      <strong>{{ mine.length }}</strong>
    </article>
    <article>
      <span>今日开放自习室</span>
      <strong
        >{{ openRooms }}<small> / {{ rooms.length }}</small></strong
      >
    </article>
    <article>
      <span>当前角色</span>
      <strong class="role">{{ auth.user?.roles.join('、') }}</strong>
    </article>
  </section>

  <div class="home-grid">
    <section class="panel">
      <div class="row between">
        <h3>我的预约</h3>
        <RouterLink to="/workflows">查看全部 →</RouterLink>
      </div>
      <ul v-if="mine.length" class="res-list">
        <li v-for="row in mine.slice(0, 4)" :key="row.id">
          <div>
            <strong>{{ row.room_name }} · {{ row.seat_code }}</strong>
            <small class="hint">{{ fmt(row.start_time) }} – {{ fmt(row.end_time) }}</small>
          </div>
          <StatusBadge :status="row.status" />
        </li>
      </ul>
      <div v-else class="empty">
        <span>暂无进行中的预约</span>
        <RouterLink to="/workflows">去预约一个座位</RouterLink>
      </div>
    </section>

    <section class="panel">
      <h3>快捷入口</h3>
      <div class="quick">
        <RouterLink to="/workflows"><b>📚</b>预约自习室</RouterLink>
        <RouterLink to="/check-in"><b>📷</b>扫码签到</RouterLink>
        <RouterLink to="/violations"><b>⚠️</b>违规记录</RouterLink>
        <RouterLink to="/notifications"><b>🔔</b>消息通知</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/config"><b>🏫</b>自习室配置</RouterLink>
        <RouterLink v-if="can('user:manage')" to="/admin/users"><b>👥</b>用户管理</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 28px 32px;
  margin-bottom: 16px;
  border-radius: var(--radius-lg);
  background: linear-gradient(120deg, #eaf1fd 0%, #e6f7f3 100%);
  border: 1px solid #dbe6f8;
}
.eyebrow {
  color: var(--brand);
  font-weight: 600;
}
.hero h2 {
  margin: 4px 0 6px;
  font-size: 1.6rem;
}
.hero-sub {
  color: var(--muted);
  max-width: 620px;
}
.hero-actions {
  margin-top: 16px;
}
.btn-link {
  display: inline-flex;
  align-items: center;
  height: 38px;
  padding: 0 18px;
  border-radius: var(--radius-sm);
  background: #fff;
  border: 1px solid var(--line-strong);
  color: var(--text);
  font-weight: 500;
}
.btn-link.primary {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
.btn-link:hover {
  text-decoration: none;
  filter: brightness(0.97);
}
.status-card {
  display: grid;
  gap: 4px;
  min-width: 220px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: var(--radius);
  border: 1px solid #dbe6f8;
}
.metrics {
  margin-bottom: 16px;
}
.metrics small {
  font-size: 0.9rem;
  color: var(--muted);
  font-weight: 400;
}
.metrics .role {
  font-size: 1.1rem;
  line-height: 2.2rem;
}
.home-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 16px;
}
.res-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.res-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}
.res-list li div {
  display: grid;
}
.quick {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.quick a {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-weight: 500;
}
.quick a:hover {
  text-decoration: none;
  border-color: var(--brand);
  background: var(--brand-soft);
}
.quick b {
  font-size: 1.1rem;
}
@media (max-width: 960px) {
  .hero,
  .home-grid {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>

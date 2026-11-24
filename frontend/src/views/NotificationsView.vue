<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client.js'
import NlLoading from '../components/NlLoading.vue'
import EmptyState from '../components/EmptyState.vue'

const notifications = ref([])
const unreadOnly = ref(false)
const error = ref('')
const loading = ref(true)

/** 加载当前登录用户最近收到的站内通知。 */
async function loadNotifications() {
  error.value = ''
  try {
    const filter = unreadOnly.value ? '?unread_only=true' : ''
    notifications.value = await api(`/notifications${filter}`)
  } catch (cause) {
    error.value = cause.message
  } finally {
    loading.value = false
  }
}

/** 将通知标为已读并刷新通知列表。 */
async function markRead(notification) {
  error.value = ''
  try {
    await api(`/notifications/${notification.id}/read`, { method: 'POST' })
    await loadNotifications()
    window.dispatchEvent(new Event('studyroom:notifications-changed'))
  } catch (cause) {
    error.value = cause.message
  }
}

/** 将通知类型映射为通知列表中的中文名称。 */
function typeLabel(type) {
  const labels = {
    reservation_confirmed: '预约结果',
    checkin_reminder: '签到提醒',
    violation: '违规 / 申诉',
    maintenance: '座位维护',
    temp_leave: '临时离开',
    system: '系统通知',
  }
  return labels[type] ?? type
}

/** 按浏览器本地格式展示通知时间。 */
function formatTime(value) {
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(loadNotifications)
</script>

<template>
  <label class="filter"
    ><input v-model="unreadOnly" type="checkbox" @change="loadNotifications" /> 只看未读</label
  >
  <p v-if="error" class="error">{{ error }}</p>
  <NlLoading v-if="loading" />
  <EmptyState
    v-else-if="!notifications.length"
    :title="unreadOnly ? '没有未读通知' : '暂时没有通知'"
  />
  <ol v-else class="inbox">
    <li
      v-for="notification in notifications"
      :key="notification.id"
      :class="{ unread: !notification.is_read }"
    >
      <div class="notice-heading">
        <strong>{{ typeLabel(notification.type) }}</strong>
        <time>{{ formatTime(notification.sent_at) }}</time>
      </div>
      <p>{{ notification.content }}</p>
      <button v-if="!notification.is_read" @click="markRead(notification)">标记已读</button>
      <span v-else class="read-status">已读</span>
    </li>
  </ol>
</template>

<style scoped>
.filter {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 12px;
}
.inbox {
  display: grid;
  gap: 0.75rem;
  padding: 0;
  list-style: none;
}
.inbox li.unread {
  border-left: 4px solid var(--brand);
  background: var(--brand-soft);
}
.notice-heading {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}
.notice-heading time,
.read-status {
  color: var(--muted);
  font-size: 0.9rem;
}
</style>

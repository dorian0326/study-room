<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client.js'

const notifications = ref([])
const unreadOnly = ref(false)
const error = ref('')

/** 加载当前登录用户最近收到的站内通知。 */
async function loadNotifications() {
  // 通知所有权由后端根据当前会话验证。
  error.value = ''
  try {
    const filter = unreadOnly.value ? '?unread_only=true' : ''
    notifications.value = await api(`/notifications${filter}`)
  } catch (cause) {
    error.value = cause.message
  }
}

/** 将通知标为已读并刷新通知列表。 */
async function markRead(notification) {
  // 重复标记已读不会改变结果，因此可以安全地重新请求。
  error.value = ''
  try {
    await api(`/notifications/${notification.id}/read`, { method: 'POST' })
    await loadNotifications()
  } catch (cause) {
    error.value = cause.message
  }
}

/** 将通知类型映射为通知列表中的中文名称。 */
function typeLabel(type) {
  // 分类名称覆盖预约、门禁、维护、违规和临时离开等事件。
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
  // ISO 时间包含服务端 UTC+8 偏移，可由 Date 转换为本地显示时间。
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(loadNotifications)
</script>

<template>
  <h2>站内通知</h2>
  <label class="filter"><input v-model="unreadOnly" type="checkbox" @change="loadNotifications" /> 只看未读</label>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="!notifications.length">暂无通知。</p>
  <ol class="inbox">
    <li v-for="notification in notifications" :key="notification.id" :class="{ unread: !notification.is_read }">
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
.filter { display: inline-flex; align-items: center; gap: 0.4rem; }
.inbox { display: grid; gap: 0.75rem; padding: 0; list-style: none; }
.inbox li { padding: 1rem; border: 1px solid #d9e2dc; border-radius: 0.75rem; }
.inbox li.unread { border-left: 4px solid #28785d; background: #f4faf6; }
.notice-heading { display: flex; justify-content: space-between; gap: 1rem; }
.notice-heading time, .read-status { color: #66736d; font-size: 0.9rem; }
</style>

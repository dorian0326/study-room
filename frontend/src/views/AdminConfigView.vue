<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api/client.js'

const DAY_TYPES = { weekday: '工作日', weekend: '周末', holiday: '节假日', exam_week: '考试周' }
const SETTING_LABELS = {
  advance_booking_days: '最多提前预约天数',
  max_active_reservations: '同时有效预约上限',
  checkin_open_before_minutes: '开始前可签到（分钟）',
  no_show_after_minutes: '未签到记爽约（分钟）',
  late_cancel_minutes: '开始前取消记违规（分钟）',
  temp_leave_minutes: '临时离开时长（固定 30 分钟）',
  missed_checkout_merge: '几次未结束使用合并为 1 次警告',
  violation_window_days: '违规累计窗口（天）',
  penalty_base_threshold: '第 1 档处罚阈值（次）',
  penalty_threshold_step: '每档阈值递增（次）',
  penalty_days_per_tier: '每档禁约天数',
  opening_earliest: '开放最早时间',
  opening_latest: '开放最晚时间',
}

const error = ref('')
const notice = ref('')
const rooms = ref([])
const roomForm = reactive({
  id: null,
  name: '',
  location: '',
  floor: '',
  capacity: 0,
  facilities: '',
})
const current = ref(null)
const schedules = ref([])
const schForm = reactive({ day_type: 'weekday', open_time: '08:00', close_time: '22:00' })
const calendar = ref([])
const dayForm = reactive({ day: '', day_type: 'holiday', note: '' })
const settings = ref(null)

/** 运行系统配置操作并统一显示成功或失败消息。 */
async function guard(fn, ok) {
  error.value = ''
  notice.value = ''
  try {
    await fn()
    if (ok) notice.value = ok
  } catch (e) {
    error.value = e.message
  }
}

/** 加载管理员可配置的自习室列表。 */
async function loadRooms() {
  rooms.value = await api('/admin/rooms')
}

/** 将指定自习室的数据载入编辑表单。 */
function editRoom(r) {
  Object.assign(roomForm, r)
}

/** 新增或更新自习室并刷新列表。 */
function saveRoom() {
  // 按是否存在数据库编号选择新增或更新接口。
  return guard(async () => {
    const { id, ...body } = roomForm
    await api(id ? `/admin/rooms/${id}` : '/admin/rooms', { method: id ? 'PUT' : 'POST', body })
    Object.assign(roomForm, {
      id: null,
      name: '',
      location: '',
      floor: '',
      capacity: 0,
      facilities: '',
    })
    await loadRooms()
  }, '已保存自习室')
}

/** 开放或关闭指定自习室。 */
function toggleRoom(r) {
  const status = r.status === 'open' ? 'closed' : 'open'
  return guard(async () => {
    await api(`/admin/rooms/${r.id}/status`, { method: 'PATCH', body: { status } })
    await loadRooms()
  })
}

/** 删除尚未关联座位或预约历史的自习室。 */
function deleteRoom(r) {
  if (!confirm(`删除自习室「${r.name}」？`)) return
  return guard(async () => {
    await api(`/admin/rooms/${r.id}`, { method: 'DELETE' })
    if (current.value?.id === r.id) current.value = null
    await loadRooms()
  }, '已删除')
}

/** 读取指定自习室的开放时间列表。 */
async function openSchedules(r) {
  current.value = r
  await guard(async () => {
    schedules.value = await api(`/admin/rooms/${r.id}/schedules`)
  })
}

/** 为当前自习室新增开放时间。 */
function addSchedule() {
  return guard(async () => {
    await api(`/admin/rooms/${current.value.id}/schedules`, { method: 'POST', body: schForm })
    schedules.value = await api(`/admin/rooms/${current.value.id}/schedules`)
  }, '已添加开放时段')
}

/** 删除选中的开放时间设置。 */
function deleteSchedule(s) {
  return guard(async () => {
    await api(`/admin/rooms/${current.value.id}/schedules/${s.id}`, { method: 'DELETE' })
    schedules.value = await api(`/admin/rooms/${current.value.id}/schedules`)
  })
}

/** 加载节假日和考试周校历。 */
async function loadCalendar() {
  calendar.value = await api('/admin/calendar')
}

/** 新增或更新校历特殊日期。 */
function saveDay() {
  return guard(async () => {
    await api(`/admin/calendar/${dayForm.day}`, { method: 'PUT', body: dayForm })
    await loadCalendar()
  }, '已保存特殊日期')
}

/** 移除指定特殊日期并刷新校历。 */
function deleteDay(d) {
  return guard(async () => {
    await api(`/admin/calendar/${d.day}`, { method: 'DELETE' })
    await loadCalendar()
  })
}

/** 保存系统业务参数并更新页面显示。 */
function saveSettings() {
  return guard(async () => {
    settings.value = await api('/admin/settings', { method: 'PUT', body: settings.value })
  }, '业务参数已保存')
}

/** 并行加载系统配置页面所需的初始数据。 */
async function loadInitialConfig() {
  await guard(async () => {
    await Promise.all([loadRooms(), loadCalendar()])
    settings.value = await api('/admin/settings')
  })
}

onMounted(loadInitialConfig)
</script>

<template>
  <h2>系统配置</h2>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>

  <section>
    <h3>自习室</h3>
    <table>
      <tr v-for="r in rooms" :key="r.id">
        <td>{{ r.name }}</td>
        <td>{{ r.location }}</td>
        <td>{{ r.floor || '—' }}</td>
        <td>容量 {{ r.capacity }}</td>
        <td>{{ r.status === 'open' ? '开放' : '关闭' }}</td>
        <td>
          <button @click="editRoom(r)">编辑</button>
          <button @click="toggleRoom(r)">{{ r.status === 'open' ? '关闭' : '开放' }}</button>
          <button @click="openSchedules(r)">开放时间</button>
          <button @click="deleteRoom(r)">删除</button>
        </td>
      </tr>
    </table>
    <form @submit.prevent="saveRoom">
      <input v-model="roomForm.name" placeholder="名称" required />
      <input v-model="roomForm.location" placeholder="位置" />
      <input v-model="roomForm.floor" placeholder="楼层" />
      <input v-model.number="roomForm.capacity" type="number" min="0" placeholder="容量" />
      <input v-model="roomForm.facilities" placeholder="设施" />
      <button>{{ roomForm.id ? '保存修改' : '新增自习室' }}</button>
    </form>
  </section>

  <section v-if="current">
    <h3>{{ current.name }} 的开放时间（06:00–23:30 内，不跨零点）</h3>
    <ul>
      <li v-for="s in schedules" :key="s.id">
        {{ DAY_TYPES[s.day_type] }} {{ s.open_time.slice(0, 5) }}–{{ s.close_time.slice(0, 5) }}
        <span v-if="s.effective_from">（{{ s.effective_from }} ~ {{ s.effective_to }}）</span>
        <button @click="deleteSchedule(s)">删除</button>
      </li>
    </ul>
    <form @submit.prevent="addSchedule">
      <select v-model="schForm.day_type">
        <option v-for="(label, k) in DAY_TYPES" :key="k" :value="k">{{ label }}</option>
      </select>
      <input v-model="schForm.open_time" type="time" />
      <input v-model="schForm.close_time" type="time" />
      <button>添加</button>
    </form>
  </section>

  <section>
    <h3>节假日 / 考试周</h3>
    <ul>
      <li v-for="d in calendar" :key="d.day">
        {{ d.day }} {{ DAY_TYPES[d.day_type] }} {{ d.note }}
        <button @click="deleteDay(d)">删除</button>
      </li>
    </ul>
    <form @submit.prevent="saveDay">
      <input v-model="dayForm.day" type="date" required />
      <select v-model="dayForm.day_type">
        <option value="holiday">节假日</option>
        <option value="exam_week">考试周</option>
      </select>
      <input v-model="dayForm.note" placeholder="备注" />
      <button>保存</button>
    </form>
  </section>

  <section v-if="settings">
    <h3>业务参数</h3>
    <form class="card" @submit.prevent="saveSettings">
      <label v-for="(label, key) in SETTING_LABELS" :key="key">
        {{ label }}
        <input v-if="key.startsWith('opening_')" v-model="settings[key]" type="time" step="60" />
        <input
          v-else
          v-model.number="settings[key]"
          type="number"
          min="0"
          :disabled="key === 'temp_leave_minutes'"
        />
      </label>
      <button>保存参数</button>
    </form>
  </section>
</template>

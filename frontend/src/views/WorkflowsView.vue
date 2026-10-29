<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client.js'

const router = useRouter()

const STATUS = {
  RESERVED: '已预约',
  ACTIVE: '使用中',
  TEMP_LEAVE: '暂离',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  EXPIRED: '已过期',
  NO_SHOW: '爽约',
  available: '空闲',
  AVAILABLE: '空闲',
  reserved: '已预约',
  in_use: '使用中',
  IN_USE: '使用中',
  maintenance: '维护中',
  disabled: '停用',
  closed: '关闭',
  CLOSED: '关闭',
}

const ZONE = { quiet: '静音区', discussion: '讨论区', open: '开放区', exam_prep: '考研区' }

const error = ref('')
const notice = ref('')
const rooms = ref([])
const seats = ref([])
const mine = ref([])
const selectedSeat = ref(null)

const search = reactive({
  room_id: '',
  date: '',
  start_time: '09:00',
  end_time: '11:00',
  zone_type: '',
  available_only: true,
})

const form = reactive({
  room_id: '',
  seat_id: '',
  start_time: '',
  end_time: '',
  request_key: '',
})

const changeForm = reactive({ reservation_id: '', seat_id: '' })

const LATE_CANCEL_MINUTES = 15

const roomOptions = computed(() => rooms.value)

function fmt(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function hoursText(room) {
  if (!room.opening_hours?.length) return '本日无开放时段'
  return room.opening_hours
    .map((w) => `${String(w.open_time).slice(0, 5)}–${String(w.close_time).slice(0, 5)}`)
    .join('，')
}

function defaultDate() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function toIso(date, time) {
  return `${date}T${time}:00`
}

function isLateCancel(row) {
  const start = new Date(row.start_time).getTime()
  return start - Date.now() <= LATE_CANCEL_MINUTES * 60 * 1000
}

async function guard(fn, ok) {
  error.value = ''
  notice.value = ''
  try {
    await fn()
    if (ok) notice.value = ok
  } catch (cause) {
    error.value = cause.message
  }
}

/** 加载自习室目录（含楼层、容量、开放时段）。 */
async function loadRooms() {
  const day = search.date || defaultDate()
  rooms.value = await api(`/rooms?date=${encodeURIComponent(day)}`)
}

/** 按条件搜索座位并刷新实时状态。 */
async function loadSeats() {
  const params = new URLSearchParams()
  if (search.room_id) params.set('room_id', search.room_id)
  if (search.date) params.set('date', search.date)
  if (search.start_time) params.set('start_time', search.start_time)
  if (search.end_time) params.set('end_time', search.end_time)
  if (search.zone_type) params.set('zone_type', search.zone_type)
  if (search.available_only) params.set('available_only', 'true')
  seats.value = await api(`/seats?${params}`)
}

/** 查看单个座位实时详情。 */
async function openSeat(seatId) {
  return guard(async () => {
    const params = new URLSearchParams()
    if (search.date) params.set('date', search.date)
    if (search.start_time) params.set('start_time', search.start_time)
    if (search.end_time) params.set('end_time', search.end_time)
    selectedSeat.value = await api(`/seats/${seatId}?${params}`)
    form.seat_id = String(seatId)
    form.room_id = String(selectedSeat.value.room_id)
  })
}

/** 加载本人当前预约。 */
async function loadMine() {
  mine.value = await api('/reservations?scope=current')
}

async function refreshAll() {
  return guard(async () => {
    if (!search.date) search.date = defaultDate()
    await loadRooms()
    await loadSeats()
    await loadMine()
  })
}

/** 创建预约；409 冲突会由 api 客户端透出可读信息。 */
function createReservation() {
  return guard(async () => {
    if (!form.seat_id || !form.start_time || !form.end_time) {
      throw new Error('请填写座位与开始/结束时间')
    }
    const withTz = (value) => {
      // datetime-local 无时区；后端要求 AwareDatetime，按北京时间补 +08:00。
      if (/[zZ]|[+-]\d{2}:\d{2}$/.test(value)) return value
      return `${value}:00+08:00`.replace(/:00:00\+/, ':00+')
    }
    const body = {
      seat_id: Number(form.seat_id),
      start_time: withTz(form.start_time),
      end_time: withTz(form.end_time),
    }
    if (form.request_key.trim()) body.request_key = form.request_key.trim()
    const created = await api('/reservations', { method: 'POST', body })
    notice.value = `已预约 ${created.reservation_no}`
    form.request_key = ''
    await loadMine()
    await loadSeats()
  })
}

/** 改约到新座位（仍须同日同时段）。 */
function changeSeat() {
  return guard(async () => {
    if (!changeForm.reservation_id || !changeForm.seat_id) {
      throw new Error('请选择预约和新座位')
    }
    await api(`/reservations/${changeForm.reservation_id}/seat`, {
      method: 'PATCH',
      body: { seat_id: Number(changeForm.seat_id) },
    })
    changeForm.reservation_id = ''
    changeForm.seat_id = ''
    await loadMine()
    await loadSeats()
  }, '已改约座位')
}

/** 取消预约；距开始不足 15 分钟会二次确认违规风险。 */
function cancelReservation(row) {
  let msg = `确认取消预约 ${row.reservation_no}？`
  if (isLateCancel(row) && ['RESERVED', 'reserved'].includes(row.status)) {
    msg += `\n距开始不足 ${LATE_CANCEL_MINUTES} 分钟，取消将记迟到取消违规。`
  }
  if (!confirm(msg)) return
  return guard(async () => {
    await api(`/reservations/${row.id}/cancel?confirm=true`, { method: 'POST' })
    await loadMine()
    await loadSeats()
  }, '已取消')
}

function tempLeave(row) {
  return guard(async () => {
    await api(`/reservations/${row.id}/temporary-leave`, { method: 'POST' })
    await loadMine()
  }, '已声明暂离，请在 30 分钟内返回')
}

function endUse(row) {
  return guard(async () => {
    await api(`/reservations/${row.id}/end`, { method: 'POST', body: { confirm: true } })
    await loadMine()
    await loadSeats()
  }, '已结束使用')
}

function useSeatForBooking(seat) {
  form.seat_id = String(seat.id)
  form.room_id = String(seat.room_id)
  if (search.date && search.start_time && search.end_time) {
    form.start_time = toIso(search.date, search.start_time)
    form.end_time = toIso(search.date, search.end_time)
  }
  selectedSeat.value = seat
  notice.value = `已选座位 ${seat.room_name} / ${seat.code}`
}

function goCheckIn(row) {
  router.push({ path: '/check-in', query: { reservation_id: String(row.id) } })
}

function pickRoomSeats(roomId) {
  search.room_id = String(roomId)
  return guard(loadSeats)
}

function startChange(row) {
  changeForm.reservation_id = String(row.id)
  notice.value = `正在为 ${row.reservation_no} 改约，请在下方填写新座位`
}

onMounted(() => {
  search.date = defaultDate()
  const start = new Date()
  start.setMinutes(0, 0, 0)
  start.setHours(start.getHours() + 1)
  const end = new Date(start)
  end.setHours(end.getHours() + 2)
  const pad = (n) => String(n).padStart(2, '0')
  const local = (d) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  form.start_time = local(start)
  form.end_time = local(end)
  refreshAll()
})
</script>

<template>
  <h2>自习室预约</h2>
  <p class="hint">浏览自习室与座位、创建/改约/取消，以及进入扫码签到。</p>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>

  <section class="panel">
    <div class="row between">
      <h3>自习室目录</h3>
      <button type="button" @click="refreshAll">刷新</button>
    </div>
    <div class="filters">
      <label>
        日期
        <input v-model="search.date" type="date" @change="refreshAll" />
      </label>
    </div>
    <div class="cards">
      <article v-for="room in roomOptions" :key="room.id" class="card">
        <header>
          <strong>{{ room.name }}</strong>
          <span class="tag">{{ room.status === 'open' ? '开放' : '关闭' }}</span>
        </header>
        <p>楼层：{{ room.floor || '—' }} · 容量 {{ room.capacity }}</p>
        <p>位置：{{ room.location || '—' }}</p>
        <p>开放：{{ hoursText(room) }}</p>
        <p v-if="room.facilities" class="muted">设施：{{ room.facilities }}</p>
        <button type="button" @click="pickRoomSeats(room.id)">查看座位</button>
      </article>
      <p v-if="!rooms.length" class="hint">暂无自习室。</p>
    </div>
  </section>

  <section class="panel">
    <h3>座位搜索</h3>
    <div class="filters">
      <label>
        自习室
        <select v-model="search.room_id">
          <option value="">全部</option>
          <option v-for="room in rooms" :key="room.id" :value="String(room.id)">
            {{ room.name }}
          </option>
        </select>
      </label>
      <label>
        开始
        <input v-model="search.start_time" type="time" />
      </label>
      <label>
        结束
        <input v-model="search.end_time" type="time" />
      </label>
      <label>
        区域
        <select v-model="search.zone_type">
          <option value="">全部</option>
          <option value="quiet">静音区</option>
          <option value="discussion">讨论区</option>
          <option value="open">开放区</option>
          <option value="exam_prep">考研区</option>
        </select>
      </label>
      <label class="check">
        <input v-model="search.available_only" type="checkbox" />
        仅空闲
      </label>
      <button type="button" @click="guard(loadSeats)">搜索</button>
    </div>
    <table>
      <thead>
        <tr>
          <th>座位</th>
          <th>自习室</th>
          <th>楼层</th>
          <th>区域</th>
          <th>状态</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="seat in seats" :key="seat.id">
          <td>{{ seat.code }}</td>
          <td>{{ seat.room_name }}</td>
          <td>{{ seat.floor || '—' }}</td>
          <td>{{ ZONE[seat.zone_type] || seat.zone_type }}</td>
          <td>{{ STATUS[seat.status] || seat.status }}</td>
          <td class="actions">
            <button type="button" @click="openSeat(seat.id)">详情</button>
            <button
              type="button"
              :disabled="!['available', 'AVAILABLE'].includes(seat.status)"
              @click="useSeatForBooking(seat)"
            >
              选用
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="!seats.length" class="hint">没有符合条件的座位。</p>
  </section>

  <section v-if="selectedSeat" class="panel">
    <h3>座位详情</h3>
    <dl class="detail">
      <div>
        <dt>座位</dt>
        <dd>{{ selectedSeat.room_name }} / {{ selectedSeat.code }}</dd>
      </div>
      <div>
        <dt>楼层 / 位置</dt>
        <dd>{{ selectedSeat.floor || '—' }} · {{ selectedSeat.location || '—' }}</dd>
      </div>
      <div>
        <dt>区域</dt>
        <dd>{{ ZONE[selectedSeat.zone_type] || selectedSeat.zone_type }}</dd>
      </div>
      <div>
        <dt>状态</dt>
        <dd>{{ STATUS[selectedSeat.status] || selectedSeat.status }}</dd>
      </div>
      <div>
        <dt>设施</dt>
        <dd>
          电源 {{ selectedSeat.has_power ? '有' : '无' }} · 靠窗
          {{ selectedSeat.by_window ? '是' : '否' }} · 无障碍
          {{ selectedSeat.accessible ? '是' : '否' }}
        </dd>
      </div>
      <div>
        <dt>签到二维码载荷</dt>
        <dd>
          <code>{{ selectedSeat.qr_payload }}</code>
        </dd>
      </div>
    </dl>
    <button type="button" @click="useSeatForBooking(selectedSeat)">用此座位预约</button>
  </section>

  <section class="panel">
    <h3>创建预约</h3>
    <form class="grid" @submit.prevent="createReservation">
      <label>
        座位 ID
        <input v-model="form.seat_id" required />
      </label>
      <label>
        开始
        <input v-model="form.start_time" type="datetime-local" required />
      </label>
      <label>
        结束
        <input v-model="form.end_time" type="datetime-local" required />
      </label>
      <label>
        幂等键（可选）
        <input v-model="form.request_key" placeholder="至少 8 位，刷新重试时保持不变" />
      </label>
      <button>提交预约</button>
    </form>
    <p class="hint">同一时段只能约一个座位；冲突会返回 409 并提示对方预约号。</p>
  </section>

  <section class="panel">
    <h3>我的当前预约</h3>
    <table>
      <thead>
        <tr>
          <th>单号</th>
          <th>座位</th>
          <th>时段</th>
          <th>状态</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in mine" :key="row.id">
          <td>{{ row.reservation_no }}</td>
          <td>{{ row.room_name }} / {{ row.seat_code }}</td>
          <td>{{ fmt(row.start_time) }} → {{ fmt(row.end_time) }}</td>
          <td>
            {{ STATUS[row.status] || row.status }}
            <span v-if="isLateCancel(row) && row.status === 'RESERVED'" class="warn">
              · 临近开始
            </span>
          </td>
          <td class="actions">
            <button v-if="row.status === 'RESERVED'" type="button" @click="goCheckIn(row)">
              签到
            </button>
            <button v-if="row.status === 'RESERVED'" type="button" @click="startChange(row)">
              改座位
            </button>
            <button v-if="row.status === 'ACTIVE'" type="button" @click="tempLeave(row)">
              暂离
            </button>
            <button
              v-if="row.status === 'ACTIVE' || row.status === 'TEMP_LEAVE'"
              type="button"
              @click="endUse(row)"
            >
              结束
            </button>
            <button v-if="row.status === 'RESERVED'" type="button" @click="cancelReservation(row)">
              取消
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="!mine.length" class="hint">暂无进行中的预约。</p>

    <form class="grid tight" @submit.prevent="changeSeat">
      <h4>改约座位</h4>
      <label>
        预约 ID
        <input v-model="changeForm.reservation_id" required />
      </label>
      <label>
        新座位 ID
        <input v-model="changeForm.seat_id" required />
      </label>
      <button>确认改约</button>
    </form>
  </section>
</template>

<style scoped>
.panel {
  margin: 1rem 0;
  padding: 1rem;
  border: 1px solid #d9e2dc;
  border-radius: 0.75rem;
  display: grid;
  gap: 0.75rem;
}
.row.between {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}
.filters,
.grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: end;
}
.grid.tight {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px dashed #d9e2dc;
}
.filters label,
.grid label {
  display: grid;
  gap: 0.3rem;
  font-size: 0.9rem;
}
.check {
  display: flex !important;
  align-items: center;
  gap: 0.4rem;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem;
}
.card {
  border: 1px solid #e5ece8;
  border-radius: 0.6rem;
  padding: 0.75rem;
  display: grid;
  gap: 0.35rem;
  background: #fbfcfb;
}
.card header {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}
.tag {
  font-size: 0.75rem;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  background: #e7f5ec;
  color: #1f6b3a;
}
.muted,
.hint {
  color: #53635b;
}
.detail {
  display: grid;
  gap: 0.4rem;
}
.detail > div {
  display: grid;
  grid-template-columns: 8rem 1fr;
  gap: 0.5rem;
}
.detail dt {
  color: #53635b;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.warn {
  color: #a15c00;
  font-size: 0.85rem;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  border-bottom: 1px solid #e5ece8;
  padding: 0.45rem 0.35rem;
  text-align: left;
  vertical-align: top;
}
</style>

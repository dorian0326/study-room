<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api/client.js'

const rooms = ref([])
const reservations = ref([])
const roomId = ref('')
const seatId = ref('')
const scope = ref('all')
const error = ref('')
const notice = ref('')

/** 生成浏览器本地日期，作为预约表单的默认日期。 */
function todayForInput() {
  // 直接读取本地年月日，避免 UTC 转换在午夜附近造成日期偏移。
  const current = new Date()
  const year = current.getFullYear()
  const month = String(current.getMonth() + 1).padStart(2, '0')
  const day = String(current.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const booking = reactive({ day: todayForInput(), start: '08:00', end: '09:00' })

/** 读取预约表单当前选择的自习室。 */
function readSelectedRoom() {
  // 使用自习室编号定位，刷新列表后仍保留用户当前选择。
  return rooms.value.find((room) => room.id === Number(roomId.value)) ?? null
}

const selectedRoom = computed(readSelectedRoom)

/** 返回当前预约区间内可供新预约选择的座位。 */
function readAvailableSeats() {
  // 维护中和停用的座位保留在布局中显示，但不允许提交预约。
  const room = selectedRoom.value
  return room ? room.seats.filter((seat) => seat.status === 'available') : []
}

const availableSeats = computed(readAvailableSeats)

/** 加载开放自习室及座位属性，供预约表单选择。 */
async function loadRooms() {
  // 提交时后端会重新检查座位冲突与开放时间。
  const params = new URLSearchParams()
  if (booking.day && booking.start && booking.end) {
    params.set('start_time', `${booking.day}T${booking.start}:00+08:00`)
    params.set('end_time', `${booking.day}T${booking.end}:00+08:00`)
  }
  rooms.value = await api(`/rooms${params.size ? `?${params}` : ''}`)
  if (!roomId.value && rooms.value.length) roomId.value = String(rooms.value[0].id)
  if (availableSeats.value.length && !seatId.value) {
    seatId.value = String(availableSeats.value[0].id)
  }
}

/** 加载当前登录用户的当前预约或历史预约。 */
async function loadReservations() {
  // 接口会按当前登录账号过滤预约记录。
  reservations.value = await api(`/reservations?scope=${scope.value}`)
}

/** 加载预约资源和历史记录，并在页面显示错误信息。 */
async function loadWorkspace() {
  error.value = ''
  try {
    await Promise.all([loadRooms(), loadReservations()])
  } catch (cause) {
    error.value = cause.message
  }
}

/** 按 README 的 Asia/Shanghai 时间约定创建预约。 */
async function createBooking() {
  error.value = ''
  notice.value = ''
  try {
    await api('/reservations', {
      method: 'POST',
      body: {
        seat_id: Number(seatId.value),
        start_time: `${booking.day}T${booking.start}:00+08:00`,
        end_time: `${booking.day}T${booking.end}:00+08:00`,
        request_key: crypto.randomUUID(),
      },
    })
    notice.value = '预约已提交，结果和签到提醒会发送到站内通知。'
    await Promise.all([loadRooms(), loadReservations()])
  } catch (cause) {
    error.value = cause.message
  }
}

/** 将预约状态转换为页面展示的中文名称。 */
function reservationStatus(value) {
  // 保留所有服务端状态名称，方便用户查看取消和超时记录。
  const labels = {
    RESERVED: '已预约',
    ACTIVE: '使用中',
    TEMP_LEAVE: '临时离开',
    COMPLETED: '已结束',
    CANCELLED: '已取消',
    ADMIN_CANCELLED: '管理员取消',
    EXPIRED: '未签到释放',
    TIMED_OUT: '超时释放',
  }
  return labels[value] ?? value
}

/** 将接口时间转换为浏览器本地显示格式。 */
function formatTime(value) {
  // ISO 时间包含服务端 UTC+8 时区偏移，由 Date 转换后展示。
  return value ? new Date(value).toLocaleString('zh-CN') : '—'
}

/** 执行预约操作，并在服务端响应后刷新预约状态。 */
async function operate(action, reservation) {
  error.value = ''
  notice.value = ''
  if (action === 'end' && !window.confirm('确认结束本次连续使用？后续紧接的预约也会释放。')) return
  if (action === 'cancel' && !window.confirm('确认取消这条预约？')) return
  const paths = {
    checkin: `/reservations/${reservation.id}/check-in`,
    leave: `/reservations/${reservation.id}/temporary-leave`,
    return: `/reservations/${reservation.id}/return`,
    end: `/reservations/${reservation.id}/end`,
    cancel: `/reservations/${reservation.id}/cancel`,
  }
  try {
    const body = action === 'end' ? { confirm: true } : undefined
    await api(paths[action], { method: 'POST', body })
    notice.value = '操作已完成。'
    await Promise.all([loadReservations(), loadRooms()])
  } catch (cause) {
    error.value = cause.message
  }
}

onMounted(loadWorkspace)
</script>

<template>
  <h2>预约与使用</h2>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>

  <section class="panel">
    <h3>新建预约</h3>
    <form class="booking-form" @submit.prevent="createBooking">
      <label>
        自习室
        <select v-model="roomId" @change="seatId = String(availableSeats[0]?.id ?? '')">
          <option v-for="room in rooms" :key="room.id" :value="String(room.id)">
            {{ room.name }}{{ room.location ? ` · ${room.location}` : '' }}
          </option>
        </select>
      </label>
      <label>
        座位
        <select v-model="seatId" required>
          <option v-for="seat in availableSeats" :key="seat.id" :value="String(seat.id)">
            {{ seat.code }} · {{ seat.zone_type }}{{ seat.by_window ? ' · 靠窗' : '' }}{{ seat.has_power ? ' · 有电源' : '' }}
          </option>
        </select>
      </label>
      <label>日期 <input v-model="booking.day" type="date" required @change="loadRooms" /></label>
      <label>开始 <input v-model="booking.start" type="time" step="1800" required @change="loadRooms" /></label>
      <label>结束 <input v-model="booking.end" type="time" step="1800" required @change="loadRooms" /></label>
      <button :disabled="!seatId">确认预约</button>
    </form>
    <p class="hint">预约按 30 分钟粒度提交，系统会校验开放时间和座位冲突。</p>
  </section>

  <section class="panel">
    <div class="section-title">
      <h3>我的预约</h3>
      <select v-model="scope" @change="loadReservations">
        <option value="all">全部记录</option>
        <option value="current">当前与待开始</option>
        <option value="history">历史与已结束</option>
      </select>
    </div>
    <p v-if="!reservations.length">暂无预约记录。</p>
    <div class="table-scroll">
      <table v-if="reservations.length">
        <thead>
          <tr><th>预约号</th><th>自习室 / 座位</th><th>开始 – 结束</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="reservation in reservations" :key="reservation.id">
            <td>{{ reservation.reservation_no }}</td>
            <td>{{ reservation.room_name }} / {{ reservation.seat_code }}</td>
            <td>{{ formatTime(reservation.start_time) }}<br />{{ formatTime(reservation.end_time) }}</td>
            <td>{{ reservationStatus(reservation.status) }}</td>
            <td class="actions">
              <button v-if="reservation.status === 'RESERVED'" @click="operate('checkin', reservation)">签到</button>
              <button v-if="reservation.status === 'RESERVED'" @click="operate('cancel', reservation)">取消</button>
              <button v-if="reservation.status === 'ACTIVE'" @click="operate('leave', reservation)">临时离开</button>
              <button v-if="reservation.status === 'TEMP_LEAVE'" @click="operate('return', reservation)">我已返回</button>
              <button v-if="['ACTIVE', 'TEMP_LEAVE'].includes(reservation.status)" @click="operate('end', reservation)">结束使用</button>
              <span v-if="!['RESERVED', 'ACTIVE', 'TEMP_LEAVE'].includes(reservation.status)">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.panel { margin: 1rem 0; padding: 1rem; border: 1px solid #d9e2dc; border-radius: 0.75rem; }
.booking-form { display: flex; flex-wrap: wrap; align-items: end; gap: 0.75rem; }
.booking-form label { display: grid; gap: 0.3rem; }
.section-title { display: flex; align-items: center; justify-content: space-between; }
.table-scroll { overflow-x: auto; }
.actions { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.hint { color: #53635b; }
</style>

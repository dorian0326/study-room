<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api/client.js'
import { confirmDialog } from '../confirm.js'

const rooms = ref([])
const seats = ref([])
const roomId = ref('')
const error = ref('')
const notice = ref('')
const csvText = ref(
  'code,zone_type,has_power,by_window,accessible,status\nA01,quiet,true,false,false,available',
)
const seatForm = reactive({
  id: null,
  code: '',
  zone_type: 'quiet',
  has_power: false,
  by_window: false,
  accessible: false,
  status: 'available',
})

/** 加载管理员可维护的自习室，并默认选中第一个房间。 */
async function loadRooms() {
  // 每个自习室管理请求都会由后端重新校验权限。
  rooms.value = await api('/admin/rooms')
  if (!roomId.value && rooms.value.length) roomId.value = String(rooms.value[0].id)
}

/** 加载所选自习室的座位布局和已保存属性。 */
async function loadSeats() {
  // 编辑器限定在一个自习室中，避免不同房间的座位编号产生歧义。
  seats.value = roomId.value ? await api(`/admin/rooms/${roomId.value}/seats`) : []
}

/** 刷新自习室和座位列表，并向管理员显示后端错误。 */
async function refresh() {
  error.value = ''
  try {
    await loadRooms()
    await loadSeats()
  } catch (cause) {
    error.value = cause.message
  }
}

/** 将已保存的座位属性载入编辑表单。 */
function editSeat(seat) {
  // 数据库编号单独保存，提交时据此选择新增或更新接口。
  Object.assign(seatForm, seat)
}

/** 保存一个座位并重新加载当前房间的布局。 */
async function saveSeat() {
  error.value = ''
  notice.value = ''
  try {
    const { id, ...body } = seatForm
    const path = id
      ? `/admin/rooms/${roomId.value}/seats/${id}`
      : `/admin/rooms/${roomId.value}/seats`
    await api(path, { method: id ? 'PUT' : 'POST', body })
    Object.assign(seatForm, {
      id: null,
      code: '',
      zone_type: 'quiet',
      has_power: false,
      by_window: false,
      accessible: false,
      status: 'available',
    })
    notice.value = '座位信息已保存。'
    await loadSeats()
  } catch (cause) {
    error.value = cause.message
  }
}

/** 修改座位状态，并在维护操作前确认预约取消后果。 */
async function changeStatus(seat, status) {
  if (
    status === 'maintenance' &&
    !(await confirmDialog({
      title: `将座位 ${seat.code} 设为维护？`,
      message: '进入维护后，所有未开始预约将被取消且不补偿。',
      confirmText: '设为维护',
      danger: true,
    }))
  )
    return
  error.value = ''
  notice.value = ''
  try {
    const result = await api(`/admin/rooms/${roomId.value}/seats/${seat.id}/status`, {
      method: 'PATCH',
      body: {
        status,
        reason: status === 'maintenance' ? '管理员将座位设为维护中' : '管理员恢复座位状态',
      },
    })
    notice.value =
      status === 'maintenance'
        ? `座位已维护，取消 ${result.cancelled_reservations ?? 0} 条待开始预约。`
        : '座位状态已更新。'
    await loadSeats()
  } catch (cause) {
    error.value = cause.message
  }
}

/** 删除从未产生预约历史的座位。 */
async function deleteSeat(seat) {
  const ok = await confirmDialog({
    title: `删除座位 ${seat.code}？`,
    message: '仅能删除从未产生预约历史的座位，删除后无法恢复。',
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  error.value = ''
  try {
    await api(`/admin/rooms/${roomId.value}/seats/${seat.id}`, { method: 'DELETE' })
    await loadSeats()
  } catch (cause) {
    error.value = cause.message
  }
}

/** 读取本地 CSV 文件到导入编辑器，不会自动上传文件。 */
async function readCsvFile(event) {
  // 管理员明确提交导入前，文件内容只保留在浏览器页面中。
  const file = event.target.files?.[0]
  if (file) csvText.value = await file.text()
}

/** 提交 CSV 座位配置，由后端原子新增或更新座位。 */
async function importCsv() {
  error.value = ''
  notice.value = ''
  try {
    const result = await api(`/admin/rooms/${roomId.value}/seats/import`, {
      method: 'POST',
      body: { content: csvText.value },
    })
    notice.value = `导入完成：新增 ${result.created} 个，更新 ${result.updated} 个。`
    await loadSeats()
  } catch (cause) {
    error.value = cause.message
  }
}

/** 将座位状态转换为管理员表格展示的中文名称。 */
function statusLabel(value) {
  // 维护、永久停用和普通关闭使用不同的状态名称。
  const labels = {
    available: '可用',
    reserved: '已预约',
    in_use: '使用中',
    maintenance: '维护中',
    closed: '已关闭',
    disabled: '已停用',
  }
  return labels[value] ?? value
}

onMounted(refresh)
</script>

<template>
  <header class="page-header">
    <div>
      <h2>座位布局与维护</h2>
    </div>
  </header>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>
  <section class="panel">
    <div class="row between">
      <h3>座位列表</h3>
      <label class="room-pick"
        >自习室
        <select v-model="roomId" @change="loadSeats">
          <option v-for="room in rooms" :key="room.id" :value="String(room.id)">
            {{ room.name }}
          </option>
        </select>
      </label>
    </div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>座位</th>
            <th>区域</th>
            <th>靠窗</th>
            <th>电源</th>
            <th>状态</th>
            <th>维护操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="seat in seats" :key="seat.id">
            <td>{{ seat.code }}</td>
            <td>{{ seat.zone_type }}</td>
            <td>{{ seat.by_window ? '是' : '否' }}</td>
            <td>{{ seat.has_power ? '是' : '否' }}</td>
            <td>{{ statusLabel(seat.status) }}</td>
            <td class="actions">
              <button @click="editSeat(seat)">编辑</button>
              <button
                v-if="seat.status !== 'maintenance'"
                @click="changeStatus(seat, 'maintenance')"
              >
                维护并取消待开始预约
              </button>
              <button v-else @click="changeStatus(seat, 'available')">恢复可用</button>
              <button class="danger" @click="deleteSeat(seat)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <h3>{{ seatForm.id ? '修改座位' : '新增座位' }}</h3>
    <form class="seat-form" @submit.prevent="saveSeat">
      <label>编号 <input v-model="seatForm.code" maxlength="32" required /></label>
      <label
        >区域
        <select v-model="seatForm.zone_type">
          <option value="quiet">静音区</option>
          <option value="discussion">讨论区</option>
          <option value="exam_prep">考研区</option>
        </select></label
      >
      <label><input v-model="seatForm.by_window" type="checkbox" /> 靠窗</label>
      <label><input v-model="seatForm.has_power" type="checkbox" /> 有电源</label>
      <label><input v-model="seatForm.accessible" type="checkbox" /> 无障碍</label>
      <button>保存座位</button>
    </form>
  </section>

  <section class="panel">
    <h3>批量导入座位配置（CSV）</h3>
    <p>
      列名：code, zone_type, has_power, by_window, accessible,
      status；状态变化为维护时会依规则取消未开始预约。
    </p>
    <input type="file" accept=".csv,text/csv" @change="readCsvFile" />
    <textarea v-model="csvText" rows="7" spellcheck="false" />
    <button @click="importCsv">校验并导入</button>
  </section>
</template>

<style scoped>
.room-pick {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
textarea {
  display: block;
  width: min(100%, 760px);
  margin: 0.75rem 0;
  font-family: monospace;
}
</style>

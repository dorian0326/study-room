<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client.js'

const route = useRoute()
const router = useRouter()

const reservations = ref([])
const reservationId = ref('')
const token = ref('')
const error = ref('')
const notice = ref('')
const scanning = ref(false)
const scanSupported = ref(typeof window !== 'undefined' && 'BarcodeDetector' in window)

const video = ref(null)
let stream = null
let detector = null
let scanTimer = null

const reserved = computed(() =>
  reservations.value.filter((row) => row.status === 'RESERVED' || row.status === 'reserved'),
)

/** 加载可签到的本人预约。 */
async function loadReservations() {
  error.value = ''
  try {
    reservations.value = await api('/reservations?scope=current')
    const preferred = Number(route.query.reservation_id || 0)
    if (preferred && reserved.value.some((row) => row.id === preferred)) {
      reservationId.value = String(preferred)
    } else if (!reservationId.value && reserved.value.length) {
      reservationId.value = String(reserved.value[0].id)
    }
  } catch (cause) {
    error.value = cause.message
  }
}

/** 从扫码内容解析座位编号。 */
function parseSeatToken(raw) {
  const text = String(raw || '').trim()
  const match = text.match(/studyroom:seat:(\d+)/i)
  if (match) return Number(match[1])
  if (/^\d+$/.test(text)) return Number(text)
  return null
}

/** 提交签到；有座位令牌时按扫码校验，否则走手动签到。 */
async function submitCheckIn(rawToken = token.value) {
  error.value = ''
  notice.value = ''
  if (!reservationId.value) {
    error.value = '请先选择要签到的预约'
    return
  }
  const seatId = parseSeatToken(rawToken)
  const body = seatId ? { seat_id: seatId } : undefined
  if (rawToken && !seatId) {
    error.value = '无法识别座位二维码，请使用 studyroom:seat:<编号> 或座位 ID'
    return
  }
  try {
    await api(`/reservations/${reservationId.value}/check-in`, { method: 'POST', body })
    notice.value = seatId ? '扫码签到成功。' : '签到成功。'
    await loadReservations()
  } catch (cause) {
    error.value = cause.message
  }
}

/** 启动摄像头并用 BarcodeDetector 识别桌上二维码。 */
async function startScan() {
  error.value = ''
  notice.value = ''
  if (!scanSupported.value) {
    error.value = '当前浏览器不支持摄像头扫码，请改用手输座位令牌。'
    return
  }
  try {
    detector = new window.BarcodeDetector({ formats: ['qr_code'] })
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    })
    scanning.value = true
    await new Promise((resolve) => requestAnimationFrame(resolve))
    if (video.value) {
      video.value.srcObject = stream
      await video.value.play()
    }
    scanTimer = window.setInterval(async () => {
      if (!video.value || !detector) return
      try {
        const codes = await detector.detect(video.value)
        if (codes.length) {
          token.value = codes[0].rawValue
          await stopScan()
          await submitCheckIn(codes[0].rawValue)
        }
      } catch {
        // 个别帧识别失败时忽略，继续下一轮。
      }
    }, 500)
  } catch (cause) {
    scanning.value = false
    error.value = cause.message || '无法打开摄像头，请检查权限或改用手输。'
  }
}

/** 关闭摄像头与扫码循环。 */
async function stopScan() {
  if (scanTimer) {
    clearInterval(scanTimer)
    scanTimer = null
  }
  if (stream) {
    stream.getTracks().forEach((track) => track.stop())
    stream = null
  }
  detector = null
  scanning.value = false
}

onMounted(loadReservations)
onBeforeUnmount(stopScan)
</script>

<template>
  <h2>扫码签到</h2>
  <p class="hint">对准桌上二维码，或粘贴 <code>studyroom:seat:&lt;座位ID&gt;</code>。不刷脸。</p>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>

  <section class="panel">
    <label>
      选择预约
      <select v-model="reservationId">
        <option disabled value="">请选择</option>
        <option v-for="row in reserved" :key="row.id" :value="String(row.id)">
          {{ row.reservation_no }} · {{ row.room_name }} / {{ row.seat_code }} ·
          {{ new Date(row.start_time).toLocaleString('zh-CN') }}
        </option>
      </select>
    </label>
    <p v-if="!reserved.length" class="hint">当前没有待签到的预约。</p>
  </section>

  <section class="panel">
    <h3>摄像头扫码</h3>
    <div class="scan-actions">
      <button
        v-if="!scanning"
        type="button"
        class="primary"
        :disabled="!reservationId"
        @click="startScan"
      >
        打开摄像头
      </button>
      <button v-else type="button" @click="stopScan">关闭摄像头</button>
      <button type="button" @click="router.push('/workflows')">返回预约台</button>
    </div>
    <video v-show="scanning" ref="video" class="preview" playsinline muted></video>
    <p v-if="!scanSupported" class="hint">本浏览器没有 BarcodeDetector，请使用下方手输。</p>
  </section>

  <section class="panel">
    <h3>手动输入座位令牌</h3>
    <form class="manual" @submit.prevent="submitCheckIn()">
      <input
        v-model="token"
        placeholder="studyroom:seat:12 或 12"
        autocomplete="off"
        spellcheck="false"
      />
      <button class="primary" :disabled="!reservationId">签到</button>
      <button type="button" :disabled="!reservationId" @click="submitCheckIn('')">
        无码手动签到
      </button>
    </form>
  </section>
</template>

<style scoped>
.scan-actions,
.manual {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.manual input {
  min-width: 16rem;
  flex: 1;
}
.preview {
  width: min(100%, 420px);
  border-radius: 0.5rem;
  background: #111;
}
</style>

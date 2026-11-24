<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client.js'
import NlLoading from '../components/NlLoading.vue'
import EmptyState from '../components/EmptyState.vue'

const route = useRoute()
const router = useRouter()

const reservations = ref([])
const reservationId = ref('')
const token = ref('')
const error = ref('')
const notice = ref('')
const loading = ref(true)
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
  } finally {
    loading.value = false
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
    error.value = '无法识别这个二维码，请对准座位上的码，或改输入座位编号。'
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
    error.value = '当前浏览器不支持摄像头扫码，请改用下方输入座位编号。'
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
    error.value = cause.message || '无法打开摄像头，请检查权限或改用手输座位编号。'
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
  <p class="hint">对准座位上的二维码即可签到；也可以在下方输入座位编号。</p>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>

  <NlLoading v-if="loading" />

  <template v-else>
    <EmptyState
      v-if="!reserved.length"
      title="当前没有待签到的预约"
      action-to="/workflows"
      action-text="去预约一个座位"
    />

    <template v-else>
      <section class="panel">
        <label>
          选择预约
          <select v-model="reservationId">
            <option disabled value="">请选择</option>
            <option v-for="row in reserved" :key="row.id" :value="String(row.id)">
              {{ row.reservation_no }} / {{ row.room_name }} / {{ row.seat_code }} /
              {{ new Date(row.start_time).toLocaleString('zh-CN') }}
            </option>
          </select>
        </label>
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
        <div v-show="scanning" class="scan-frame">
          <video ref="video" class="preview" playsinline muted></video>
          <span class="scan-hint">将二维码置于框内</span>
        </div>
        <p v-if="!scanSupported" class="hint">这台浏览器暂时不能扫码，请改用下方输入座位编号。</p>
      </section>

      <section class="panel">
        <h3>输入座位编号</h3>
        <form class="manual" @submit.prevent="submitCheckIn()">
          <input
            v-model="token"
            placeholder="例如 12，或粘贴座位码"
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
  </template>
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
.scan-frame {
  width: min(100%, 420px);
  margin-top: 8px;
  padding: 10px;
  border: 2px solid var(--brand);
  border-radius: 16px;
  background: var(--bg-elevated);
  display: grid;
  gap: 8px;
  justify-items: center;
}
.preview {
  width: 100%;
  aspect-ratio: 3 / 4;
  max-height: 360px;
  object-fit: cover;
  border-radius: 12px;
  background: #111;
}
.scan-hint {
  color: var(--muted);
  font-size: 0.86rem;
}
</style>

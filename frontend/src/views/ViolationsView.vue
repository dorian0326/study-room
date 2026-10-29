<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client.js'

const violations = ref([])
const appeals = ref([])
const error = ref('')
const notice = ref('')
const manual = ref({ record_type: 'entry', reason: '', reservation_id: '' })

/** 加载本人违规记录和以往的申诉审核结果。 */
async function loadCases() {
  // 两类数据都会由后端限制为当前登录用户本人。
  error.value = ''
  try {
    const [violationRows, appealRows] = await Promise.all([api('/violations'), api('/appeals')])
    violations.value = violationRows
    appeals.value = appealRows
  } catch (cause) {
    error.value = cause.message
  }
}

/** 为选定的违规记录提交申诉，并要求填写理由。 */
async function appealViolation(violation) {
  const reason = window.prompt('请说明申诉理由（至少 5 个字符）')
  if (!reason) return
  error.value = ''
  notice.value = ''
  try {
    await api('/appeals', {
      method: 'POST',
      body: { violation_id: violation.id, reason },
    })
    notice.value = '申诉已提交，审核结果会通过站内通知送达。'
    await loadCases()
  } catch (cause) {
    error.value = cause.message
  }
}

/** 门禁回调不可用时提交入馆或出馆人工核验申请。 */
async function submitGateAppeal() {
  error.value = ''
  notice.value = ''
  try {
    const reservationId = manual.value.reservation_id ? Number(manual.value.reservation_id) : null
    await api('/ops/entry-exit/manual-appeals', {
      method: 'POST',
      body: {
        record_type: manual.value.record_type,
        reason: manual.value.reason,
        reservation_id: reservationId,
      },
    })
    notice.value = '门禁人工核验申请已提交。'
    manual.value.reason = ''
  } catch (cause) {
    error.value = cause.message
  }
}

/** 将违规和申诉状态转换为学生页面使用的中文名称。 */
function stateLabel(value) {
  // 页面区分处理中、已归档、审核中和已完成等状态。
  const labels = {
    active: '待处理',
    archived: '已归档',
    none: '未申诉',
    pending: '申诉审核中',
    approved: '申诉通过',
    rejected: '申诉驳回',
    warning: '警告',
    restricted: '禁约处罚',
  }
  return labels[value] ?? value
}

/** 将时间戳转换为浏览器易读的格式。 */
function formatTime(value) {
  // 服务端时间包含 UTC+8 偏移，由 Date 处理显示转换。
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(loadCases)
</script>

<template>
  <h2>违规与申诉</h2>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>
  <section class="panel">
    <h3>我的违规记录</h3>
    <p v-if="!violations.length">暂无违规记录。</p>
    <table v-if="violations.length">
      <thead>
        <tr>
          <th>时间</th>
          <th>类型</th>
          <th>窗口次数</th>
          <th>处理</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="violation in violations" :key="violation.id">
          <td>{{ formatTime(violation.occurred_at) }}</td>
          <td>{{ violation.violation_type }}</td>
          <td>{{ violation.period_seq }}</td>
          <td>{{ stateLabel(violation.result) }} · {{ stateLabel(violation.appeal_status) }}</td>
          <td>
            <button
              v-if="violation.appeal_status !== 'pending'"
              @click="appealViolation(violation)"
            >
              提交申诉
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
  <section class="panel">
    <h3>申诉进度</h3>
    <ul>
      <li v-for="appeal in appeals" :key="appeal.id">
        记录 #{{ appeal.violation_id }}：{{ stateLabel(appeal.result ?? 'pending')
        }}<span v-if="appeal.review_comment"> — {{ appeal.review_comment }}</span>
      </li>
    </ul>
  </section>
  <section class="panel">
    <h3>门禁不可用时的人工核验</h3>
    <form class="manual-form" @submit.prevent="submitGateAppeal">
      <label
        >类型
        <select v-model="manual.record_type">
          <option value="entry">入馆</option>
          <option value="exit">出馆</option>
        </select></label
      >
      <label
        >关联预约编号（可选）<input v-model="manual.reservation_id" type="number" min="1"
      /></label>
      <label
        >情况说明 <textarea v-model="manual.reason" required minlength="5" maxlength="4000" />
      </label>
      <button>提交人工核验</button>
    </form>
  </section>
</template>

<style scoped>
.manual-form {
  display: grid;
  gap: 0.75rem;
  max-width: 640px;
}
textarea {
  min-height: 6rem;
}
</style>

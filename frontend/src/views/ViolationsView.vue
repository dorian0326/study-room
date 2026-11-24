<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client.js'
import { promptDialog } from '../confirm.js'
import { violationTypeLabel } from '../labels.js'
import NlLoading from '../components/NlLoading.vue'
import EmptyState from '../components/EmptyState.vue'

const violations = ref([])
const appeals = ref([])
const error = ref('')
const notice = ref('')
const loading = ref(true)
const manual = ref({ record_type: 'entry', reason: '', reservation_id: '' })

/** 加载本人违规记录和以往的申诉审核结果。 */
async function loadCases() {
  error.value = ''
  try {
    const [violationRows, appealRows] = await Promise.all([api('/violations'), api('/appeals')])
    violations.value = violationRows
    appeals.value = appealRows
  } catch (cause) {
    error.value = cause.message
  } finally {
    loading.value = false
  }
}

/** 为选定的违规记录提交申诉，并要求填写理由。 */
async function appealViolation(violation) {
  const reason = await promptDialog({
    title: '提交申诉',
    message: '请说明申诉理由（至少 5 个字符）。',
    placeholder: '例如：当时已在座位上，签到设备故障',
  })
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

function formatTime(value) {
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(loadCases)
</script>

<template>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>
  <NlLoading v-if="loading" />
  <template v-else>
    <section class="panel">
      <h3>我的违规记录</h3>
      <EmptyState v-if="!violations.length" title="暂无违规记录，继续保持就好。" />
      <div v-else class="table-scroll desk-table">
        <table>
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
              <td>{{ violationTypeLabel(violation.violation_type) }}</td>
              <td>{{ violation.period_seq }}</td>
              <td>
                {{ stateLabel(violation.result) }} / {{ stateLabel(violation.appeal_status) }}
              </td>
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
      </div>
      <div v-if="violations.length" class="rec-cards">
        <article v-for="violation in violations" :key="violation.id" class="rec-card">
          <header>
            <strong>{{ violationTypeLabel(violation.violation_type) }}</strong>
            <span class="muted">第 {{ violation.period_seq }} 次</span>
          </header>
          <p class="when">{{ formatTime(violation.occurred_at) }}</p>
          <p>{{ stateLabel(violation.result) }} / {{ stateLabel(violation.appeal_status) }}</p>
          <div class="actions">
            <button
              v-if="violation.appeal_status !== 'pending'"
              type="button"
              @click="appealViolation(violation)"
            >
              提交申诉
            </button>
          </div>
        </article>
      </div>
    </section>
    <section class="panel">
      <h3>申诉进度</h3>
      <EmptyState v-if="!appeals.length" title="还没有提交过申诉。" />
      <ul v-else class="appeal-list">
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
.appeal-list {
  margin: 0;
  padding-left: 1.2rem;
  display: grid;
  gap: 8px;
}
.rec-cards {
  display: none;
}
.rec-card {
  display: grid;
  gap: 6px;
  padding: 14px 16px 14px 20px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--bg-muted);
  box-shadow: inset 4px 0 0 var(--danger);
}
.rec-card header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.when {
  font-variant-numeric: tabular-nums;
}
@media (max-width: 700px) {
  .desk-table {
    display: none;
  }
  .rec-cards {
    display: grid;
    gap: 10px;
    margin: 0;
    border-top: none;
  }
}
</style>

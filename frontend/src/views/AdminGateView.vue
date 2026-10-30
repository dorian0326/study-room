<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client.js'

const error = ref('')
const notice = ref('')
const rows = ref([])
const syncStatus = ref('')
const mock = ref({
  external_id: '',
  masked_user_key: '',
  record_type: 'entry',
  recorded_at: '',
})

function fmt(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
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

async function load() {
  const params = new URLSearchParams({ limit: '200' })
  if (syncStatus.value) params.set('sync_status', syncStatus.value)
  rows.value = await api(`/ops/entry-exit/records?${params}`)
}

function refresh() {
  return guard(load)
}

function submitMock() {
  return guard(async () => {
    const body = {
      external_id: mock.value.external_id.trim(),
      masked_user_key: mock.value.masked_user_key.trim(),
      record_type: mock.value.record_type,
      recorded_at: mock.value.recorded_at
        ? `${mock.value.recorded_at}:00+08:00`.replace(/:00:00\+/, ':00+')
        : new Date().toISOString(),
    }
    await api('/ops/entry-exit/mock', { method: 'POST', body })
    mock.value.external_id = ''
    await load()
  }, '已写入模拟门禁事件')
}

onMounted(refresh)
const SYNC = {
  matched: ['已匹配', 'ok'],
  synced: ['已同步', 'ok'],
  pending: ['待处理', 'warn'],
  late: ['延迟到达', 'info'],
  unmatched: ['未匹配', 'warn'],
  manual_review: ['人工核验', 'danger'],
  delayed: ['延迟', 'info'],
}
</script>

<template>
  <h2>入馆 / 出馆记录</h2>
  <p class="hint">
    查看脱敏后的门禁同步记录（US-014）。当前为模拟接入，无真实闸机轮询；详见文档限制说明。
  </p>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>

  <section class="panel">
    <form class="filters" @submit.prevent="refresh">
      <label>
        同步状态
        <select v-model="syncStatus">
          <option value="">全部</option>
          <option value="matched">已匹配</option>
          <option value="unmatched">未匹配</option>
          <option value="manual_review">人工核验</option>
          <option value="delayed">延迟</option>
        </select>
      </label>
      <div class="btns">
        <button class="primary">查询</button>
        <button type="button" @click="refresh">刷新</button>
      </div>
    </form>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>来源</th>
            <th>类型</th>
            <th>脱敏键</th>
            <th>记录时间</th>
            <th>接收时间</th>
            <th>状态</th>
            <th>延迟(s)</th>
            <th>预约</th>
            <th>备注</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ row.id }}</td>
            <td>{{ row.source_system }}</td>
            <td>
              <span class="badge" :class="row.record_type === 'entry' ? 'tone-brand' : 'tone-info'">
                {{ row.record_type === 'entry' ? '入馆' : '出馆' }}
              </span>
            </td>
            <td>
              <code :title="row.masked_user_key">{{ row.masked_user_key }}</code>
            </td>
            <td>{{ fmt(row.recorded_at) }}</td>
            <td>{{ fmt(row.received_at) }}</td>
            <td>
              <span class="badge" :class="`tone-${(SYNC[row.sync_status] || [0, 'neutral'])[1]}`">
                {{ (SYNC[row.sync_status] || [row.sync_status])[0] }}
              </span>
            </td>
            <td>{{ row.sync_delay_seconds ?? '—' }}</td>
            <td>{{ row.reservation_id ?? '—' }}</td>
            <td>{{ row.manual_note || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="!rows.length" class="hint">暂无记录。</p>
  </section>

  <section class="panel">
    <h3>写入模拟事件</h3>
    <form class="filters" @submit.prevent="submitMock">
      <label>外部 ID <input v-model="mock.external_id" required /></label>
      <label>脱敏用户键 <input v-model="mock.masked_user_key" required /></label>
      <label>
        类型
        <select v-model="mock.record_type">
          <option value="entry">入馆</option>
          <option value="exit">出馆</option>
        </select>
      </label>
      <label>记录时间 <input v-model="mock.recorded_at" type="datetime-local" /></label>
      <div class="btns"><button class="primary">提交</button></div>
    </form>
  </section>
</template>

<style scoped>
.btns {
  display: flex;
  gap: 8px;
  align-items: center;
}
code {
  display: inline-block;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
  font-size: 0.82rem;
}
td {
  white-space: nowrap;
}
</style>

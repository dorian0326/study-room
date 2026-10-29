<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client.js'
import { can } from '../auth.js'

const error = ref('')
const notice = ref('')
const status = ref(null)
const backups = ref([])
const busy = ref(false)

function fmtBytes(n) {
  if (n == null) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`
  return `${(n / 1024 ** 3).toFixed(2)} GB`
}

function fmtTs(ts) {
  if (!ts) return '—'
  const ms = ts > 1e12 ? ts : ts * 1000
  return new Date(ms).toLocaleString('zh-CN', { hour12: false })
}

function fmtUptime(sec) {
  if (sec == null) return '—'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return `${h} 小时 ${m} 分钟`
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

async function loadStatus() {
  if (!can('system_log:read')) return
  status.value = await api('/ops/status')
}

async function loadBackups() {
  if (!can('system:backup')) return
  backups.value = await api('/ops/backups')
}

function refresh() {
  return guard(async () => {
    await loadStatus()
    await loadBackups()
  })
}

function runBackup() {
  return guard(async () => {
    busy.value = true
    try {
      await api('/ops/backups', { method: 'POST' })
      await loadBackups()
      await loadStatus()
    } finally {
      busy.value = false
    }
  }, '备份已创建')
}

onMounted(refresh)
</script>

<template>
  <h2>备份与监控</h2>
  <p class="hint">
    查看运行状态、数据库体积与备份列表（#9）。定时备份可用环境变量开启，CLI 仍可用。
  </p>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>

  <div class="row">
    <button type="button" @click="refresh">刷新</button>
    <button
      v-if="can('system:backup')"
      class="primary"
      type="button"
      :disabled="busy"
      @click="runBackup"
    >
      {{ busy ? '备份中…' : '立即备份' }}
    </button>
  </div>

  <section v-if="status" class="panel">
    <h3>运行状态</h3>
    <dl class="detail">
      <div>
        <dt>运行时长</dt>
        <dd>{{ fmtUptime(status.uptime_seconds) }}</dd>
      </div>
      <div>
        <dt>用户数</dt>
        <dd>{{ status.users }}</dd>
      </div>
      <div>
        <dt>活跃会话</dt>
        <dd>{{ status.active_sessions }}</dd>
      </div>
      <div>
        <dt>数据库</dt>
        <dd>{{ fmtBytes(status.database?.size_bytes) }}</dd>
      </div>
      <div>
        <dt>WAL</dt>
        <dd>{{ fmtBytes(status.database?.wal_bytes) }}</dd>
      </div>
      <div>
        <dt>最近备份</dt>
        <dd>
          <template v-if="status.latest_backup">
            {{ status.latest_backup.name }} · {{ fmtBytes(status.latest_backup.size_bytes) }} ·
            {{ fmtTs(status.latest_backup.created_at) }}
          </template>
          <template v-else>暂无</template>
        </dd>
      </div>
      <div v-if="status.requests">
        <dt>请求计数</dt>
        <dd>
          <code>{{ JSON.stringify(status.requests) }}</code>
        </dd>
      </div>
    </dl>
  </section>

  <section v-if="can('system:backup')" class="panel">
    <h3>备份列表</h3>
    <table>
      <thead>
        <tr>
          <th>文件名</th>
          <th>大小</th>
          <th>创建时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in backups" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ fmtBytes(row.size_bytes) }}</td>
          <td>{{ fmtTs(row.created_at) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!backups.length" class="hint">还没有备份文件。</p>
  </section>
</template>

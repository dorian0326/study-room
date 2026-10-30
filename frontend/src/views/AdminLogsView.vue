<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api/client.js'
import { can } from '../auth.js'

const tab = ref(can('audit_log:read') ? 'audit' : 'login')
const error = ref('')
const notice = ref('')
const audit = reactive({
  total: 0,
  items: [],
  page_no: 1,
  operator: '',
  op_type: '',
  target_type: '',
})
const login = reactive({ total: 0, items: [], page_no: 1, student_no: '', event: '', success: '' })
const size = 50

const OP_TYPES = {
  admin_action: ['管理操作', 'brand'],
  violation: ['违规认定', 'warn'],
  permission_change: ['权限变更', 'info'],
  login: ['登录', 'ok'],
  logout: ['登出', 'neutral'],
}
const RESULTS = {
  success: ['成功', 'ok'],
  failure: ['失败', 'danger'],
  failed: ['失败', 'danger'],
  denied: ['拒绝', 'danger'],
  error: ['错误', 'danger'],
}
const EVENTS = { login: ['登录', 'brand'], logout: ['登出', 'neutral'] }
const REASONS = {
  invalid_credentials: '学号或密码错误',
  invalid_student_no: '学号不存在',
  disabled: '账号已停用',
  locked: '失败次数过多已锁定',
}
const TARGETS = {
  user: '用户',
  room: '自习室',
  seat: '座位',
  reservation: '预约',
  violation: '违规',
  violation_record: '违规记录',
  user_role: '用户角色',
  room_hours: '开放时段',
  system_setting: '系统参数',
  appeal: '申诉',
  setting: '参数',
  settings: '参数',
  system: '系统',
  backup: '备份',
}

/** 枚举值 → [中文, 徽标色]；未知值原样显示。 */
function label(map, value) {
  return map[value] || [value || '—', 'neutral']
}

function fmt(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

async function guard(fn) {
  error.value = ''
  notice.value = ''
  try {
    await fn()
  } catch (cause) {
    error.value = cause.message
  }
}

async function loadAudit() {
  const params = new URLSearchParams({ page_no: String(audit.page_no), size: String(size) })
  if (audit.operator.trim()) params.set('operator', audit.operator.trim())
  if (audit.op_type) params.set('op_type', audit.op_type)
  if (audit.target_type.trim()) params.set('target_type', audit.target_type.trim())
  const data = await api(`/ops/audit-logs?${params}`)
  audit.total = data.total
  audit.items = data.items
}

async function loadLogin() {
  const params = new URLSearchParams({ page_no: String(login.page_no), size: String(size) })
  if (login.student_no.trim()) params.set('student_no', login.student_no.trim())
  if (login.event) params.set('event', login.event)
  if (login.success !== '') params.set('success', login.success)
  const data = await api(`/ops/login-logs?${params}`)
  login.total = data.total
  login.items = data.items
}

function refresh() {
  return guard(async () => {
    if (tab.value === 'audit') await loadAudit()
    else await loadLogin()
  })
}

function showAudit() {
  tab.value = 'audit'
  return refresh()
}

function showLogin() {
  tab.value = 'login'
  return refresh()
}

function searchAudit() {
  audit.page_no = 1
  return refresh()
}

function searchLogin() {
  login.page_no = 1
  return refresh()
}

function prevAudit() {
  audit.page_no -= 1
  return refresh()
}

function nextAudit() {
  audit.page_no += 1
  return refresh()
}

function prevLogin() {
  login.page_no -= 1
  return refresh()
}

function nextLogin() {
  login.page_no += 1
  return refresh()
}

onMounted(refresh)
</script>

<template>
  <h2>系统日志</h2>
  <p class="hint">查看操作审计与登录日志（#8）。</p>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>

  <div class="tabs">
    <button
      v-if="can('audit_log:read')"
      type="button"
      :class="{ primary: tab === 'audit' }"
      @click="showAudit"
    >
      操作日志
    </button>
    <button
      v-if="can('system_log:read')"
      type="button"
      :class="{ primary: tab === 'login' }"
      @click="showLogin"
    >
      登录日志
    </button>
  </div>

  <section v-if="tab === 'audit'" class="panel">
    <form class="filters" @submit.prevent="searchAudit">
      <label>操作人学号 <input v-model="audit.operator" /></label>
      <label>
        类型
        <select v-model="audit.op_type">
          <option value="">全部</option>
          <option value="admin_action">管理操作</option>
          <option value="violation">违规认定</option>
          <option value="permission_change">权限变更</option>
        </select>
      </label>
      <label>目标类型 <input v-model="audit.target_type" /></label>
      <button class="primary">查询</button>
    </form>
    <p class="muted">共 {{ audit.total }} 条</p>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>操作人</th>
            <th>类型</th>
            <th>目标</th>
            <th>结果</th>
            <th>IP</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in audit.items" :key="row.id">
            <td>{{ fmt(row.occurred_at) }}</td>
            <td>{{ row.operator_student_no || row.operator_id || '—' }}</td>
            <td>
              <span class="badge" :class="`tone-${label(OP_TYPES, row.op_type)[1]}`">
                {{ label(OP_TYPES, row.op_type)[0] }}
              </span>
            </td>
            <td>
              {{ TARGETS[row.target_type] || row.target_type || '—' }}
              <span v-if="row.target_id" class="muted">#{{ row.target_id }}</span>
            </td>
            <td>
              <span class="badge" :class="`tone-${label(RESULTS, row.result)[1]}`">
                {{ label(RESULTS, row.result)[0] }}
              </span>
            </td>
            <td>{{ row.ip_address || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="pager">
      <button type="button" :disabled="audit.page_no <= 1" @click="prevAudit">上一页</button>
      <span>第 {{ audit.page_no }} 页</span>
      <button type="button" :disabled="audit.page_no * size >= audit.total" @click="nextAudit">
        下一页
      </button>
    </div>
  </section>

  <section v-else class="panel">
    <form class="filters" @submit.prevent="searchLogin">
      <label>学号 <input v-model="login.student_no" /></label>
      <label>
        事件
        <select v-model="login.event">
          <option value="">全部</option>
          <option value="login">登录</option>
          <option value="logout">登出</option>
        </select>
      </label>
      <label>
        结果
        <select v-model="login.success">
          <option value="">全部</option>
          <option value="true">成功</option>
          <option value="false">失败</option>
        </select>
      </label>
      <button class="primary">查询</button>
    </form>
    <p class="muted">共 {{ login.total }} 条</p>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>学号</th>
            <th>事件</th>
            <th>结果</th>
            <th>原因</th>
            <th>IP</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in login.items" :key="row.id">
            <td>{{ fmt(row.occurred_at) }}</td>
            <td>{{ row.student_no }}</td>
            <td>
              <span class="badge" :class="`tone-${label(EVENTS, row.event)[1]}`">
                {{ label(EVENTS, row.event)[0] }}
              </span>
            </td>
            <td>
              <span class="badge" :class="row.success ? 'tone-ok' : 'tone-danger'">
                {{ row.success ? '成功' : '失败' }}
              </span>
            </td>
            <td>{{ REASONS[row.reason] || row.reason || '—' }}</td>
            <td>{{ row.ip_address || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="pager">
      <button type="button" :disabled="login.page_no <= 1" @click="prevLogin">上一页</button>
      <span>第 {{ login.page_no }} 页</span>
      <button type="button" :disabled="login.page_no * size >= login.total" @click="nextLogin">
        下一页
      </button>
    </div>
  </section>
</template>

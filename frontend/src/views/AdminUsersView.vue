<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client.js'

const ROLES = { user: '用户', admin: '管理员', ops: '运维' }
const q = ref('')
const users = ref([])
const total = ref(0)
const error = ref('')
const notice = ref('')

async function load() {
  error.value = ''
  try {
    const data = await api(`/admin/users?q=${encodeURIComponent(q.value)}`)
    users.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.message
  }
}

async function toggleRole(u, role) {
  const roles = u.roles.includes(role) ? u.roles.filter((r) => r !== role) : [...u.roles, role]
  await run(() => api(`/admin/users/${u.id}/roles`, { method: 'PUT', body: { roles } }))
}

async function toggleStatus(u) {
  const status = u.status === 'normal' ? 'disabled' : 'normal'
  await run(() => api(`/admin/users/${u.id}/status`, { method: 'PATCH', body: { status } }))
}

async function resetCode(u) {
  try {
    const r = await api(`/admin/users/${u.id}/reset-code`, { method: 'POST' })
    notice.value = `${u.student_no} 的重置码：${r.reset_code}（${r.expires_in / 60} 分钟内有效，仅显示一次）`
  } catch (e) {
    error.value = e.message
  }
}

async function run(fn) {
  error.value = ''
  try {
    await fn()
    await load()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <h2>用户管理</h2>
  <form @submit.prevent="load">
    <input v-model="q" placeholder="学号或姓名" />
    <button>搜索</button>
    <span>共 {{ total }} 人</span>
  </form>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>
  <table>
    <thead>
      <tr>
        <th>学号</th>
        <th>姓名</th>
        <th>角色</th>
        <th>状态</th>
        <th>操作</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="u in users" :key="u.id">
        <td>{{ u.student_no }}</td>
        <td>{{ u.name }}</td>
        <td>
          <label v-for="(label, role) in ROLES" :key="role">
            <input
              type="checkbox"
              :checked="u.roles.includes(role)"
              @change="toggleRole(u, role)"
            />
            {{ label }}
          </label>
        </td>
        <td>{{ u.status === 'normal' ? '正常' : '禁用' }}</td>
        <td>
          <button @click="toggleStatus(u)">{{ u.status === 'normal' ? '禁用' : '启用' }}</button>
          <button @click="resetCode(u)">签发重置码</button>
        </td>
      </tr>
    </tbody>
  </table>
</template>

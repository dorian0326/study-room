<script setup>
import { reactive, ref } from 'vue'
import { api } from '../api/client.js'

const form = reactive({ student_no: '', reset_code: '', new_password: '' })
const error = ref('')
const done = ref(false)

async function submit() {
  error.value = ''
  try {
    await api('/auth/reset-password', { method: 'POST', body: form })
    done.value = true
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <h2>重置密码</h2>
  <p>请联系管理员核验身份并获取一次性重置码。</p>
  <form class="card" @submit.prevent="submit">
    <input v-model="form.student_no" placeholder="学号" required />
    <input v-model="form.reset_code" placeholder="重置码" required />
    <input v-model="form.new_password" type="password" placeholder="新密码" required />
    <button>重置</button>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="done" class="ok">密码已重置，请<RouterLink to="/login">重新登录</RouterLink>。</p>
  </form>
</template>

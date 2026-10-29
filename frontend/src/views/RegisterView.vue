<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client.js'
import { login } from '../auth.js'

const router = useRouter()
const form = reactive({ student_no: '', name: '', password: '', department: '', contact: '' })
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await api('/auth/register', {
      method: 'POST',
      body: { ...form, department: form.department || null, contact: form.contact || null },
    })
    await login(form.student_no, form.password)
    router.push('/')
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <h2>注册</h2>
  <form class="card" @submit.prevent="submit">
    <input v-model="form.student_no" placeholder="学号" required />
    <input v-model="form.name" placeholder="姓名" required />
    <input
      v-model="form.password"
      type="password"
      placeholder="密码（至少 8 位，含字母和数字）"
      autocomplete="new-password"
      required
    />
    <input v-model="form.department" placeholder="院系（可选）" />
    <input v-model="form.contact" placeholder="联系方式（可选）" />
    <button>注册</button>
    <p v-if="error" class="error">{{ error }}</p>
  </form>
</template>

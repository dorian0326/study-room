<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '../auth.js'

const route = useRoute()
const router = useRouter()
const studentNo = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await login(studentNo.value, password.value)
    router.push(route.query.next || '/')
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <h2>登录</h2>
  <form class="card" @submit.prevent="submit">
    <input v-model="studentNo" placeholder="学号" autocomplete="username" required />
    <input
      v-model="password"
      type="password"
      placeholder="密码"
      autocomplete="current-password"
      required
    />
    <button :disabled="busy">登录</button>
    <p v-if="error" class="error">{{ error }}</p>
  </form>
  <p>
    没有账号？<RouterLink to="/register">注册</RouterLink>；忘记密码？<RouterLink
      to="/reset-password"
      >用重置码重置</RouterLink
    >
  </p>
</template>

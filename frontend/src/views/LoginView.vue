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
  <div class="auth-wrap">
    <section class="auth-card">
      <header>
        <h2>欢迎回来</h2>
        <p class="hint">登录奶龙自习室，预约你的专属座位</p>
      </header>
      <form @submit.prevent="submit">
        <label class="field">
          学号
          <input v-model="studentNo" placeholder="请输入学号" autocomplete="username" required />
        </label>
        <label class="field">
          密码
          <input
            v-model="password"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
            required
          />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <button class="primary" :class="{ loading: busy }" :disabled="busy">登录</button>
      </form>
      <footer>
        没有账号？<RouterLink to="/register">立即注册</RouterLink>
        <span class="sep">·</span>
        <RouterLink to="/reset-password">忘记密码</RouterLink>
      </footer>
    </section>
  </div>
</template>

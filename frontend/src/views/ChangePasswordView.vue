<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, setToken } from '../api/client.js'
import { auth } from '../auth.js'

const router = useRouter()
const oldPassword = ref('')
const newPassword = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await api('/auth/change-password', {
      method: 'POST',
      body: { old_password: oldPassword.value, new_password: newPassword.value },
    })
    // 改密后所有会话失效，需重新登录
    setToken(null)
    auth.user = null
    router.push('/login')
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="auth-wrap">
    <section class="auth-card">
      <header>
        <h2>修改密码</h2>
        <p class="hint">修改后需要重新登录</p>
      </header>
      <form @submit.prevent="submit">
        <label class="field">
          原密码
          <input v-model="oldPassword" type="password" placeholder="原密码" required />
        </label>
        <label class="field">
          新密码
          <input v-model="newPassword" type="password" placeholder="新密码" required />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <button class="primary">确认修改</button>
      </form>
    </section>
  </div>
</template>

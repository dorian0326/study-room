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
  <div class="auth-wrap">
    <section class="auth-card">
      <header>
        <h2>重置密码</h2>
        <p class="hint">请联系管理员核验身份并获取一次性重置码。</p>
      </header>
      <form @submit.prevent="submit">
        <label class="field">
          学号
          <input v-model="form.student_no" placeholder="学号" required />
        </label>
        <label class="field">
          重置码
          <input v-model="form.reset_code" placeholder="管理员提供的重置码" required />
        </label>
        <label class="field">
          新密码
          <input v-model="form.new_password" type="password" placeholder="新密码" required />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="done" class="ok">密码已重置，请<RouterLink to="/login">重新登录</RouterLink>。</p>
        <button class="primary">重置密码</button>
      </form>
      <footer><RouterLink to="/login">返回登录</RouterLink></footer>
    </section>
  </div>
</template>

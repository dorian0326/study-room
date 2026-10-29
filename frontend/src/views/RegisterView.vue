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
  <div class="auth-wrap">
    <section class="auth-card">
      <header>
        <h2>注册账号</h2>
        <p class="hint">使用学号注册，注册后即可预约座位</p>
      </header>
      <form @submit.prevent="submit">
        <label class="field">
          学号
          <input v-model="form.student_no" placeholder="学号" required />
        </label>
        <label class="field">
          姓名
          <input v-model="form.name" placeholder="姓名" required />
        </label>
        <label class="field">
          密码
          <input
            v-model="form.password"
            type="password"
            placeholder="至少 8 位，含字母和数字"
            autocomplete="new-password"
            required
          />
        </label>
        <label class="field">
          院系（可选）
          <input v-model="form.department" placeholder="院系" />
        </label>
        <label class="field">
          联系方式（可选）
          <input v-model="form.contact" placeholder="手机或邮箱" />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <button class="primary">注册</button>
      </form>
      <footer>已有账号？<RouterLink to="/login">去登录</RouterLink></footer>
    </section>
  </div>
</template>
